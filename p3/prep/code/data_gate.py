from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
WORK = BASE / "data/split_rebuild3"
EXPECTED_SPLITS = {
    "train": 14_130_321,
    "validation": 164_280,
    "test": 108_979,
    "family_validation": 7_525_752,
    "family_test": 7_082_895,
}
REQUIRED_COLUMNS = {
    "canonical_sequence", "rna_type", "cluster_id", "split_membership",
    "canonical_sequence_hash", "length", "length_bin", "accessions",
    "num_accessions",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-parquet", type=Path,
                        default=BASE / "data/release22_split_8080.parquet")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    deep_path = WORK / "split8080_deep_verify_rebuilt.json"
    representatives_path = WORK / "representative_verify.json"
    probe_path = WORK / "probe_count_smoke.json"
    stage_path = BASE / "logs/split_rebuild3/pipeline_stage.txt"
    result = {"data_parquet": str(args.data_parquet), "checks": {}}

    def check(name: str, condition: bool) -> None:
        result["checks"][name] = bool(condition)

    check("final_parquet_exists", args.data_parquet.is_file())
    check("deep_receipt_exists", deep_path.is_file())
    check("representative_receipt_exists", representatives_path.is_file())
    check("probe_receipt_exists", probe_path.is_file())
    check("pipeline_complete", stage_path.is_file() and
          stage_path.read_text().strip().splitlines()[-1].endswith(" COMPLETE"))
    if not all(result["checks"].values()):
        result["pass"] = False
        finish(args.output, result)

    deep = read_json(deep_path)
    representatives = read_json(representatives_path)
    probe = read_json(probe_path)
    actual_sha256 = sha256(args.data_parquet)
    result["actual_sha256"] = actual_sha256
    result["deep_receipt"] = str(deep_path)
    result["representative_receipt"] = str(representatives_path)
    result["probe_receipt"] = str(probe_path)
    check("deep_full_content_pass", deep.get("pass") is True and
          all(deep.get("checks", {}).values()))
    check("deep_receipt_bound_to_final_file",
          Path(deep.get("file", "")) in {
              args.data_parquet, WORK / "release22_split_8080.candidate.parquet"
          } and deep.get("actual_sha256") == actual_sha256)
    check("rows_exact", deep.get("rows") == 29_012_227)
    check("split_counts_exact", deep.get("split_counts") == EXPECTED_SPLITS)
    check("cluster_mapping_bidirectional_pass", representatives.get("pass") is True and
          representatives.get("old_only_count") == 0 and
          representatives.get("new_only_count") == 0)
    check("no_cluster_or_exact_sequence_leak",
          deep.get("leak_clusters_spanning_splits") == 0 and
          deep.get("leak_exact_sequences_spanning_splits") == 0)
    check("train_oracle_566077_all_fields_exact",
          deep.get("checks", {}).get("train_oracle_complete") is True and
          deep.get("checks", {}).get("train_oracle_all_fields_exact") is True and
          deep.get("train_oracle_rows") == 566_077)
    check("probe_stream_counts_pass", probe.get("pass") is True and
          probe.get("family_validation_count") == 20_000 and
          probe.get("family_test_count") == 4_000)
    parquet = pq.ParquetFile(args.data_parquet)
    check("physical_rows_match_receipt", parquet.metadata.num_rows == 29_012_227)
    check("required_schema_present", REQUIRED_COLUMNS <= set(parquet.schema.names))
    result["pass"] = all(result["checks"].values())
    finish(args.output, result)


def finish(output: Path | None, result: dict) -> None:
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    print(text, end="")
    if not result["pass"]:
        raise SystemExit("P3.1 DATA_NOT_READY: refusing training launch")


if __name__ == "__main__":
    main()
