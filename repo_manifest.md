# P4.2 仓库、权重与数据发布清单

- 日期：2026-11-26
- 仓库：<https://github.com/Cunyu-Liu/RNA-scaling>（public，默认分支 `main`）
- 盘点基线：`0684b98`（`P3 prereg+prep, P4 assertion harness, split rebuild pipeline, chain summary`）
- 工作副本：`/tmp/rna-scaling-push`，已 `fetch origin main` 并 `reset --hard origin/main`
- 备份根 `$B`：`/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc`（只读；本轮未修改）
- 边界：这是发布资产与复现边界清单，不把准备、重建中间产物或未完成实验登记为完成结果；GitHub 不接收权重或大数据。

## 1. 权威源与本地对应关系

| 资产 | 权威源 | 本地/备份对应 | 说明 |
|---|---|---|---|
| 训练、测评、绘图代码 | GitHub 本仓库 | `$B/code_git/` | 备份索引记录其 HEAD 为 `aca9a2c`；后续 P0–P4 代码以 GitHub 新提交为准。`/tmp/rna-scaling-push` 只是推送工作副本。 |
| 单 run 配置与终态 | 各 `runs/<RUN_ID>/manifest.json` | `$B/runs_final2_ckpt/runs/` | 模型、种子、超参、验证曲线和 ckpt 坐标以 manifest 为地面真值。 |
| 原始测评结果 | 各 `eval/*.jsonl` | `$B/eval_evidence_logs/eval/` | 汇总表不能替代原始账本。 |
| P0 对账 | 本仓库 `reconciliation/20261125/` | 项目根 `对账_P0_20261125/` | 数字裁决、口径和未完成项登记。 |
| P2 补证 | 本仓库 `p2/20261126/` | 项目根 `补证_P2_20261125/` | 预注册、脚本和轻量证据；大文件不进 Git。 |
| 图表与数字溯源 | 本仓库 `figures/`、`provenance/` | 项目根 `figs_v6/`、`论文重写_P1_20261125/sections/` | PDF 与绘图脚本发布；本地 PNG 等不必然全部入仓库。 |
| 论文材料 | 本仓库 `paper/`、`preprint/` | 项目根 `论文重写_P1_20261125/`、`论文/` | `paper/` 当前只有一页证据链摘要；完整草稿位于 `preprint/`。 |

旧复现文档对齐核验：盘点前，本仓库 `REPRODUCE.md`、`$B/code_git/REPRODUCE.md`、`$B/delta_20261014/REPRODUCE.md` 三者逐字节相同，SHA-256 均为 `5fac0769b207e4cede2181d57061f78e98a6f5134f7fd2006cd1319b019bdaff`。本轮只更新 GitHub 工作副本，以新证据修正其中 split 和未完成臂状态；备份两份历史快照不改写。

## 2. GitHub 已发布内容（基线 `0684b98`）

仓库共有 525 个跟踪文件，Git pack 约 1.12 MiB；没有权重、parquet 或大型原始语料。

| 目录 | 文件数 | 基线内容 | 状态边界 |
|---|---:|---|---|
| `reconciliation/20261125/` | 43 | P0 主表/差值表、种子与语料对账、基线表、远端核查、未完成注册表、黑名单检查及重生成脚本 | 已发布轻量表和报告。 |
| `figures/` | 12 | 6 张主图的 PDF 与对应 Python 脚本 | 不是全部历史图；其他图仍在本地/备份。 |
| `provenance/` | 14 | 摘要至附录的逐节数字溯源 CSV | 与 P4 数字门配套。 |
| `p2/20261126/` | 147 | P2.1–P2.6 预注册、执行脚本、轻量 JSON/CSV 证据、上传与 split 调查证据 | P2.5/P2.7 只有预注册，没有完成结果；RNA-FM 为未运行。 |
| `p3/` | 18 | P3.1/P3.2 预注册、训练准备代码、配置和报告 | **仅 PREP_COMPLETE；正式训练未启动、无正式 run。** |
| `p4/20261126/` | 3 | 数字断言脚本、逐条结果、覆盖率报告 | 报告记录的是当时输入稿，不代表所有写作门已通过。 |
| `paper/` | 1 | `chain_summary_onepage.md` | 一页证据链摘要。 |
| `preprint/` | 8 | 草稿、参考文献、标识符核验日志、提纲和基线表 | 与 `paper/` 分工不同。 |

## 3. 自训权重清单

### 3.1 只读备份

`$B/runs_final2_ckpt/runs/` 实测 **38 个 run 目录**：34 个含 ckpt 与 manifest，另 4 个为空。34 个有权重的目录由 **32 个终态 run + 2 个 MARS 中间臂**组成，不能把 38 写成 38 个已完成训练。

