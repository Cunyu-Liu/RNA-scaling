#!/usr/bin/env python3
"""P0.2b: regenerate both caliber adjudications from read-only evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

DEFAULT_BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
DEFAULT_OUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125")
SCALES = ("1M", "10M", "30M", "100M")
TRAIN_SEEDS = (17, 29, 43)
PROBE_SEEDS = (29, 43, 61)
B59_RUNS = {"300M": "RNA-Sc-300M_s17_b59", "650M": "RNA-Sc-650M_s17_b59"}


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            row["_line"] = line_number
            rows.append(row)
    return rows


def write_csv(path: Path, fieldnames, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def f(value, digits=4) -> str:
    return f"{value:.{digits}f}"


def final_best(rows, run: str):
    eligible = [r for r in rows if r["run"] == run and r.get("n_train", 0) >= 4000
                and r.get("ckpt_nt") is not None]
    if not eligible:
        raise AssertionError(f"No eligible rows for {run}")
    final_nt = max(r["ckpt_nt"] for r in eligible)
    by_layer = {r["layer"]: r for r in eligible if r["ckpt_nt"] == final_nt}
    return max(by_layer.values(), key=lambda r: r["f1_macro"]), final_nt, len(eligible)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    root = args.backup_root
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    evidence = root / "eval_evidence_logs" / "evidence"
    evaluation = root / "eval_evidence_logs" / "eval"
    code = root / "code_git"
    paths = {
        "s1_seed_table": evidence / "s1_seed_table.json",
        "s1_final_verdict": evidence / "s1_final_verdict.json",
        "factorial_verdict": evidence / "factorial_verdict.json",
        "b59_reseed": evidence / "b59_reseed_300vs650.json",
        "probe": evaluation / "probe_results.jsonl",
        "probe_b59": evaluation / "probe_results_b59_family.jsonl",
        "s1_seed_code": code / "rna_sc" / "s1_seed_table.py",
        "s1_final_code": code / "rna_sc" / "s1_final_verdict.py",
        "factorial_code": code / "rna_sc" / "factorial_verdict.py",
        "probe_code": code / "rna_sc" / "probe.py",
        "reseed_driver_code": code / "reseed_b59_300vs650.py",
        "reseed_inner_code": code / "reseed_inner.py",
        "draft_protocol_context": root / "delta_20261014" / "DRAFT_v1_final_20261014.md",
    }
    seed_table = read_json(paths["s1_seed_table"])
    final_verdict = read_json(paths["s1_final_verdict"])
    factorial = read_json(paths["factorial_verdict"])
    reseed = read_json(paths["b59_reseed"])
    probe_rows = read_jsonl(paths["probe"])
    b59_rows = read_jsonl(paths["probe_b59"])
    assert len(probe_rows) == 3430
    assert len(b59_rows) == 1434

    s1_details = []
    s1_summary = []
    for scale in SCALES:
        values = []
        for seed in TRAIN_SEEDS:
            run = f"RNA-Sc-{scale}_s{seed}"
            best, final_nt, eligible_count = final_best(probe_rows, run)
            expected = next(r for r in final_verdict["five_scale_table"][scale]["runs"]
                            if r["run"] == run)
            assert best["f1_macro"] == expected["f1"]
            assert best["layer"] == expected["best_layer"]
            values.append(best["f1_macro"])
            s1_details.append({
                "scale": scale, "training_seed": seed, "run": run,
                "final_ckpt_nt": final_nt, "eligible_rows_across_ckpts": eligible_count,
                "best_layer": best["layer"], "n_layers": best["n_layers"],
                "rel_depth": best["rel_depth"], "f1_macro": f(best["f1_macro"]),
                "n_train": best["n_train"], "n_eval": best["n_eval"],
                "split": best["split"], "pooling": best["pooling"],
                "ledger_file": str(paths["probe"]), "ledger_line": best["_line"],
            })
        mean = statistics.mean(values)
        std1 = statistics.stdev(values)
        std0 = statistics.pstdev(values)
        old_std = seed_table[scale]["probe_best_f1"][1]
        new_std = final_verdict["five_scale_table"][scale]["f1_std"]
        assert round(mean, 4) == seed_table[scale]["probe_best_f1"][0]
        assert round(mean, 4) == final_verdict["five_scale_table"][scale]["f1_mean"]
        assert round(std1, 4) == old_std
        assert round(std0, 4) == new_std
        s1_summary.append({
            "scale": scale, "n_training_seeds": 3,
            "f1_values_s17_s29_s43": "/".join(f(v) for v in values),
            "mean": f(mean, 8), "sample_std_ddof1": f(std1, 8),
            "population_std_ddof0": f(std0, 8),
            "sample_to_population_ratio": f(std1 / std0, 8),
            "s1_seed_table_std": f(old_std), "s1_final_verdict_std": f(new_std),
            "seed_table_protocol": "sample std (ddof=1)",
            "final_verdict_protocol": "population std (ddof=0)",
        })

    original = {}
    for scale, run in B59_RUNS.items():
        best, final_nt, _ = final_best(probe_rows, run)
        expected = factorial["table"][scale]["f1_5.9B"]
        assert final_nt == 5800296014 == expected["ckpt_nt"]
        assert best["f1_macro"] == expected["f1"]
        assert best["layer"] == expected["layer"]
        matching_probe_lines = [r["_line"] for r in probe_rows if r["run"] == run
                                and r["ckpt_nt"] == final_nt and r["layer"] == best["layer"]
                                and r["f1_macro"] == best["f1_macro"]]
        matching_b59_lines = [r["_line"] for r in b59_rows if r["run"] == run
                              and r["ckpt_nt"] == final_nt and r["layer"] == best["layer"]
                              and r["f1_macro"] == best["f1_macro"]]
        original[scale] = {
            "best": best, "probe_lines": matching_probe_lines,
            "b59_lines": matching_b59_lines,
        }

    reseed_layers = []
    reseed_by_scale = {}
    for scale, run in B59_RUNS.items():
        per_seed = {}
        for seed in PROBE_SEEDS:
            layer_values = reseed[run][str(seed)]
            assert set(map(int, layer_values)) == set(range(19, 24) if scale == "300M" else range(23, 28))
            for layer_text, value in layer_values.items():
                ledger_matches = [r["_line"] for r in b59_rows if r["run"] == run
                                  and r["ckpt_nt"] == 5800296014
                                  and r["layer"] == int(layer_text)
                                  and r["f1_macro"] == value]
                reseed_layers.append({
                    "scale": scale, "run": run, "training_seed": 17,
                    "probe_seed": seed, "layer": int(layer_text), "f1_macro": f(value),
                    "evidence_file": str(paths["b59_reseed"]),
                    "evidence_key": f'["{run}"]["{seed}"]["{layer_text}"]',
                    "b59_family_jsonl_exact_match_lines": ";".join(map(str, ledger_matches)),
                    "ledger_trace_status": "present" if ledger_matches else "MISSING",
                })
            best_layer = max(layer_values, key=lambda layer: (layer_values[layer], -int(layer)))
            per_seed[seed] = {"f1": layer_values[best_layer], "layer": int(best_layer)}
        reseed_by_scale[scale] = per_seed
    assert all(r["ledger_trace_status"] == "MISSING" for r in reseed_layers)

    reseed_details = []
    paired_deltas = []
    for seed in PROBE_SEEDS:
        v300 = reseed_by_scale["300M"][seed]["f1"]
        v650 = reseed_by_scale["650M"][seed]["f1"]
        delta = v650 - v300
        paired_deltas.append(delta)
        for scale in ("300M", "650M"):
            item = reseed_by_scale[scale][seed]
            reseed_details.append({
                "probe_seed": seed, "scale": scale, "training_seed": 17,
                "run": B59_RUNS[scale], "best_layer_in_retest_window": item["layer"],
                "best_f1": f(item["f1"]), "paired_650_minus_300_pp": f(delta * 100, 8),
                "paired_650_above_300": str(v650 > v300).lower(),
            })
    assert all(delta > 0 for delta in paired_deltas)

    b59_summary = []
    for scale in ("300M", "650M"):
        values = [reseed_by_scale[scale][seed]["f1"] for seed in PROBE_SEEDS]
        best = original[scale]["best"]
        b59_summary.append({
            "scale": scale, "training_run": B59_RUNS[scale], "training_seed": 17,
            "ckpt_nt": 5800296014, "n_probe_seeds": 3,
            "probe_seeds": "29/43/61", "retest_best_f1_values": "/".join(f(v) for v in values),
            "retest_best_layers": "/".join(str(reseed_by_scale[scale][s]["layer"]) for s in PROBE_SEEDS),
            "retest_mean": f(statistics.mean(values), 8),
            "retest_sample_std_ddof1": f(statistics.stdev(values), 8),
            "retest_population_std_ddof0": f(statistics.pstdev(values), 8),
            "retest_sem_ddof1_over_sqrt3": f(statistics.stdev(values) / math.sqrt(3), 8),
            "retest_n_train": 8000, "retest_n_eval": 4000,
            "retest_layer_window": "19-23" if scale == "300M" else "23-27",
            "original_full_layer_f1": f(best["f1_macro"]),
            "original_best_layer": best["layer"], "original_probe_seed": 17,
            "original_n_train": best["n_train"], "original_n_eval": best["n_eval"],
            "original_probe_results_lines": ";".join(map(str, original[scale]["probe_lines"])),
            "original_b59_family_lines": ";".join(map(str, original[scale]["b59_lines"])),
            "pooling_both_protocols": best["pooling"],
        })

    mean_delta = statistics.mean(paired_deltas)
    paired_std1 = statistics.stdev(paired_deltas)
    v650 = [reseed_by_scale["650M"][s]["f1"] for s in PROBE_SEEDS]
    v300 = [reseed_by_scale["300M"][s]["f1"] for s in PROBE_SEEDS]
    original_delta_pp = (original["650M"]["best"]["f1_macro"] - original["300M"]["best"]["f1_macro"]) * 100

    write_csv(out / "p02b_s1_seed_recalc.csv", list(s1_details[0]), s1_details)
    write_csv(out / "p02b_s1_std_summary.csv", list(s1_summary[0]), s1_summary)
    write_csv(out / "p02b_b59_reseed_layers.csv", list(reseed_layers[0]), reseed_layers)
    write_csv(out / "p02b_b59_seed_comparison.csv", list(reseed_details[0]), reseed_details)
    write_csv(out / "p02b_b59_summary.csv", list(b59_summary[0]), b59_summary)

    s1_rows_md = []
    for row in s1_summary:
        s1_rows_md.append(
            f"| {row['scale']} | {row['f1_values_s17_s29_s43']} | {f(float(row['mean']))} | "
            f"{f(float(row['sample_std_ddof1']))} | {f(float(row['population_std_ddof0']))} | "
            f"{row['s1_seed_table_std']} | {row['s1_final_verdict_std']} |")
    raw_s1_md = []
    for row in s1_details:
        raw_s1_md.append(
            f"| {row['scale']} | s{row['training_seed']} | {row['final_ckpt_nt']} | "
            f"L{row['best_layer']} | {row['f1_macro']} | {row['ledger_line']} |")
    paired_md = []
    for seed, delta in zip(PROBE_SEEDS, paired_deltas):
        a = reseed_by_scale["300M"][seed]
        b = reseed_by_scale["650M"][seed]
        paired_md.append(
            f"| {seed} | {f(a['f1'])} @ L{a['layer']} | {f(b['f1'])} @ L{b['layer']} | "
            f"{f(delta * 100, 4)} | 是 |")

    report = f"""# P0.2b 两处口径差裁决

