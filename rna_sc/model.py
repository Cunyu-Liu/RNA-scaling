"""ALiBi MLM Transformer encoder for RNA (SPEC 7.3 five mandatory designs).

Design points (frozen):
  - single-nucleotide ACGU tokenizer (+[MASK]/[CLS]/[PAD] specials);
  - MLM objective: 15% selection (80/10/10), no dynamic masking across epochs
    is used so exposure accounting stays deterministic in nt;
  - ALiBi relative positions (BEACON finding; learnable absolute pos is banned);
  - bidirectional encoder (DNA/RNA-FM/RiNALMo all use MLM encoders);
  - checkpoints every CKPT_NT valid-nt interval (pretraining-time axis, S6).
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

VOCAB = 4            # A C G U
PAD, MASK, CLS = 4, 5, 6
VOCAB_TOTAL = 7
IGNORE = -100
CONTEXT_NT = 1024


def alibi_slopes(n_heads: int) -> torch.Tensor:
    """Standard ALiBi slopes (Press et al. 2021) for n_heads."""
    def slope(i: int) -> float:
        return math.pow(2.0, -8.0 * (i + 1) / n_heads) if n_heads <= 16 else \
            math.pow(2.0, -8.0 * (i + 1) * math.sqrt(2.0 / 3.0) / n_heads)
    return torch.tensor([slope(i) for i in range(n_heads)], dtype=torch.float32)


class MLMSelfAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.out = nn.Linear(d_model, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.register_buffer("slopes", alibi_slopes(n_heads).view(1, n_heads, 1, 1),
                             persistent=False)

    def forward(self, x, key_padding_mask):
        # x: (B, T, C); key_padding_mask: (B, T) True at PAD positions.
        B, T, C = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)

        def _r(t):
            return t.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        q, k, v = _r(q), _r(k), _r(v)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        pos = torch.arange(T, device=x.device, dtype=att.dtype)
        dist = (pos.view(1, -1) - pos.view(-1, 1)).abs().clamp(min=1)
        att = att - self.slopes.to(att.dtype) * dist.view(1, 1, T, T)
        if key_padding_mask is not None:
            pad = key_padding_mask.view(B, 1, 1, T)
            att = att.masked_fill(pad, float("-inf"))
        att = F.softmax(att, dim=-1)
        att = self.dropout(att)
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.out(y)


class MLMSelfAttentionSDPA(nn.Module):
    """Memory-efficient attention via SDPA + ALiBi bias (preferred path)."""

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.out = nn.Linear(d_model, d_model, bias=False)
        self.dropout = dropout
        self.register_buffer("slopes", alibi_slopes(n_heads).view(1, n_heads, 1, 1),
                             persistent=False)

    def _bias(self, T: int, device, dtype, key_padding_mask):
        pos = torch.arange(T, device=device)
        dist = (pos.view(1, -1) - pos.view(-1, 1)).abs().clamp(min=1)
        bias = -self.slopes.to(dtype) * dist.view(1, 1, T, T).to(dtype)
        if key_padding_mask is not None:
            bias = bias.masked_fill(
                key_padding_mask.view(-1, 1, 1, T), float("-inf"))
        return bias

    def forward(self, x, key_padding_mask):
        B, T, C = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)

        def _r(t):
            return t.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        q, k, v = _r(q), _r(k), _r(v)
        bias = self._bias(T, x.device, q.dtype, key_padding_mask)
        y = F.scaled_dot_product_attention(
            q, k, v, attn_mask=bias,
            dropout_p=self.dropout if self.training else 0.0)
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.out(y)


class MLMBlock(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.0):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = MLMSelfAttentionSDPA(d_model, n_heads, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_ff, bias=False),
            nn.GELU(),
            nn.Linear(d_ff, d_model, bias=False),
        )

    def forward(self, x, key_padding_mask):
        x = x + self.attn(self.ln1(x), key_padding_mask)
        x = x + self.mlp(self.ln2(x))
        return x


class RNAMLMEncoder(nn.Module):
    """Bidirectional MLM encoder with ALiBi, tied head, [CLS] token.

    forward(ids, targets) where:
      ids     : (B, T) long, PAD allowed;
      targets : (B, T) long, IGNORE where not part of MLM objective;
    returns (logits, loss). Also exposes hidden states per layer for probes.
    """

    def __init__(self, d_model: int, n_layers: int, n_heads: int, d_ff: int,
                 dropout: float = 0.0, use_checkpoint: bool = True):
        super().__init__()
        self.d_model = d_model
        self.n_layers = n_layers
        self.use_checkpoint = use_checkpoint
        self.tok_emb = nn.Embedding(VOCAB_TOTAL, d_model, padding_idx=PAD)
        self.cls_emb = nn.Parameter(torch.zeros(1, 1, d_model))
        self.ln_f = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, VOCAB_TOTAL, bias=False)
        self.lm_head.weight = self.tok_emb.weight
        self.blocks = nn.ModuleList(
            MLMBlock(d_model, n_heads, d_ff, dropout) for _ in range(n_layers))
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)
            with torch.no_grad():
                if m.padding_idx is not None:
                    m.weight[m.padding_idx].zero_()

    def forward(self, ids, targets=None, return_all_hiddens: bool = False):
        B, T = ids.shape
        key_padding = ids == PAD
        x = torch.where(ids == CLS, torch.zeros_like(ids), ids)
        x = self.tok_emb(x)
        cls = self.cls_emb.expand(B, 1, self.d_model)
        x = torch.cat([cls, x], dim=1)          # (B, T+1, D)
        kpm = torch.cat(
            [torch.zeros(B, 1, dtype=torch.bool, device=ids.device), key_padding],
            dim=1)
        hiddens = []
        for blk in self.blocks:
            if self.use_checkpoint and self.training:
                from torch.utils.checkpoint import checkpoint
                x = checkpoint(blk, x, kpm, use_reentrant=False)
            else:
                x = blk(x, kpm)
            if return_all_hiddens:
                hiddens.append(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)                 # (B, T+1, VOCAB_TOTAL)
        logits = logits[:, 1:, :]                # drop CLS position
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), targets.reshape(-1),
                ignore_index=IGNORE)
        if return_all_hiddens:
            return logits, loss, [h[:, 1:, :] for h in hiddens]
        return logits, loss
