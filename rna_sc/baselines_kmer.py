"""T1.2.5 classical ML baselines (Q4, NABench reviewer-endorsed).

Every downstream task gets a non-LM baseline row so "pretraining gain"
is reported as LM - strongest classical baseline (paper discipline).

v1 scope: rna_type classification (S11 global property task),
  - k-mer(1-6) frequency + logistic regression (class-weighted)
  - k-mer(3) + ridge (fallback linear)
Features: per-sequence k-mer frequency vector (4^1+4^2+...+4^6 = 5460
dims, sparse in practice). Deterministic: kmer index = base4 encoding.
Splits: family (family_validation -> family_test, day-1 protocol) and
random (same i%5 rule as eval_matrix for exact comparability).

Output: evidence/classical_baselines.json + stdout table.

Usage: python -m rna_sc.baselines_kmer [--device N] (GPU only used for
parity checks; k-mer extraction is CPU streaming, model-free)
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pyarrow.parquet as pq

SPLIT_8080 = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
OUT = "/mnt/cunyuliu/rna-sc/evidence/classical_baselines.json"
ALPHABET = "ACGU"
KMAX = 6
N_FEATS = sum(4 ** k for k in range(1, KMAX + 1))


def kmer_index(kmer: str) -> int:
    v = 0
    for ch in kmer:
        v = v * 4 + ALPHABET.index(ch)
    return v


def offset_for_k(k: int) -> int:
    return sum(4 ** j for j in range(1, k))


def seq_to_feats(seq: str) -> np.ndarray:
    x = np.zeros(N_FEATS, dtype=np.float32)
    canon = seq.upper().replace("T", "U")
    L = len(canon)
    for k in range(1, KMAX + 1):
        off = offset_for_k(k)
        denom = max(1, L - k + 1)
        for i in range(L - k + 1):
            km = canon[i:i + k]
            if all(c in ALPHABET for c in km):
                x[off + kmer_index(km)] += 1.0 / denom
    return x


def collect_rows(split: str, n_seq: int):
    """Stream (sequence, rna_type) rows from a split pool."""
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


def macro_f1(y_true, y_pred, classes):
    from collections import Counter
    ct = Counter(zip(y_true, y_pred))
    per = []
    for c in classes:
        tp = ct[(c, c)]
        fp = sum(v for (t, p), v in ct.items() if p == c and t != c)
        fn = sum(v for (t, p), v in ct.items() if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per.append(f1)
    return float(np.mean(per)), per


def run_split(Xtr, ytr, Xev, yev, seed=17):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    classes = sorted(set(ytr))
    cls_map = {c: i for i, c in enumerate(classes)}
    ytri = np.array([cls_map[c] for c in ytr])
    keep_ev = np.array([i for i, c in enumerate(yev) if c in cls_map])
    yevi = np.array([cls_map[yev[i]] for i in keep_ev])
    Xev_k = Xev[keep_ev]

    sc = StandardScaler(with_mean=False)
    Xtr_s = sc.fit_transform(Xtr)
    Xev_s = sc.transform(Xev_k)

    clf = LogisticRegression(
        max_iter=2000, class_weight="balanced", C=1.0,
        solver="lbfgs", random_state=seed)
    clf.fit(Xtr_s, ytri)
    pred = clf.predict(Xev_s)
    acc = float((pred == yevi).mean())
    f1, _ = macro_f1(list(yevi), list(pred), range(len(classes)))
    return acc, f1, len(classes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    args = ap.parse_args()

    out = {}
    # family split (day-1 protocol, direct LM comparison)
    tr_seqs, y_tr = collect_rows("family_validation", args.n_train)
    ev_seqs, y_ev = collect_rows("family_test", args.n_eval)
    Xtr = np.stack([seq_to_feats(s) for s in tr_seqs])
    Xev = np.stack([seq_to_feats(s) for s in ev_seqs])
    acc, f1, nc = run_split(Xtr, y_tr, Xev, y_ev)
    out["family"] = {"acc": round(acc, 4), "f1_macro": round(f1, 4),
                     "n_classes": nc, "n_train": len(y_tr),
                     "n_eval": len(y_ev),
                     "baseline": "kmer1-6+logistic(balanced)"}
    print("family: acc=%.4f f1=%.4f (classes=%d)" % (acc, f1, nc))

    # random split (i%5 rule, exact eval_matrix comparability)
    n_all = args.n_train + args.n_eval
    all_seqs, y_all = collect_rows("family_validation", n_all)
    idx_ev = [i for i in range(n_all) if i % 5 == 0]
    idx_tr = [i for i in range(n_all) if i % 5 != 0]
    Xtr2 = np.stack([seq_to_feats(all_seqs[i]) for i in idx_tr])
    Xev2 = np.stack([seq_to_feats(all_seqs[i]) for i in idx_ev])
    acc2, f12, _ = run_split(Xtr2, [y_all[i] for i in idx_tr],
                             Xev2, [y_all[i] for i in idx_ev])
    out["random"] = {"acc": round(acc2, 4), "f1_macro": round(f12, 4),
                     "n_train": len(idx_tr), "n_eval": len(idx_ev),
                     "baseline": "kmer1-6+logistic(balanced)"}
    print("random: acc=%.4f f1=%.4f" % (acc2, f12))
    out["delta_random_family"] = round(f12 - f1, 4)

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