## 总结裁决

1. **S1 三种子 std**：`s1_seed_table.json` 是样本标准差（ddof=1），`s1_final_verdict.json` 是总体标准差（ddof=0）。两者使用完全相同的最终 checkpoint、逐训练种子最佳层 F1 与均值；主文统一为 **mean ± sample SD（ddof=1，n=3 个训练种子）**，即 0.0131/0.0173/0.0162/0.0147。
2. **650M@5.9B**：原始终值口径为 **0.3747@L25**，300M 为 **0.3821@L22**，650M−300M={f(original_delta_pp, 2)}pp；探针种子复测口径为 **650M 0.4491±0.0147、300M 0.3826±0.0159**（mean±sample SD，n=3 个探针种子），3/3 配对均为 650M 更高，均值差 **+{f(mean_delta * 100, 4)}pp**。
3. 复测是同一训练种子 s17、同一 5.9B 权重上的**探针种子重复**，不是三个训练种子，也不是序列 bootstrap。复测 30 个数值只存在于 `b59_reseed_300vs650.json`，**1434 行 `probe_results_b59_family.jsonl` 中 30/30 均无对应行**，不能声称已从该 JSONL 独立复现。

路径缩写：`$B={root}`、`$O={out}`；所有账本行号均为 1-based。生成器与机读明细见 `$O/p02b_regen.py` 及同名前缀 CSV。

