# X-split4：代表集差异调查与 family-split 重建路径

日期：2026-11-26  
状态：**BLOCKED_REAL_CLUSTER_MEMBERSHIP_DIFFERENCE；无可行的原池精确恢复或同池统计等价降级路径；未重跑聚类、未生成候选 split parquet、未发布。**

## 1. 结论摘要

1. 新旧差异不是单纯 representative 命名变化。新聚类中，**15,231** 个簇包含多个旧代表，**3,550** 个簇完全不含旧代表，证明旧簇同时发生合并与拆分；**1,126** 个新簇还包含不同旧 split 标签，旧 `cluster→split` 无法无冲突传播。
2. 原代码和本轮代码都把 dedup 表按唯一 canonical SHA-256 排序，并以 0-based 行号写 FASTA；输入顺序没有可自由调整的工程自由度。本轮实测 `cluster-mode=0`、`cov-mode=1`、`0.8/0.8`、32 threads，MMseqs commit 与文档一致。原始二进制哈希和原始运行日志缺失，不能把唯一根因伪定为线程、硬件或 `--split-memory-limit`。
3. family 哈希本身确实只依赖 `SPLIT_SEED + family 名`，但 **eligibility 的簇数和 held-out family 向整个簇的传播都依赖 member→cluster**。因此“只重建 family_validation/family_test 即可绕过代表差异”不成立。
4. 用新簇实际重算得到 family_validation **7,525,341**（旧值 −411）、family_test **7,086,474**（旧值 +3,579）。更严重的是，仅在旧代表行上就能观察到 **340 条旧 train 序列进入新 family_validation、219 条进入新 family_test**；新池不再保证相对旧 checkpoint 的预训练 held-out。
5. P2.4/P2.5/P2.7 均不能使用新 family 池冒充原协议。P2.7 的“同池统计等价 + 显式差异裁决”也不能消除已证实的 train 泄漏；本时间盒的裁决是 **不做该降级实验**。若另立新规，必须冻结为新数据版本、重新预注册，并重训所有需要比较的相关模型臂。

## 2. 原始规则钉死

权威代码：`/Users/liucunyu/Documents/Codex/2026-08-26/new-chat/work/tokenizer-benchmark/data/`。

### 2.1 dedup 与聚类输入顺序

- `dedup.py:23-34`：先按 `canonical_sequence_hash` 排序、精确分组，最终再次按 hash 排序。
- `cluster.py:21-26`：按 dedup 表行序写 FASTA，ID 为 `0..N-1`；cluster ID 是 representative 的十进制行号。
- 本轮低内存 dedup 仅按 hash 的第一位十六进制字符分区，各区仍调用原 `dedup()`，再按 `0..f` 合并并检查全局 hash 非降序；FASTA 流式写出仍使用同一行号规则。
- canonical hash 是 canonical sequence 的 SHA-256，且每行唯一。因此在同一行集合下，原/新聚类输入顺序由数学规则唯一确定；分区实现没有留下可解释差异的排序自由度。

独立 oracle 核对进一步通过：新 dedup 的 **29,012,227** 行中，旧 train oracle 的 **566,077/566,077** 个 hash 全部找到；`canonical_sequence/rna_type/length/length_bin/num_accessions/accessions` 六字段全部零差异，包括 accession 拼接顺序。证据：`dedup_train_oracle_verify.json`。

### 2.2 MMseqs 参数

原 `cluster.py` 调用：

```text
mmseqs easy-cluster FASTA OUT TMP --min-seq-id 0.8 -c 0.8 --cov-mode 1 --threads 32
```

原脚本没有显式 `--cluster-mode`，所以使用 MMseqs 默认模式。本轮完整日志明确显示：

```text
MMseqs Version: 8cc5ce367b5638c4306c2d7cfc652dd099a4643f
Coverage mode: 1
Cluster mode: 0
Set cluster mode GREEDY MEM
```

本轮唯一新增的命令行工程参数是 `--split-memory-limit 16G`；数学参数未改。原始记录只保留版本标签 `18.8cc5c`，没有原二进制 SHA256 或完整运行日志，故不能确认原/新二进制构建、CPU 调度及内部分区完全一致。

### 2.3 family 与 cluster 切分

原 `split.py` 的实际顺序为：

1. 取 accession 列表第一个 URS，按最高分 Rfam hit 得到 family。
2. family eligibility：`n_seq >= 100 AND n_clusters >= 10`。
3. 仅对 eligible family 计算 `sha256("20260808:fam:<family>")`，依次为 10% family_test、10% family_validation、80% keep。
4. 若某簇包含 held-out family，则整簇进入 family_test（优先）或 family_validation。
5. 其余簇才按 `sha256("20260808:cl:<cluster_id>")` 分 98% train、1% validation、1% test。

