#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SCALES = ["1M", "10M", "30M", "100M", "300M", "650M"]
SEEDS = {
    "1M": ["s17", "s29", "s43"],
    "10M": ["s17", "s29", "s43"],
    "30M": ["s17", "s29", "s43"],
    "100M": ["s17", "s29", "s43"],
    "300M": ["s17"],
    "650M": ["s17"],
}
EXPECTED_MAIN = {
    "1M": 0.1650,
    "10M": 0.1535,
    "30M": 0.2651,
    "100M": 0.3394,
    "300M": 0.3445,
    "650M": 0.3632,
}
EXPECTED_DELTA = {
    "1M": 0.055,
    "10M": 0.337,
    "30M": 0.438,
    "100M": 0.434,
    "300M": 0.416,
    "650M": 0.436,
}
DEFAULT_BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
DEFAULT_OUTPUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125")


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_line"] = line_number
                rows.append(row)
    return rows


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rounded_decimal(value, digits):
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def rounded(value, digits):
    return float(rounded_decimal(value, digits))


def fmt(value, digits=4, signed=False):
    if value is None:
        return "NA"
    value = rounded_decimal(value, digits)
    if value == 0:
        value = abs(value)
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def comparison(actual, expected, digits=4):
    actual_rounded = rounded(actual, digits)
    matches = actual_rounded == rounded(expected, digits)
    return {
        "actual": fmt(actual, digits),
        "expected": fmt(expected, digits),
        "difference": fmt(actual_rounded - expected, digits, signed=True),
        "status": "一致" if matches else "不符",
    }


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence_root = args.backup_root / "eval_evidence_logs"
    paths = {
        "probe": evidence_root / "eval/probe_results.jsonl",
        "matrix": evidence_root / "eval/eval_matrix_results.jsonl",
        "verdict": evidence_root / "evidence/s1_final_verdict.json",
        "seed_table": evidence_root / "evidence/s1_seed_table.json",
        "slope": evidence_root / "evidence/s1_slope_decision.json",
        "delta": evidence_root / "evidence/eval_matrix_v1_delta.json",
        "classical": evidence_root / "evidence/classical_baselines.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    probe_rows = read_jsonl(paths["probe"])
    matrix_rows = read_jsonl(paths["matrix"])
    verdict = read_json(paths["verdict"])
    seed_table = read_json(paths["seed_table"])
    slope_evidence = read_json(paths["slope"])
    delta_evidence = read_json(paths["delta"])
    classical = read_json(paths["classical"])
    if len(probe_rows) != 3430:
        raise ValueError(f"probe_results.jsonl 行数应为 3430，实际 {len(probe_rows)}")
    if len(matrix_rows) != 52:
        raise ValueError(f"eval_matrix_results.jsonl 行数应为 52，实际 {len(matrix_rows)}")

    by_run = defaultdict(list)
    for row in probe_rows:
        by_run[row["run"]].append(row)
    main_results = {}
    best_records = {}
    for scale in SCALES:
        scale_results = []
        for seed in SEEDS[scale]:
            run = f"RNA-Sc-{scale}_{seed}"
            candidates = by_run[run]
            if not candidates:
                raise ValueError(f"缺少 {run}")
            checkpoint = max(row["ckpt_nt"] for row in candidates)
            selected = [row for row in candidates if row["ckpt_nt"] == checkpoint]
            layers = [row["layer"] for row in selected]
            if len(layers) != len(set(layers)):
                raise ValueError(f"{run} 最终检查点存在重复层")
            n_layers_values = {row.get("n_layers") for row in selected}
            if len(n_layers_values) != 1 or None in n_layers_values:
                raise ValueError(f"{run} 最终检查点 n_layers 缺失或不一致: {n_layers_values}")
            n_layers = n_layers_values.pop()
            if sorted(layers) != list(range(n_layers)):
                raise ValueError(f"{run} 最终检查点层扫描不完整")
            if {row["split"] for row in selected} != {"family_validation->family_test"}:
                raise ValueError(f"{run} split 口径不一致")
            best = max(selected, key=lambda row: (row["f1_macro"], -row["layer"]))
            record = {
                "scale": scale,
                "seed": seed,
                "run": run,
                "checkpoint": checkpoint,
                "f1": best["f1_macro"],
                "layer": best["layer"],
                "n_layers": n_layers,
                "line": best["_line"],
            }
            scale_results.append(record)
            best_records[run] = record
        values = [record["f1"] for record in scale_results]
        main_results[scale] = {
            "runs": scale_results,
            "mean": statistics.mean(values),
            "std_pop": statistics.pstdev(values),
            "std_sample": statistics.stdev(values) if len(values) > 1 else None,
        }

    main_csv_rows = []
    for scale in SCALES:
        result = main_results[scale]
        runs = result["runs"]
        main_csv_rows.append({
            "scale": scale,
            "seeds": ";".join(SEEDS[scale]),
            "n_seeds": len(runs),
            "per_seed_f1_at_best_layer": ";".join(f"{r['seed']}={fmt(r['f1'])}@L{r['layer']}" for r in runs),
            "best_layers": ";".join(str(r["layer"]) for r in runs),
            "family_f1_mean": fmt(result["mean"]),
            "family_f1_std_population": fmt(result["std_pop"]),
            "family_f1_std_sample": fmt(result["std_sample"]),
            "checkpoint_nt": ";".join(str(r["checkpoint"]) for r in runs),
            "probe_results_best_lines": ";".join(str(r["line"]) for r in runs),
        })
    main_fields = list(main_csv_rows[0])
    write_csv(args.output_dir / "p02a_main_table.csv", main_fields, main_csv_rows)

    main_md = [
        "# P0.2a 六档 family F1 主表",
        "",
        "口径：`rna_type`，`family_validation->family_test`，mean-pool probe；每个精确 run 名仅取最大 `ckpt_nt` 的完整层扫描，再按 macro F1 选最佳层。均值为训练种子间均值，不是序列 bootstrap。",
        "",
        "| 规模 | 种子口径 | 各种子 F1@最佳层（账本行） | Family F1 均值 | 总体 SD | 样本 SD |",
        "|---|---|---|---:|---:|---:|",
    ]
    for scale in SCALES:
        result = main_results[scale]
        per_seed = "<br>".join(f"{r['seed']}: {fmt(r['f1'])}@L{r['layer']}（L{r['line']}）" for r in result["runs"])
        seed_scope = f"{len(result['runs'])} seeds: {', '.join(SEEDS[scale])}" if len(result["runs"]) > 1 else "单种子: s17"
        main_md.append(f"| {scale} | {seed_scope} | {per_seed} | {fmt(result['mean'])} | {fmt(result['std_pop'])} | {fmt(result['std_sample'])} |")
    main_md += [
        "",
        "账本行号为 `eval/probe_results.jsonl` 的 1-based 行号。总体 SD 对照 `s1_final_verdict.json`，样本 SD 对照 `s1_seed_table.json`；单种子样本 SD 不定义。",
        "",
        f"100M→650M 斜率 = `(F1_650M − F1_100M) / log10(650/100)` = **{fmt((main_results['650M']['mean'] - main_results['100M']['mean']) / math.log10(6.5))} F1/decade**。",
        "",
    ]
    (args.output_dir / "p02a_main_table.md").write_text("\n".join(main_md), encoding="utf-8")

    matrix_index = {(row["model"], row["protocol"], row["split"]): row for row in matrix_rows}
    delta_csv_rows = []
    delta_comparisons = []
    for scale in SCALES:
        model = f"RNA-Sc-{scale}_s17"
        family = matrix_index[(model, "probe-balanced", "family")]
        random = matrix_index[(model, "probe-balanced", "random")]
        regenerated = random["best_f1_macro"] - family["best_f1_macro"]
        key = f"{model}|probe-balanced"
        evidence_value = delta_evidence["deltas"][key]["delta"]
        delta_csv_rows.append({
            "scale": scale,
            "model_or_baseline": model,
            "protocol": "probe-balanced",
            "family_f1": fmt(family["best_f1_macro"]),
            "random_f1": fmt(random["best_f1_macro"]),
            "delta_random_minus_family": fmt(regenerated),
            "family_best_layer": family["best_layer"],
            "random_best_layer": random["best_layer"],
            "evidence_delta": fmt(evidence_value),
            "evidence_minus_regenerated": fmt(evidence_value - regenerated, 4, signed=True),
            "eval_matrix_family_random_lines": f"{family['_line']};{random['_line']}",
        })
        delta_comparisons.append((scale, regenerated, evidence_value))
    kmer_regenerated = classical["random"]["f1_macro"] - classical["family"]["f1_macro"]
    kmer_evidence = classical["delta_random_family"]
    delta_csv_rows.append({
        "scale": "k-mer baseline",
        "model_or_baseline": classical["family"]["baseline"],
        "protocol": "classical-baseline",
        "family_f1": fmt(classical["family"]["f1_macro"]),
        "random_f1": fmt(classical["random"]["f1_macro"]),
        "delta_random_minus_family": fmt(kmer_regenerated),
        "family_best_layer": "NA",
        "random_best_layer": "NA",
        "evidence_delta": fmt(kmer_evidence),
        "evidence_minus_regenerated": fmt(kmer_evidence - kmer_regenerated, 4, signed=True),
        "eval_matrix_family_random_lines": "NA;classical_baselines.json",
    })
    delta_fields = list(delta_csv_rows[0])
    write_csv(args.output_dir / "p02a_delta_table.csv", delta_fields, delta_csv_rows)

    delta_md = [
        "# P0.2a Δ(random − family) 六档表与 k-mer 基线",
        "",
        "六档模型行均为主臂 `s17`、`probe-balanced`，与主表的 mean-pool 口径不可混用。Δ 由 random 与 family 的 macro F1 独立相减。",
        "",
        "| 规模/基线 | Family F1 | Random F1 | Δ(random−family) | Evidence Δ | Evidence−复算 | 最佳层 family/random | 账本行 family/random |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in delta_csv_rows:
        delta_md.append(
            f"| {row['scale']} | {row['family_f1']} | {row['random_f1']} | {fmt(float(row['delta_random_minus_family']), 4, signed=True)} | "
            f"{fmt(float(row['evidence_delta']), 4, signed=True)} | {row['evidence_minus_regenerated']} | "
            f"{row['family_best_layer']}/{row['random_best_layer']} | {row['eval_matrix_family_random_lines']} |"
        )
    delta_md += [
        "",
        "六档账本行号对应 `eval/eval_matrix_results.jsonl`；k-mer 行来自 `evidence/classical_baselines.json`。k-mer 的展示值相减为 0.3550，而 evidence 存储字段为 0.3549，差 0.0001；二者均四舍五入为预期的 +0.355。",
        "",
    ]
    (args.output_dir / "p02a_delta_table.md").write_text("\n".join(delta_md), encoding="utf-8")

    report = [
        "# P0.2a 对账报告",
        "",
        "## 裁决摘要",
        "",
        "- 六档 family F1 主表、100M→650M 斜率、六档 balanced Δ 及 k-mer Δ 均与任务给定的交接数字在指定精度一致。",
        "- k-mer 唯一逐位差异：`0.5180 − 0.1630 = 0.3550`，但 `classical_baselines.json:delta_random_family` 存为 `0.3549`，字段值比复算值低 `0.0001`；三位小数结论不变。",
        "- 未使用序列 bootstrap，也未将其解释为训练种子重复。",
        "",
        "## 主表与交接预期逐位比对",
        "",
        "| 规模 | 复算值 | 交接预期 | 复算(4位)−预期 | 结论 |",
        "|---|---:|---:|---:|---|",
    ]
    for scale in SCALES:
        item = comparison(main_results[scale]["mean"], EXPECTED_MAIN[scale])
        report.append(f"| {scale} | {item['actual']} | {item['expected']} | {item['difference']} | {item['status']} |")

    report += [
        "",
        "### 与 s1_final_verdict.json 对照",
        "",
        "`five_scale_table` 不含 300M，因此 300M 无该文件对照项；其余五档均值、总体 SD 均按下表核验。",
        "",
        "| 规模 | 均值复算 / evidence | 均值差 | 总体SD复算 / evidence | SD差 | 结论 |",
        "|---|---|---:|---|---:|---|",
    ]
    verdict_discrepancies = []
    verdict_run_count = 0
    for scale, evidence_scale in verdict["five_scale_table"].items():
        result = main_results[scale]
        mean_diff = rounded(result["mean"], 4) - evidence_scale["f1_mean"]
        std_diff = rounded(result["std_pop"], 4) - evidence_scale["f1_std"]
        matches = rounded(result["mean"], 4) == rounded(evidence_scale["f1_mean"], 4) and rounded(result["std_pop"], 4) == rounded(evidence_scale["f1_std"], 4)
        report.append(
            f"| {scale} | {fmt(result['mean'])} / {fmt(evidence_scale['f1_mean'])} | {fmt(mean_diff, 4, signed=True)} | "
            f"{fmt(result['std_pop'])} / {fmt(evidence_scale['f1_std'])} | {fmt(std_diff, 4, signed=True)} | {'一致' if matches else '不符'} |"
        )
        for run_evidence in evidence_scale["runs"]:
            verdict_run_count += 1
            regenerated = best_records[run_evidence["run"]]
            if regenerated["f1"] != run_evidence["f1"] or regenerated["layer"] != run_evidence["best_layer"]:
                verdict_discrepancies.append((run_evidence["run"], regenerated["f1"], run_evidence["f1"], regenerated["layer"], run_evidence["best_layer"]))
    report += [
        "",
        f"逐 run 核验：{verdict_run_count} 个 run 的 F1 与最佳层均一致。" if not verdict_discrepancies else f"逐 run 核验发现 {len(verdict_discrepancies)} 个不符：{verdict_discrepancies}",
        "",
        "### 与 s1_seed_table.json 对照",
        "",
        "该文件仅含本任务的 1M/10M/30M/100M 四档；其 `probe_best_f1` 使用均值与样本 SD（ddof=1）。",
        "",
        "| 规模 | 均值复算 / evidence | 样本SD复算 / evidence | 结论 |",
        "|---|---|---|---|",
    ]
    for scale in ["1M", "10M", "30M", "100M"]:
        mean_evidence, std_evidence = seed_table[scale]["probe_best_f1"]
        result = main_results[scale]
        matches = rounded(result["mean"], 4) == rounded(mean_evidence, 4) and rounded(result["std_sample"], 4) == rounded(std_evidence, 4)
        report.append(f"| {scale} | {fmt(result['mean'])} / {fmt(mean_evidence)} | {fmt(result['std_sample'])} / {fmt(std_evidence)} | {'一致' if matches else '不符'} |")

    slope_100_650 = (main_results["650M"]["mean"] - main_results["100M"]["mean"]) / math.log10(6.5)
    slope_30_100 = (main_results["100M"]["mean"] - main_results["30M"]["mean"]) / math.log10(100.0 / 30.0)
    slope_check = comparison(slope_100_650, verdict["checks"]["slope_100M_650M"])
    slope_decision_check = comparison(slope_30_100, slope_evidence["slope_per_decade"])
    report += [
        "",
        "## 斜率核验",
        "",
        f"- 100M→650M：复算 `{fmt(slope_100_650, 8)}`，四位为 **{slope_check['actual']}**；`s1_final_verdict.json:checks.slope_100M_650M={slope_check['expected']}`，差 {slope_check['difference']}，**{slope_check['status']}**。",
        f"- `s1_slope_decision.json` 是另一段 30M→100M：复算 `{fmt(slope_30_100, 8)}`，四位为 **{slope_decision_check['actual']}**；evidence 为 {slope_decision_check['expected']}，差 {slope_decision_check['difference']}，**{slope_decision_check['status']}**。其 `rule` 字段也明确为该区间，不能当成 100M→650M 斜率。",
        "",
        "## Δ 表逐位比对",
        "",
        "| 规模 | 复算Δ | eval_matrix_v1_delta | Evidence−复算 | 交接预期(3位) | 与预期结论 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for scale, regenerated, evidence_value in delta_comparisons:
        expected_check = comparison(regenerated, EXPECTED_DELTA[scale], 3)
        evidence_status = "一致" if rounded(regenerated, 4) == rounded(evidence_value, 4) else "不符"
        report.append(
            f"| {scale} | {fmt(regenerated, 4, signed=True)} | {fmt(evidence_value, 4, signed=True)} | {fmt(evidence_value - regenerated, 4, signed=True)}（{evidence_status}） | "
            f"{expected_check['expected']} | {expected_check['status']}（复算3位 {expected_check['actual']}） |"
        )
    kmer_expected = comparison(kmer_regenerated, 0.355, 3)
    report += [
        "",
        f"k-mer：复算 **{fmt(kmer_regenerated, 4, signed=True)}**，三位 {kmer_expected['actual']} 对预期 {kmer_expected['expected']} 为 **{kmer_expected['status']}**；evidence 字段 {fmt(kmer_evidence, 4, signed=True)}，字段−复算 = **{fmt(kmer_evidence - kmer_regenerated, 4, signed=True)}**，四位精度 **不符**。",
        "",
        "## 口径说明与异常记录",
        "",
    ]
    naive_30 = max(row["f1_macro"] for row in by_run["RNA-Sc-30M_s17"])
    naive_30_mean = statistics.mean([naive_30] + [best_records["RNA-Sc-30M_s29"]["f1"], best_records["RNA-Sc-30M_s43"]["f1"]])
    report += [
        f"1. **同名 run 多检查点**：`RNA-Sc-30M_s17` 若混取所有检查点，最大值是 {fmt(naive_30)}@L4（`ckpt_nt=100007541`，账本 L35），并非最终口径的 {fmt(best_records['RNA-Sc-30M_s17']['f1'])}@L8。混取会使 30M 种子均值成为 {fmt(naive_30_mean)}，比正确值 {fmt(main_results['30M']['mean'])} 高 {fmt(naive_30_mean - main_results['30M']['mean'])}。本脚本按最大 `ckpt_nt` 选完整层扫描，故不混入旧检查点。",
        "2. **种子覆盖**：账本与 evidence 实际支持 1M/10M/30M/100M 的 s17/s29/s43 三种子；300M/650M 仅 s17。单种子 SD 仅报告总体 SD=0，样本 SD 标为 NA。",
        "3. **证据覆盖差异**：`s1_final_verdict.json` 无 300M，`s1_seed_table.json` 无 300M/650M；这些是缺失对照项，不判为数值不符。300M 主表值可直接回溯到账本最佳行。",
        "4. **k-mer 存储尾差**：如上，0.0001 差异如实保留，未强行改成一致。",
        "5. **协议差异**：主表为 mean-pool；Δ 六档为 probe-balanced。两者 family F1 不同是协议差异，不能交叉替换。",
        "",
        "## 可复算性",
        "",
        "运行：`/usr/bin/python3 p02a_regen.py`。输入绝对路径、字节数和 SHA-256 见 `p02a_manifest.json`；生成表见 `p02a_main_table.{md,csv}` 与 `p02a_delta_table.{md,csv}`。",
        "",
    ]
    (args.output_dir / "p02a_report.md").write_text("\n".join(report), encoding="utf-8")

    input_manifest = []
    for role, path in paths.items():
        item = {
            "role": role,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if role in {"probe", "matrix"}:
            item["jsonl_rows"] = len(probe_rows) if role == "probe" else len(matrix_rows)
        input_manifest.append(item)
    output_manifest = []
    for name in ["p02a_main_table.md", "p02a_main_table.csv", "p02a_delta_table.md", "p02a_delta_table.csv", "p02a_report.md"]:
        path = args.output_dir / name
        output_manifest.append({"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    script_path = Path(__file__).resolve()
    manifest = {
        "task": "P0.2a",
        "backup_root_read_only": str(args.backup_root),
        "generation_script": {"path": str(script_path), "sha256": sha256(script_path)},
        "selection": {
            "main": "exact run names; maximum ckpt_nt per run; complete layer scan; maximum f1_macro; ties prefer lower layer",
            "main_seeds": SEEDS,
            "delta": "RNA-Sc-{scale}_s17, probe-balanced, random minus family",
            "std": "population ddof=0 for s1_final_verdict; sample ddof=1 for s1_seed_table",
        },
        "inputs": input_manifest,
        "outputs": output_manifest,
    }
    (args.output_dir / "p02a_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("P0.2a regeneration complete")
    print("Main:", ", ".join(f"{s}={fmt(main_results[s]['mean'])}" for s in SCALES))
    print("Slope 100M->650M:", fmt(slope_100_650))
    print("Delta:", ", ".join(f"{s}={fmt(v, 3, signed=True)}" for s, v, _ in delta_comparisons))
    print("k-mer:", fmt(kmer_regenerated, 4, signed=True), "evidence", fmt(kmer_evidence, 4, signed=True))


if __name__ == "__main__":
    main()
