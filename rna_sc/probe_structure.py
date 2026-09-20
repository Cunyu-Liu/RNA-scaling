"""S7 structure probe on bpRNA: per-pair-position classification.

First non-rna_type task: tests whether the attrition/layer-migration
findings generalize to a STRUCTURE task (preprint limitation currently
says "attrition shown for rna_type only").

Protocol (day-1 pooled-probe style, inc12 deterministic):
  - Input: bpRNA_parsed.parquet (name/source/split/seq/pairs)
  - Task: per-token binary classification — is position i a PAIRED
    position (participates in any pair [i, j])?
  - Representation: layer-l mean-pooled token states at position i
    (per-token states, NOT sequence pooling — structure is local)
  - Head: linear per layer, class-balanced (rRNA-like bias: ~50% paired
    in structured families)
  - Split: bpRNA TR0 -> TS0 (official standard split; families held by
    construction at source level)
  - Metric: macro-F1 (paired vs unpaired) + PR-AUC (imbalance check)
  - Family source labels kept for stratified reporting (E2)

Output: eval/probe_structure_results.jsonl + evidence/s7_structure_probe.json

Usage:
  python -m rna_sc.probe_structure --run-dir runs/RNA-Sc-10M_s17 \
      --device 6 [--n-train-seqs 8000] [--n-eval-seqs 1500]
"""
from __future__ import annotations

import argparse
import json
import os
import random

import torch
import pyarrow.parquet as pq

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

BPRNA = "/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet"
OUT_JSONL = "/mnt/cunyuliu/rna-sc/eval/probe_structure_results.jsonl"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/s7_structure_probe.json"
ALPHABET = "ACGU"
PAD = 4


def collect_token_states(model, device, seqs, pairs_list, L,
                          context_nt=256, batch=32):
    """Per-token hidden states for all layers, per sequence.

    Returns list-per-layer of tensors [total_tokens, d_model] plus the
    paired/unpaired labels [total_tokens], truncated at context_nt.
    """
    model = model.to(device).eval()
    states = [[] for _ in range(L)]
    labels = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for si, (seq, pairs) in enumerate(zip(seqs, pairs_list)):
            ids = [ALPHABET.index(b) for b in seq.upper().replace("T", "U")
                   if b in ALPHABET][:context_nt]
            n = len(ids)
            if n < 4:
                continue
            paired = [0] * n
            for i, j in pairs:
                if i <= n and j <= n:
                    paired[i - 1] = 1
                    paired[j - 1] = 1
            x = torch.tensor([ids], device=device)
            _, _, hids = model(x, return_all_hiddens=True)
            for li, h in enumerate(hids):
                states[li].append(h[0, :n].float().cpu())
            labels.extend(paired)
    states = [torch.cat(s, dim=0) for s in states]
    y = torch.tensor(labels, dtype=torch.long)
    return states, y


def macro_f1_binary(pred, y):
    tp = sum(1 for p, t in zip(pred, y) if p == 1 and t == 1)
    fp = sum(1 for p, t in zip(pred, y) if p == 1 and t == 0)
    fn = sum(1 for p, t in zip(pred, y) if p == 0 and t == 1)
    f1_p = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return f1_p, prec, rec