## 裁决①：三种子 std 两版本

### 原始行选择与证据

筛选协议与两个原生成器一致：每个 run 只保留 `n_train>=4000` 且 `ckpt_nt` 非空的行，取最大 `ckpt_nt`，按 layer 去重，再在该最终 checkpoint 的全部层中取最大 `f1_macro`。依据：`$B/code_git/rna_sc/s1_seed_table.py:69-104`、`$B/code_git/rna_sc/s1_final_verdict.py:34-54`。

| 规模 | 训练种子 | 最终 ckpt_nt | 最佳层 | 原始 F1 | `probe_results.jsonl` 行 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(raw_s1_md)}

完整字段（split、pooling、n_train/n_eval、行号）见 `p02b_s1_seed_recalc.csv`。特别注意：30M_s17 另有 0.1B checkpoint 的 L4 F1=0.2846（账本第35行）；若跨 checkpoint 直接取最大值会错误替换正式终值 0.2466，因此最终 checkpoint 过滤不可省略。

### 重算与文件逐一核对

下表 F1 按 s17/s29/s43 排列；直接对账本中的四位小数三值重算，聚合结果再保留四位。

| 规模 | 三个最佳层 F1 | 均值 | 样本 std ddof=1 | 总体 std ddof=0 | seed_table | final_verdict |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(s1_rows_md)}