所以，family 名对应的哈希桶可以独立于代表 ID 复算，但 **family 是否 eligible、family 池包含哪些序列、以及簇冲突时进入哪个 family 池均不能脱离聚类成员关系复算**。普通 train/validation/test 还直接把 representative 行号字符串放入哈希，代表差异会进一步改变这些标签。

## 3. 代表差异是真实拓扑差异

对完整 29,012,227 行新 TSV，把每个 member ID 与旧 3,357,201 个 representative ID 集合交叉扫描，结果如下：

| 指标 | 实测 |
|---|---:|
| 旧 representative 数 | 3,357,201 |
| 新 representative 数 | 3,334,304 |
| old_only / new_only | 28,089 / 5,192 |
| 含多个旧 representative 的新簇 | 15,231 |
| 这些簇内超出每簇一个的旧 representative 总数 | 26,447 |
| 完全不含旧 representative 的新簇 | 3,550 |
| 含至少两个不同旧 split 标签的新簇 | 1,126 |

其中“含多个旧代表”直接证明旧簇被合并；“完全不含旧代表”证明原旧簇还发生了拆分，不能只通过把新代表重命名为旧代表修复。1,126 个混合标签新簇中，按标签计数为：train 1,114、validation 396、test 380、family_validation 213、family_test 159（同一新簇可计入多个标签）。

证据：`representative_collision_analysis.json`；远端同内容位于 `/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/split_rebuild4/representative_collision_analysis.json`。

### 根因裁决

- **输入顺序：排除为合理根因。** 原/新规则都唯一固定 hash 行序，566,077 条独立 oracle 全字段核对也通过。
- **`--cluster-mode`：排除。** 原代码未显式传参，本轮日志确认实际默认值为 0，与原调用语义一致。
- **`cov-mode`、identity、coverage、threads：排除。** 原代码和本轮实际命令/日志一致。
- **MMseqs 版本标签：一致；二进制构建是否一致：未知。** 原二进制不可取得，不能比较哈希。
- **剩余候选但未证实：** 原/新二进制构建、CPU/线程调度、运行硬件，以及本轮新增 `--split-memory-limit 16G` 对内部执行分区的影响。没有原日志或原 member 映射，无法进一步归因。

没有依据支持通过排列输入或改某个工程参数获得双向零差异。强行偏离原 hash 行序会成为另一套聚类协议，且旧 member 映射缺失，无法验证排列搜索是否恢复原簇。去掉内存参数全量重跑既不能在 2 小时时间盒完成，也不能保证解决差异，因此本轮未重跑。

## 4. family-only 重建的实测否定结果

使用原 `load_family_annotations`、`_stable_accept` 和相同优先级，在新 cluster parquet 上重算全部 family/eligibility/cluster split；只输出统计证据，没有生成或发布候选 parquet。

### 4.1 五类计数与旧代表标签变化

| split | 旧计数 | 新计数 | 新−旧 |
|---|---:|---:|---:|
| train | 14,130,321 | 14,126,529 | -3,792 |
| validation | 164,280 | 163,074 | -1,206 |
| test | 108,979 | 110,809 | +1,830 |
| family_validation | 7,525,752 | 7,525,341 | -411 |
| family_test | 7,082,895 | 7,086,474 | +3,579 |

新簇得到 949 个 eligible family；其哈希桶为 family_test 88、family_validation 89、keep 772。旧表没有独立保存 eligible family 全集，因此这里不把 949 与未知旧总数作差。

在可直接观测的 3,357,201 个旧 representative 行上，新旧 split 不一致 **1,687** 条。关键混淆如下：

| 旧 → 新 | 条数 | 含义 |
|---|---:|---|
| train → family_validation | 340 | 已证实的新 family_validation 预训练泄漏 |
| train → family_test | 219 | 已证实的新 family_test 预训练泄漏 |
| family_validation → train | 26 | 原 held-out 序列回流训练池 |
| family_test → train | 19 | 原 held-out 序列回流训练池 |
| train → test | 273 | random/cluster test 也不再等价 |
| test → train | 269 | 原 test 序列回流训练池 |

559 条 train→family 只是旧 representative 行给出的**可观测下界**；旧非代表成员的完整标签已丢失，实际进入新 family 池的旧 train 序列可能更多。即使删除这 559 条，也不能证明全量零重叠。

### 4.2 eligibility 边界敏感性

下表是在每个 `n_seq>=100` family 的现有 `n_clusters` 上人为增加 delta，再重新判断 `>=10`；它直接测量簇数微差对 eligibility 的影响：

