# X-split：release22_split_8080 重建调查报告

## 结论

**状态：`BLOCKED_NO_VALID_FULL_SOURCE`。未重建出合格文件，P2.5/P2.7 继续阻塞。**

调查期间，共享目标路径曾出现一份由其他并发执行者创建的文件；本任务没有创建、覆盖或删除它。该文件经全行审计确认是 rfamcap 子集派生物，**不是 release22_split_8080，不得用于正式测评**。2026-11-25 18:43:48 UTC 最终复查时它已被外部移除，目标路径恢复为不存在：

- 路径：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/release22_split_8080.parquet`
- 状态：`INVALID_CONCURRENT_RFAMCAP_SUBSTITUTE`
- 566,077 行，只有 `canonical_sequence/split_membership/cluster_id`，缺少 `rna_type`。
- `canonical_sequence + cluster_id` 及行顺序与备份 `r22_train_rfamcap.parquet` 完全一致。
- 仅覆盖 148,607 / 3,357,201 簇（4.4265%）；五类切分中的 `family_validation`、`family_test` 均为 0 行。
- 116,907 行的 `split_membership` 与权威 `release22_cluster_split.parquet` 不一致。
- 其 SHA256 为 `6d4f86a96946278ee769a2086329b8060e3ae91c087e7216b8ca39099110f879`，与权威原文件哈希不符。

在首次远端盘点（2026-11-25 18:21 UTC 左右）中该路径不存在；18:38 UTC 的原始 JSON 清单记录了新文件；18:43:48 UTC 的 `final_target_status.json` 记录其已不存在。按“不删除非本任务创建文件”的约束，本任务只标记其无效，移除发生在其他执行侧。**后续仍须防止同路径伪替代，只有完整验收才能解除阻塞。**

## 权威验收基线

预注册合同要求 P2.5 使用 `family_validation` 前 8,000 与 `family_test` 前 4,000，P2.7 使用 `family_validation` 顺序 24,000；因此不能用 train-only、重抽样、重加权或 rfamcap 子集替代。

| 验收项 | 权威预期 | 曾出现的并发 target | 判定 |
|---|---:|---:|---|
| 行数 | 29,012,227 | 566,077 | FAIL |
| 必需列 | `split_membership/canonical_sequence/rna_type` | 缺 `rna_type` | FAIL |
| train | 14,130,321 | 449,170 | FAIL |
| validation | 164,280 | 53,218 | FAIL |
| test | 108,979 | 63,689 | FAIL |
| family_validation | 7,525,752 | 0 | FAIL |
| family_test | 7,082,895 | 0 | FAIL |
| 簇数 | 3,357,201 | 148,607 | FAIL |
| 原文件 SHA256 | `eaa9e44ff760d79ad0f52debb555ebf808afa6adda7bb09644215bec72586b8a` | `6d4f86a96946278ee769a2086329b8060e3ae91c087e7216b8ca39099110f879` | FAIL |

其他旧深验证预期：长度 `<16` 8,891、`16-4096` 28,756,105、`4097-16384` 208,293、`>16384` 38,938；最短 10、最长 583,414；A/C/G/U alphabet-count 各 29,009,257 / 29,006,295 / 29,008,086 / 29,009,979；簇跨切分与精确序列跨切分均为 0。由于没有合格重建文件，这些项目均为 `NOT_RUN`，不是 PASS。

原 split SHA256 来自公开仓库 `Cunyu-Liu/tokenizer-benchmark` 固定提交 `a236530f8348f7d02ff74c15ce9267ee0989954f` 的 `docs/acceptance/P1_acceptance.json`。该验收文件还给出上游 `release22_cluster_8080.parquet` SHA256：`bd8347ab0bfdf5c2970789730f5315544ffd7f5e73136622eba80406b75c06ca`。

## 数据源调查与比对

### 可用的簇→切分表

备份 `data_corpus/release22_cluster_split.parquet` 可读，3,357,201 行且 `cluster_id` 全部唯一、无空值。重新统计得到：train 3,022,118、family_validation 227,978、family_test 45,281、validation 30,780、test 31,044，逐项匹配旧 `family_index_summary.json`。

它只提供 `cluster_id → split`，不含序列和 RNA 类型，无法单独恢复 29,012,227 行。

### 候选序列源均不完整或不可读

| 候选 | 实测 schema / 状态 | 不能用于完整 join 的原因 |
|---|---|---|
| `r22_train_rfamcap.parquet` | 566,077 行；含序列、类型、簇、切分 | 仅 rfamcap 子集；当前并发 target 的序列+簇正来自它 |
| `r22_train_reweighted.parquet` | Parquet footer 不可读 | 备份审计早已标记为截断残片；即使完整也只有 train 的爆炸式重复，无 held-out 和 `rna_type` |
| `rinalmo_corpus_v1.parquet` | Parquet footer 不可读 | 截断残片；原构建流程做长度过滤、去重并删除 held-out，不能恢复五切分 |
| `mars_corpus.parquet` | Parquet footer 不可读 | 外部 MARS train 语料，不是 RNAcentral 全量 clustered 源 |
| `subsamples/c1Mcs.parquet` | 190,917 行，仅 `cluster_id` | 无序列、类型 |
| `subsamples/c5Mcs.parquet` | 975,339 行，仅 `cluster_id` | 无序列、类型 |
| `release22_cluster_split.parquet` | 3,357,201 行，仅 `cluster_id/split` | 只是 join 右侧，不是序列源 |
| `rinalmo_corpus_work/` | 有 MMseqs TSV 与代表 FASTA；缺 `all_raw.fasta/all_uniq.fasta` | 28,922,968 个成员 ID 不能还原序列；`dedup_eval` 已删 14,896,089 条 held-out 相关记录，且新聚类 ID 非原 80/80 `cluster_id` |

远端调查原始结果见 `remote_server1_inventory.json` 和 `remote_server2_inventory.json`：

- 服务器1 `/root/rna-sc` 只有 runs；`/root/rnaft_restore/03_RNA迁移学习_rna-sc/data_corpus` 是上述备份镜像，含同样的截断文件。
- 服务器1、2 的 `/mnt/cunyuliu/tokenizer-benchmark` 和 `/mnt/cunyuliu/rna-sc/data` 均不存在。
- 服务器2 `/home/cunyuliu/rna-sc` 是代码快照；共享 `rna-sc-p2/data` 除簇表、测评小数据和上述无效 target 外，没有全量源。
- GitHub `tokenizer-benchmark` 无 releases 数据资产；备份盘也没有 `release22_primary/dedup/cluster_8080.parquet` 或 `rnacentral_active.fasta.gz`。

## 精确缺失项与可行恢复路线

直接 join 所缺的是：**含 29,012,227 条 `canonical_sequence/rna_type/cluster_id` 的原 `release22_cluster_8080.parquet`（或等价完整 clustered/dedup 源）**。拿到后可与现有 `release22_cluster_split.parquet` 连接，再逐项验收。

另一条完整路线是从公开 RNAcentral 22.0 重建上游：

1. `rnacentral_active.fasta.gz`，权威登记及当前 HTTP Content-Length 均为 7,281,938,321 字节。
2. 按固定提交的 `data/canonicalize.py` 得到 30,191,670 → 29,252,916 主序列（938,754 QC）。
3. 按 `data/dedup.py` 得到 29,012,227 去重序列（合并 240,689）。
4. 按 `data/cluster.py` 以 MMseqs2 80/80、cov-mode 1 重聚类；旧环境冻结为 MMseqs2 `18.8cc5c`、polars `1.43.2`、pyarrow `25.0.0`。
5. 用现有 cluster-split join，或用 `data/split.py` 加 `rfam_annotations.tsv.gz` 重放 `SPLIT_SEED=20260808`，最后核对全部统计量及哈希。

本轮没有执行该完整上游重建：服务器1实测下载约 11.7 kB/s；服务器2约 647 kB/s，仅 FASTA 下载约需 3 小时，且 16 核 load average 已超过 40，后续全量聚类不能视为快速 join。当前环境也未发现可用 `mmseqs` 命令。因此这只是后续路线，不记为已恢复。

## 影响面与执行边界

- **P2.5：阻塞。** 无法取得协议规定的 family_validation/family_test 原始流。
- **P2.7：阻塞。** 无法取得 family_validation 顺序 24,000 条；不得用 random 自行重抽或 rfamcap 替代。
- 上述无效 target 曾位于 `sitecustomize` 指向路径，故“文件存在”不能作为解除阻塞依据；最终复查时该文件已不存在，后续只能以完整统计量和哈希验收解除阻塞。
- 未启动 GPU、未发生 CUDA/CPU 降级；未 kill 进程；未修改备份、交接文档、论文稿或旧账本。
- 未写出任何自称合格的 `release22_split_8080.parquet`。

## 证据文件

- `expected_stats.json`：旧深验证、簇计数、上游计数及权威 artifact 哈希。
- `source_inventory.json/.csv`：备份全部 9 个 parquet 的 schema、行数、错误、SHA256，以及 RiNALMo 工作文件审计。
- `remote_server1_inventory.json`、`remote_server2_inventory.json`：远端路径与 parquet 原始清单。
- `invalid_target_audit.json`、`invalid_target_detailed.json`：并发伪替代文件的哈希、切分、全行来源与 cluster-split 不一致审计。
- `final_target_status.json`：最终复查时目标路径不存在的时间线证据。
- `audit_sources.py`：本地只读盘点脚本。
- `manifest.json`、`SHA256SUMS`：本证据包文件哈希。
