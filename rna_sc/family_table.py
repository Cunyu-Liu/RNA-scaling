"""Global family assignment table (T0.2.2 / Z1, acceptance A4).

Every evaluation sequence (bpRNA / ArchiveII / Rfam / RNAGym) is mapped to
the release22 split via sequence-cluster identity, using the cluster_id as
the GLOBAL family key. Rule (Z1):
  - an eval dataset sequence whose cluster appears in TRAIN -> eval must
    use a family-level split that excludes that cluster from the fine-tune
    side (or the sequence is flagged contaminated);
  - an eval sequence matching a family_validation/family_test cluster ->
    clean holdout.
Output: /mnt/cunyuliu/rna-sc/data/family_assignment.parquet + summary JSON.

Stage 1 (this script): build the release22 cluster index
  (cluster_id -> split) + sequence-hash lookup for eval-set joins.
Stage 2 (when eval datasets land): join each dataset, emit per-dataset
  assignment tables with unique family ownership.
"""
from __future__ import annotations

import collections
import json
import sys

import pyarrow.parquet as pq

SPLIT = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/family_index_summary.json"
OUT_PARQUET = "/mnt/cunyuliu/rna-sc/data/release22_cluster_split.parquet"


def main() -> int:
    import os
    os.makedirs(os.path.dirname(OUT_PARQUET), exist_ok=True)
    pf = pq.ParquetFile(SPLIT)
    cluster_split = {}
    n = 0
    for rb in pf.iter_batches(batch_size=500_000,
                               columns=["cluster_id", "split_membership"]):
        d = rb.to_pydict()
        for cid, sm in zip(d["cluster_id"], d["split_membership"]):
            prev = cluster_split.get(cid)
            if prev is None:
                cluster_split[cid] = sm
            elif prev != sm:
                print("FATAL: cluster %s spans splits (%s vs %s) — split "
                      "is NOT cluster-pure" % (cid, prev, sm), file=sys.stderr)
                return 1
            n += 1
    # write compact cluster -> split table
    import pyarrow as pa
    tbl = pa.table({
        "cluster_id": list(cluster_split.keys()),
        "split": list(cluster_split.values()),
    })
    pq.write_table(tbl, OUT_PARQUET)
    cnt = collections.Counter(cluster_split.values())
    summary = {
        "rows_scanned": n,
        "clusters": len(cluster_split),
        "cluster_split_counts": dict(cnt),
        "cluster_pure": True,
        "index_path": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
