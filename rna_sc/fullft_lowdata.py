"""T1.2.6 full-FT line: low-data regime with FULL fine-tuning.

Complements t126_lowdata.json (probe line): the same 100/1000/10000
subsample sizes, but the encoder is fully fine-tuned (not frozen)
with a class-balanced linear head, family split, 3 epochs (small n)
/ 1 epoch (20k), bf16 autocast, AdamW.

Deterministic: torch.manual_seed(SEED + nsub); same sub-sample indices
as the probe line (RandomState(SEED + nsub)).

Output: evidence/t126_fullft.json
Usage: python -m rna_sc.fullft_lowdata --device 4
(v1.1: 650M s17 appended for the five-scale T1.2.6 full-FT curve)
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
    "10M": "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17",
    "100M": "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-100M_s17",
    "650M": "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-650M_s17",
}
OUT = "/mnt/cunyuliu/rna-sc/evidence/t126_fullft.json"
ALPHABET = "ACGU"
PAD = 4
N_EVAL = 4000
N_TRAIN_MAX = 20000
LOWDATA_NS = (100, 1000, 10000)
SEED = 17


def collect_seqs(split, n_seq):
    import pyarrow.parquet as pq
    seqs, ys = [], []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence", "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm != split:
                continue
            seqs.append(seq[:256])
            ys.append(rt)
            if len(ys) >= n_seq:
                return seqs, ys
    return seqs, ys


def seq_ids(seq):
    canon = seq.upper().replace("T", "U")
    return [ALPHABET.index(b) for b in canon if b in ALPHABET][:256]


def run_fullft(model, tr_ids, ytr, ev_ids, yev, ncls, device, nsub,
               d_model, epochs=3, batch=32, lr=5e-5):
    import torch.nn as nn

    torch.manual_seed(SEED + nsub)
    model = model.to(device)
    model.train()
    head = nn.Linear(d_model, ncls).to(device)

    params = list(model.parameters()) + list(head.parameters())
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.01)

    freq = collections.Counter(ytr)
    n = len(ytr)
    w = torch.tensor(
        [min(10.0, n / max(1, freq[c])) for c in range(ncls)],
        dtype=torch.float32, device=device)
    crit = nn.CrossEntropyLoss(weight=w)

    ytr_arr = np.asarray(ytr)
    for ep in range(epochs):
        perm = np.random.RandomState(SEED * 1000 + nsub + ep).permutation(
            len(tr_ids))
        for i in range(0, len(perm), batch):
            idx = perm[i:i + batch]
            B = len(idx)
            T = max(len(tr_ids[j]) for j in idx)
            ids = torch.full((B, T), PAD, dtype=torch.long, device=device)
            mask = torch.zeros(B, T, dtype=torch.bool, device=device)
            for b, j in enumerate(idx):
                x = tr_ids[j]
                ids[b, :len(x)] = torch.tensor(x, device=device)
                mask[b, :len(x)] = True
            yb = torch.tensor(ytr_arr[idx], dtype=torch.long, device=device)
            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                _, _, hids = model(ids, return_all_hiddens=True)
                pooled = (hids[-1].float() * mask.unsqueeze(-1)).sum(1) \
                    / mask.sum(1, keepdim=True).float()
                logits = head(pooled)
                loss = crit(logits, yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(ev_ids), 64):
            chunk = ev_ids[i:i + 64]
            B = len(chunk)
            T = max(len(x) for x in chunk)
            ids = torch.full((B, T), PAD, dtype=torch.long, device=device)
            mask = torch.zeros(B, T, dtype=torch.bool, device=device)
            for b, x in enumerate(chunk):
                ids[b, :len(x)] = torch.tensor(x, device=device)
                mask[b, :len(x)] = True
            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                _, _, hids = model(ids, return_all_hiddens=True)
                pooled = (hids[-1].float() * mask.unsqueeze(-1)).sum(1) \
                    / mask.sum(1, keepdim=True).float()
                logits = head(pooled)
                preds.extend(logits.argmax(-1).cpu().tolist())

    yev_arr = np.asarray(yev)
    acc = float((np.asarray(preds) == yev_arr).mean())
    tp = collections.Counter(zip(list(yev), preds))
    f1s = []
    for c in range(ncls):
        ctp = tp[(c, c)]
        cfp = sum(v for (t, p), v in tp.items() if p == c and t != c)
        cfn = sum(v for (t, p), v in tp.items() if t == c and p != c)
        prec = ctp / (ctp + cfp) if ctp + cfp else 0.0
        rec = ctp / (ctp + cfn) if ctp + cfn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return acc, sum(f1s) / ncls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=4)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    tr_seqs, y_tr = collect_seqs("family_validation", N_TRAIN_MAX)
    ev_seqs, y_ev = collect_seqs("family_test", N_EVAL)
    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    y_tri = np.asarray([cls_map[c] for c in y_tr])
    keep = np.asarray([c in cls_map for c in y_ev])
    y_evi = np.asarray([cls_map[c] for c in y_ev if c in cls_map])
    ev_ids = [seq_ids(ev_seqs[i]) for i in range(len(y_ev)) if keep[i]]
    ncls = len(classes)
    print("[data] train=%d eval=%d classes=%d"
          % (len(y_tri), len(y_evi), ncls))

    out = {"ns": list(LOWDATA_NS), "scales": {}}
    tr_ids_all = [seq_ids(s) for s in tr_seqs]

    for scale, run_dir in RUNS.items():
        model, ck = load_encoder(run_dir)
        d_model = ck["cfg"]["arch"]["d_model"]
        rec = {}
        for nsub in LOWDATA_NS:
            rng = np.random.RandomState(SEED + nsub)
            idx = rng.choice(len(y_tri), size=nsub, replace=False)
            sub_ids = [tr_ids_all[j] for j in idx]
            acc, f1 = run_fullft(
                model, sub_ids, list(y_tri[idx]), ev_ids,
                list(y_evi), ncls, dev, nsub, d_model, epochs=3)
            rec[str(nsub)] = round(f1, 4)
            print("[%s] fullft n=%5d acc=%.4f f1=%.4f"
                  % (scale, nsub, acc, f1))
            model, ck = load_encoder(run_dir)
        out["scales"][scale] = rec
        del model
        torch.cuda.empty_cache()

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
