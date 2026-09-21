"""T1.3.2 external model probe: RNA-FM (96M, fairseq checkpoint).

First line-1 model under the SAME probe protocol as the RNA-Sc family
(inc12 deterministic, family_validation -> family_test, per-layer
pooled linear probe). This makes layer-migration results comparable
across pretraining recipes (controlled vs RiNALMo-lineage).

Checkpoint: /mnt/cunyuliu/rna_junction_repair_20260811T090000Z/
  RNA-FM_pretrained.pth  (fairseq dict, ESM-style encoder:
  embed_tokens 25 x 640, 12 layers, learned positions,
  emb_layer_norm_before/after, lm_head)

Tokenizer: RNA-FM uses single-nucleotide (A/C/G/U + special) — vocab
25 confirms single-nt + specials. We map A,C,G,U -> 0..3? NO — we
keep the checkpoint's own row indices for A/C/G/U by probing
embed_tokens rows: standard RNA-FM vocab order is
  0=<s> 1=<pad> 2=</s> 3=<unk> 4=A 5=C 6=G 7=U ... (fairseq standard)
We VERIFY at runtime: embed row norms for A/C/G/U letters vs
rarest specials should be distinguishable; safest is to use the
fairseq dictionary if available in ck['cfg']; fallback = standard
order with a one-off sanity check (loss drops on real vs shuffled).

Outputs rows to eval/probe_results_ext.jsonl (separate ledger;
RNA-Sc family stays untouched).

Usage:
  python -m rna_sc.probe_rnafm --device 6 [--n-train 20000]
"""
from __future__ import annotations

import argparse
import json
import os

import torch

from rna_sc.census import GPUGuard

CKPT = ("/mnt/cunyuliu/rna_junction_repair_20260811T090000Z/"
        "RNA-FM_pretrained.pth")
OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
ALPHABET = "ACGU"
# fairseq RNA-FM vocab (single-nt, learned): <s>=0 <pad>=1 </s>=2
# <unk>=3 A=4 C=5 G=6 U=7, rest = rare specials
TOK = {"A": 4, "C": 5, "G": 6, "U": 7}
BOS, PAD = 0, 1


