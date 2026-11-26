# P3.2 预注册：650M 跨模型结构差距的语料配方 × 曝光制度归因

- 日期：2026-11-26。
- 状态：**已预注册，未授权启动，未执行训练；数据与时长均为硬约束**。
- 任务：`T-P3.3`。`$B` 为只读备份根 `/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc`；`$P` 为项目内 `补证_P2_20261125/`。
- 外部制度依据：[RiNALMo, arXiv:2403.00043, Methods 4.3–4.4 与 Extended Data Fig. 2](https://arxiv.org/html/2403.00043)。

## 1. 保住的主张与边界

同一 S7 paired-position 口径下，RiNALMo-giga 650M 为 **0.728@L32**，RNA-Sc-650M 为 **0.6255**，跨模型差距 **0.1025（约 +0.10）**。本臂要把目前混杂的“联合 corpus-architecture-recipe 效应”拆出两个受控估计量：

1. 同 RNA-Sc 架构、同 2B nt 下，RiNALMo 语料配方相对 R22 的效应；
2. 在同一 RiNALMo 语料上，RiNALMo 曝光制度相对 2B 单遍曝光的增量效应。

RFamCap 已否定“纯 Rfam 富集即可解释 +0.10”：P2.1 终预算结构效应仅 30M **+1.77pp**、100M **+0.14pp**，且有 randinit 对照。本臂仍不能分离 RoPE/ALiBi、层宽深、SwiGLU/ZLoss 等架构与优化因素，也不能消除外部模型训练—评测双向黑箱；即使完成，也只支持本架构、本语料、本种子下的受控归因。

## 2. 触发条件与授权门

同时满足才可启动：

1. P2 后主代理确认必须解释 +0.10，而不是保留现行诚实降级：“联合 corpus-architecture-recipe 效应，语料为首要嫌疑但未隔离”。
2. 主代理明确批准 **两个新 650M 训练**及第 11 节的实际时长；只批准一个多 epoch 新臂不构成可执行授权，因为缺少同语料 2B 对照。
3. 第 6 节的 split、36M/17M 语料和六 epoch exposure manifest 全部验收；主代理根据精确总 nt 再次确认预算。
4. 启动当日核实两台 5090 的可用显存、`/teams` 空间和长任务保留策略。

“GPU 填满”和“一月内正结果”不构成减少 epoch、改用残片、取消对照或把在飞写成完成的理由。若一月为不可更改的硬截止且精确预算超过该窗口，**本臂不触发**。

## 3. 三格设计与对照

| 格 | 模型与语料 | 曝光制度 | 状态 | 回答的问题 |
|---|---|---|---|---|
| A | RNA-Sc-650M，R22 主语料 | 2B valid nt 单遍 | 已有 `RNA-Sc-650M_s17` | 自训主锚，S7=0.6255 |
| B | RNA-Sc-650M，完整 RiNALMo 配方语料 | **2B valid nt iso-token 单遍** | 新训，必需 | 语料配方效应 B−A |
| C | RNA-Sc-650M，与 B 完全同语料 | **RiNALMo 六簇 epoch** | 新训，必需 | 曝光增量 C−B |
| R | RiNALMo-giga | 原始外部配方 | 观察性锚 | S7=0.728，不作受控对照 |

- 新 run ID 固定为 `RNA-Sc-650M_s17_rinalmo36m_2b`（B）和 `RNA-Sc-650M_s17_rinalmo36m_6ep`（C）。
- A/B/C 均为 650M、s17；同一 randinit17 初始化对照只评一次，因为架构和初始化种子相同。不得用 30M/100M/300M 的旧 RiNALMo 复刻臂替代 B：它们尺度不同，不能直接解释 650M 的 +0.10。
- B−A 固定总 valid nt，隔离语料配方；C−B 固定语料、架构、优化器和训练种子，隔离**曝光制度包**（唯一序列覆盖、簇均衡、重复次数及随机裁剪）。C−B 不再细分各子成分。
- 外部残差 R−C 只描述剩余差距，不命名为纯架构效应。

## 4. RNA-Sc 配方与超参（两臂共同冻结）

权威实现：`$B/code_git/rna_sc/train.py`、`config.py`、`data.py`、`specs.py`。本实验操纵曝光制度，**不移植 RiNALMo 的优化超参**。

| 项 | 冻结值 |
|---|---|
| 架构 | 666,279,680 参数；d_model=1408，28 layers，22 heads，d_ff=5632，ALiBi |
| tokenizer / objective | 单核苷酸 ACGU；MLM 15%，80/10/10 |
| optimizer | AdamW，betas=(0.9,0.95)，weight_decay=0.1 |
| base LR | 3e-4；不使用 RiNALMo 的 5e-5、min-LR=1e-5 或其 2000-step warmup |
| schedule | 前 0.5% 总预算 valid nt 线性 warmup，之后 cosine 至该 run 的总预算终点 |
| batch / context | 16,384 valid nt per optimizer step；1024-nt context |
| precision / clipping / dropout | BF16 autocast / grad-norm 1.0 / 0.0 |
| validation | 原 split `validation`，每 100M nt，masked-target NLL 至 4M nt |
| Early Stop / CPU fallback | 关闭 / 禁止；GPUGuard 计数必须为 0 |
| 训练种子 | s17；B/C 从相同种子随机初始化，不从 A 或 RiNALMo 权重续训 |

B 的 warmup 固定为 10M nt、cosine 终点 2B nt。C 必须在六 epoch exposure manifest 生成后得到精确预算 \(N_C\)，再冻结 `budget_nt=N_C`、`warmup_nt=int(0.005*N_C)`；不得先跑一段再决定 cosine 总长。

## 5. 曝光制度操作化

### 5.1 B：iso-token 语料对照

- 输入是与 C 完全相同的 36M-corpus parquet，按冻结行序流式读取，长序列切成非重叠 1024-nt chunks。
- 到 **2,000,000,000 cumulative valid nt** 停止；允许最后 batch 最多 16,384 nt 的越界并记录真实值。
- 不重复序列，不做簇均衡重采样；validation 始终使用原 R22 split，不用训练语料充当 validation。

### 5.2 C：RiNALMo 六簇 epoch

RiNALMo 原文的关键不是“36M 序列普通循环六次”，而是：36M unique sequences 聚为约 17M clusters，**每 epoch 从每簇随机抽 1 条，即约 17M samples/epoch，共 6 epochs**；长序列每 epoch 重新随机裁剪。Extended Data Fig. 2 记录约 77k steps（原全局 batch 为 192×7，不与本项目的 valid-nt batch 混用）。

C 冻结为：

1. 六个完整 cluster epochs，epoch 索引 e=0…5；每簇每 epoch 恰好一条 member，簇顺序和 member 抽样由 `sample_seed=17+e` 固定。
2. 对长度 >1024 nt 的选中序列，每 epoch 取一个随机连续 1024-nt crop，`crop_seed=10017+e`；短序列取全长。RNA-Sc 不添加 RiNALMo 的 CLS/EOS，故不用其 1022-nt 特殊 token 口径。
3. 保留 RNA-Sc 的确定性 MLM mask（`CRC32(canonical sequence) XOR 17`），不把 RiNALMo 的动态 mask、优化器或 tokenizer 一并搬入。重复 epoch 的科学干预仅限覆盖/簇抽样/重复/crop。
4. 在训练前预计算六 epoch 的 `(epoch,cluster_id,member_id,crop_start,crop_length)` manifest 和精确 \(N_C=\sum crop\_length\)。实际曝光约 6×17M=102M sequence samples；总 nt 由冻结语料和抽样决定，不伪写为固定 2B、12B 或 77k×16,384。
5. 中途不 Early Stop；完成六 epoch 才是科学终点。缩短为 1/2/4 epochs 只能算另一个未授权实验，不能验收本协议。

## 6. 数据依赖与硬验收

### 6.1 原 split（A/B/C 共同需要）

`release22_split_8080.parquet` 仍在重建。须通过 P3.1 第 6 节同一套内容等价验收：29,012,227 行、五 split 计数与 schema、cluster/split 双向一致、零泄漏、全表内容摘要和 566,077 条 train oracle。目标原文件 SHA256 为 `eaa9e44ff760d79ad0f52debb555ebf808afa6adda7bb09644215bec72586b8a`，但内容等价不能由文件 SHA 或行数单独证明。统计等价的新 split 不可直接替代。

### 6.2 完整 RiNALMo 配方语料（B/C 共同需要）

按 `$B/code_git/build_rinalmo_corpus.py` 和原文 Methods 4.3：RNAcentral + Rfam + nt + Ensembl，长度 16–8192，canonical 去重，`mmseqs easy-linclust --min-seq-id 0.7 -c 0.8`；剔除与 `family_validation/family_test/validation/test` 的 canonical 及反向互补重叠。执行 parquet 必须含 `canonical_sequence/split_membership='train'/cluster_id/length/source`。

- 原文 36M/17M 是取整报告；记录重建后的精确序列数、簇数、总 nt、长度分布和各 source 数，不伪造恰好 36,000,000/17,000,000。
- **现有 v1 不是本协议语料**：审计仅 14,026,879 条、6,753,180 簇、10,044,287,765 nt；v2 为 18,510,642 条。二者均不能冒充 36M/17M。
- `$B/data_corpus/rinalmo_corpus_v1.parquet` 已在 X-split 盘点中登记为 **Parquet footer 不可读的截断残片**，不得直接用于训练。即使修复页脚，14M 版本也只可另立探索实验，不能验收 P3.2。
- B1 held-out 剔除后的簇成员表、行序和 parquet 必须冻结并哈希；若无法恢复完整 36M/17M 配方，状态保持 `BLOCKED_CORPUS_NOT_READY`。

### 6.3 bpRNA 与 checkpoint

`bpRNA_parsed.parquet` 使用与 S7 相同的冻结文件及 SHA256。A 的既有最大留存 checkpoint 为 1,900,122,218 nt；B/C 训练完成后也取各自 manifest 中最大 `ckpt_nt`，B 预期约 1.9B，C 取最后一个 100M validation checkpoint。训练真实总 nt 与 probe checkpoint nt 分列，不能混写。

## 7. 结构测评与随机性

权威脚本：`$B/code_git/rna_sc/probe_structure.py`。

- bpRNA TR0→TS0；`random.Random(17)` 顺序抽 8,000 train、1,500 test；ACGU、T→U、256 nt、1-based pair 坐标转 0-based。
- 全 28 层逐 token 隐状态，无 mask、eval、BF16；每层零初始化线性头，AdamW lr=1e-3、weight_decay=0.01、6 epochs、token batch 512，类权重 `[1,max(1,n_neg/n_pos)]`，头种子 17+layer。
- **主指标为旧 S7 可比的 `f1_paired_legacy`**（paired 正类 F1），每 run 在 TS0 全层取最大值。真正二分类 macro-F1 另作敏感性指标，不能与 0.728/0.6255 混算。
- 保存逐 token 预测及 sequence_id，做 **2,000 次按序列配对 bootstrap，seed=20261126**，重算 A/B/C 同一抽样序列上的差和 percentile 95% CI。该 CI 只反映评估样本不确定性；本臂只有一个训练种子，不得写成训练种子 CI。
- TS0 选最佳层沿用旧描述性协议；不把它包装成独立确认性测试，不用 best layer 之外的事后层选择改善归因。

## 8. 预注册归因判据

令 \(F_A,F_B,F_C,F_R\) 为上述 best-layer legacy F1，定义：

\[
\Delta_{corpus}=F_B-F_A,\qquad
\Delta_{exposure}=F_C-F_B,\qquad
\Delta_{joint}=F_C-F_A,\qquad
\Delta_{residual}=F_R-F_C.
\]

所有效应以 pp 报告，并给按序列 bootstrap CI。判决冻结为：

1. **语料独立正贡献**：\(\Delta_{corpus}\) 点估计 ≥1pp 且 95% CI 下界 >0。若只满足 CI，记“可检测但小于 1pp”；CI 跨 0 为未检出，CI 全负为负效应。
2. **曝光独立正贡献**：对 \(\Delta_{exposure}\) 使用同一规则。它是本臂保住“曝光制度可独立归因”的直接判据；不能用 C>R 或 C 接近 R 代替。
3. **语料+曝光共同解释主要部分**：\(\Delta_{joint}\) 的 95% CI 下界 ≥**5.125pp**（0.1025 的一半）。达到才可写“在本架构内共同解释至少一半观察差距”；否则只报告实际分解。
4. **残余差距**：始终报告 \(\Delta_{residual}\)，不归因给单一架构部件。若 C 超过 R，也如实报告过冲，不选择性换层。
5. 比例 \(\Delta_{corpus}/0.1025\)、\(\Delta_{exposure}/0.1025\) 仅作描述，允许为负或超过 100%；不作为独立显著性证据，也不外推为普遍定律。

科学终点是完整估计两个受控对比，不要求结果必须为正。完成 B 而未完成 C，不能回答曝光归因；完成 C 而未完成 B，仍是语料×曝光混杂。

## 9. 工程终点与验收产出

未来结果只写 `$P/results/P3_2/`：

- `exposure_manifest.parquet/json`：六 epoch 全部抽样/crop、精确 \(N_C\)、唯一覆盖和每簇每 epoch 计数；在训练前哈希冻结。
- `training_manifests/`：B/C manifest、日志、checkpoint 索引及 SHA256；两 run 均 `DONE/budget/cpu_fallback_count=0`，C 明确 `epochs_completed=6`。
- `p3_2_structure_layers.jsonl`：A/B/C 及 randinit 的完整层行、逐 token 预测索引和真实 ckpt_nt。
- `p3_2_attribution.csv/json`：四个 F1、四个差、paired bootstrap CI、第 8 节逐项判决。
- `p3_2_bootstrap.jsonl`、`manifest.json`、`SHA256SUMS`：评估重采样、输入和代码全链指纹。

缺 B/C 任一、C 少任一 epoch、使用 14M/18.5M 替代语料、缺原始层行或缺同语料对照均不验收。

## 10. 失败降级

- 未获授权、数据未就绪、时长未批准或 B/C 未同时完成：维持 T-P3.3 原文——“**+0.10 保持联合 corpus-architecture-recipe 效应，语料为首要嫌疑但未隔离**”。
- 只有 B：可新增 650M 的单种子语料配方对比 B−A，但曝光制度仍未隔离。
- \(\Delta_{exposure}\) CI 跨 0：写“未检出独立曝光效应”，不写“曝光无效应”；CI 全负则如实写重复曝光在该设置下不利。
- 联合效应不足 5.125pp 或外部残差仍大：不得宣称 +0.10 已由语料/曝光解释，继续保留架构、优化和外部数据黑箱限定。
- 单种子结果始终是受控单种子证据；不得用序列 bootstrap 升级成“训练稳健”或 E3。

## 11. RTX 5090 资源、存储与并行编排

650M/2B 的旧训练基线为 15,579MiB、95.3h；5090 规划单卡峰值 **16–24GB**，B 预计 **2–4 天**，结构 probe 另需 6–10GB、每 run 约 0.5–2h。

C 的 \(N_C\) 目前不能诚实给定：完整 36M 语料和六 epoch 抽样尚不存在。为授权前量级评估，若 \(N_C=50–80B\) valid nt、650M 实测有效吞吐 8k–20k nt/s，则单卡约 **29–116 天**；这只是区间估算，不是实测或一月承诺。精确 manifest 生成后必须用 `N_C / smoke实测吞吐 × 1.10` 重算，并由主代理再授权。

- **服务器1**：B（2B）→ B 结构 probe；完成后只等待，不自动加发 P3.1。
- **服务器2**：C（六 epoch）→ C 结构 probe；A/randinit 可在 B 的 probe 泳道顺序复测。
- 每台只跑一个训练，不与另一个 650M 或重 probe 同卡并发。C 用 `nohup` 后台和轮询，禁止为填满 GPU 叠加第二个大模型。
- 100M validation 节奏保持不变。checkpoint 科学配置仍为每 100M；为控制运营存储，执行适配器只保留 latest 2、每 5B nt 里程碑及终点，manifest 记录全部点。该保留策略不改变训练轨迹；预计仍需数十至数百 GB，启动前按精确 \(N_C\) 核查 `/teams`。
- 若一月期限不可延长且重算超过窗口，应停止本臂而非减少 epoch；P3.1 是独立的较短候选，不得拿 P3.1 的完成冒充 P3.2。

## 12. 源码指纹（只读核验时）

| 文件（相对 `$B`） | SHA256 |
|---|---|
| `code_git/rna_sc/train.py` | `4ef53be57ed2c4b996d9a01d7c7d21d06018a2ad32771e8004e8798515fbc6ef` |
| `code_git/rna_sc/config.py` | `e1fef7c37cd1ec2d79f95c872a773859bd517a6a3914e981f7d0557bc10295e6` |
| `code_git/rna_sc/data.py` | `e6355986132944437de73e65b07a55d2360b6674e14ad055c704a62f16e4eafa` |
| `code_git/rna_sc/specs.py` | `6773c6adb54bae6d04ae7fad5b62472ecc2e5299d39e662a7a8376beea309833` |
| `code_git/rna_sc/probe_structure.py` | `be3feef768d766811ac700645ab18a4fd06a8dd9ecf3e820ba936128fcaf9679` |
| `code_git/build_rinalmo_corpus.py` | `25aba696bc2ab994ffebf9d498203c55162decba6240007e2149295538d0b8a1` |
| `code_git/fix_corpus_schema.py` | `2f1712e47f17d032f7d36d0284435ccfab0c7344a8b62b61632dabe672c48a76` |
| `eval_evidence_logs/evidence/t435_corpus_audit.json` | `3c82b0802edbe29db54f34d2020067651a29867b48fde08523ad6145d3c053f8` |

执行副本须匹配上述版本；六 epoch sampler、checkpoint 保留和预测保存适配均以新文件落盘并另记哈希，备份永不改写。
