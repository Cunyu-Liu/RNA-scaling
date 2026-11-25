# P0.3 基线口径裁决

## 裁决摘要

1. **100M family 下 LightGBM 0.1760 确实高于旧口径 LM 0.170**：精确值是 balanced-probe、s17 的 0.1696 对 LightGBM s17 的 0.1760，差 **-0.0064**（约 −0.006）。这只证明 balanced-probe 单种子比较为负；mean-pool s17 为 0.3263，对同一 LightGBM 为 +0.1503，方向相反。
2. **旧 +0.007** 的精确复算为 0.1696−0.1630=+0.0066，是 100M、s17、balanced-probe 对 k-mer logistic；不是对观测最强基线 LightGBM。
3. **30M +0.089** 的精确口径为 mean-pool 三种子 LM 均值 0.26510000−LightGBM s17 0.1760=+0.08910000，显示为 **+0.0891**。
4. **100M +0.163** 的精确口径为 mean-pool 三种子 LM 均值 0.33936667−LightGBM s17 0.1760=+0.16336667，显示为 **+0.1634**；若先将 LM 显示为 0.3394，则 0.3394−0.1760=0.1634。
5. +0.089/+0.163 都不是完整三种子基线对比：LightGBM 仅有 s17。严格同种子覆盖时，三种子档改对 CNN 三种子均值，结果见主表 `Δ_strict`。
6. 两套旧口径同时改变了 **LM 读出协议（balanced vs mean-pool）、LM 种子聚合（s17 vs 三种子均值）和基线模型（logistic vs LightGBM）**，不可并排当作同一个“LM−最强基线”量。

## 各基线的切分、协议与种子

| 基线 | family F1 | 切分与评价 | 训练协议 | 种子口径 |
|---|---:|---|---|---|
| k-mer(1–6)+logistic | 0.1630 | family_validation→family_test；20k/4k；19 类 macro-F1 | k=1–6 频率、StandardScaler、class_weight=balanced、LBFGS | 代码固定 `random_state=17`；evidence 无 `seed` 字段，仅一次固定运行 |
| k-mer(1–6)+LightGBM | 0.1760 | 同上 | balanced、400 trees、`deterministic=True`、`force_row_wise=True` | 仅 s17；s29/s43 JSON 明确缺失 |
| one-hot CNN | 0.1725/0.1502/0.1541；均值 0.15893333，样本 SD 0.01190980 | 同上 | 2 层 Conv1d、masked global max-pool、加权交叉熵、10 epochs | s17/s29/s43，完整三种子 |
| random-embedding head | 0.0702/0.0692/0.0259；均值 0.05510000 | 同上 | 冻结随机 embedding、可训练 attention-pool head、10 epochs | s17/s29/s43，完整三种子 |

LM 的比较协议：`probe-meanpool`、最终 checkpoint、每层 linear probe 后取最佳 macro-F1；1M/10M/30M/100M 为预训练种子 s17/s29/s43 均值，300M/650M 仅 s17。经典基线与 LM 使用相同 family 样本和评价指标，但训练读出头天然不同，因此不能称作“所有训练细节完全同协议”。

## 旧数字出处与不可混用原因

- `delta_20261014/DRAFT_v1_final_20261014.md:37-38,810-812,1003-1007`：写 0.170 vs 0.163=+0.007，并同时提示 LightGBM 0.176。其 LM 来源为 `eval_matrix_results.jsonl:13` 的 0.1696（balanced），logistic 来源为 `classical_baselines.json family.f1_macro`。
- `DRAFT_v1_final_20261014.md:812` 与 `code_git/rna_sc/table1_baselines.py:40-58,70-89`：+0.089/+0.163 来自 `s1_seed_table.json` 的 mean-pool 均值减 `classical_baselines_extra.json` 的 s17 LightGBM。生成器没有构造 LightGBM 三种子均值。
- `code_git/preprint/TABLE1_baselines.md:1` 把该表标为 `balanced probe protocol`，但 0.1650/0.1535/0.2651/0.3394 实为 `s1_seed_table.json` 的 mean-pool 汇总；这是标题/协议标签错误。
- 因而不能用 +0.007 否定 +0.163，也不能用 +0.163 改写 +0.007：它们不是同一读出、种子聚合和基线定义。论文若只保留一个主口径，应使用主表并同时说明 LightGBM 种子缺失。

## 复算核验与异常

- 逐层账本最终 checkpoint 复算：1M=0.16503333±0.01308065，10M=0.15353333±0.01729287，30M=0.26510000±0.01619290，100M=0.33936667±0.01471099；均与 `s1_seed_table.json` 四位小数一致（样本 SD）。300M=0.3445、650M=0.3632 与 eval matrix 一致。
- `probe_results.jsonl` 中 1M、30M、100M 的 s17 混有中间与最终 checkpoint；若不过滤 `ckpt_nt`，30M s17 会错误取到 0.2846 而非最终 0.2466。本脚本按每个 run 的最大 `ckpt_nt` 过滤，并校验 s17 与 eval matrix 一致。
- DRAFT 的 CNN family 0.159±0.010 对应三种子均值与**总体** SD（0.0097），而 LM 汇总使用样本 SD；本主表统一样本 SD（CNN 0.0119）。旧 `TABLE1_baselines.md` 的 CNN family 0.1725 则只是 s17，不是三种子均值。
- 未以序列 bootstrap 替代训练种子重复；未插补 LightGBM s29/s43；所有差值均由上述固定证据复算。

## 文件别名

备份根：`/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc`。`probe_results.jsonl` 与 `eval_matrix_results.jsonl` 位于 `eval_evidence_logs/eval/`，其余 evidence JSON 位于 `eval_evidence_logs/evidence/`。输入绝对路径与 SHA-256 见 `p03_manifest.json`。