四个规模均满足 `sample_std / population_std = sqrt(3/2) = 1.22474487`，且分别与两文件四位小数完全吻合。机读高精度值见 `p02b_s1_std_summary.csv`。

### 差异根因与主文建议

- `s1_seed_table.py:46-52` 明确除以 `len(v)-1`，即 ddof=1；`s1_final_verdict.py:91-100` 明确除以 `len(f1s)`，即 ddof=0。
- **不是最佳层口径差异**：两文件的 12 个逐种子 F1/最佳层完全相等，本次也已逐行回查账本。
- 主文表、图和摘要统一写成“mean ± sample SD（ddof=1；n=3 training seeds）”，采用 `s1_seed_table` 的 std。总体 std 可入附录的口径说明，不应与样本 std 混用，也不得把 SD 写成 SE。

## 裁决②：650M@5.9B 双口径

### A. 原始终值口径（全层、20k/4k、probe seed 17）

| 规模 | F1@最佳层 | ckpt_nt | `probe_results.jsonl` 行 | `probe_results_b59_family.jsonl` 行 |
|---|---|---:|---|---|
| 300M | 0.3821@L22 | 5800296014 | 1618 | 115 |
| 650M | 0.3747@L25 | 5800296014 | 2185（完全重复于2213） | 509（完全重复于537） |

