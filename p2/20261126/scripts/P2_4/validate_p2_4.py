from __future__ import annotations

import csv
import json
import math

import numpy as np

from p2_4_common import ARMS, BOOTSTRAP_N, OUT, SEED, coordinate_validation, write_json

METRICS = {"all_position": ("all_f1", 30), "long_range": ("long_f1", 20)}
BINS = ["low", "mid", "high"]
LENGTH_BINS = ["Q1", "Q2", "Q3", "Q4"]


def close(actual, expected):
    if actual in (None, "") and expected in (None, ""):
        return True
    return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-10)


def numeric(value):
    return float(value) if value not in (None, "") else np.nan


def recompute(rows, metric):
    field, minimum = METRICS[metric]
    values = np.asarray([numeric(row[field]) for row in rows])
    global_bin = np.asarray([row["global_rns_bin"] for row in rows])
    within_bin = np.asarray([row["within_length_rns_bin"] for row in rows])
    length_bin = np.asarray([row["length_bin"] for row in rows])
    low = values[(global_bin == "low") & np.isfinite(values)]
    high = values[(global_bin == "high") & np.isfinite(values)]
    raw = 100 * (high.mean() - low.mean())
    valid_layers = []
    numerator, denominator = 0.0, 0
    for length in LENGTH_BINS:
        counts = {
            rns_bin: int(np.sum((length_bin == length) & (within_bin == rns_bin)
                                & np.isfinite(values))) for rns_bin in BINS
        }
        if not all(count >= minimum for count in counts.values()):
            continue
        valid_layers.append(length)
        low_layer = values[(length_bin == length) & (within_bin == "low")
                           & np.isfinite(values)]
        high_layer = values[(length_bin == length) & (within_bin == "high")
                            & np.isfinite(values)]
        weight = len(low_layer) + len(high_layer)
        numerator += weight * (high_layer.mean() - low_layer.mean())
        denominator += weight
    adjusted = 100 * numerator / denominator if denominator and len(valid_layers) >= 2 else None
    return raw, adjusted, valid_layers


def main():
    checks = {"coordinate_validation": coordinate_validation()["passed"]}
    smoke_text = "\n".join(
        path.read_text() for path in [
            OUT / "logs" / "smoke.log",
            OUT / "logs" / "smoke_bf16_residual.log",
        ] if path.is_file()
    )
    checks["cuda_bf16_head_seed_smoke"] = all(token in smoke_text for token in [
        '"smoke": "PASS"', '"device": "cuda:0"',
        '"head_seed": 17', '"head_reproducible": true',
        '"cpu_fallback": false',
    ])
    with (OUT / "p2_4_bin_per_sequence.csv").open() as handle:
        sequence_rows = list(csv.DictReader(handle))
    with (OUT / "p2_4_length_decision.csv").open() as handle:
        decision_rows = list(csv.DictReader(handle))
    checks["six_decision_rows"] = len(decision_rows) == 6
    blocker_path = OUT / "p2_4_input_blocker.json"
    if not sequence_rows:
        checks["no_formal_rows_without_source"] = blocker_path.is_file()
        checks["all_six_not_run"] = all(
            row["decision_code"] == "NOT_RUN_SOURCE_BLOCKED" for row in decision_rows)
        checks["no_numeric_delta_claims"] = all(
            not row["delta_raw_high_minus_low_pp"]
            and not row["delta_adjusted_high_minus_low_pp"] for row in decision_rows)
        status = "BLOCKED_INPUT_SOURCE_VERIFIED" if all(checks.values()) else "FAIL"
        write_json(OUT / "p2_4_validation.json", {
            "status": status, "checks": checks,
            "formal_delta_or_ci_produced": False,
        })
        print(json.dumps({"status": status, "checks": checks}))
        if status == "FAIL":
            raise SystemExit(1)
        return

    grouped = {arm: [row for row in sequence_rows if row["arm"] == arm] for arm in ARMS}
    checks["three_arms"] = all(grouped.values())
    reference_ids = [row["sequence_id"] for row in grouped["100M"]]
    checks["identical_sequence_order"] = all(
        [row["sequence_id"] for row in rows] == reference_ids for rows in grouped.values())
    comparisons = []
    for decision in decision_rows:
        arm, metric = decision["arm"], decision["metric"]
        raw, adjusted, valid_layers = recompute(grouped[arm], metric)
        raw_ok = close(raw, decision["delta_raw_high_minus_low_pp"])
        adjusted_ok = close(adjusted, decision["delta_adjusted_high_minus_low_pp"])
        layers_ok = valid_layers == json.loads(decision["valid_length_layers"])
        comparisons.append({"arm": arm, "metric": metric, "raw_ok": raw_ok,
                            "adjusted_ok": adjusted_ok, "layers_ok": layers_ok})
        ci = json.loads(decision["delta_adjusted_ci95_pp"])
        point = numeric(decision["delta_adjusted_high_minus_low_pp"])
        code = decision["decision_code"]
        if len(valid_layers) < 2 or not np.isfinite(point):
            checks[f"decision_{arm}_{metric}"] = code == "NOT_ADJUDICABLE"
        elif point < 0 and ci[1] < 0:
            checks[f"decision_{arm}_{metric}"] = code == "FLIP_TO_DEGRADATION"
        elif point > 0 and ci[0] > 0:
            checks[f"decision_{arm}_{metric}"] = code == "REVERSE_PERSISTS"
        else:
            checks[f"decision_{arm}_{metric}"] = code == "UNCERTAIN"
    checks["independent_recompute"] = all(
        item["raw_ok"] and item["adjusted_ok"] and item["layers_ok"]
        for item in comparisons)
    summaries = []
    for arm in ARMS:
        summary = json.loads((OUT / "units" / arm / "unit_summary.json").read_text())
        summaries.append(summary)
        checks[f"head_seed_{arm}"] = summary["head_seed"] == SEED
        checks[f"cuda_{arm}"] = summary["device"].startswith("cuda") and summary["cpu_fallback_count"] == 0
        checks[f"bootstrap_{arm}"] = all(
            row["bootstrap_seed"] == str(SEED) and row["bootstrap_n"] == str(BOOTSTRAP_N)
            for row in decision_rows if row["arm"] == arm)
    shared_hashes = {summary["shared_freeze_sha256"] for summary in summaries}
    checks["one_shared_freeze"] = len(shared_hashes) == 1
    status = "PASS" if all(checks.values()) else "FAIL"
    write_json(OUT / "p2_4_validation.json", {
        "status": status, "checks": checks,
        "independent_recompute": comparisons,
        "per_sequence_rows": len(sequence_rows),
        "shared_freeze_sha256": list(shared_hashes),
    })
    print(json.dumps({"status": status, "checks": checks}))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
