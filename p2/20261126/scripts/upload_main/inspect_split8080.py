import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
TARGET = BASE / "data" / "release22_split_8080.parquet"
CLUSTER = BASE / "data" / "release22_cluster_split.parquet"
OUT = BASE / "results" / "upload_main" / "split8080_assessment.json"
EXPECTED = {
    "rows": 29012227,
    "clusters": 3357201,
    "split_counts": {
        "family_test": 7082895,
        "family_validation": 7525752,
        "test": 108979,
        "train": 14130321,
        "validation": 164280,
    },
}
REQUIRED = ["split_membership", "canonical_sequence", "rna_type"]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    target_exists = TARGET.is_file()
    pf = pq.ParquetFile(CLUSTER)
    counts = Counter()
    for batch in pf.iter_batches(columns=["split"], batch_size=250000):
        counts.update(batch.column(0).to_pylist())
    columns = pf.schema.names
    missing = [column for column in REQUIRED if column not in columns]
    result = {
        "status": "PASS" if target_exists else "BLOCKED_MISSING_SOURCE",
        "target_path": str(TARGET),
        "target_exists": target_exists,
        "target_sha256": sha256(TARGET) if target_exists else None,
        "old_evidence_expected": EXPECTED,
        "cluster_split": {
            "path": str(CLUSTER),
            "sha256": sha256(CLUSTER),
            "rows": pf.metadata.num_rows,
            "columns": columns,
            "schema": str(pf.schema),
            "split_counts": dict(sorted(counts.items())),
            "missing_required_columns": missing,
        },
        "equivalent_reconstruction_possible": False if missing else None,
        "reason": (
            "The cluster table has one row per cluster and no sequence or RNA-type "
            "columns; it cannot reconstruct the old 29,012,227-row sequence table."
            if missing else "Target file exists; run full deep verification separately."
        ),
        "impact": [
            "P2.5 family_validation/family_test probe input remains blocked",
            "P2.7 family_validation random-protocol input remains blocked",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