| 分组 | 数量 | run 名称规则 |
|---|---:|---|
| 主家族种子与大模型 | 14 | 1M/10M/30M/100M × s17/s29/s43，加 300M/650M × s17 |
| b59 预算臂 | 4 | 30M/100M/300M/650M × `_b59` |
| 语料规模臂 | 5 | 30M `_c1M/_c10M`；10M `_c1Mcs/_c5Mcs`；30M_s29 `_c1Mcs` |
| 语料族臂 | 6 | 30M/100M `_rfamcap`；10M/30M/100M/300M `_rinalmocorpus` |
| 多样性臂 | 3 | 10M/30M/100M `_rw1` |
| MARS 中间臂 | 2 | 100M 最新 400,023,183 nt；300M 最新 200,010,618 nt |

每个有权重目录实测保留 2 个 `.pt`（MARS 100M 为例外，保留 4 个），并带 manifest；中间臂只可复测该中间坐标，不得冒充 2B 终态。

### 3.2 团队远端已上传的三份主臂终值权重

位置：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights/`。这是团队存储，不是 GitHub release。三份均为去 optimizer 的模型权重，源哈希、逐张量一致性、strict load 与 CUDA 前向均为 PASS。

| run | 文件 | nt / step | 字节 | SHA-256 |
|---|---|---:|---:|---|
| RNA-Sc-30M_s17 | `RNA-Sc-30M_s17/ckpt_nt1900121822_step202784.pt` | 1,900,121,822 / 202,784 | 132,860,263 | `21b9e8594c46648610a9221019e3f0b1b846b7c652966111cb3e09100e8f7037` |
| RNA-Sc-100M_s17 | `RNA-Sc-100M_s17/ckpt_nt1900122218_step202784.pt` | 1,900,122,218 / 202,784 | 366,586,871 | `7e73e31317b7a4eac601356942bff4dd885729556f5255b9c079b61749d3bb45` |
| RNA-Sc-650M_s17 | `RNA-Sc-650M_s17/ckpt_nt1900122218_step202784.pt` | 1,900,122,218 / 202,784 | 2,665,204,775 | `0631ccb128900f84eb02fb0c4396ae1de5b2330d1ea003465f4134098e63512d` |

证据：`p2/20261126/evidence/upload_main/weight_verification.json`。远端只登记上述三份；其余权重仍以只读备份为来源，未宣称已上传到团队远端。

### 3.3 外部模型权重

- `$B/ext_baselines/`：RiNALMo micro/mega/giga 与 NucleicBERT，实测 29 个有效文件、4,946,968,875 字节（备份索引约记 4.6G）。
- **RNA-FM `RNA-FM_pretrained.pth` 未备份、未上传。** P2.3 状态是 `NOT_RUN_WEIGHT_MISSING`，结果为空而非零；如未来补测须从官方 `ml4bio/RNA-FM` 获取并另行记录哈希。
- 第三方模型、数据和代码不因本仓库 MIT LICENSE 而改变其原始许可证。

## 4. 数据清单与可读性

`$B/data_corpus/` 实测 28 个有效文件、3 个子目录、3,760,893,060 字节。包含 9 个 parquet、bpRNA/ArchiveII 测评数据、Rfam.cm 及索引、`subsamples/`、`s12_work/` 和 `rinalmo_corpus_work/`。文件存在不等于内容完整。

### 4.1 Parquet 实测

| 文件 | 行数 | 状态 | 用途/边界 |
|---|---:|---|---|
| `archiveii.parquet` | 3,975 | READABLE | 结构测评。 |
| `bpRNA_parsed.parquet` | 12,317 | READABLE | 结构测评。 |
| `r22_train_rfamcap.parquet` | 566,077 | READABLE | rfamcap 训练臂及 train oracle。 |
| `release22_cluster_split.parquet` | 3,357,201 | READABLE | 仅 `cluster_id,split`；不是序列级 split8080。 |
| `subsamples/c1Mcs.parquet` | 190,917 | READABLE | 仅 cluster allowlist。 |
| `subsamples/c5Mcs.parquet` | 975,339 | READABLE | 仅 cluster allowlist。 |
| `mars_corpus.parquet` | — | **UNREADABLE，footer 非 Parquet magic** | 543,686,656 字节残片；需从 MARS OMIX003037 重建，不能当完整语料。 |
| `r22_train_reweighted.parquet` | — | **UNREADABLE，footer 非 Parquet magic** | 821,833,304 字节残片；需由 reweight 管线重建。 |
| `rinalmo_corpus_v1.parquet` | — | **UNREADABLE，footer 非 Parquet magic** | 415,525,072 字节残片；需由 RiNALMo recipe 重建。 |

逐文件哈希、schema 和错误：`p2/20261126/evidence/split_rebuild/source_inventory.csv`。RNAcentral 大语料 parquet 不在备份中；构建入口为仓库 `build_corpus_rnacentral.py`。MARS 与 RiNALMo 构建入口分别为 `build_corpus_mars.py`、`build_rinalmo_corpus.py`。

### 4.2 重建管线产物（保留审计，不是合格替代数据）

代码：仓库 `p2/20261126/scripts/split_rebuild3/`；本地完整报告：项目根 `补证_P2_20261125/results/split_rebuild3/report.md`。远端中间产物保留在 `/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/split_rebuild3/`，未进入 GitHub。

- RNAcentral 22.0 源 FASTA 已完整下载：7,281,938,321 字节；Rfam annotations 为 331,006,468 字节。
- canonical 完成：30,191,670 输入 → 29,252,916 primary + 938,754 QC。
- dedup 完成：29,012,227 条唯一序列；rfamcap train oracle 566,077/566,077 内容核验一致。
- 新 MMseqs2 聚类 TSV 为 29,012,227 行、497,144,593 字节；cluster parquet 为 11,969,669,033 字节。
- **验收失败**：新代表 3,334,304，旧代表 3,357,201；簇拓扑改变。后续 split/deep_verify/oracle/probe 发布门禁未通过，未发布最终 parquet。

本地最新终裁为 `补证_P2_20261125/split_final_adjudication.md`：重建序列内容管线正确，但至少 340 条旧 train 序列进入新 family_validation、至少 219 条进入新 family_test；用于旧 checkpoint 会破坏 held-out 前提。该终裁及完整重建报告不在基线提交 `0684b98` 中，本清单明确记录这一发布缺口，不把基线中的“重建中”状态当作最新科学状态。

## 5. `release22_split_8080.parquet` 缺失声明

**原文件未备份，备份与两台远端搜索均无精确命中；当前没有合格替代品。** 原验收记录为 29,012,227 行、3,357,201 簇，至少包含 `split_membership/canonical_sequence/rna_type`，原 SHA-256 为 `eaa9e44ff760d79ad0f52debb555ebf808afa6adda7bb09644215bec72586b8a`。现有 `release22_cluster_split.parquet` 只有每簇一行，不能单独恢复每序列一行。

缺失的不是一个可用 rfamcap/train-only 文件替代的通用数据文件，而是旧训练的协议输入。全量重建因聚类代表和泄漏验收失败，不能用于旧模型正式测评或 iso-split 新训练。

按最新终裁：

- P2.5 650M@5.9B 重测固化：**不做**；旧重测摘要仅作未复核历史记录。
- P2.7 650M random 终值：**不做**；预算免疫主张限已有三尺度，650M 只保留 5B midpoint 标签。
- P2.4 RNS 分箱控长度：**不做**；相关方向主张撤回，轴依赖机制未裁决。
- P3.1 多种子补训：**不触发且未启动**；换数据版本会破坏与原比较臂的可比性。P3.2 曝光臂同样不触发。

## 6. 未完成语谱臂

| 臂 | 备份权重 | 当前可复现边界 |
|---|---|---|
| MARS 30M | 空目录 | 须先训练；无探针结果。 |
| MARS 100M | 4 个 ckpt，最新 400,023,183 nt | 只能复测中间点；不是 2B 完成臂。 |
| MARS 300M | 2 个 ckpt，最新 200,010,618 nt | 只能复测中间点；不是 2B 完成臂。 |
| RNAcentral 30M | 空目录 | 须先训练；无探针结果。 |
| RNAcentral 100M | 空目录；旧状态快照称 3 ckpt，与备份不符 | 须找回权重或重训，不能从备份复测。 |
| RNAcentral 300M | 空目录；旧状态快照称 2 ckpt，与备份不符 | 须找回权重或重训，不能从备份复测。 |

六臂均没有已完成的正式探针结果。MARS/RNAcentral 大语料也未形成可直接恢复的完整备份，因此“脚本存在”不等于“一键重训已就绪”。

## 7. 显式未知项与发布缺口

1. 原 `release22_split_8080.parquet`、原 member→representative 映射、原聚类 parquet、原 MMseqs2 二进制及完整运行日志均缺失；无法唯一判定新旧簇拓扑差异根因。
2. MARS/RNAcentral 六臂未收口；MARS、RiNALMo、reweighted 三份 parquet 残片不可读，RNAcentral 大语料缺失。
3. RNA-FM 权重缺失，P2.3 RNA-FM 未运行；不得零填充。
4. 团队远端只有三份主臂去 optimizer 权重，其他自训臂和 b59 权重未登记为已上传。
5. P3 目录是启动准备而非正式结果；不得把 smoke 或 prep 写成多种子/曝光实验完成。
6. 最新 split 终裁与完整重建报告仍在项目根本地目录，尚未作为独立报告纳入基线 GitHub 提交；本提交只发布清单和复现边界修正。
7. 旧 `REPRODUCE.md` 提到的历史环境导出路径和 `redteam_numbers.py/redteam_final.py` 不属于当前备份根/仓库已核实资产；使用新 P4 `assert_numbers.py` 时，应按 `p4/20261126/coverage_report.md` 的输入约定执行。

## 8. 许可证与再发布

- 基线 `0684b98` 无 `LICENSE`，GitHub API `licenseInfo=null`；`docs/TASKS_V2.md` 的仓库发布任务明确要求 MIT。
- 本轮在仓库根新增标准 **MIT LICENSE**（Copyright (c) 2026 Cunyu Liu）。
- MIT 文本覆盖本仓库可授权内容；第三方模型权重、RNAcentral/Rfam/MARS 数据及其构建源仍遵循各自条款。
- 本轮提交只包含 `repo_manifest.md`、`REPRODUCE.md`、`LICENSE`，不上传权重、parquet、FASTA、cluster TSV 或其他大数据。
