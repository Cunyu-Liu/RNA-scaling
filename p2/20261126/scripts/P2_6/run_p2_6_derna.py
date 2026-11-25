#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
EXPECTED_LAYERS = {"30M": 12, "100M": 23, "300M": 24, "650M": 28}
GROUPS = {
    "rfamcap": {
        "arm_suffix": "_rfamcap",
        "scales": ["30M", "100M"],
        "claim": "RFamCap corpus effect remains positive at both scales",
    },
    "rinalmocorpus": {
        "arm_suffix": "_rinalmocorpus",
        "scales": ["30M", "100M", "300M"],
        "claim": "Positive RiNALMoCorpus gain is monotonically non-increasing with capacity",
    },
    "b59_budget": {
        "arm_suffix": "_b59",
        "scales": ["30M", "100M", "300M", "650M"],
        "claim": "Budget effect retains the negative, negative, positive, positive scale pattern",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            row["_source_file"] = path.name
            row["_source_line"] = line_number
            rows.append(row)
    return rows


def macro_f1_excluding(per_class_f1: dict, exclude_prefixes=("rRNA",)):
    values = [
        value
        for key, value in per_class_f1.items()
        if value is not None
        and not any(key.startswith(prefix) or prefix in key for prefix in exclude_prefixes)
    ]
    return sum(values) / len(values) if values else None


def select_official(rows: list[dict], run: str, group: str) -> tuple[list[dict], dict]:
    candidates = [
        row
        for row in rows
        if row.get("run") == run
        and row.get("n_train", 0) >= 4000
        and row.get("ckpt_nt") is not None
    ]
    fixed_b59 = group == "b59_budget" and run.endswith("_b59")
    if fixed_b59:
        candidates = [row for row in candidates if row["ckpt_nt"] == 5800296014]
    if not candidates:
        raise ValueError(f"No official rows for {run}")
    final_ckpt = 5800296014 if fixed_b59 else max(row["ckpt_nt"] for row in candidates)
    selected = [row for row in candidates if row["ckpt_nt"] == final_ckpt]
    by_layer = defaultdict(list)
    for row in selected:
        by_layer[row["layer"]].append(row)
    deduplicated = []
    duplicate_count = 0
    for layer in sorted(by_layer):
        duplicates = by_layer[layer]
        canonical = {
            key: value for key, value in duplicates[0].items() if not key.startswith("_")
        }
        for duplicate in duplicates[1:]:
            comparable = {
                key: value for key, value in duplicate.items() if not key.startswith("_")
            }
            if comparable != canonical:
                raise ValueError(f"Conflicting duplicate rows: {run} layer {layer}")
        row = dict(duplicates[0])
        row["_source_lines"] = [item["_source_line"] for item in duplicates]
        row["_duplicates_removed"] = len(duplicates) - 1
        duplicate_count += len(duplicates) - 1
        deduplicated.append(row)
    scale = next(scale for scale in EXPECTED_LAYERS if run.startswith(f"RNA-Sc-{scale}_"))
    expected = EXPECTED_LAYERS[scale]
    actual_layers = {row["layer"] for row in deduplicated}
    if actual_layers != set(range(expected)):
        raise ValueError(f"Incomplete layers for {run}: {sorted(actual_layers)}")
    metadata = {
        "run": run,
        "selected_ckpt_nt": final_ckpt,
        "n_train": sorted({row["n_train"] for row in deduplicated}),
        "expected_layers": expected,
        "deduplicated_layers": len(deduplicated),
        "raw_rows": len(selected),
        "duplicate_rows_removed": duplicate_count,
        "available_checkpoints_n_train_ge_4000": sorted({row["ckpt_nt"] for row in candidates}),
        "status": "OK",
    }
    return deduplicated, metadata


def derive_layer(row: dict, group: str, scale: str, arm: str) -> dict:
    per_class = row.get("per_class_f1") or {}
    excluded = sorted(key for key in per_class if "rRNA" in key)
    remaining = sorted(key for key in per_class if key not in excluded and per_class[key] is not None)
    f1_der = macro_f1_excluding(per_class)
    if f1_der is None or len(remaining) < 2 or row.get("f1_macro") is None:
        raise ValueError(f"Not evaluable: {row['run']} layer {row['layer']}")
    return {
        "analysis_group": group,
        "scale": scale,
        "arm": arm,
        "run": row["run"],
        "ckpt_nt": row["ckpt_nt"],
        "n_train": row["n_train"],
        "layer": row["layer"],
        "f1_all": row["f1_macro"],
        "f1_der": f1_der,
        "n_classes_all_nonnull": sum(value is not None for value in per_class.values()),
        "n_classes_der": len(remaining),
        "excluded_classes": "|".join(excluded),
        "remaining_classes": "|".join(remaining),
        "source_file": row["_source_file"],
        "source_lines": "|".join(str(value) for value in row["_source_lines"]),
        "duplicate_rows_removed": row["_duplicates_removed"],
        "status": "OK",
    }


def best(rows: list[dict], metric: str) -> dict:
    return max(rows, key=lambda row: row[metric])


def at_layer(rows: list[dict], layer: int) -> dict:
    return next(row for row in rows if row["layer"] == layer)


def make_comparison(group: str, scale: str, arm_rows: list[dict], main_rows: list[dict]) -> dict:
    arm_all = best(arm_rows, "f1_all")
    main_all = best(main_rows, "f1_all")
    arm_der = best(arm_rows, "f1_der")
    main_der = best(main_rows, "f1_der")
    arm_fixed = at_layer(arm_rows, arm_all["layer"])
    main_fixed = at_layer(main_rows, main_all["layer"])
    delta = 100 * (arm_der["f1_der"] - main_der["f1_der"])
    fixed_delta = 100 * (arm_fixed["f1_der"] - main_fixed["f1_der"])
    return {
        "analysis_group": group,
        "scale": scale,
        "arm_run": arm_der["run"],
        "main_run": main_der["run"],
        "arm_ckpt_nt": arm_der["ckpt_nt"],
        "main_ckpt_nt": main_der["ckpt_nt"],
        "arm_all_best_f1": arm_all["f1_all"],
        "arm_all_best_layer": arm_all["layer"],
        "main_all_best_f1": main_all["f1_all"],
        "main_all_best_layer": main_all["layer"],
        "all_delta_pp": 100 * (arm_all["f1_all"] - main_all["f1_all"]),
        "arm_der_best_f1": arm_der["f1_der"],
        "arm_der_best_layer": arm_der["layer"],
        "main_der_best_f1": main_der["f1_der"],
        "main_der_best_layer": main_der["layer"],
        "delta_der_pp": delta,
        "independent_direction_retained": delta > 0 if group != "b59_budget" else None,
        "arm_der_at_all_best_layer": arm_fixed["f1_der"],
        "arm_fixed_layer": arm_fixed["layer"],
        "main_der_at_all_best_layer": main_fixed["f1_der"],
        "main_fixed_layer": main_fixed["layer"],
        "delta_der_fixed_layers_pp": fixed_delta,
        "fixed_layer_direction_retained": fixed_delta > 0 if group != "b59_budget" else None,
        "status": "OK",
    }


def rounded(value, digits=10):
    return round(value, digits) if isinstance(value, float) else value


def json_comparison(row: dict) -> dict:
    return {
        key: rounded(value, 6 if key.endswith("_pp") else 10)
        for key, value in row.items()
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            rendered = {}
            for key in fieldnames:
                value = row.get(key)
                if isinstance(value, float):
                    rendered[key] = f"{value:.6f}" if key.endswith("_pp") else f"{value:.10f}"
                elif value is None:
                    rendered[key] = ""
                else:
                    rendered[key] = value
            writer.writerow(rendered)


def build_report(headlines: dict) -> str:
    lines = [
        "# P2.6 新臂 de-rRNA 分层：既有 20k 重聚合",
        "",
        "口径：逐层剔除键名包含 `rRNA` 的类，其余 9 个非空类 F1 等权平均；de-rRNA 最优层独立选择。固定层敏感性使用 arm/main 各自原 all-F1 最优层。所有输入均只读，未运行 GPU。",
        "",
        "## RFamCap（终预算 1,900,086,380nt）",
        "",
        "| 尺度 | arm de-r best | main de-r best | Δ_der (pp) | 固定层 Δ_der (pp) | 独立方向 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in headlines["groups"]["rfamcap"]["per_scale"]:
        lines.append(
            f"| {row['scale']} | {row['arm_der_best_f1']:.6f}@L{row['arm_der_best_layer']} "
            f"| {row['main_der_best_f1']:.6f}@L{row['main_der_best_layer']} "
            f"| {row['delta_der_pp']:+.6f} | {row['delta_der_fixed_layers_pp']:+.6f} "
            f"| {'保留' if row['independent_direction_retained'] else '未过'} |"
        )
    lines.extend([
        "",
        f"结论：{headlines['groups']['rfamcap']['verdict']}。旧 `ckpt_nt=200006790` 未混入；不复活已撤回的 +1.85pp。",
        "",
        "## RiNALMoCorpus（2B 对 2B）",
        "",
        "| 尺度 | arm de-r best | main de-r best | Δ_der (pp) | 固定层 Δ_der (pp) |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in headlines["groups"]["rinalmocorpus"]["per_scale"]:
        lines.append(
            f"| {row['scale']} | {row['arm_der_best_f1']:.6f}@L{row['arm_der_best_layer']} "
            f"| {row['main_der_best_f1']:.6f}@L{row['main_der_best_layer']} "
            f"| {row['delta_der_pp']:+.6f} | {row['delta_der_fixed_layers_pp']:+.6f} |"
        )
    group = headlines["groups"]["rinalmocorpus"]
    lines.extend([
        "",
        f"独立最优层 Δ 顺序：{' → '.join(f'{value:+.6f}' for value in group['delta_der_sequence_pp'])} pp；"
        f"三点均正={group['all_positive']}，单调不增={group['monotonically_non_increasing']}。结论：{group['verdict']}。",
        "",
        "## b59 预算（5.9B−2B）",
        "",
        "| 尺度 | b59 de-r best | 2B de-r best | Δ_budget_der (pp) | 固定层 Δ (pp) |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in headlines["groups"]["b59_budget"]["per_scale"]:
        lines.append(
            f"| {row['scale']} | {row['arm_der_best_f1']:.6f}@L{row['arm_der_best_layer']} "
            f"| {row['main_der_best_f1']:.6f}@L{row['main_der_best_layer']} "
            f"| {row['delta_der_pp']:+.6f} | {row['delta_der_fixed_layers_pp']:+.6f} |"
        )
    group = headlines["groups"]["b59_budget"]
    lines.extend([
        "",
        f"符号模式：{group['sign_pattern']}；两负两正={group['pattern_retained']}。结论：{group['verdict']}。",
        "",
        "## 覆盖与缺口",
        "",
        "- 正式 20k：18/18 个 run×checkpoint 完整，去重后 362/362 层行可重聚合；每层 10 类非空，排除 1 个 rRNA，保留 9 类。",
        "- `650M_b59` 每层一条完全重复行，保留两个来源行号、只计一次，不作为额外种子。",
        "- RFamCap `1.800083135B` 没有旧 family 层行，不臆算；它不是本协议终预算 headline。",
        "- P2.5 的 8k/4k、五层窗、probe seeds 29/43/61 本节为 `PENDING_P2_5`，本任务不以 20k 行替代。",
        "",
        "详细机器可读判决见 `p2_6_derna_headlines.json`，缺失与待补项见 `p2_6_gaps.csv`。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    main_path = args.backup_root / "eval_evidence_logs/eval/probe_results.jsonl"
    b59_path = args.backup_root / "eval_evidence_logs/eval/probe_results_b59_family.jsonl"
    function_path = args.backup_root / "code_git/rna_sc/der_rna.py"
    source_rows = {
        main_path.name: read_jsonl(main_path),
        b59_path.name: read_jsonl(b59_path),
    }
    layers = []
    coverage_runs = []
    selected = {}
    for group, spec in GROUPS.items():
        for scale in spec["scales"]:
            for arm, suffix in [("arm", spec["arm_suffix"]), ("main", "")]:
                run = f"RNA-Sc-{scale}_s17{suffix}"
                source_name = b59_path.name if group == "b59_budget" and arm == "arm" else main_path.name
                rows, metadata = select_official(source_rows[source_name], run, group)
                derived = [derive_layer(row, group, scale, arm) for row in rows]
                selected[(group, scale, arm)] = derived
                layers.extend(derived)
                coverage_runs.append({
                    "analysis_group": group,
                    "scale": scale,
                    "arm": arm,
                    "source_file": source_name,
                    **metadata,
                })
    comparisons = defaultdict(list)
    for group, spec in GROUPS.items():
        for scale in spec["scales"]:
            comparisons[group].append(make_comparison(
                group,
                scale,
                selected[(group, scale, "arm")],
                selected[(group, scale, "main")],
            ))
    headlines = {
        "protocol": "prereg/P2_6.md",
        "scope": "existing 20k rows only; P2.5 8k/4k pending",
        "de_rna_rule": "mean of non-null per_class_f1 values whose keys do not contain rRNA",
        "best_layer_rule": "independent argmax of unrounded f1_der; ties retain lowest layer",
        "groups": {},
    }
    for group, spec in GROUPS.items():
        rows = comparisons[group]
        entry = {
            "claim": spec["claim"],
            "per_scale": [json_comparison(row) for row in rows],
        }
        if group == "rfamcap":
            passed = all(row["independent_direction_retained"] for row in rows)
            entry.update({
                "direction_retained": passed,
                "verdict": "PASS_NON_RRNA_INDEPENDENT_SUPPORT" if passed else "NOT_RETAINED_DE_RRNA",
            })
        elif group == "rinalmocorpus":
            deltas = [row["delta_der_pp"] for row in rows]
            all_positive = all(value > 0 for value in deltas)
            monotonic = all(left >= right for left, right in zip(deltas, deltas[1:]))
            passed = all_positive and monotonic
            entry.update({
                "delta_der_sequence_pp": [rounded(value, 6) for value in deltas],
                "all_positive": all_positive,
                "monotonically_non_increasing": monotonic,
                "direction_and_decay_retained": passed,
                "verdict": "PASS_NON_RRNA_INDEPENDENT_SUPPORT" if passed else "NOT_RETAINED_DE_RRNA",
            })
        else:
            signs = ["+" if row["delta_der_pp"] > 0 else "-" if row["delta_der_pp"] < 0 else "0" for row in rows]
            passed = signs == ["-", "-", "+", "+"]
            entry.update({
                "sign_pattern": signs,
                "pattern_retained": passed,
                "verdict": "PASS_NON_RRNA_INDEPENDENT_SUPPORT" if passed else "NOT_RETAINED_DE_RRNA",
            })
        headlines["groups"][group] = entry
    headlines["groups"]["p2_5_retest"] = {
        "status": "PENDING_P2_5",
        "scope": "8k/4k, five-layer windows, probe seeds 29/43/61",
        "evaluation": None,
        "note": "Not part of this 20k execution; never substitute 20k rows.",
    }
    coverage = {
        "protocol": "prereg/P2_6.md",
        "scope": "existing 20k official final rows",
        "summary": {
            "expected_run_checkpoints": 18,
            "covered_run_checkpoints": len(coverage_runs),
            "expected_deduplicated_layers": 362,
            "covered_deduplicated_layers": len(layers),
            "raw_selected_rows_before_dedup": sum(item["raw_rows"] for item in coverage_runs),
            "duplicate_rows_removed": sum(item["duplicate_rows_removed"] for item in coverage_runs),
            "all_layers_evaluable": len(layers) == 362,
            "all_class_names_recognized": all(row["n_classes_all_nonnull"] == 10 for row in layers),
            "excluded_class_per_layer": "rRNA",
            "remaining_class_count_per_layer": 9,
        },
        "runs": coverage_runs,
        "missing_official_20k": [],
        "excluded_or_unavailable": [
            {
                "item": "RFamCap ckpt_nt=200006790",
                "status": "EXCLUDED_NONFINAL",
                "reason": "Official RFamCap terminal checkpoint is 1900086380; retracted +1.85pp is not used.",
            },
            {
                "item": "RFamCap ckpt_nt=1800083135 family layers",
                "status": "NOT_EVALUABLE_MISSING_FAMILY_LAYERS",
                "reason": "No old family per-layer rows; no de-rRNA value inferred. Not the preregistered terminal headline.",
            },
            {
                "item": "Early main checkpoints below selected final ckpt",
                "status": "EXCLUDED_BY_FINAL_CHECKPOINT_RULE",
                "reason": "Includes old 30M/100M rows without per_class_f1; they are not official final rows.",
            },
        ],
        "p2_5_retest": {
            "status": "PENDING_P2_5",
            "covered": False,
            "reason": "This task explicitly executes existing 20k only.",
        },
    }
    gaps = [
        {
            "item": "official_20k_rfamcap_rinalmocorpus_b59",
            "status": "NO_GAP",
            "reason": "18/18 run-checkpoints and 362/362 deduplicated layers have non-null per-class F1.",
            "required_followup": "None for the preregistered 20k reaggregation.",
        },
        {
            "item": "P2.5_8k_4k_five_layer_windows_seeds_29_43_61",
            "status": "PENDING_P2_5",
            "reason": "P2.5 per-class retest rows are not an input to this 20k-only task.",
            "required_followup": "After P2.5, select de-r best per seed and five-layer window; report 300M/650M means, ddof=1 SD, and three paired differences.",
        },
        {
            "item": "RFamCap_1800083135",
            "status": "NOT_EVALUABLE_MISSING_FAMILY_LAYERS",
            "reason": "No old family layer ledger at this checkpoint; weights alone cannot supply per-class F1.",
            "required_followup": "No inference; only a separately authorized family probe evaluation could fill it.",
        },
    ]
    layer_fields = [
        "analysis_group", "scale", "arm", "run", "ckpt_nt", "n_train", "layer",
        "f1_all", "f1_der", "n_classes_all_nonnull", "n_classes_der",
        "excluded_classes", "remaining_classes", "source_file", "source_lines",
        "duplicate_rows_removed", "status",
    ]
    comparison_fields = list(comparisons["rfamcap"][0])
    write_csv(output / "p2_6_derna_layers.csv", layers, layer_fields)
    flat_comparisons = [row for group in GROUPS for row in comparisons[group]]
    write_csv(output / "p2_6_derna_headlines.csv", flat_comparisons, comparison_fields)
    with (output / "p2_6_derna_headlines.json").open("w", encoding="utf-8") as handle:
        json.dump(headlines, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (output / "p2_6_derna_coverage.json").open("w", encoding="utf-8") as handle:
        json.dump(coverage, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_csv(output / "p2_6_gaps.csv", gaps, ["item", "status", "reason", "required_followup"])
    (output / "p2_6_report.md").write_text(build_report(headlines), encoding="utf-8")

    with (output / "p2_6_derna_layers.csv").open(newline="", encoding="utf-8") as handle:
        reread = list(csv.DictReader(handle))
    reread_groups = defaultdict(list)
    for row in reread:
        for key in ["layer", "ckpt_nt"]:
            row[key] = int(row[key])
        for key in ["f1_all", "f1_der"]:
            row[key] = float(row[key])
        reread_groups[(row["analysis_group"], row["scale"], row["arm"])].append(row)
    max_recalc_error = 0.0
    for row in flat_comparisons:
        for arm in ["arm", "main"]:
            run = row[f"{arm}_run"]
            candidates = [
                candidate
                for values in reread_groups.values()
                for candidate in values
                if candidate["run"] == run
            ]
            der_best = max(candidates, key=lambda candidate: candidate["f1_der"])
            all_best = max(candidates, key=lambda candidate: candidate["f1_all"])
            assert der_best["layer"] == row[f"{arm}_der_best_layer"]
            assert all_best["layer"] == row[f"{arm}_all_best_layer"]
            max_recalc_error = max(
                max_recalc_error,
                abs(der_best["f1_der"] - row[f"{arm}_der_best_f1"]),
            )
    assert len(reread) == 362
    assert len({(row["analysis_group"], row["run"], row["ckpt_nt"], row["layer"]) for row in reread}) == 362
    assert all(row["n_classes_der"] == "9" for row in reread)
    assert all(row["excluded_classes"] == "rRNA" for row in reread)
    assert all(row["ckpt_nt"] == 1900086380 for row in reread if row["analysis_group"] == "rfamcap" and row["arm"] == "arm")
    assert all(row["ckpt_nt"] == 5800296014 for row in reread if row["analysis_group"] == "b59_budget" and row["arm"] == "arm")
    validation = {
        "status": "PASS",
        "headline_recomputed_from_layers_csv": True,
        "max_absolute_f1_recalculation_error": max_recalc_error,
        "unique_group_run_ckpt_layer_rows": 362,
        "duplicate_650m_b59_rows_not_counted_as_seeds": True,
        "checkpoint_rules_verified": True,
        "all_official_layers_have_nine_non_rrna_classes": True,
        "p2_5_not_substituted_by_20k": True,
    }
    with (output / "p2_6_validation.json").open("w", encoding="utf-8") as handle:
        json.dump(validation, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    primary = [
        "run_p2_6_derna.py",
        "p2_6_derna_layers.csv",
        "p2_6_derna_headlines.csv",
        "p2_6_derna_headlines.json",
        "p2_6_derna_coverage.json",
        "p2_6_gaps.csv",
        "p2_6_report.md",
        "p2_6_validation.json",
    ]
    manifest = {
        "task": "P2_6",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "prereg/P2_6.md",
        "scope": "Existing 20k de-rRNA reaggregation only; P2.5 pending",
        "compute": "CPU Python standard library only; no GPU used",
        "backup_root_read_only": str(args.backup_root),
        "inputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in [main_path, b59_path, function_path]
        ],
        "function_reference": "code_git/rna_sc/der_rna.py::macro_f1_excluding",
        "outputs": [
            {"path": name, "bytes": (output / name).stat().st_size, "sha256": sha256(output / name)}
            for name in primary
        ],
        "validation": validation,
    }
    with (output / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (output / "manifest_sha256.tsv").open("w", encoding="utf-8") as handle:
        for name in primary + ["manifest.json"]:
            handle.write(f"{sha256(output / name)}\t{name}\n")
    print(json.dumps({
        "layers": len(layers),
        "run_checkpoints": len(coverage_runs),
        "duplicates_removed": coverage["summary"]["duplicate_rows_removed"],
        "verdicts": {name: group.get("verdict", group.get("status")) for name, group in headlines["groups"].items()},
        "validation": validation["status"],
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
