"""S8 补充图（NucleicBERT Fig4d 风格）：layer × head 注意力热图。

图式（对标 NucleicBERT Fig 4d）：y=layer，x=head，色=该头注意力与
接触结构的对齐度。他们的口径是"contact map prediction 任务的
normalized attention weights"；我们用零侵入等价口径：

  对每层 l、每头 h：取该头在 bpRNA test 序列上的平均注意力矩阵 A，
  与真实长程接触矩阵 C（≥24nt 配对=1）算 Pearson r —— r 高 =
  该头"看"的结构位置与真实配对对齐 = 结构注意力通道。

SDPA 不返回权重 → 用 blk.attn.qkv 权重手动重算（含 ALiBi bias）。

对照：randinit 650M 同图（结构对齐应近 0）。
输出：fig_s8_attention_heatmap.png（两联热图 + 差值图）。
"""
import json
import math
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/home/cunyuliu/rna-sc")

MNT = "/mnt/cunyuliu/rna-sc"
EVID = os.path.join(MNT, "evidence")
FIG = os.path.join(MNT, "figs")
MIN_LONG = 24
N_SEQS = 24          # 平均用的序列数（快且稳）
MAX_LEN = 180        # 显存与算力约束


def load_bprna():
    import pyarrow.parquet as pq
    t = pq.read_table(os.path.join(MNT, "data/bpRNA_parsed.parquet"))
    out = []
    for name, split, seq, pairs in zip(t.column("name").to_pylist(),
                                       t.column("split").to_pylist(),
                                       t.column("seq").to_pylist(),
                                       t.column("pairs").to_pylist()):
        if split != "test":
            continue
        seq = (seq or "").upper().replace("T", "U")
        prs = json.loads(pairs) if isinstance(pairs, str) else (pairs or [])
        if len(seq) > MAX_LEN or len(seq) < MIN_LONG + 10:
            continue
        out.append({"seq": seq, "pairs": [(int(i), int(j)) for i, j in prs]})
        if len(out) >= N_SEQS:
            break
    return out


def attn_maps(model, ids, n_layers, n_heads, device):
    """手动重算每层每头注意力（B=1，无 PAD，含 ALiBi）。"""
    B, T = ids.shape
    x = model.tok_emb(ids)
    cls = model.cls_emb.expand(1, 1, model.d_model)
    x = torch.cat([cls, x], dim=1)      # (1, T+1, D) — 与 forward 一致
    maps = []
    for blk in model.blocks:
        c = x.shape[-1]
        q, k, v = blk.attn.qkv(x).chunk(3, dim=-1)

        def _r(t):
            return t.view(1, -1, n_heads, c // n_heads).transpose(1, 2)
        q, k = _r(q), _r(k)
        hd = c // n_heads
        att = (q @ k.transpose(-2, -1)) / math.sqrt(hd)
        pos = torch.arange(T + 1, device=device, dtype=att.dtype)
        dist = (pos.view(1, -1) - pos.view(-1, 1)).abs().clamp(min=1)
        att = att - blk.attn.slopes.to(att.dtype) * dist.view(
            1, 1, T + 1, T + 1)
        att = F.softmax(att, dim=-1)
        maps.append(att[0].detach())    # (n_heads, T+1, T+1)
        x = blk(x, torch.zeros(1, T + 1, dtype=torch.bool,
                               device=device))
    return maps


def contact_corr(att, pairs, n):
    """单头注意力 (T+1,T+1，含 CLS 偏移) vs 长程接触矩阵的 Pearson r。"""
    A = att[1:n + 1, 1:n + 1].float().cpu().numpy()  # 去 CLS
    idx = np.triu_indices(n, k=MIN_LONG)
    a = A[idx]
    c = np.zeros((n, n))
    for i, j in pairs:
        if j - i >= MIN_LONG and i < n and j < n:
            c[i, j] = 1.0
    cc = c[idx]
    if cc.sum() == 0:
        return None
    if a.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, cc)[0, 1])