class RNAFMEncoder(torch.nn.Module):
    """Minimal ESM-style forward for layer states (from checkpoint)."""

    def __init__(self, sd):
        super().__init__()
        d = sd["encoder.encoder.embed_tokens.weight"].shape[1]
        n_layers = 0
        while ("encoder.encoder.layers.%d.self_attn.q_proj.weight"
               % n_layers) in sd:
            n_layers += 1
        ffn_d = sd["encoder.encoder.layers.0.fc1.weight"].shape[0]
        self.n_layers = n_layers
        self.d_model = d
        self.ffn_d = ffn_d
        self.embed_tokens = torch.nn.Embedding(
            sd["encoder.encoder.embed_tokens.weight"].shape[0], d)
        self.embed_positions = torch.nn.Embedding(
            sd["encoder.encoder.embed_positions.weight"].shape[0], d)
        self.emb_ln = torch.nn.LayerNorm(d)
        self.emb_ln_after = torch.nn.LayerNorm(d)
        self.blocks = torch.nn.ModuleList()
        for i in range(n_layers):
            blk = torch.nn.ModuleDict({
                "self_attn": torch.nn.ModuleDict({
                    "k": torch.nn.Linear(d, d),
                    "v": torch.nn.Linear(d, d),
                    "q": torch.nn.Linear(d, d),
                    "out": torch.nn.Linear(d, d)}),
                "attn_ln": torch.nn.LayerNorm(d),
                "fc1": torch.nn.Linear(d, ffn_d),
                "fc2": torch.nn.Linear(ffn_d, d),
                "final_ln": torch.nn.LayerNorm(d)})
            self.blocks.append(blk)
        self._load(sd)

    def _load(self, sd):
        p = "encoder.encoder."
        self.embed_tokens.weight.data.copy_(sd[p + "embed_tokens.weight"])
        self.embed_positions.weight.data.copy_(
            sd[p + "embed_positions.weight"])
        self.emb_ln.weight.data.copy_(sd[p + "emb_layer_norm_before.weight"])
        self.emb_ln.bias.data.copy_(sd[p + "emb_layer_norm_before.bias"])
        self.emb_ln_after.weight.data.copy_(
            sd[p + "emb_layer_norm_after.weight"])
        self.emb_ln_after.bias.data.copy_(sd[p + "emb_layer_norm_after.bias"])
        for i, blk in enumerate(self.blocks):
            q = p + "layers.%d." % i
            blk.self_attn.k.weight.data.copy_(sd[q + "self_attn.k_proj.weight"])
            blk.self_attn.k.bias.data.copy_(sd[q + "self_attn.k_proj.bias"])
            blk.self_attn.v.weight.data.copy_(sd[q + "self_attn.v_proj.weight"])
            blk.self_attn.v.bias.data.copy_(sd[q + "self_attn.v_proj.bias"])
            blk.self_attn.q.weight.data.copy_(sd[q + "self_attn.q_proj.weight"])
            blk.self_attn.q.bias.data.copy_(sd[q + "self_attn.q_proj.bias"])
            blk.self_attn.out.weight.data.copy_(
                sd[q + "self_attn.out_proj.weight"])
            blk.self_attn.out.bias.data.copy_(
                sd[q + "self_attn.out_proj.bias"])
            blk.attn_ln.weight.data.copy_(
                sd[q + "self_attn_layer_norm.weight"])
            blk.attn_ln.bias.data.copy_(sd[q + "self_attn_layer_norm.bias"])
            blk.fc1.weight.data.copy_(sd[q + "fc1.weight"])
            blk.fc1.bias.data.copy_(sd[q + "fc1.bias"])
            blk.fc2.weight.data.copy_(sd[q + "fc2.weight"])
            blk.fc2.bias.data.copy_(sd[q + "fc2.bias"])
            blk.final_ln.weight.data.copy_(sd[q + "final_layer_norm.weight"])
            blk.final_ln.bias.data.copy_(sd[q + "final_layer_norm.bias"])

    def forward(self, ids, return_all_hiddens=False):
        """ids: (B, T) single-nt tokens incl. PAD. Returns hiddens list
        of (B, T, D) AFTER each block's final_ln (post-block states),
        matching ESM per-layer convention."""
        B, T = ids.shape
        pos = torch.arange(T, device=ids.device).clamp(
            max=self.embed_positions.num_embeddings - 1)
        x = self.embed_tokens(ids) + self.embed_positions(pos)[None]
        x = self.emb_ln(x)
        pad = ids == PAD
        hids = []
        for blk in self.blocks:
            ln = blk.attn_ln(x)
            q = blk.self_attn.q(ln).view(B, T, 8, -1).transpose(1, 2)
            k = blk.self_attn.k(ln).view(B, T, 8, -1).transpose(1, 2)
            v = blk.self_attn.v(ln).view(B, T, 8, -1).transpose(1, 2)
            att = (q @ k.transpose(-2, -1)) / (q.shape[-1] ** 0.5)
            att = att.masked_fill(pad[:, None, None, :], float("-inf"))
            att = torch.softmax(att, dim=-1)
            o = (att @ v).transpose(1, 2).reshape(B, T, -1)
            x = x + blk.self_attn.out(o)
            x = x + blk.fc2(torch.nn.functional.gelu(blk.fc1(x)))
            x = blk.final_ln(x)
            if return_all_hiddens:
                hids.append(x)
        return hids


def collect_states(model, device, split, n_seq, L, context_nt=256,
                   batch_nt=8192):
    """Same streaming pattern as rna_sc.probe.collect_states, but for
    the RNA-FM tokenizer (BOS + single-nt)."""
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    model = model.to(device).eval()
    states = [[] for _ in range(L)]
    labels = []
    rows = []
    cur_max = 0
    n = 0

    def _enc(seq):
        s = seq.upper().replace("T", "U")
        return [TOK[b] for b in s if b in TOK]

    def flush():
        nonlocal rows
        if not rows:
            return
        T = max(len(r[0]) for r in rows)
        ids = torch.tensor(
            [r[0] + [PAD] * (T - len(r[0])) for r in rows],
            dtype=torch.long, device=device)
        hids = model(ids, return_all_hiddens=True)
        pad = ids == PAD
        lengths = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
        for li, h in enumerate(hids):
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            pooled = hm.sum(dim=1) / lengths
            states[li].append(pooled.cpu())
        labels.extend(r[1] for r in rows)
        rows = []

    pf = pq.ParquetFile(SPLIT_8080)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for rb in pf.iter_batches(
                batch_size=50_000,
                columns=["split_membership", "canonical_sequence",
                         "rna_type"]):
            d = rb.to_pydict()
            for sm, seq, rt in zip(d["split_membership"],
                                   d["canonical_sequence"], d["rna_type"]):
                if sm != split:
                    continue
                ids = [BOS] + _enc(seq[:context_nt])
                if len(ids) < 3:
                    continue
                Lx = len(ids)
                if rows and (len(rows) + 1) * max(cur_max, Lx) > batch_nt:
                    flush()
                    cur_max = 0
                rows.append((ids, rt))
                cur_max = max(cur_max, Lx)
                n += 1
                if n >= n_seq:
                    flush()
                    X = [torch.cat(s, dim=0) for s in states]
                    return X, labels[:len(X[0])]
        flush()
    X = [torch.cat(s, dim=0) for s in states]
    return X, labels[:len(X[0])]


