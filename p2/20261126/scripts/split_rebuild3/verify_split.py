from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

EXPECTED_SPLITS = {
    "train": 14_130_321,
    "validation": 164_280,
    "test": 108_979,
    "family_validation": 7_525_752,
    "family_test": 7_082_895,
}
EXPECTED_LENGTH_BINS = {"16-4096": 28_756_105, "4097-16384": 208_293, "<16": 8_891, ">16384": 38_938}
EXPECTED_ALPHABET = {"A": 29_009_257, "C": 29_006_295, "G": 29_008_086, "U": 29_009_979}
ORIGINAL_SHA256 = "eaa9e44ff760d79ad0f52debb555ebf808afa6adda7bb09644215bec72586b8a"


def length_bin(length: int) -> str:
    if length < 16:
        return "<16"
    if length <= 4096:
        return "16-4096"
    if length <= 16384:
        return "4097-16384"
    return ">16384"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-parquet", required=True, type=Path)
    ap.add_argument("--cluster-split", required=True, type=Path)
    ap.add_argument("--train-oracle", required=True, type=Path)
    ap.add_argument("--output-json", required=True, type=Path)
    args = ap.parse_args()

    split_table = pq.read_table(args.cluster_split, columns=["cluster_id", "split"])
    split_data = split_table.to_pydict()
    cluster_to_split = dict(zip(split_data["cluster_id"], split_data["split"]))
    del split_table, split_data

    oracle_pf = pq.ParquetFile(args.train_oracle)
    oracle_columns = oracle_pf.schema.names
    oracle_batches = []
    for batch in oracle_pf.iter_batches(batch_size=100_000, columns=oracle_columns):
        data = batch.to_pydict()
        oracle_batches.extend(zip(*(data[column] for column in oracle_columns)))
    hash_index = oracle_columns.index("canonical_sequence_hash")
    oracle = {row[hash_index]: row for row in oracle_batches}
    del oracle_batches

    split_counts: Counter[str] = Counter()
    length_bins: Counter[str] = Counter()
    alphabet_counts: Counter[str] = Counter()
    seen_clusters: set[str] = set()
    rows = 0
    seq_len_min = None
    seq_len_max = 0
    previous_hash = None
    previous_split = None
    hash_order_violations = 0
    duplicate_hash_rows = 0
    exact_sequences_spanning_splits = 0
    canonical_hash_mismatches = 0
    alphabet_violations = 0
    length_mismatches = 0
    length_bin_mismatches = 0
    accession_count_mismatches = 0
    missing_cluster_ids = 0
    cluster_split_mismatches = 0
    oracle_seen = 0
    oracle_mismatches = 0
    oracle_mismatch_examples = []

    candidate_pf = pq.ParquetFile(args.split_parquet)
    candidate_columns = candidate_pf.schema.names
    for batch in candidate_pf.iter_batches(batch_size=50_000, columns=candidate_columns):
        data = batch.to_pydict()
        for i in range(len(data["canonical_sequence_hash"])):
            h = data["canonical_sequence_hash"][i]
            seq = data["canonical_sequence"][i]
            split = data["split_membership"][i]
            cluster = data["cluster_id"][i]
            length = data["length"][i]
            observed_bin = data["length_bin"][i]
            rows += 1
            split_counts[split] += 1
            length_bins[observed_bin] += 1
            seen_clusters.add(cluster)
            seq_len_min = length if seq_len_min is None else min(seq_len_min, length)
            seq_len_max = max(seq_len_max, length)
            for base in "ACGU":
                alphabet_counts[base] += int(base in seq)

            if previous_hash is not None:
                if h < previous_hash:
                    hash_order_violations += 1
                elif h == previous_hash:
                    duplicate_hash_rows += 1
                    exact_sequences_spanning_splits += int(split != previous_split)
            previous_hash = h
            previous_split = split

            canonical_hash_mismatches += int(hashlib.sha256(seq.encode("ascii")).hexdigest() != h)
            alphabet_violations += int(not set(seq) <= set("ACGU"))
            length_mismatches += int(len(seq) != length)
            length_bin_mismatches += int(length_bin(length) != observed_bin)
            accessions = data["accessions"][i]
            accession_count_mismatches += int(accessions.count("\t") + 1 != data["num_accessions"][i])
            expected_split = cluster_to_split.get(cluster)
            if expected_split is None:
                missing_cluster_ids += 1
            elif expected_split != split:
                cluster_split_mismatches += 1

            if h in oracle:
                oracle_seen += 1
                observed = tuple(data[column][i] for column in oracle_columns)
                if observed != oracle[h]:
                    oracle_mismatches += 1
                    if len(oracle_mismatch_examples) < 5:
                        mismatch_fields = [
                            column for column, expected, actual in zip(oracle_columns, oracle[h], observed)
                            if expected != actual and column not in {"canonical_sequence", "accessions"}
                        ]
                        for column in ("canonical_sequence", "accessions"):
                            if oracle[h][oracle_columns.index(column)] != observed[oracle_columns.index(column)]:
                                mismatch_fields.append(column)
                        oracle_mismatch_examples.append({"canonical_sequence_hash": h, "fields": mismatch_fields})
        if rows % 1_000_000 < 50_000:
            print(f"verified approximately {rows:,} rows", flush=True)

    actual_sha256 = file_sha256(args.split_parquet)
    checks = {
        "rows": rows == 29_012_227,
        "split_counts": dict(split_counts) == EXPECTED_SPLITS,
        "length_bins": dict(length_bins) == EXPECTED_LENGTH_BINS,
        "alphabet_counts": dict(alphabet_counts) == EXPECTED_ALPHABET,
        "seq_len_min": seq_len_min == 10,
        "seq_len_max": seq_len_max == 583_414,
        "clusters": len(seen_clusters) == 3_357_201,
        "cluster_mapping_complete": missing_cluster_ids == 0,
        "cluster_mapping_exact": cluster_split_mismatches == 0,
        "hash_nondecreasing": hash_order_violations == 0,
        "canonical_hashes_unique": duplicate_hash_rows == 0,
        "canonical_hash_correct": canonical_hash_mismatches == 0,
        "alphabet_acgu_only": alphabet_violations == 0,
        "length_correct": length_mismatches == 0,
        "length_bin_correct": length_bin_mismatches == 0,
        "accession_counts_correct": accession_count_mismatches == 0,
        "exact_sequences_spanning_splits_zero": exact_sequences_spanning_splits == 0,
        "schema_matches_train_oracle": candidate_columns == oracle_columns,
        "train_oracle_complete": oracle_seen == len(oracle) == 566_077,
        "train_oracle_all_fields_exact": oracle_mismatches == 0,
    }
    result = {
        "file": str(args.split_parquet),
        "rows": rows,
        "split_counts": dict(split_counts),
        "split_ratios": {key: round(value / rows, 4) for key, value in split_counts.items()},
        "length_bins": dict(length_bins),
        "alphabet_counts": dict(alphabet_counts),
        "seq_len_min": seq_len_min,
        "seq_len_max": seq_len_max,
        "clusters": len(seen_clusters),
        "leak_clusters_spanning_splits": cluster_split_mismatches,
        "leak_exact_sequences_spanning_splits": exact_sequences_spanning_splits,
        "schema": candidate_columns,
        "hash_order_violations": hash_order_violations,
        "duplicate_hash_rows": duplicate_hash_rows,
        "canonical_hash_mismatches": canonical_hash_mismatches,
        "alphabet_violations": alphabet_violations,
        "length_mismatches": length_mismatches,
        "length_bin_mismatches": length_bin_mismatches,
        "accession_count_mismatches": accession_count_mismatches,
        "missing_cluster_ids": missing_cluster_ids,
        "cluster_split_mismatches": cluster_split_mismatches,
        "train_oracle_rows": len(oracle),
        "train_oracle_seen": oracle_seen,
        "train_oracle_mismatches": oracle_mismatches,
        "train_oracle_mismatch_examples": oracle_mismatch_examples,
        "actual_sha256": actual_sha256,
        "original_sha256": ORIGINAL_SHA256,
        "file_sha256_matches_original": actual_sha256 == ORIGINAL_SHA256,
        "checks": checks,
        "pass": all(checks.values()),
    }
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
