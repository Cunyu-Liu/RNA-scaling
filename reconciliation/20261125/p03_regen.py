#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get(
    "RNA_SC_BACKUP_ROOT",
    "/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc",
))
OUT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "eval_evidence_logs" / "evidence"
EVAL = ROOT / "eval_evidence_logs" / "eval"

INPUTS = {
    "kmer": EVIDENCE / "classical_baselines.json",
    "extra17": EVIDENCE / "classical_baselines_extra.json",
    "extra29": EVIDENCE / "classical_baselines_extra_s29.json",
    "extra43": EVIDENCE / "classical_baselines_extra_s43.json",
    "matrix": EVAL / "eval_matrix_results.jsonl",
    "probe": EVAL / "probe_results.jsonl",
    "seed_summary": EVIDENCE / "s1_seed_table.json",
    "draft": ROOT / "delta_20261014" / "DRAFT_v1_final_20261014.md",
    "old_generator": ROOT / "code_git" / "rna_sc" / "table1_baselines.py",
    "old_table": ROOT / "code_git" / "preprint" / "TABLE1_baselines.md",
    "kmer_code": ROOT / "code_git" / "rna_sc" / "baselines_kmer.py",
    "extra_code": ROOT / "code_git" / "rna_sc" / "baselines_extra.py",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                rows.append((line_number, json.loads(line)))
    return rows


def fmt(value, signed=False):
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


data = {key: load_json(INPUTS[key]) for key in ("kmer", "extra17", "extra29", "extra43", "seed_summary")}
matrix_rows = load_jsonl(INPUTS["matrix"])
probe_rows = load_jsonl(INPUTS["probe"])

matrix = {}
matrix_line = {}
for line_number, row in matrix_rows:
    key = (row.get("model"), row.get("protocol"), row.get("split"))
    matrix[key] = row
    matrix_line[key] = line_number

pattern = re.compile(r"^RNA-Sc-(1M|10M|30M|100M)_s(17|29|43)$")
raw_groups = defaultdict(list)
for line_number, row in probe_rows:
    if pattern.fullmatch(row.get("run", "")) and row.get("split") == "family_validation->family_test":
        raw_groups[row["run"]].append((line_number, row))

lm = {}
for scale in ("1M", "10M", "30M", "100M"):
    seed_values = []
    source_lines = []
    for seed in (17, 29, 43):
        run = f"RNA-Sc-{scale}_s{seed}"
        candidates = raw_groups[run]
        final_ckpt = max(row["ckpt_nt"] for _, row in candidates)
        final_rows = [(line, row) for line, row in candidates if row["ckpt_nt"] == final_ckpt]
        layers = [row["layer"] for _, row in final_rows]
        assert len(layers) == len(set(layers)), f"duplicate final-checkpoint layers: {run}"
        line_number, best = max(final_rows, key=lambda item: item[1]["f1_macro"])
        assert best["n_train"] == 20000 and best["n_eval"] == 4000
        seed_values.append(best["f1_macro"])
        source_lines.append(f"s{seed}=probe_results.jsonl:{line_number}")
        if seed == 17:
            matrix_row = matrix[(run, "probe-meanpool", "family")]
            assert matrix_row["best_f1_macro"] == best["f1_macro"]
    mean = statistics.mean(seed_values)
    std = statistics.stdev(seed_values)
    summary = data["seed_summary"][scale]["probe_best_f1"]
    assert round(mean, 4) == summary[0] and round(std, 4) == summary[1]
    lm[scale] = {
        "seeds": "17/29/43",
        "n_seeds": 3,
        "values": seed_values,
        "mean": mean,
        "std": std,
        "sources": source_lines,
    }

for scale in ("300M", "650M"):
    model = f"RNA-Sc-{scale}_s17"
    key = (model, "probe-meanpool", "family")
    row = matrix[key]
    assert row["n_train"] == 20000 and row["n_eval"] == 4000
    lm[scale] = {
        "seeds": "17",
        "n_seeds": 1,
        "values": [row["best_f1_macro"]],
        "mean": row["best_f1_macro"],
        "std": None,
        "sources": [f"s17=eval_matrix_results.jsonl:{matrix_line[key]}"],
    }

kmer_f1 = data["kmer"]["family"]["f1_macro"]
lgbm_f1 = data["extra17"]["family"]["kmer_lgbm"]["f1_macro"]
cnn_values = [data[key]["family"]["onehot_cnn"]["f1_macro"] for key in ("extra17", "extra29", "extra43")]
randemb_values = [data[key]["family"]["randemb_head"]["f1_macro"] for key in ("extra17", "extra29", "extra43")]
cnn_mean = statistics.mean(cnn_values)
cnn_std = statistics.stdev(cnn_values)
randemb_mean = statistics.mean(randemb_values)
assert "kmer_lgbm" not in data["extra29"]["family"]
assert "kmer_lgbm" not in data["extra43"]["family"]
assert max(kmer_f1, lgbm_f1, cnn_values[0], randemb_values[0]) == lgbm_f1
assert max(cnn_mean, randemb_mean) == cnn_mean

rows = []
for scale in ("1M", "10M", "30M", "100M", "300M", "650M"):
    item = lm[scale]
    three_seed = item["n_seeds"] == 3
    strict_name = "one-hot CNN" if three_seed else "k-mer(1–6)+LightGBM"
    strict_seeds = "17/29/43" if three_seed else "17"
    strict_f1 = cnn_mean if three_seed else lgbm_f1
    rows.append({
        "scale": scale,
        "split": "family_validation->family_test",
        "metric": "macro-F1 (19 classes)",
        "n_train": 20000,
        "n_eval": 4000,
        "lm_protocol": "probe-meanpool; best layer at final checkpoint",
        "lm_seeds": item["seeds"],
        "lm_n_seeds": item["n_seeds"],
        "lm_f1_per_seed": ";".join(f"s{seed}={value:.4f}" for seed, value in zip((17, 29, 43), item["values"])) if three_seed else f"s17={item['values'][0]:.4f}",
        "lm_f1_mean": item["mean"],
        "lm_f1_sample_std": item["std"],
        "strongest_observed_baseline": "k-mer(1–6)+LightGBM",
        "strongest_observed_baseline_seeds": "17",
        "strongest_observed_f1": lgbm_f1,
        "delta_lm_minus_strongest_observed": item["mean"] - lgbm_f1,
        "strict_seed_coverage_baseline": strict_name,
        "strict_seed_coverage_baseline_seeds": strict_seeds,
        "strict_seed_coverage_f1": strict_f1,
        "delta_lm_minus_strict_seed_coverage": item["mean"] - strict_f1,
        "lm_sources": ";".join(item["sources"]),
        "baseline_sources": "classical_baselines_extra.json:family.kmer_lgbm;classical_baselines_extra{,_s29,_s43}.json:family.onehot_cnn",
    })

csv_path = OUT / "p03_baseline_table.csv"
with csv_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        formatted = {}
        for key, value in row.items():
            if isinstance(value, float):
                formatted[key] = "" if value is None else f"{value:.8f}"
            else:
                formatted[key] = "" if value is None else value
        writer.writerow(formatted)

md_lines = [
    "# P0.3 六档 family 切分 LM−最强基线主表",
    "",
    "统一比较边界：`rna_type`、19 类 macro-F1、`family_validation→family_test`、20,000/4,000；LM 一律用最终 checkpoint 的 `probe-meanpool` 最佳层。这里的“同协议”指相同样本切分与评价指标；经典模型是各自直接监督训练，并非 LM 的 mean-pool linear probe。",
    "",
    "观测最强基线是 LightGBM s17（0.1760）。但它没有 s29/s43 证据，所以三种子档的 `Δ_obs` 不是完整三种子对三种子比较；`Δ_strict` 改用具有相同种子覆盖的 CNN。两列回答不同问题，不得混称。",
    "",
    "| 档位 | LM F1（种子） | 观测最强基线 F1（种子） | Δ_obs=LM−观测最强 | 同种子覆盖基线 F1（种子） | Δ_strict=LM−同覆盖最强 |",
    "|---|---:|---:|---:|---:|---:|",
]
for row in rows:
    item = lm[row["scale"]]
    lm_text = fmt(item["mean"])
    if item["std"] is not None:
        lm_text += "±" + fmt(item["std"])
    else:
        lm_text += "（单种子）"
    strict_text = fmt(row["strict_seed_coverage_f1"])
    if row["strict_seed_coverage_baseline"] == "one-hot CNN":
        strict_text += "±" + fmt(cnn_std)
    md_lines.append(
        f"| {row['scale']} | {lm_text}（s{item['seeds']}） | "
        f"{fmt(lgbm_f1)} LightGBM（s17） | {fmt(row['delta_lm_minus_strongest_observed'], True)} | "
        f"{strict_text} {row['strict_seed_coverage_baseline']}（s{row['strict_seed_coverage_baseline_seeds']}） | "
        f"{fmt(row['delta_lm_minus_strict_seed_coverage'], True)} |"
    )
md_lines += [
    "",
    "注：LM 与 CNN 的 ± 为三种子样本标准差（ddof=1）；单种子档不报告标准差。`Δ` 用未四舍五入均值计算，再显示四位小数。严格列仅是种子覆盖一致，不声称不同模型之间是配对种子实验。",
    "",
    "## 逐种子追溯",
    "",
    "| 档位 | 最终 checkpoint 的 mean-pool 最佳层 F1 与账本行 |",
    "|---|---|",
]
for scale in ("1M", "10M", "30M", "100M", "300M", "650M"):
    md_lines.append(f"| {scale} | {'；'.join(lm[scale]['sources'])} |")
md_lines += [
    "",
    "基线字段：`classical_baselines_extra.json family.kmer_lgbm.f1_macro=0.1760`；`classical_baselines_extra{,_s29,_s43}.json family.onehot_cnn.f1_macro=[0.1725,0.1502,0.1541]`。k-mer logistic 的 0.1630 来自 `classical_baselines.json family.f1_macro`，因仅固定 s17 单次结果而不进入三种子严格列。",
    "",
    "复算规则与完整旧口径裁决见 `p03_caliber_adjudication.md`；机读全精度结果见 `p03_baseline_table.csv`。",
]
md_path = OUT / "p03_baseline_table.md"
md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

balanced_100 = matrix[("RNA-Sc-100M_s17", "probe-balanced", "family")]
meanpool_100 = matrix[("RNA-Sc-100M_s17", "probe-meanpool", "family")]
balanced_delta_logistic = balanced_100["best_f1_macro"] - kmer_f1
balanced_delta_lgbm = balanced_100["best_f1_macro"] - lgbm_f1
meanpool_s17_delta_lgbm = meanpool_100["best_f1_macro"] - lgbm_f1
old_30 = lm["30M"]["mean"] - lgbm_f1
old_100 = lm["100M"]["mean"] - lgbm_f1

adj_lines = [
    "# P0.3 基线口径裁决",
    "",
    "## 裁决摘要",
    "",
    f"1. **100M family 下 LightGBM 0.1760 确实高于旧口径 LM 0.170**：精确值是 balanced-probe、s17 的 {balanced_100['best_f1_macro']:.4f} 对 LightGBM s17 的 {lgbm_f1:.4f}，差 **{balanced_delta_lgbm:+.4f}**（约 −0.006）。这只证明 balanced-probe 单种子比较为负；mean-pool s17 为 {meanpool_100['best_f1_macro']:.4f}，对同一 LightGBM 为 {meanpool_s17_delta_lgbm:+.4f}，方向相反。",
    f"2. **旧 +0.007** 的精确复算为 {balanced_100['best_f1_macro']:.4f}−{kmer_f1:.4f}={balanced_delta_logistic:+.4f}，是 100M、s17、balanced-probe 对 k-mer logistic；不是对观测最强基线 LightGBM。",
    f"3. **30M +0.089** 的精确口径为 mean-pool 三种子 LM 均值 {lm['30M']['mean']:.8f}−LightGBM s17 {lgbm_f1:.4f}={old_30:+.8f}，显示为 **+0.0891**。",
    f"4. **100M +0.163** 的精确口径为 mean-pool 三种子 LM 均值 {lm['100M']['mean']:.8f}−LightGBM s17 {lgbm_f1:.4f}={old_100:+.8f}，显示为 **+0.1634**；若先将 LM 显示为 0.3394，则 0.3394−0.1760=0.1634。",
    "5. +0.089/+0.163 都不是完整三种子基线对比：LightGBM 仅有 s17。严格同种子覆盖时，三种子档改对 CNN 三种子均值，结果见主表 `Δ_strict`。",
    "6. 两套旧口径同时改变了 **LM 读出协议（balanced vs mean-pool）、LM 种子聚合（s17 vs 三种子均值）和基线模型（logistic vs LightGBM）**，不可并排当作同一个“LM−最强基线”量。",
    "",
    "## 各基线的切分、协议与种子",
    "",
    "| 基线 | family F1 | 切分与评价 | 训练协议 | 种子口径 |",
    "|---|---:|---|---|---|",
    f"| k-mer(1–6)+logistic | {kmer_f1:.4f} | family_validation→family_test；20k/4k；19 类 macro-F1 | k=1–6 频率、StandardScaler、class_weight=balanced、LBFGS | 代码固定 `random_state=17`；evidence 无 `seed` 字段，仅一次固定运行 |",
    f"| k-mer(1–6)+LightGBM | {lgbm_f1:.4f} | 同上 | balanced、400 trees、`deterministic=True`、`force_row_wise=True` | 仅 s17；s29/s43 JSON 明确缺失 |",
    f"| one-hot CNN | {cnn_values[0]:.4f}/{cnn_values[1]:.4f}/{cnn_values[2]:.4f}；均值 {cnn_mean:.8f}，样本 SD {cnn_std:.8f} | 同上 | 2 层 Conv1d、masked global max-pool、加权交叉熵、10 epochs | s17/s29/s43，完整三种子 |",
    f"| random-embedding head | {randemb_values[0]:.4f}/{randemb_values[1]:.4f}/{randemb_values[2]:.4f}；均值 {randemb_mean:.8f} | 同上 | 冻结随机 embedding、可训练 attention-pool head、10 epochs | s17/s29/s43，完整三种子 |",
    "",
    "LM 的比较协议：`probe-meanpool`、最终 checkpoint、每层 linear probe 后取最佳 macro-F1；1M/10M/30M/100M 为预训练种子 s17/s29/s43 均值，300M/650M 仅 s17。经典基线与 LM 使用相同 family 样本和评价指标，但训练读出头天然不同，因此不能称作“所有训练细节完全同协议”。",
    "",
    "## 旧数字出处与不可混用原因",
    "",
    "- `delta_20261014/DRAFT_v1_final_20261014.md:37-38,810-812,1003-1007`：写 0.170 vs 0.163=+0.007，并同时提示 LightGBM 0.176。其 LM 来源为 `eval_matrix_results.jsonl:13` 的 0.1696（balanced），logistic 来源为 `classical_baselines.json family.f1_macro`。",
    "- `DRAFT_v1_final_20261014.md:812` 与 `code_git/rna_sc/table1_baselines.py:40-58,70-89`：+0.089/+0.163 来自 `s1_seed_table.json` 的 mean-pool 均值减 `classical_baselines_extra.json` 的 s17 LightGBM。生成器没有构造 LightGBM 三种子均值。",
    "- `code_git/preprint/TABLE1_baselines.md:1` 把该表标为 `balanced probe protocol`，但 0.1650/0.1535/0.2651/0.3394 实为 `s1_seed_table.json` 的 mean-pool 汇总；这是标题/协议标签错误。",
    "- 因而不能用 +0.007 否定 +0.163，也不能用 +0.163 改写 +0.007：它们不是同一读出、种子聚合和基线定义。论文若只保留一个主口径，应使用主表并同时说明 LightGBM 种子缺失。",
    "",
    "## 复算核验与异常",
    "",
    f"- 逐层账本最终 checkpoint 复算：1M={lm['1M']['mean']:.8f}±{lm['1M']['std']:.8f}，10M={lm['10M']['mean']:.8f}±{lm['10M']['std']:.8f}，30M={lm['30M']['mean']:.8f}±{lm['30M']['std']:.8f}，100M={lm['100M']['mean']:.8f}±{lm['100M']['std']:.8f}；均与 `s1_seed_table.json` 四位小数一致（样本 SD）。300M={lm['300M']['mean']:.4f}、650M={lm['650M']['mean']:.4f} 与 eval matrix 一致。",
    "- `probe_results.jsonl` 中 1M、30M、100M 的 s17 混有中间与最终 checkpoint；若不过滤 `ckpt_nt`，30M s17 会错误取到 0.2846 而非最终 0.2466。本脚本按每个 run 的最大 `ckpt_nt` 过滤，并校验 s17 与 eval matrix 一致。",
    f"- DRAFT 的 CNN family 0.159±0.010 对应三种子均值与**总体** SD（{statistics.pstdev(cnn_values):.4f}），而 LM 汇总使用样本 SD；本主表统一样本 SD（CNN {cnn_std:.4f}）。旧 `TABLE1_baselines.md` 的 CNN family 0.1725 则只是 s17，不是三种子均值。",
    "- 未以序列 bootstrap 替代训练种子重复；未插补 LightGBM s29/s43；所有差值均由上述固定证据复算。",
    "",
    "## 文件别名",
    "",
    f"备份根：`{ROOT}`。`probe_results.jsonl` 与 `eval_matrix_results.jsonl` 位于 `eval_evidence_logs/eval/`，其余 evidence JSON 位于 `eval_evidence_logs/evidence/`。输入绝对路径与 SHA-256 见 `p03_manifest.json`。",
]
adj_path = OUT / "p03_caliber_adjudication.md"
adj_path.write_text("\n".join(adj_lines) + "\n", encoding="utf-8")

manifest = {
    "task": "P0.3 LM−strongest-baseline caliber unification",
    "generated_at": datetime.now().astimezone().isoformat(),
    "backup_root_read_only": str(ROOT),
    "generator": {
        "path": str(Path(__file__).resolve()),
        "sha256": sha256(Path(__file__).resolve()),
    },
    "inputs": [
        {
            "key": key,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for key, path in INPUTS.items()
    ],
    "outputs": [
        {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in (md_path, csv_path, adj_path)
    ],
    "calculation": {
        "lm_checkpoint_rule": "maximum ckpt_nt per run, then maximum family macro-F1 across layers",
        "lm_seed_aggregation": "arithmetic mean and sample standard deviation (ddof=1) for s17/s29/s43; 300M/650M s17 only",
        "strongest_observed": "s17 LightGBM 0.1760 for all scales; explicitly not three-seed at 1M/10M/30M/100M",
        "strict_seed_coverage": "three-seed CNN mean at 1M/10M/30M/100M; s17 LightGBM at 300M/650M",
        "bootstrap_used": False,
    },
}
manifest_path = OUT / "p03_manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"wrote {md_path}")
print(f"wrote {csv_path}")
print(f"wrote {adj_path}")
print(f"wrote {manifest_path}")
for row in rows:
    print(row["scale"], f"delta_obs={row['delta_lm_minus_strongest_observed']:+.8f}", f"delta_strict={row['delta_lm_minus_strict_seed_coverage']:+.8f}")
