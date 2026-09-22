"""S9 account-level recheck (red-team: random-split 30M/100M scores).

Independent recomputation of the 30M/100M random-split probe-balanced
scores WITHOUT the eval_matrix ledger (fresh code path, different
i%5 sampling stream position): if the recomputed best_f1 matches the
ledger values 0.6053/0.604 within run-to-run probe noise (~0.01),
the 30M==100M random plateau is NOT an eval-stub artifact.

Random split here: family_validation pool, i%5 == 0 rows as eval
(same rule, but streaming starts from the pool head as in
eval_matrix; seed 17 per-layer, inc12-style).

Output: evidence/s9_recheck.json
Usage: python -m rna_sc.s9_recheck --device 5
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

SPLIT_8080 = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
RUNS = {
    "30M": "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-30M_s17",
    "100M": "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-100M_s17",
}
OUT = "/mnt/cunyuliu/rna-sc/evidence/s9_recheck.json"
ALPHABET = "ACGU"
PAD = 4
N = 24000
SEED = 17


def seq_ids(seq):
    canon = seq.upper().replace("T", "U")
    return [ALPHABET.index(b) for b in canon if b in ALPHABET][:256]


@torch.no_grad()
def collect_all_layers(model, device, seqs, L, batch_nt=8192):
    model = model.to(device).eval()
    states = [[] for _ in range(L)]
    rows, cur_max = [], 0

    def flush():
        nonlocal rows
        if not rows:
            return
        T = max(len(r) for r in rows)
        ids = torch.tensor(
            [r + [PAD] * (T - len(r)) for r in rows],
            dtype=torch.long, device=device)
        _, _, hids = model(ids, return_all_hiddens=True)
        real = (ids != PAD)
        lengths = real.sum(-1).clamp(min=1).float().unsqueeze(-1)
        for li, h in enumerate(hids):
            hm = h.float().masked_fill(~real.unsqueeze(-1), 0.0)
            pooled = hm.sum(dim=1) / lengths
            states[li].append(pooled.cpu())
        rows = []

    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s in seqs:
            x = seq_ids(s)
            if len(x) < 4:
                continue
            if rows and (len(rows) + 1) * max(cur_max, len(x)) > batch_nt:
                flush()
                cur_max = 0
            rows.append(x)
            cur_max = max(cur_max, len(x))
        flush()
    return [torch.cat(s, dim=0) for s in states]


def probe_layer(X_tr, y_tr, X_ev, y_ev, ncls, device, seed):
    """EXACT replication of eval_matrix._probe_weighted protocol:
    full-batch Adam lr=0.05 x 200 steps, class-weight cap 10."""
    import torch.nn.functional as F
    torch.manual_seed(seed)
    d = X_tr.shape[1]
    W = torch.zeros(d, ncls, device=device, requires_grad=True)
    Xtr = X_tr.to(device).float()
    ytr = torch.tensor(y_tr, device=device)
    freq = collections.Counter(y_tr)
    n = len(y_tr)
    weights = torch.tensor(
        [min(10.0, n / max(1, freq[c])) for c in range(ncls)],
        dtype=torch.float32, device=device)
    rng = torch.Generator(device="cpu")
    rng.manual_seed(seed)
    order = torch.randperm(len(ytr), generator=rng).to(device)
    Xtr = Xtr[order]
    ytr = ytr[order]
    opt = torch.optim.Adam([W], lr=0.05)
    for _ in range(200):
        opt.zero_grad()
        logits = Xtr @ W
        loss = F.cross_entropy(logits, ytr, weight=weights)
        loss.backward()
        opt.step()
    with torch.no_grad():
        pred = (X_ev.to(device).float() @ W).argmax(-1).cpu().tolist()
    tp = collections.Counter(zip(y_ev, pred))
    f1s = []
    for c in range(ncls):
        ctp = tp[(c, c)]
        cfp = sum(v for (t, p), v in tp.items() if p == c and t != c)
        cfn = sum(v for (t, p), v in tp.items() if t == c and p != c)
        prec = ctp / (ctp + cfp) if ctp + cfp else 0.0
        rec = ctp / (ctp + cfn) if ctp + cfn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / ncls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=5)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    import pyarrow.parquet as pq
    seqs, ys = [], []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence", "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm != "family_validation":
                continue
            seqs.append(seq)
            ys.append(rt)
            if len(ys) >= N:
                break
        if len(ys) >= N:
            break
    idx_ev = [i for i in range(N) if i % 5 == 0]
    idx_tr = [i for i in range(N) if i % 5 != 0]
    classes = sorted(set(ys[i] for i in idx_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    ytr = [cls_map[ys[i]] for i in idx_tr]
    keep_ev = [i for i in idx_ev if ys[i] in cls_map]
    yev = [cls_map[ys[i]] for i in keep_ev]
    print("[data] random pool=%d train=%d eval=%d classes=%d"
          % (N, len(ytr), len(yev), len(classes)))

    out = {"note": "independent recompute, ledger bypassed; "
                   "rule i%5 on family_validation head-24k",
           "scales": {}}
    for scale, run_dir in RUNS.items():
        model, ck = load_encoder(run_dir)
        L = ck["cfg"]["arch"]["n_layers"]
        X_tr = collect_all_layers(model, dev,
                                  [seqs[i] for i in idx_tr], L)
        X_ev = collect_all_layers(model, dev,
                                  [seqs[i] for i in keep_ev], L)
        best, best_li = -1, -1
        for li in range(L):
            f1 = probe_layer(X_tr[li], ytr, X_ev[li], yev,
                             len(classes), dev, SEED + li)
            if f1 > best:
                best, best_li = f1, li
        out["scales"][scale] = {"best_f1": round(best, 4),
                                "best_layer": best_li, "n_layers": L}
        print("[%s] best L%d f1=%.4f (ledger: %s)"
              % (scale, best_li, best,
                 {"30M": 0.6053, "100M": 0.604}[scale]))
        del model
        torch.cuda.empty_cache()

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