两值与 `factorial_verdict.json` 的 `table.*.f1_5.9B` 完全一致。原始口径下 650M 比 300M 低 **0.74pp**。650M 的 28 层在两份账本中都完整重复一次，最佳层选择按 layer 去重，不能把重复行当独立重复实验。

### B. 探针种子复测口径（局部深层窗口、8k/4k、probe seeds 29/43/61）

`b59_reseed_300vs650.json` 的 2 run×3 seed×5 layer=30 个单元全部列入 `p02b_b59_reseed_layers.csv`；逐 seed 先在自己的五层窗口内取最大值：

| probe seed | 300M 最佳 F1@层 | 650M 最佳 F1@层 | 650M−300M (pp) | 650M>300M |
|---:|---|---|---:|---|
{chr(10).join(paired_md)}

| 规模 | 三值均值 | 样本 std ddof=1 | 总体 std ddof=0 | 样本 SEM=SD/√3 |
|---|---:|---:|---:|---:|
| 300M | {f(statistics.mean(v300), 8)} | {f(statistics.stdev(v300), 8)} | {f(statistics.pstdev(v300), 8)} | {f(statistics.stdev(v300) / math.sqrt(3), 8)} |
| 650M | {f(statistics.mean(v650), 8)} | {f(statistics.stdev(v650), 8)} | {f(statistics.pstdev(v650), 8)} | {f(statistics.stdev(v650) / math.sqrt(3), 8)} |

因此统一样本 std 后是 **0.4491±0.0147 vs 0.3826±0.0159**；底本的 300M `±0.013` 实际是 ddof=0（0.01299085），与 650M 的 ddof=1 不能混排。配对差为 0.0644/0.0690/0.0660，均值 +{f(mean_delta * 100, 8)}pp、样本 std {f(paired_std1, 8)}；**3/3 成立**。高精度汇总见 `p02b_b59_summary.csv`，逐 seed 对比见 `p02b_b59_seed_comparison.csv`。

### 两口径的协议差异与根因判定

| 维度 | 原始终值 | 探针种子复测 |
|---|---|---|
| 权重 | 两者均为训练 run s17、5.9B 最终权重 | 完全相同；没有新增训练种子 |
| probe seed | 17；各层 `layer_seed=17+layer` | 29/43/61；各层直接 `layer_seed=seed` |
| 层搜索 | 300M 全 L0–23，650M 全 L0–27 | 300M 仅 L19–23，650M 仅 L23–27 |
| 训练/评估序列数 | 20000/4000 | 8000/4000 |
| split | family_validation→family_test | 相同 |
| pooling/head | 非 pad token mean-pool + linear head | 相同；**pooling 不是差异来源** |
| 最佳层 | 在 family_test 上取全层最大 F1 | 在 family_test 上取窗口内最大 F1 |

代码依据：`probe.py:78-145,159-186,218-238,307-334`、`reseed_b59_300vs650.py:15-35`、`reseed_inner.py:10-37`。0.0744 的 650M 单点差（0.4491−0.3747）是 probe seed、每层 seed 规则、训练样本数和层搜索窗口共同变化的**协议合成差**，不能归因于 pooling，也不能单独归因为“种子噪声”。

### headline 与附录方案

