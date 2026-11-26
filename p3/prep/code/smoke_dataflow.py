from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "code_git"))
from rna_sc.data import IGNORE, iter_mlm_batches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    work = args.output.parent / "synthetic_data"
    work.mkdir(parents=True, exist_ok=True)
    parquet = work / "tiny.parquet"
    sequences = [
        "ACGUACGUACGU", "AAAAACCCCC", "ACGU" * 700,
        "GGGGUUUUAAAA", "AC", "U" * 2049,
    ]
    table = pa.table({
        "split_membership": ["train", "validation", "train", "train", "train", "train"],
        "canonical_sequence": sequences,
        "cluster_id": [str(i) for i in range(len(sequences))],
        "rna_type": ["synthetic"] * len(sequences),
    })
    pq.write_table(table, parquet)
    batches = list(iter_mlm_batches(str(parquet), "train", 29, 1024, 16384))
    if not batches:
        raise RuntimeError("No synthetic batches generated")
    total_valid = sum(batch["valid_nt"] for batch in batches)
    expected_valid = sum(len(seq) for i, seq in enumerate(sequences) if i != 1)
    shapes = []
    for batch in batches:
        if len(batch["ids"]) != len(batch["targets"]):
            raise RuntimeError("ID/target row mismatch")
        if any(len(row) != len(batch["ids"][0]) for row in batch["ids"]):
            raise RuntimeError("Non-rectangular ID batch")
        if any(len(row) != len(batch["targets"][0]) for row in batch["targets"]):
            raise RuntimeError("ID/target shape mismatch")
        if len(batch["ids"]) * len(batch["ids"][0]) > 16384:
            raise RuntimeError("batch_nt overflow")
        masked = sum(value != IGNORE for row in batch["targets"] for value in row)
        if masked == 0:
            raise RuntimeError("No MLM targets")
        shapes.append({"batch": [len(batch["ids"]), len(batch["ids"][0])],
                       "valid_nt": batch["valid_nt"], "masked_targets": masked})
    repeat = list(iter_mlm_batches(str(parquet), "train", 29, 1024, 16384))
    other_seed = list(iter_mlm_batches(str(parquet), "train", 43, 1024, 16384))
    deterministic = batches == repeat
    seed_changes_mask = batches != other_seed
    result = {
        "mode": "SYNTHETIC_SMOKE_ONLY_NOT_DATA_ACCEPTANCE",
        "batch_shapes": shapes,
        "total_valid_nt": total_valid,
        "expected_valid_nt": expected_valid,
        "nonoverlap_valid_nt_exact": total_valid == expected_valid,
        "deterministic_same_seed": deterministic,
        "different_seed_changes_mask": seed_changes_mask,
    }
    result["pass"] = all([
        result["nonoverlap_valid_nt_exact"], deterministic, seed_changes_mask,
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