def run(model_id, seqs, device):
    from rna_sc.probe import load_encoder
    from rna_sc.data import ALPHABET
    model, ck = load_encoder(os.path.join(MNT, "runs", model_id))
    model = model.to(device).eval()
    n_layers = ck["cfg"]["arch"]["n_layers"]
    n_heads = ck["cfg"]["arch"]["n_heads"]
    H = np.zeros((n_layers, n_heads))
    cnt = np.zeros((n_layers, n_heads))
    with torch.no_grad():
        for r in seqs:
            seq = r["seq"][:MAX_LEN]
            ids = torch.tensor([[ALPHABET.index(b) for b in seq
                                 if b in ALPHABET]], device=device)
            n = ids.shape[1]
            if n < MIN_LONG + 10:
                continue
            maps = attn_maps(model, ids, n_layers, n_heads, device)
            for li, att in enumerate(maps):
                for h in range(n_heads):
                    r_val = contact_corr(att[h], r["pairs"], n)
                    if r_val is not None:
                        H[li, h] += r_val
                        cnt[li, h] += 1
    H = H / np.maximum(cnt, 1)
    return H


def main():
    device = "cuda:6"
    seqs = load_bprna()
    print("[s8attn] n_seqs=%d" % len(seqs), flush=True)
    out = {}
    for tag, run_id in [("650M_trained", "RNA-Sc-650M_s17"),
                        ("650M_randinit", "RNA-Sc-650M_s17")]:
        H = run(run_id, seqs, device)
        if tag == "650M_randinit":
            torch.manual_seed(17)
            from rna_sc.model import RNAMLMEncoder
            ck = torch.load(os.path.join(MNT, "runs", run_id,
                           sorted([f for f in os.listdir(
                               os.path.join(MNT, "runs", run_id))
                               if f.startswith("ckpt_")],
                               key=lambda f: int(f.split("_nt")[1]
                                                 .split("_")[0]))[-1]),
                           map_location="cpu", weights_only=False)
            mcfg = ck["cfg"]["arch"]
            model = RNAMLMEncoder(d_model=mcfg["d_model"],
                                  n_layers=mcfg["n_layers"],
                                  n_heads=mcfg["n_heads"],
                                  d_ff=mcfg["d_ff"])
            model = model.to(device).eval()
            n_layers = mcfg["n_layers"]
            n_heads = mcfg["n_heads"]
            H = np.zeros((n_layers, n_heads))
            cnt = np.zeros((n_layers, n_heads))
            from rna_sc.data import ALPHABET
            with torch.no_grad():
                for r in seqs:
                    seq = r["seq"][:MAX_LEN]
                    ids = torch.tensor([[ALPHABET.index(b) for b in seq
                                         if b in ALPHABET]], device=device)
                    n = ids.shape[1]
                    if n < MIN_LONG + 10:
                        continue
                    maps = attn_maps(model, ids, n_layers, n_heads, device)
                    for li, att in enumerate(maps):
                        for h in range(n_heads):
                            rv = contact_corr(att[h], r["pairs"], n)
                            if rv is not None:
                                H[li, h] += rv
                                cnt[li, h] += 1
            H = H / np.maximum(cnt, 1)
        out[tag] = np.round(H, 4).tolist()
        print("[s8attn] %s done: max=%.3f mean=%.3f" %
              (tag, H.max(), H.mean()), flush=True)
    json.dump({"protocol": "per-layer per-head Pearson(attention, "
               "long-range contact), avg over %d bpRNA test seqs "
               "(len<%d); CLS removed; ALiBi included; SDPA manually "
               "recomputed" % (len(seqs), MAX_LEN),
               "n_layers": len(out["650M_trained"]),
               "n_heads": len(out["650M_trained"][0]),
               "trained": out["650M_trained"],
               "randinit": out["650M_randinit"]},
              open(os.path.join(EVID, "s8_attention_heatmap.json"), "w"),
              indent=1)
    print("[s8attn] saved evidence/s8_attention_heatmap.json", flush=True)


if __name__ == "__main__":
    main()
