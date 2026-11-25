from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from p2_4_common import (
    ARMS, BOOTSTRAP_N, OUT, SEED, average_rank, residual_on_length, write_json,
)

METRICS = {
    "all_position": {"field": "all_f1", "min_n": 30},
    "long_range": {"field": "long_f1", "min_n": 20},
}
BINS = ["low", "mid", "high"]
LENGTH_BINS = ["Q1", "Q2", "Q3", "Q4"]
PER_SEQUENCE_FIELDS = [
    "arm", "run", "layer", "sequence_id", "source_row", "name", "source",
    "length", "rns", "all_f1", "long_f1", "length_bin", "global_rns_bin",
    "within_length_rns_bin",
]


def tercile_edges(values):
    return np.quantile(np.asarray(values, dtype=float), [1 / 3, 2 / 3]).tolist()


def tercile_assign(values, edges):
    values = np.asarray(values, dtype=float)
    return np.where(values <= edges[0], "low",
                    np.where(values <= edges[1], "mid", "high"))


def length_assign(lengths, edges):
    lengths = np.asarray(lengths, dtype=float)
    return np.where(lengths <= edges[0], "Q1",
                    np.where(lengths <= edges[1], "Q2",
                             np.where(lengths <= edges[2], "Q3", "Q4")))


def load_units():
    data = {}
    for arm in ARMS:
        path = OUT / "units" / arm / "p2_4_per_sequence.jsonl"
        if not path.is_file():
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        assert len({row["sequence_id"] for row in rows}) == len(rows)
        data[arm] = rows
    return data


def freeze_length_edges():
    path = OUT / "p2_4_shared_freeze.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())["test_length_edges"]


def add_bins(data, length_edges):
    edges_output = {}
    for arm, rows in data.items():
        rns = np.asarray([row["rns"] for row in rows])
        lengths = np.asarray([row["length"] for row in rows])
        global_edges = tercile_edges(rns)
        global_bins = tercile_assign(rns, global_edges)
        length_bins = length_assign(lengths, length_edges)
        within_bins = np.empty(len(rows), dtype=object)
        within_edges = {}
        for length_bin in LENGTH_BINS:
            mask = length_bins == length_bin
            edges = tercile_edges(rns[mask])
            within_edges[length_bin] = edges
            within_bins[mask] = tercile_assign(rns[mask], edges)
        for index, row in enumerate(rows):
            row["length_bin"] = str(length_bins[index])
            row["global_rns_bin"] = str(global_bins[index])
            row["within_length_rns_bin"] = str(within_bins[index])
        edges_output[arm] = {
            "global_rns_terciles": global_edges,
            "within_length_rns_terciles": within_edges,
        }
    return edges_output


def write_per_sequence(data):
    path = OUT / "p2_4_bin_per_sequence.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_SEQUENCE_FIELDS)
        writer.writeheader()
        for arm in ARMS:
            for row in data.get(arm, []):
                writer.writerow({key: row.get(key) for key in PER_SEQUENCE_FIELDS})


def finite_values(rows, metric):
    return np.asarray([
        float(row[METRICS[metric]["field"]])
        if row[METRICS[metric]["field"]] is not None else np.nan for row in rows
    ])


