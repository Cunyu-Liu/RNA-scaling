from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import pyarrow.parquet as pq

BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
CORPUS = BACKUP / "data_corpus"
EVIDENCE = BACKUP / "eval_evidence_logs/evidence"
REPO = Path(__file__).resolve().parents[2] / "staging/split_rebuild/tokenizer-benchmark"
OUT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            count += chunk.count(b"\n")
    return count


def main() -> None:
    deep = json.loads((EVIDENCE / "split8080_deep_verify.json").read_text())
    acceptance = json.loads((REPO / "docs/acceptance/P1_acceptance.json").read_text())
    family = json.loads((EVIDENCE / "family_index_summary.json").read_text())
    expected = {
        "target_schema_minimum": ["split_membership", "canonical_sequence", "rna_type"],
        "deep_verify": deep,
        "artifact_sha256": acceptance["artifact_hashes"],
        "upstream_counts": {
            "fasta_records": 30191670,
            "primary_records": 29252916,
            "qc_records": 938754,
            "deduplicated_records": 29012227,
            "duplicates_merged": 240689,
        },
        "cluster_split_counts": family["cluster_split_counts"],
        "provenance": {
            "deep_verify": str(EVIDENCE / "split8080_deep_verify.json"),
            "family_index_summary": str(EVIDENCE / "family_index_summary.json"),
            "acceptance_repo": "https://github.com/Cunyu-Liu/tokenizer-benchmark",
            "acceptance_commit": "a236530f8348f7d02ff74c15ce9267ee0989954f",
            "acceptance_file": "docs/acceptance/P1_acceptance.json",
        },
    }
    (OUT / "expected_stats.json").write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n")

    records = []
    for path in sorted(CORPUS.rglob("*.parquet")):
        if path.name.startswith("._"):
            continue
        record = {
            "path": str(path.relative_to(CORPUS)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        try:
            parquet = pq.ParquetFile(path)
            record["read_status"] = "READABLE"
            record["rows"] = parquet.metadata.num_rows
            record["row_groups"] = parquet.metadata.num_row_groups
            record["fields"] = [{"name": field.name, "type": str(field.type)} for field in parquet.schema_arrow]
        except Exception as exc:
            record["read_status"] = "UNREADABLE"
            record["error"] = str(exc)
        records.append(record)

    work_records = []
    work = CORPUS / "rinalmo_corpus_work"
    for name in ["extract.done", "dedup_eval.done", "cluster.done", "mmseqs_out_cluster.tsv", "clusters_dedup.tsv", "mmseqs_out_rep_seq.fasta"]:
        path = work / name
        record = {"path": str(path.relative_to(CORPUS)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        if path.suffix in {".tsv", ".fasta"}:
            record["lines"] = line_count(path)
        else:
            record["content"] = path.read_text().strip()
        work_records.append(record)
    work_records.append({
        "missing_required_intermediates": ["all_raw.fasta", "all_uniq.fasta"],
        "reason": "Member IDs alone cannot restore canonical_sequence; dedup_eval also removes held-out rows.",
    })

    cluster_path = CORPUS / "release22_cluster_split.parquet"
    table = pq.read_table(cluster_path)
    clusters = table.column("cluster_id").to_pylist()
    splits = table.column("split").to_pylist()
    observed_cluster_counts = dict(collections.Counter(splits))
    cluster_audit = {
        "rows": len(clusters),
        "unique_clusters": len(set(clusters)),
        "null_cluster_ids": sum(value is None for value in clusters),
        "split_counts": observed_cluster_counts,
        "matches_family_index_summary": observed_cluster_counts == family["cluster_split_counts"],
    }
    inventory = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "backup_root_read_only": str(BACKUP),
        "parquet_sources": records,
        "rinalmo_work": work_records,
        "cluster_split_audit": cluster_audit,
        "tokenizer_benchmark_commit": "a236530f8348f7d02ff74c15ce9267ee0989954f",
    }
    (OUT / "source_inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
    with (OUT / "source_inventory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256", "read_status", "rows", "row_groups", "schema", "error"])
        writer.writeheader()
        for record in records:
            writer.writerow({
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "read_status": record["read_status"],
                "rows": record.get("rows"),
                "row_groups": record.get("row_groups"),
                "schema": json.dumps(record.get("fields", []), ensure_ascii=False),
                "error": record.get("error", ""),
            })
    print(json.dumps({"parquet_files": len(records), "cluster_split_audit": cluster_audit}, indent=2))


if __name__ == "__main__":
    main()
