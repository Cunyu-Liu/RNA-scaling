from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster-tsv", required=True, type=Path)
    ap.add_argument("--cluster-split", required=True, type=Path)
    ap.add_argument("--n-sequences", required=True, type=int)
    ap.add_argument("--output-json", required=True, type=Path)
    args = ap.parse_args()

    old_ids_list = pq.read_table(args.cluster_split, columns=["cluster_id"]).column("cluster_id").to_pylist()
    old_ids = set(old_ids_list)
    new_reps: set[str] = set()
    seen = bytearray(args.n_sequences)
    rows = 0
    duplicate_members = 0
    invalid_members = 0
    self_representative_rows = 0

    with args.cluster_tsv.open() as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 2:
                raise ValueError(f"Malformed cluster row {rows + 1}: {line!r}")
            rep = int(fields[0])
            member = int(fields[1])
            rows += 1
            new_reps.add(str(rep))
            self_representative_rows += int(rep == member)
            if member < 0 or member >= args.n_sequences:
                invalid_members += 1
            elif seen[member]:
                duplicate_members += 1
            else:
                seen[member] = 1

    old_only = sorted(old_ids - new_reps, key=int)
    new_only = sorted(new_reps - old_ids, key=int)
    result = {
        "cluster_tsv": str(args.cluster_tsv),
        "cluster_split": str(args.cluster_split),
        "expected_sequences": args.n_sequences,
        "cluster_rows": rows,
        "expected_old_clusters": len(old_ids),
        "old_cluster_rows": len(old_ids_list),
        "new_clusters": len(new_reps),
        "old_only_count": len(old_only),
        "new_only_count": len(new_only),
        "old_only_examples": old_only[:20],
        "new_only_examples": new_only[:20],
        "missing_members": seen.count(0),
        "duplicate_members": duplicate_members,
        "invalid_members": invalid_members,
        "self_representative_rows": self_representative_rows,
    }
    result["pass"] = (
        rows == args.n_sequences
        and len(old_ids_list) == len(old_ids) == 3_357_201
        and len(new_reps) == len(old_ids)
        and not old_only
        and not new_only
        and result["missing_members"] == 0
        and duplicate_members == 0
        and invalid_members == 0
        and self_representative_rows == len(new_reps)
    )
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
