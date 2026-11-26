from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-parquet", required=True, type=Path)
    ap.add_argument("--n-train", type=int, default=20_000)
    ap.add_argument("--n-eval", type=int, default=4_000)
    ap.add_argument("--output-json", required=True, type=Path)
    args = ap.parse_args()

    targets = {"family_validation": args.n_train, "family_test": args.n_eval}
    counts = dict.fromkeys(targets, 0)
    labels = {key: set() for key in targets}
    pf = pq.ParquetFile(args.split_parquet)
    for batch in pf.iter_batches(batch_size=50_000, columns=["split_membership", "canonical_sequence", "rna_type"]):
        data = batch.to_pydict()
        for split, seq, rna_type in zip(data["split_membership"], data["canonical_sequence"], data["rna_type"]):
            if split not in targets or counts[split] >= targets[split]:
                continue
            encoded = [base for base in seq[:256].upper().replace("T", "U") if base in "ACGU"]
            if len(encoded) < 2:
                continue
            counts[split] += 1
            labels[split].add(rna_type)
        if all(counts[key] >= targets[key] for key in targets):
            break

    result = {
        "file": str(args.split_parquet),
        "protocol": "probe.collect_states: stream order, first 256 nt, ACGU filter, len >= 2",
        "family_validation_count": counts["family_validation"],
        "family_validation_target": args.n_train,
        "family_test_count": counts["family_test"],
        "family_test_target": args.n_eval,
        "family_validation_classes": len(labels["family_validation"]),
        "family_test_classes": len(labels["family_test"]),
        "family_test_labels_missing_from_validation": sorted(labels["family_test"] - labels["family_validation"]),
    }
    result["pass"] = counts == targets
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