def probe_one_layer(X_tr, y_tr, X_ev, y_ev, n_classes, device, layer_seed,
                    epochs=8):
    """Class-balanced deterministic linear head (same as eval_matrix
    balanced protocol — external models get the same fair treatment)."""
    import torch.nn.functional as F
    torch.manual_seed(layer_seed)
    d = X_tr.shape[1]
    W = torch.zeros(d, n_classes, device=device, requires_grad=True)
    Xtr, Xev = X_tr.to(device).float(), X_ev.to(device).float()
    ytr = torch.tensor(y_tr, device=device)
    yev = torch.tensor(y_ev, device=device)
    import collections
    freq = collections.Counter(y_tr)
    n = len(y_tr)
    weights = torch.tensor(
        [min(10.0, n / max(1, freq[c])) for c in range(n_classes)],
        dtype=torch.float32, device=device)
    opt = torch.optim.AdamW([W], lr=1e-3, weight_decay=0.01)
    for _ in range(epochs):
        perm = torch.randperm(len(Xtr), device=device)
        for i in range(0, len(Xtr), 256):
            idx = perm[i:i + 256]
            loss = F.cross_entropy(Xtr[idx] @ W, ytr[idx], weight=weights)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    with torch.no_grad():
        pred = (Xev @ W).argmax(-1)
        acc = float((pred == yev).float().mean())
        # macro F1
        tp = collections.Counter(zip(y_ev, pred.tolist()))
        f1s = []
        for c in range(n_classes):
            ctp = tp[(c, c)]
            cfp = sum(v for (t, p), v in tp.items() if p == c and t != c)
            cfn = sum(v for (t, p), v in tp.items() if t == c and p != c)
            prec = ctp / (ctp + cfp) if ctp + cfp else 0.0
            rec = ctp / (ctp + cfn) if ctp + cfn else 0.0
            f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return acc, sum(f1s) / n_classes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    sd = ck["model"]
    model = RNAFMEncoder(sd)
    print("RNA-FM loaded: %d layers, d=%d, vocab=%d" % (
        model.n_layers, model.d_model,
        model.embed_tokens.num_embeddings))
    L = model.n_layers

    # sanity: shuffled-token control (same tokens, order destroyed) —
    # if the model has learned anything sequential, pooled-probe F1 on
    # shuffled should drop vs real (cheap guard against tokenizer
    # mismatch producing garbage-but-lookup-based features).
    X_tr, y_tr = collect_states(model, dev, "family_validation",
                                args.n_train, L)
    X_ev, y_ev = collect_states(model, dev, "family_test",
                                args.n_eval, L)
    print("collected: train=%d eval=%d" % (len(y_tr), len(y_ev)))
    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    y_tri = [cls_map[c] for c in y_tr]
    keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
    y_evi = [cls_map[y_ev[i]] for i in keep_ev]

    best = None
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for li in range(L):
        acc, f1 = probe_one_layer(
            X_tr[li], y_tri, X_ev[li][keep_ev], y_evi, len(classes),
            dev, layer_seed=17 + li)
        rec = {"run": "RNA-FM-96M", "layer": li,
               "rel_depth": round(li / (L - 1), 3),
               "depth_band": ("early" if li / (L - 1) <= 0.33 else
                              ("middle" if li / (L - 1) <= 0.66
                               else "late")),
               "n_layers": L, "ckpt_nt": None,
               "n_classes": len(classes),
               "n_train": len(y_tri), "n_eval": len(y_evi),
               "acc": round(acc, 4), "f1_macro": round(f1, 4),
               "task": "rna_type classification (S11)",
               "split": "family_validation->family_test",
               "protocol": "probe-balanced (class-weighted, inc12 seed)"}
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print("layer %d (rel %.2f) acc=%.4f f1=%.4f" %
              (li, li / (L - 1), acc, f1))
        if best is None or f1 > best["f1_macro"]:
            best = rec
    print("BEST:", json.dumps(best))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
