from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pyarrow.parquet as pq

from p2_4_common import (
    ARMS, BPRNA, BOOTSTRAP_N, EXPECTED_SPLIT_COUNTS, EXPECTED_SPLIT_ROWS,
    K, LEN_CAP, LONG_RANGE, N_REAL, OUT, RAND_MULT, SEED, SPLIT,
    clean_seq, coordinate_validation, di_freq, ks_check, make_random_pool,
    mono_freq, sha256, stream_real, write_json,
)


def inspect_split(path):
    pf = pq.ParquetFile(path)
    counts = Counter()
    for batch in pf.iter_batches(batch_size=500_000,
                                 columns=["split_membership"]):
        counts.update(batch.column(0).to_pylist())
    return {
        "path": str(path),
        "sha256": sha256(path),
        "rows": pf.metadata.num_rows,
        "row_groups": pf.num_row_groups,
        "columns": pf.schema.names,
        "split_counts": dict(sorted(counts.items())),
    }


def validate_source(path):
    actual = inspect_split(path)
    required = {"split_membership", "canonical_sequence", "rna_type"}
    reasons = []
    if actual["rows"] != EXPECTED_SPLIT_ROWS:
        reasons.append(f"rows {actual['rows']} != {EXPECTED_SPLIT_ROWS}")
    if actual["split_counts"] != EXPECTED_SPLIT_COUNTS:
        reasons.append("split_counts differ from the legacy verified asset")
    missing = sorted(required - set(actual["columns"]))
    if missing:
        reasons.append(f"missing columns: {missing}")
    return actual, reasons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default=str(SPLIT))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    validation = coordinate_validation()
    write_json(OUT / "p2_4_coordinate_validation.json", validation)

    if not args.split or not __import__("pathlib").Path(args.split).is_file():
        blocker = {
            "task": "X-P24 / P2.4",
            "status": "BLOCKED_MISSING_SOURCE",
            "reason": f"split parquet not found: {args.split}",
            "expected_rows": EXPECTED_SPLIT_ROWS,
            "expected_split_counts": EXPECTED_SPLIT_COUNTS,
            "coordinate_validation": validation,
        }
        write_json(OUT / "p2_4_input_blocker.json", blocker)
        raise SystemExit(2)

    actual, reasons = validate_source(args.split)
    if reasons:
        blocker = {
            "task": "X-P24 / P2.4",
            "status": "BLOCKED_MISMATCHED_SOURCE",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "reasons": reasons,
            "actual": actual,
            "expected": {
                "rows": EXPECTED_SPLIT_ROWS,
                "split_counts": EXPECTED_SPLIT_COUNTS,
                "required_columns": ["split_membership", "canonical_sequence", "rna_type"],
                "legacy_verification": "results/upload_main/split8080_deep_verify_legacy.json",
            },
            "formal_run_started": False,
            "coordinate_validation": validation,
        }
        write_json(OUT / "p2_4_input_blocker.json", blocker)
        print("BLOCKED_MISMATCHED_SOURCE", reasons, flush=True)
        raise SystemExit(2)

    real = stream_real(N_REAL, SEED, args.split)
    assert len(real) == N_REAL
    random_seqs, expected_mono, expected_di = make_random_pool(
        [seq for seq, _ in real], RAND_MULT, SEED)
    assert len(random_seqs) == N_REAL * RAND_MULT
    real_mono = mono_freq([seq for seq, _ in real])
    random_mono = mono_freq(random_seqs)
    real_di = di_freq([seq for seq, _ in real])
    random_di = di_freq(random_seqs)
    ks_d, ks_p = ks_check([len(seq) for seq, _ in real],
                          [len(seq) for seq in random_seqs])
    mono_dev = max(abs(real_mono[b] - random_mono[b]) for b in real_mono)
    di_dev = max(abs(real_di[key] - random_di[key]) for key in real_di)
    qc = {
        "seed_real": SEED,
        "seed_random": SEED,
        "n_real": len(real),
        "n_random": len(random_seqs),
        "ks_d": ks_d,
        "ks_p": ks_p,
        "real_mono": real_mono,
        "random_mono": random_mono,
        "mono_max_abs_dev": mono_dev,
        "real_di": real_di,
        "random_di": random_di,
        "di_max_abs_dev": di_dev,
        "generator_expected_mono": expected_mono,
        "generator_expected_di": expected_di,
        "legacy_hard_gate": {"ks_p>0.05": ks_p > 0.05,
                             "mono_max_abs_dev<0.02": mono_dev < 0.02},
    }
    qc["passed"] = all(qc["legacy_hard_gate"].values())
    write_json(OUT / "p2_4_random_pool_qc.json", qc)
    if not qc["passed"]:
        raise RuntimeError(f"random-pool QC failed: {qc}")

    rows = pq.read_table(BPRNA).to_pydict()
    train, test = [], []
    for index, (name, source, split, seq, pairs) in enumerate(zip(
            rows["name"], rows["source"], rows["split"], rows["seq"],
            rows["pairs"])):
        cleaned = clean_seq(seq)
        record = {
            "sequence_id": f"bpRNA_{split}_row{index}",
            "source_row": index,
            "name": name,
            "source": source,
            "sequence": cleaned,
            "pairs": pairs,
        }
        if split == "train" and pairs is not None and len(train) < 2000:
            train.append(record)
        elif split == "test" and pairs and len(cleaned) >= 8:
            test.append(record)
    assert len(train) == 2000
    assert test and len({row["sequence_id"] for row in test}) == len(test)
    lengths = np.asarray([len(row["sequence"]) for row in test])
    length_edges = np.quantile(lengths, [0.25, 0.5, 0.75]).tolist()
    freeze = {
        "task": "X-P24 / P2.4",
        "status": "FROZEN",
        "protocol": {
            "real_pool": "stream_real(1500, seed=17), original parquet order",
            "random_pool": "make_random_pool(real, 3, seed=17)",
            "rns": "RNS@10 in TS0 real + shared random pool, self excluded",
            "layers": {arm: spec["layer"] for arm, spec in ARMS.items()},
            "train": "TR0 first 2000 rows with pairs not None, parquet order",
            "test": "TS0 pairs nonempty and clean length>=8",
            "clean": f"ACGU-only, T->U, LEN_CAP={LEN_CAP}",
            "pair_coordinates": "1-based -> 0-based (i0=i-1,j0=j-1)",
            "long_range_separation": LONG_RANGE,
            "rns_k": K,
            "head": "linear 2-class, Adam lr=1e-3, 3 epochs, token batch=65536",
            "head_seed_per_arm": SEED,
            "randinit_seed": SEED,
            "length_edges_method": "np.quantile(all eligible TS0 lengths,[.25,.5,.75])",
            "rns_bins": "arm-specific global and within-length terciles",
            "bootstrap": {"n": BOOTSTRAP_N, "seed": SEED,
                          "unit": "sequence", "ci": "percentile 95%",
                          "bins": "fixed from original per-sequence table"},
        },
        "source_split": actual,
        "bpRNA": {"path": str(BPRNA), "sha256": sha256(BPRNA)},
        "n_train": len(train),
        "n_test": len(test),
        "test_length_edges": length_edges,
        "test_length_min_max": [int(lengths.min()), int(lengths.max())],
        "train_rows": train,
        "test_rows": test,
        "random_real_rows": [
            {"sequence_id": f"family_validation_{i}", "sequence": seq,
             "rna_type": rna_type}
            for i, (seq, rna_type) in enumerate(real)
        ],
        "random_rows": [
            {"sequence_id": f"random_{i}", "sequence": seq}
            for i, seq in enumerate(random_seqs)
        ],
        "coordinate_validation": validation,
    }
    write_json(OUT / "p2_4_shared_freeze.json", freeze)
    write_json(OUT / "p2_4_shared_freeze_sha256.json", {
        "path": str(OUT / "p2_4_shared_freeze.json"),
        "sha256": sha256(OUT / "p2_4_shared_freeze.json"),
    })
    (OUT / "p2_4_input_blocker.json").unlink(missing_ok=True)
    print(f"FROZEN train={len(train)} test={len(test)} "
          f"random={len(random_seqs)} length_edges={length_edges}", flush=True)


if __name__ == "__main__":
    main()