| delta | eligibility 翻转 family 数 | 其中 family_test / family_validation / keep 哈希桶 |
|---:|---:|---:|
| -5 | 42 | 2 / 4 / 36 |
| -2 | 11 | 1 / 1 / 9 |
| -1 | 4 | 1 / 1 / 2 |
| +1 | 6 | 1 / 1 / 4 |
| +2 | 10 | 1 / 1 / 8 |
| +5 | 28 | 1 / 4 / 23 |

±1 簇已足以改变 held-out family 身份。例如 RF00663（247 seq、10 clusters、family_test 桶）与 RF00887（137 seq、10 clusters、family_validation 桶）在少 1 簇时失去 eligibility；RF00991（133 seq、9 clusters、family_validation 桶）与 RF04124（463 seq、9 clusters、family_test 桶）在多 1 簇时获得 eligibility。完整 96 个边界家族见 `family_eligibility_boundary.csv`。

即使只保留远离边界的 family，也只能稳定其哈希身份，不能证明簇内成员、family 间传播冲突和 parquet 流顺序与原表相同。因此“稳健 family 子集”不是原 P2.4/P2.5/P2.7 输入池的精确恢复。

## 5. 可行路径与降级裁决

### 5.1 仅重建 family_validation/family_test：不可作为原协议替代

- family 哈希可复算，但 eligibility、成员和传播不可脱离原簇复算。
- 实测两个 family 池计数已不同，且至少 559 条旧 train 代表进入新 family 池。
- 旧全量 family 池、原 member→rep 和原协议前 8,000/4,000/24,000 条输入哈希均不在备份中；即使计数碰巧一致，也不能证明序列内容或流前缀一致。
- P2.4、P2.5、P2.7 都依赖相对旧 checkpoint 的 pretraining-held-out，新池不满足该前提。

### 5.2 P2.7“同池统计等价 + 显式差异裁决”：不做

统计接近不能修复数据泄漏，也不能把新数据版本的结果回填为 650M random 原协议终值。显式差异裁决可以描述差异，不能把差异变成等价。

若未来另立独立新实验，最低验收应包括：冻结新 cluster TSV/parquet 及哈希、固定完整运行环境与参数、发布 family/eligibility/边界表、记录新旧代表混淆和已知泄漏、保存实际 24,000 条输入哈希，并重新预注册。**要使 family-held-out 结论有效，所有需要比较的训练臂都必须在新 split 上重训；仅在旧 checkpoint 上换池测评不满足验收。** 因此它不是当前 P2.7 的低成本降级路径。

P2.5 同理：换池后 30 个 probe 单元不再是原逐位重测，不能与旧 30 行作同状态复现验收。P2.4 同理不能复用旧模型解释新 family_validation 为 held-out。

### 5.3 唯一保留的原数据恢复路径

优先找回原 `release22_cluster_8080.parquet` 或原 MMseqs member→rep TSV，再使用旧 `release22_cluster_split.parquet` 回填。若未来重跑聚类，必须先达到：

1. 29,012,227 个 member 全覆盖、无重复/越界，representative 双向零差异；
2. 逐 cluster 的 split 字典与旧 3,357,201 行 oracle 完全一致；
3. 全表 canonical hash/序列/长度/accession/行序检查及 566,077 条 train oracle 全字段零差异；
4. deep_verify 五类计数和长度统计全部一致，P2.5/P2.7/P2.4 所需流前缀计数与输入哈希落盘；
5. 在上述门禁全部通过前不得移动到正式发布路径。

需要注意：representative 集合相同并不在数学上单独证明所有 member 边相同；在原 member 映射缺失时，即便通过现有可用 oracle，也只能称“通过现有证据的内容等价验收”，不能声称独立证明了逐 member 完全一致。

## 6. 本轮产出与未做事项

本目录：`补证_P2_20261125/results/split_rebuild4/`。

- `report.md`：本报告。
- `representative_collision_analysis.json`：完整新旧代表碰撞与 split 标签冲突统计。
- `family_pool_analysis.json`：新 family split 计数、旧代表混淆、敏感性及变化示例。
- `family_eligibility_boundary.csv`：96 个 eligibility 边界家族。
- `dedup_train_oracle_verify.json`：566,077 条 train oracle 全字段核对通过。
- `code/analyze_representatives.py`、`code/analyze_family_pools.py`、`code/verify_dedup_against_train_oracle.py`：可复跑分析代码，均通过语法解析并真实运行完成。

远端证据目录：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/split_rebuild4/`；远端代码：`/home/cunyuliu/rna-sc-p2/split_rebuild4/`。

未修改 split_rebuild3 的 TSV/parquet，未启动新 MMseqs 长跑，未生成新 split candidate，未运行 deep_verify/probe，未触碰其他课题进程。正式目标 `/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/release22_split_8080.parquet` 仍未发布。