- **650M 与 300M 的同复测协议对比 headline**：建议用 `650M 0.4491±0.0147 vs 300M 0.3826±0.0159（mean±sample SD，n=3 probe seeds，同一 s17 权重；3/3 paired seeds；Δ=+6.65pp）`。必须标明这是探针读出稳定性，不是训练种子泛化结论；正式投稿前应补齐复测原始 JSONL。
- **原始终值入附录**：保留 `0.3747@L25 vs 0.3821@L22（20k/4k，全层，probe seed 17）`，作为协议敏感性和单种子反转案例，不删除、不判为错误。
- **2B→5.9B 预算效应不要跨协议混算**：析因主表的 650M 预算效应仍应用同原始终值协议的 `0.3747−0.3632=+1.15pp`。底本（`$B/delta_20261014/DRAFT_v1_final_20261014.md:298-302`）把 2B 原始 20k 的 0.3632 与 5.9B 复测 8k 的 0.4491 相减得到 +8.59pp，只能标为跨协议描述性差，不能作为干净的预算效应 headline；若要将复测用于预算效应，需对 2B 权重执行相同 8k/4k、相同 probe seeds 与预设层窗口的复测。

## 异常与限制

1. **复测溯源缺口**：30/30 个 evidence 数值在指定 1434 行 JSONL 中无精确 `(run, layer, f1_macro)` 对应行；本次复算权威来源只能是 evidence JSON 的 seed/layer 单元。`p02b_b59_reseed_layers.csv` 将每项标为 `MISSING`。
2. **std 混用**：既有 650M `±0.015` 是样本 SD，而 300M `±0.013` 是总体 SD；统一后 300M 应为 `±0.0159`。
3. **差值 rounding**：未舍入均值差是 +6.64666667pp，写两位为 +6.65pp、一位为 +6.6pp；底本 +6.5pp 不是由当前三值常规四舍五入得到。
4. **重复账本行**：650M 原始终值最佳层在两份账本均各出现两次，已去重；重复行不构成额外种子。
5. **层窗口限制**：复测只覆盖深层窗口，不能证明它是所有层、所有 probe seed 下的全局最大值；两口径也都以 family_test 选择最佳层。

## 产出对应关系

- 裁决①原始行：`p02b_s1_seed_recalc.csv`；std 汇总：`p02b_s1_std_summary.csv`。
- 裁决②复测全部单元：`p02b_b59_reseed_layers.csv`；逐 seed 配对：`p02b_b59_seed_comparison.csv`；双口径汇总：`p02b_b59_summary.csv`。
- 本文即各表的人类可读 `.md`；`p02b_manifest.json` 记录所有输入、生成器和上述输出的 sha256。
"""
    (out / "p02b_caliber_adjudication.md").write_text(report, encoding="utf-8")

    output_names = [
        "p02b_caliber_adjudication.md", "p02b_s1_seed_recalc.csv",
        "p02b_s1_std_summary.csv", "p02b_b59_reseed_layers.csv",
        "p02b_b59_seed_comparison.csv", "p02b_b59_summary.csv",
    ]
    manifest = {
        "task": "P0.2b",
        "backup_root": str(root),
        "read_only_inputs": [
            {"role": role, "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for role, path in paths.items()
        ],
        "ledger_row_counts": {"probe_results.jsonl": len(probe_rows),
                              "probe_results_b59_family.jsonl": len(b59_rows)},
        "reseed_ledger_trace": {"evidence_cells": len(reseed_layers),
                                "exact_jsonl_matches": 0,
                                "status": "30/30 missing from probe_results_b59_family.jsonl"},
        "generator": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "outputs": [
            {"path": str(out / name), "sha256": sha256(out / name)} for name in output_names
        ],
        "manifest_self_hash_excluded": True,
    }
    (out / "p02b_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(output_names) + 1} files to {out}")
    print(f"S1: sample ddof=1 matches seed_table; population ddof=0 matches final_verdict for {len(s1_summary)} scales")
    print(f"Retest: 650M={statistics.mean(v650):.4f}+-{statistics.stdev(v650):.4f}; 300M={statistics.mean(v300):.4f}+-{statistics.stdev(v300):.4f}; paired 3/3; delta={mean_delta * 100:.4f}pp")
    print("Reseed JSONL trace: 0/30 exact matches (documented as missing)")


if __name__ == "__main__":
    main()