def run_one_layer(Xtr, ytr, Xev, yev, device, seed, epochs=6, lr=1e-3):
    torch.manual_seed(seed)
    d = Xtr.shape[1]
    W = torch.zeros(d, 2, device=device, requires_grad=True)
    Xtr_d, Xev_d = Xtr.to(device).float(), Xev.to(device).float()
    ytr_d, yev_d = ytr.to(device), yev.to(device)
    # class weights for imbalance
    npos = float((ytr_d == 1).sum())
    nneg = float(len(ytr_d) - npos)
    w = torch.tensor([1.0, max(1.0, nneg / max(1.0, npos))],
                     device=device)
    opt = torch.optim.AdamW([W], lr=lr, weight_decay=0.01)
    for _ in range(epochs):
        perm = torch.randperm(len(Xtr_d), device=device)
        for i in range(0, len(Xtr_d), 512):
            idx = perm[i:i + 512]
            loss = torch.nn.functional.cross_entropy(
                Xtr_d[idx] @ W, ytr_d[idx], weight=w)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    with torch.no_grad():
        pred = (Xev_d @ W).argmax(-1).cpu()
        f1, prec, rec = macro_f1_binary(pred.tolist(), yev.tolist())
        logits = (Xev_d @ W)[:, 1].cpu()
        acc = float((pred == yev).float().mean())
    return acc, f1, prec, rec, logits, yev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train-seqs", type=int, default=8000)
    ap.add_argument("--n-eval-seqs", type=int, default=1500)
    ap.add_argument("--random-init", type=int, default=None,
                    help="S4 control on the structure task: probe a "
                         "RANDOM-INIT model (seed) with the same arch")
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    tab = pq.read_table(BPRNA).to_pydict()
    by_split = {"train": [], "test": []}
    for i, sp in enumerate(tab["split"]):
        if sp in by_split:
            by_split[sp].append(i)
    rng = random.Random(17)
    tr_idx = rng.sample(by_split["train"],
                        min(args.n_train_seqs, len(by_split["train"])))
    ev_idx = rng.sample(by_split["test"],
                        min(args.n_eval_seqs, len(by_split["test"])))
    tr_seqs = [tab["seq"][i] for i in tr_idx]
    tr_pairs = [tab["pairs"][i] for i in tr_idx]
    ev_seqs = [tab["seq"][i] for i in ev_idx]
    ev_pairs = [tab["pairs"][i] for i in ev_idx]
    tr_src = [tab["source"][i] for i in tr_idx]
    ev_src = [tab["source"][i] for i in ev_idx]
    print("train seqs=%d eval seqs=%d (sources: %s)" %
          (len(tr_seqs), len(ev_seqs),
           sorted(set(ev_src))[:6]))

    model, ck = load_encoder(args.run_dir)
    if args.random_init is not None:
        from rna_sc.model import RNAMLMEncoder
        torch.manual_seed(args.random_init)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        run_name = "%s_randinit%d" % (
            os.path.basename(args.run_dir), args.random_init)
    else:
        run_name = os.path.basename(args.run_dir)
    L = ck["cfg"]["arch"]["n_layers"]
    Xtr, ytr = collect_token_states(model, dev, tr_seqs, tr_pairs, L)
    Xev, yev = collect_token_states(model, dev, ev_seqs, ev_pairs, L)
    print("tokens: train=%d eval=%d (paired rate train=%.3f eval=%.3f)"
          % (len(ytr), len(yev), float(ytr.float().mean()),
             float(yev.float().mean())))

    best = None
    for li in range(L):
        acc, f1, prec, rec, _, _ = run_one_layer(
            Xtr[li], ytr, Xev[li], yev, dev, seed=17 + li)
        rec_out = {"run": run_name, "task": "bpRNA paired-position",
                   "layer": li, "rel_depth": round(li / (L - 1), 3),
                   "acc": round(acc, 4), "f1": round(f1, 4),
                   "precision": round(prec, 4), "recall": round(rec, 4),
                   "n_tokens_train": len(ytr), "n_tokens_eval": len(yev)}
        with open(OUT_JSONL, "a") as fh:
            fh.write(json.dumps(rec_out) + "\n")
        print("layer %d (rel %.2f) acc=%.4f f1=%.4f prec=%.4f rec=%.4f"
              % (li, li / (L - 1), acc, f1, prec, rec))
        if best is None or f1 > best["f1"]:
            best = rec_out
    best["run"] = run_name
    best["task"] = "bpRNA paired-position (S7 first structure task)"
    with open(OUT_JSON, "w") as fh:
        json.dump(best, fh, indent=2)
    print("BEST:", json.dumps(best, indent=2))
    print("saved", OUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