def mean_or_none(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return float(values.mean()) if len(values) else None


def make_cells(data):
    rows_out = []
    for arm in ARMS:
        rows = data.get(arm, [])
        for metric, spec in METRICS.items():
            values = finite_values(rows, metric) if rows else np.asarray([])
            for cell_type, length_bin, bin_field in (
                    [("global", "GLOBAL", "global_rns_bin")]
                    + [("length_stratified", length, "within_length_rns_bin")
                       for length in LENGTH_BINS]):
                for rns_bin in BINS:
                    if rows:
                        selected = [
                            index for index, row in enumerate(rows)
                            if row[bin_field] == rns_bin
                            and (cell_type == "global" or row["length_bin"] == length_bin)
                            and np.isfinite(values[index])
                        ]
                        cell_values = values[selected]
                    else:
                        selected, cell_values = [], np.asarray([])
                    n = len(cell_values)
                    if not rows:
                        reason = "arm_not_executed"
                    elif n < spec["min_n"]:
                        reason = f"n<{spec['min_n']}"
                    else:
                        reason = ""
                    rows_out.append({
                        "arm": arm,
                        "metric": metric,
                        "cell_type": cell_type,
                        "length_bin": length_bin,
                        "rns_bin": rns_bin,
                        "n": n,
                        "mean_f1": mean_or_none(cell_values),
                        "std_f1": float(cell_values.std()) if n else None,
                        "minimum_n": spec["min_n"],
                        "eligible": bool(rows and n >= spec["min_n"]),
                        "exclusion_reason": reason,
                    })
    path = OUT / "p2_4_bin_cells.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows_out[0]))
        writer.writeheader()
        writer.writerows(rows_out)
    return rows_out


def valid_strata(rows, metric):
    spec = METRICS[metric]
    values = finite_values(rows, metric)
    valid = []
    counts = {}
    for length_bin in LENGTH_BINS:
        cell_counts = {}
        for rns_bin in BINS:
            cell_counts[rns_bin] = int(sum(
                row["length_bin"] == length_bin
                and row["within_length_rns_bin"] == rns_bin
                and np.isfinite(values[index]) for index, row in enumerate(rows)))
        counts[length_bin] = cell_counts
        if all(cell_counts[rns_bin] >= spec["min_n"] for rns_bin in BINS):
            valid.append(length_bin)
    return valid, counts


def delta_estimates(rows, metric, valid_layers, indices=None):
    if indices is not None:
        rows = [rows[index] for index in indices]
    values = finite_values(rows, metric)
    global_bins = np.asarray([row["global_rns_bin"] for row in rows])
    within_bins = np.asarray([row["within_length_rns_bin"] for row in rows])
    length_bins = np.asarray([row["length_bin"] for row in rows])

    def selected(bin_values, rns_bin, length_bin=None):
        mask = (bin_values == rns_bin) & np.isfinite(values)
        if length_bin is not None:
            mask &= length_bins == length_bin
        return values[mask]

    low = selected(global_bins, "low")
    mid = selected(global_bins, "mid")
    high = selected(global_bins, "high")
    raw = float(high.mean() - low.mean()) if len(low) and len(high) else None
    numerator = 0.0
    denominator = 0
    layer_effects = {}
    for length_bin in valid_layers:
        low_layer = selected(within_bins, "low", length_bin)
        high_layer = selected(within_bins, "high", length_bin)
        if not len(low_layer) or not len(high_layer):
            continue
        effect = float(high_layer.mean() - low_layer.mean())
        weight = len(low_layer) + len(high_layer)
        layer_effects[length_bin] = {
            "effect": effect, "weight": weight,
            "n_low": len(low_layer), "n_high": len(high_layer),
        }
        numerator += weight * effect
        denominator += weight
    adjusted = numerator / denominator if denominator else None
    return {
        "raw": raw,
        "adjusted": adjusted,
        "raw_low_mean": float(low.mean()) if len(low) else None,
        "raw_mid_mean": float(mid.mean()) if len(mid) else None,
        "raw_high_mean": float(high.mean()) if len(high) else None,
        "raw_low_n": len(low), "raw_mid_n": len(mid), "raw_high_n": len(high),
        "layer_effects": layer_effects,
    }


def percentile_ci(values, scale=100.0):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return [None, None]
    return (np.percentile(values, [2.5, 97.5]) * scale).tolist()


def partial_statistics(rows, metric):
    values = finite_values(rows, metric)
    mask = np.isfinite(values)
    lengths = np.asarray([row["length"] for row in rows], dtype=float)[mask]
    rns = np.asarray([row["rns"] for row in rows], dtype=float)[mask]
    values = values[mask]
    rank_length = average_rank(lengths)
    rank_rns = average_rank(rns)
    rank_f1 = average_rank(values)
    residual_rns = residual_on_length(rank_rns, rank_length)
    residual_f1 = residual_on_length(rank_f1, rank_length)
    return {
        "n": int(mask.sum()),
        "partial_spearman_rns_f1_given_length": float(np.corrcoef(residual_rns, residual_f1)[0, 1]),
        "spearman_len_rns": float(np.corrcoef(rank_length, rank_rns)[0, 1]),
        "spearman_len_f1": float(np.corrcoef(rank_length, rank_f1)[0, 1]),
    }


def decision_label(adjusted_pp, ci, valid_layers):
    if len(valid_layers) < 2 or adjusted_pp is None:
        return "不可裁决", "NOT_ADJUDICABLE"
    if adjusted_pp < 0 and ci[1] is not None and ci[1] < 0:
        return "翻转为蛋白式高RNS降解", "FLIP_TO_DEGRADATION"
    if adjusted_pp > 0 and ci[0] is not None and ci[0] > 0:
        return "反向仍存", "REVERSE_PERSISTS"
    return "方向不确定/未过判决", "UNCERTAIN"


def analyze_arm(arm, rows):
    output = []
    bootstrap_cache = {}
    for metric in METRICS:
        valid_layers, strata_counts = valid_strata(rows, metric)
        point = delta_estimates(rows, metric, valid_layers)
        bootstrap_cache[metric] = {"valid_layers": valid_layers, "samples": []}
        output.append({
            "arm": arm,
            "run": rows[0]["run"],
            "layer": rows[0]["layer"],
            "metric": metric,
            "point": point,
            "valid_layers": valid_layers,
            "strata_counts": strata_counts,
            "partial": partial_statistics(rows, metric),
        })
    rng = np.random.default_rng(SEED)
    for _ in range(BOOTSTRAP_N):
        indices = rng.integers(0, len(rows), len(rows))
        for metric in METRICS:
            estimate = delta_estimates(
                rows, metric, bootstrap_cache[metric]["valid_layers"], indices)
            bootstrap_cache[metric]["samples"].append(
                [estimate["raw"], estimate["adjusted"]])
    decision_rows = []
    for item in output:
        metric = item["metric"]
        samples = np.asarray(bootstrap_cache[metric]["samples"], dtype=float)
        point = item["point"]
        raw_pp = point["raw"] * 100 if point["raw"] is not None else None
        adjusted_pp = point["adjusted"] * 100 if point["adjusted"] is not None else None
        raw_ci = percentile_ci(samples[:, 0])
        adjusted_ci = percentile_ci(samples[:, 1])
        label, code = decision_label(adjusted_pp, adjusted_ci, item["valid_layers"])
        relative = (100 * point["raw"] / point["raw_low_mean"]
                    if point["raw"] is not None and point["raw_low_mean"] else None)
        decision = {
            "arm": arm,
            "run": item["run"],
            "layer": item["layer"],
            "metric": metric,
            "n_sequences": len(rows),
            "n_metric_sequences": item["partial"]["n"],
            "raw_low_n": point["raw_low_n"],
            "raw_mid_n": point["raw_mid_n"],
            "raw_high_n": point["raw_high_n"],
            "raw_low_mean_f1": point["raw_low_mean"],
            "raw_mid_mean_f1": point["raw_mid_mean"],
            "raw_high_mean_f1": point["raw_high_mean"],
            "delta_raw_high_minus_low_pp": raw_pp,
            "delta_raw_ci95_pp": raw_ci,
            "delta_raw_relative_high_minus_low_pct": relative,
            "delta_adjusted_high_minus_low_pp": adjusted_pp,
            "delta_adjusted_ci95_pp": adjusted_ci,
            "valid_length_layers": item["valid_layers"],
            "n_valid_length_layers": len(item["valid_layers"]),
            "adjusted_layer_effects_pp": {
                key: {**value, "effect": value["effect"] * 100}
                for key, value in point["layer_effects"].items()
            },
            **item["partial"],
            "decision": label,
            "decision_code": code,
            "historical_reference_raw_relative_pct": (
                {"all_position": 18.0, "long_range": 29.3}[metric]
                if arm == "100M" else None),
            "pair_coordinates": "corrected_1based_to_0based",
            "head_seed": SEED,
            "bootstrap_seed": SEED,
            "bootstrap_n": BOOTSTRAP_N,
        }
        decision_rows.append(decision)
        item["bootstrap_ci"] = {"raw_pp": raw_ci, "adjusted_pp": adjusted_ci}
        item["decision"] = label
        item["decision_code"] = code
    return decision_rows, output


def empty_decisions():
    rows = []
    for arm, spec in ARMS.items():
        for metric in METRICS:
            rows.append({
                "arm": arm,
                "run": "RNA-Sc-100M_s17_randinit17" if spec["randinit"] else spec["run"],
                "layer": spec["layer"], "metric": metric,
                "n_sequences": 0, "n_metric_sequences": 0,
                "valid_length_layers": [], "n_valid_length_layers": 0,
                "decision": "不可裁决：共享随机池源表缺失/不匹配，臂未执行",
                "decision_code": "NOT_RUN_SOURCE_BLOCKED",
                "pair_coordinates": "corrected_1based_to_0based",
                "head_seed": SEED, "bootstrap_seed": SEED,
                "bootstrap_n": BOOTSTRAP_N,
                "historical_reference_raw_relative_pct": (
                    {"all_position": 18.0, "long_range": 29.3}[metric]
                    if arm == "100M" else None),
            })
    return rows


def write_decisions(rows):
    fields = [
        "arm", "run", "layer", "metric", "n_sequences", "n_metric_sequences",
        "raw_low_n", "raw_mid_n", "raw_high_n", "raw_low_mean_f1",
        "raw_mid_mean_f1", "raw_high_mean_f1", "delta_raw_high_minus_low_pp",
        "delta_raw_ci95_pp", "delta_raw_relative_high_minus_low_pct",
        "delta_adjusted_high_minus_low_pp", "delta_adjusted_ci95_pp",
        "valid_length_layers", "n_valid_length_layers", "adjusted_layer_effects_pp",
        "partial_spearman_rns_f1_given_length", "spearman_len_rns",
        "spearman_len_f1", "decision", "decision_code",
        "historical_reference_raw_relative_pct", "pair_coordinates", "head_seed",
        "bootstrap_seed", "bootstrap_n",
    ]
    with (OUT / "p2_4_length_decision.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key in ["delta_raw_ci95_pp", "delta_adjusted_ci95_pp",
                        "valid_length_layers", "adjusted_layer_effects_pp"]:
                flat[key] = json.dumps(flat.get(key), ensure_ascii=False)
            writer.writerow({key: flat.get(key) for key in fields})


def make_figure(data, decisions):
    figure, axes = plt.subplots(2, 3, figsize=(15, 9))
    if not data:
        figure.text(0.5, 0.55, "P2.4 not run: authoritative family_validation source unavailable",
                    ha="center", va="center", fontsize=15)
        figure.text(0.5, 0.45, "No delta or CI is estimated; all arms are non-adjudicable.",
                    ha="center", va="center", fontsize=12)
        for axis in axes.flat:
            axis.axis("off")
    else:
        colors = {"Q1": "#4477AA", "Q2": "#66CCEE", "Q3": "#EE8833", "Q4": "#CC3311"}
        for column, arm in enumerate(ARMS):
            if arm not in data:
                axes[0, column].axis("off")
                axes[1, column].axis("off")
                continue
            arm_decisions = [row for row in decisions if row["arm"] == arm]
            x = np.arange(2)
            width = 0.36
            for offset, kind, label in [(-width / 2, "raw", "Raw"),
                                        (width / 2, "adjusted", "Length-adjusted")]:
                values = [row[f"delta_{kind}_high_minus_low_pp"] for row in arm_decisions]
                cis = [row[f"delta_{kind}_ci95_pp"] for row in arm_decisions]
                heights = [value if value is not None else 0 for value in values]
                axes[0, column].bar(x + offset, heights, width, label=label)
                for xi, value, ci in zip(x + offset, values, cis):
                    if value is not None and ci[0] is not None:
                        axes[0, column].errorbar(xi, value, yerr=[[value - ci[0]], [ci[1] - value]],
                                                 fmt="none", color="black", capsize=4)
            axes[0, column].axhline(0, color="black", linewidth=0.8)
            axes[0, column].set_xticks(x, ["All-position", "Long-range"])
            axes[0, column].set_ylabel("High minus low RNS F1 (pp)")
            axes[0, column].set_title(arm)
            axes[0, column].legend()
            for row in data[arm]:
                axes[1, column].scatter(row["rns"], row["all_f1"], s=9, alpha=0.35,
                                        color=colors[row["length_bin"]])
            for length_bin in LENGTH_BINS:
                axes[1, column].scatter([], [], color=colors[length_bin], label=length_bin)
            axes[1, column].set_xlabel("RNS@10")
            axes[1, column].set_ylabel("All-position paired F1")
            axes[1, column].legend(title="Length quartile")
    figure.tight_layout()
    (OUT / "figs").mkdir(exist_ok=True)
    figure.savefig(OUT / "figs" / "p2_4_length_control.png", dpi=200)
    plt.close(figure)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = load_units()
    length_edges = freeze_length_edges()
    if data and length_edges is None:
        raise RuntimeError("units exist but shared frozen length edges are missing")
    expected_ids = None
    for rows in data.values():
        ids = [row["sequence_id"] for row in rows]
        if expected_ids is None:
            expected_ids = ids
        assert ids == expected_ids, "arms do not share identical TS0 sequence order"
    edges = add_bins(data, length_edges) if data else {}
    write_per_sequence(data)
    cells = make_cells(data)
    write_json(OUT / "p2_4_rns_bin_edges.json", {
        "length_edges": length_edges,
        "length_rule": "<=q1; q1<L<=q2; q2<L<=q3; >q3",
        "rns_rule": "<=q1; q1<RNS<=q2; >q2",
        "arms": edges,
    })
    decisions, details = [], []
    for arm in ARMS:
        if arm in data:
            arm_decisions, arm_details = analyze_arm(arm, data[arm])
            decisions.extend(arm_decisions)
            details.extend(arm_details)
    if not decisions:
        decisions = empty_decisions()
    else:
        decisions.extend(
            row for row in empty_decisions() if row["arm"] not in data)
        arm_order = {arm: index for index, arm in enumerate(ARMS)}
        metric_order = {metric: index for index, metric in enumerate(METRICS)}
        decisions.sort(key=lambda row: (arm_order[row["arm"]],
                                        metric_order[row["metric"]]))
    write_decisions(decisions)
    status = "COMPLETE" if len(data) == len(ARMS) else "BLOCKED_OR_INCOMPLETE"
    write_json(OUT / "p2_4_length_decision.json", {
        "task": "X-P24 / P2.4",
        "status": status,
        "completed_arms": list(data),
        "required_arms": list(ARMS),
        "length_edges": length_edges,
        "decision_rule": {
            "flip": "delta_adj<0 and entire 95% CI<0",
            "reverse_persists": "delta_adj>0 and entire 95% CI>0",
            "otherwise": "uncertain; CI crossing zero is never a direction claim",
            "minimum_valid_layers": 2,
            "valid_layer": "all low/mid/high cells meet metric-specific n threshold",
        },
        "bootstrap": {
            "n": BOOTSTRAP_N, "seed": SEED, "unit": "sequence",
            "method": "percentile 95%; fixed original bins and valid strata",
        },
        "decisions": decisions,
        "details": details,
    })
    make_figure(data, decisions)
    print(json.dumps({"status": status, "completed_arms": list(data),
                      "n_decision_rows": len(decisions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
