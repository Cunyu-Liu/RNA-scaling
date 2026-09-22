"""T1.3.3 length-bin probe + T1.2.6 low-data regime (probe line).

Combined run: for each controlled scale, collect ONLY the best layer's
states (from the final-checkpoint ledger), then
  (a) length_bin: evaluate the trained linear probe on three sequence
      length bins (16-127 / 128-511 / 512-256), family split;
  (b) low-data: retrain the probe on n in {100, 1000, 10000} sampled
      training sequences, macro-F1 learning curve.

Both use the same probe protocol as s1 (class-balanced linear head,
inc12-style seed 17, 8 epochs, batch 256).

Outputs:
  evidence/t133_lengthbin.json   (a)
  evidence/t126_lowdata.json     (b)

Usage: python -m rna_sc.probe_len_lowdata --device 0
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
    "1M": ("/mnt/cunyuliu/rna-sc/runs/RNA-Sc-1M_s17", 8),
    "10M": ("/mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17", 1),
    "30M": ("/mnt/cunyuliu/rna-sc/runs/RNA-Sc-30M_s17", 7),
    "100M": ("/mnt/cunyuliu/rna-sc/runs/RNA-Sc-100M_s17", 21),
}
OUT_LEN = "/mnt/cunyuliu/rna-sc/evidence/t133_lengthbin.json"
OUT_LOW = "/mnt/cunyuliu/rna-sc/evidence/t126_lowdata.json"
ALPHABET = "ACGU"
PAD = 4
BINS = ((16, 127, "16-127"), (128, 511, "128-511"),
        (512, 99999, "512+"))
N_TRAIN = 20000
N_EVAL = 4000
LOWDATA_NS = (100, 1000, 10000)
SEED = 17


def seq_ids(seq, maxlen=256):
    canon = seq.upper().replace("T", "U")
    return [ALPHABET.index(b) for b in canon if b in ALPHABET][:maxlen]


@torch.no_grad()
def collect_best_layer(model, device, split, n_seq, layer, batch_nt=8192):
    """Mean-pooled states at ONE layer (s1 probe protocol pooling)."""
    import pyarrow.parquet as pq
    model = model.to(device).eval()
    states, labels, lens = [], [], []
    rows, cur_max, n = [], 0, 0

    def flush():
        nonlocal rows
        if not rows:
            return
        T = max(len(r[0]) for r in rows)
        ids = torch.tensor(
            [r[0] + [PAD] * (T - len(r[0])) for r in rows],
            dtype=torch.long, device=device)
        _, _, hids = model(ids, return_all_hiddens=True)
        h = hids[layer]
        real = (ids != PAD)
        lengths = real.sum(-1).clamp(min=1).float().unsqueeze(-1)
        hm = h.float().masked_fill(~real.unsqueeze(-1), 0.0)
        pooled = (hm * (real.unsqueeze(-1).float())).sum(1) / lengths
        states.append(pooled.cpu())
        labels.extend(r[1] for r in rows)
        lens.extend(r[2] for r in rows)
        rows = []

    pf = pq.ParquetFile(SPLIT_8080)
    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for rb in pf.iter_batches(
                batch_size=50_000,
                columns=["split_membership", "canonical_sequence",
                         "rna_type"]):
            d = rb.to_pydict()
            for sm, seq, rt in zip(d["split_membership"],
                                   d["canonical_sequence"], d["rna_type"]):
                if sm != split:
                    continue
                ids = seq_ids(seq)
                if len(ids) < 16:
                    continue
                if rows and (len(rows) + 1) * max(cur_max, len(ids)) > batch_nt:
                    flush()
                    cur_max = 0
                rows.append((ids, rt, len(seq)))
                cur_max = max(cur_max, len(ids))
                n += 1
                if n >= n_seq:
                    flush()
                    return (torch.cat(states), labels,
                            np.asarray(lens))
        flush()
    return (torch.cat(states), labels, np.asarray(lens))


def train_probe(Xtr, ytr, n_classes, device, seed=SEED, epochs=8):
    import torch.nn.functional as F
    torch.manual_seed(seed)
    d = Xtr.shape[1]
    W = torch.zeros(d, n_classes, device=device, requires_grad=True)
    Xtr = Xtr.to(device).float()
    ytr_t = torch.tensor(ytr, device=device)
    freq = collections.Counter(ytr)
    n = len(ytr)
    weights = torch.tensor(
        [min(10.0, n / max(1, freq[c])) for c in range(n_classes)],
        dtype=torch.float32, device=device)
    opt = torch.optim.AdamW([W], lr=1e-3, weight_decay=0.01)
    for _ in range(epochs):
        perm = torch.randperm(len(Xtr), device=device)
        for i in range(0, len(Xtr), 256):
            idx = perm[i:i + 256]
            loss = F.cross_entropy(Xtr[idx] @ W, ytr_t[idx], weight=weights)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    return W.detach()


def eval_f1(W, Xev, yev, n_classes, device):
    with torch.no_grad():
        pred = (Xev.to(device).float() @ W).argmax(-1).cpu().tolist()
    tp = collections.Counter(zip(yev, pred))
    f1s = []
    for c in range(n_classes):
        ctp = tp[(c, c)]
        cfp = sum(v for (t, p), v in tp.items() if p == c and t != c)
        cfn = sum(v for (t, p), v in tp.items() if t == c and p != c)
        prec = ctp / (ctp + cfp) if ctp + cfp else 0.0
        rec = ctp / (ctp + cfn) if ctp + cfn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / n_classes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=0)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    out_len = {"bins": [b[2] for b in BINS], "scales": {}}
    out_low = {"ns": list(LOWDATA_NS), "scales": {}}

    for scale, (run_dir, layer) in RUNS.items():
        model, _ = load_encoder(run_dir)
        X_tr, y_tr, len_tr = collect_best_layer(
            model, dev, "family_validation", N_TRAIN, layer)
        X_ev, y_ev, len_ev = collect_best_layer(
            model, dev, "family_test", N_EVAL, layer)
        print("[%s] collected train=%d eval=%d (best layer %d)"
              % (scale, len(y_tr), len(y_ev), layer))

        classes = sorted(set(y_tr))
        cls_map = {c: i for i, c in enumerate(classes)}
        y_tri = np.asarray([cls_map[c] for c in y_tr])
        keep = np.asarray([c in cls_map for c in y_ev])
        y_evi = np.asarray([cls_map[c] for c in y_ev if c in cls_map])
        X_ev_k = X_ev[torch.tensor(keep)]
        ncls = len(classes)

        W = train_probe(X_tr, list(y_tri), ncls, dev)

        bin_rec = {}
        for lo, hi, name in BINS:
            m_ev = (len_ev[keep] >= lo) & (len_ev[keep] <= hi)
            if m_ev.sum() < 50:
                bin_rec[name] = {"n": int(m_ev.sum()), "f1": None}
                continue
            f1 = eval_f1(W, X_ev_k[torch.tensor(m_ev)],
                         list(y_evi[m_ev]), ncls, dev)
            bin_rec[name] = {"n": int(m_ev.sum()),
                             "f1": round(f1, 4)}
            print("  lenbin %-14s n=%5d f1=%.4f" % (name, m_ev.sum(), f1))
        out_len["scales"][scale] = {
            "best_layer": layer,
            "overall_f1": round(eval_f1(
                W, X_ev_k, list(y_evi), ncls, dev), 4),
            "bins": bin_rec}

        low_rec = {}
        for nsub in LOWDATA_NS:
            rng = np.random.RandomState(SEED + nsub)
            idx = rng.choice(len(y_tri), size=nsub, replace=False)
            W_n = train_probe(X_tr[torch.tensor(idx)],
                              list(y_tri[idx]), ncls, dev,
                              seed=SEED + nsub)
            f1 = eval_f1(W_n, X_ev_k, list(y_evi), ncls, dev)
            low_rec[str(nsub)] = round(f1, 4)
            print("  lowdata n=%5d f1=%.4f" % (nsub, f1))
        out_low["scales"][scale] = {
            "best_layer": layer,
            "full_f1": out_len["scales"][scale]["overall_f1"],
            "lowdata": low_rec}

        del model
        torch.cuda.empty_cache()

    with open(OUT_LEN, "w") as fh:
        json.dump(out_len, fh, indent=2)
    with open(OUT_LOW, "w") as fh:
        json.dump(out_low, fh, indent=2)
    print("saved", OUT_LEN, "and", OUT_LOW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
