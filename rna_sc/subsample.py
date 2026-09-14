"""Cluster-stratified corpus subsampling for the S2 data-size axis (Q3 fix).

Replaces the old 'prefix' sampling (streaming the first-N rows) with proper
cluster-stratified random subsampling:
  - sample WHOLE clusters at random (seeded) until the sequence budget is met;
  - families never get half-cut; composition follows the global cluster-size
    distribution in expectation;
  - output: a sampled cluster-id list written to a parquet; iter_mlm_batches
    gains a cluster-allowlist path so training streams only sampled clusters.

The already-run prefix-c1M is KEPT as a robustness control (sampling-method
effect), per owner decision 2026-09-15.
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
OUT_DIR = "/mnt/cunyuliu/rna-sc/data/subsamples"
SEED = 17


def build_cluster_index() -> dict[str, list[int]]:
    """cluster_id -> row indices in the train split (one pass)."""
    pf = pq.ParquetFile(SPLIT)
    clusters: dict[str, list[int]] = {}
    row = 0
    for rb in pf.iter_batches(batch_size=200_000,
                              columns=["split_membership", "cluster_id"]):
        d = rb.to_pydict()
        for sm, cid in zip(d["split_membership"], d["cluster_id"]):
            if sm == "train":
                clusters.setdefault(cid, []).append(row)
            row += 1
    return clusters


def sample_clusters(clusters: dict[str, list[int]], n_seq: int,
                    seed: int) -> list[str]:
    rng = random.Random(seed)
    cids = list(clusters.keys())
    rng.shuffle(cids)
    picked, total = [], 0
    for cid in cids:
        if total >= n_seq:
            break
        picked.append(cid)
        total += len(clusters[cid])
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-seq", type=int, required=True,
                    help="target sequence count (e.g. 1000000)")
    ap.add_argument("--tag", required=True, help="e.g. c1Mcs (cs=cluster-strat)")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    clusters = build_cluster_index()
    picked = sample_clusters(clusters, args.n_seq, args.seed)
    n = sum(len(clusters[c]) for c in picked)
    out = os.path.join(OUT_DIR, "%s.parquet" % args.tag)
    pq.write_table(pa.table({"cluster_id": picked}), out)
    meta = {
        "tag": args.tag, "n_seq_target": args.n_seq, "n_seq_actual": n,
        "n_clusters": len(picked), "seed": args.seed,
        "method": "cluster-stratified (whole-cluster random, seeded)",
        "allowlist_path": out,
    }
    with open(os.path.join(OUT_DIR, "%s.json" % args.tag), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
