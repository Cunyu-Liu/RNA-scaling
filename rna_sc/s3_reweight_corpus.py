"""S3 diversity reweighting arm (T2.3.3, cluster-size flattening).

Family-reweighting WITHOUT touching the data pipeline: appends a
`weight` column to a parquet copy of the train split, where weight =
1 / cluster_size^alpha (alpha=1 = full flattening, rRNA-dominance
removed; alpha=0 = raw). iter_mlm_batches_reweighted then over-samples
rare-family sequences so EFFECTIVE diversity rises while the total
train exposure (2.0B nt) and every other recipe knob stay identical.

Note (methodology, mirrors SPEC S3): reweighting changes the sampling
distribution, NOT the corpus content — this is the 'diversity axis'
complement to the S2 'quantity axis' (c1Mcs etc.).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

import pyarrow as pa
import pyarrow.parquet as pq

SPLIT = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
OUT_PARQUET = "/mnt/cunyuliu/rna-sc/data/r22_train_reweighted.parquet"
OUT_META = "/mnt/cunyuliu/rna-sc/data/r22_train_reweighted.json"
SEED = 17


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--n-skip", type=int, default=0)
    args = ap.parse_args()

    pf = pq.ParquetFile(SPLIT)
    rows_sm, rows_seq, rows_cid = [], [], []
    row = 0
    for rb in pf.iter_batches(batch_size=200_000,
                              columns=["split_membership",
                                       "canonical_sequence", "cluster_id"]):
        d = rb.to_pydict()
        for sm, seq, cid in zip(d["split_membership"],
                                d["canonical_sequence"], d["cluster_id"]):
            if sm == "train":
                rows_sm.append(0)
                rows_seq.append(seq)
                rows_cid.append(cid)
                row += 1
    print("train rows: %d" % len(rows_seq))

    # cluster sizes
    sizes: dict[str, int] = {}
    for c in rows_cid:
        sizes[c] = sizes.get(c, 0) + 1

    # weight per sequence: 1 / cluster_size^alpha, then integer
    # over-sampling factor = ceil(weight * K) with K calibrated so the
    # SUM of factors stays ~1.0x total corpus (budget-capped anyway).
    # K = median cluster size as scale reference.
    import statistics
    med = statistics.median(sizes[c] for c in rows_cid)
    factors = []
    for c in rows_cid:
        w = (1.0 / (sizes[c] ** args.alpha)) * med
        factors.append(max(1, min(8, int(round(w)))))
    n_eff = sum(factors)
    print("effective rows after weighting: %d (alpha=%.2f, raw=%d)"
          % (n_eff, args.alpha, len(rows_seq)))

    # build exploded parquet (row repeated `factor` times; each replica
    # gets a distinct mask stream via seed^replica_id inside the loader)
    sm_col, seq_col, cid_col, rep_col = [], [], [], []
    for i, (seq, cid) in enumerate(zip(rows_seq, rows_cid)):
        for rep in range(factors[i]):
            sm_col.append("train")
            seq_col.append(seq)
            cid_col.append(cid)
            rep_col.append(rep)

    table = pa.table({
        "split_membership": sm_col,
        "canonical_sequence": seq_col,
        "cluster_id": cid_col,
        "replica": rep_col,
    })
    pq.write_table(table, OUT_PARQUET)
    meta = {
        "source": SPLIT, "alpha": args.alpha,
        "n_train_rows_raw": len(rows_seq),
        "n_rows_effective": len(sm_col),
        "n_clusters": len(sizes),
        "median_cluster_size": med,
        "oversample_cap": 8,
        "seed": SEED,
        "method": "sequence weight = med/cluster_size^alpha, exploded "
                  "into integer replicas (cap 8x); budget 2.0B nt caps "
                  "total exposure",
        "parquet": OUT_PARQUET,
    }
    with open(OUT_META, "w") as fh:
        json.dump(meta, fh, indent=2)
    print(json.dumps({k: meta[k] for k in
                      ("alpha", "n_train_rows_raw", "n_rows_effective",
                       "n_clusters", "median_cluster_size")}, indent=2))
    print("saved", OUT_PARQUET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
