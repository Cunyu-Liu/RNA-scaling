# P3.1 预注册：300M/650M 三种子饱和稳健性

- 日期：2026-11-26。
- 状态：**已预注册，未授权启动，未执行训练**。本文只冻结协议，不代表 P2 缺口已裁决或数据已就绪。
- **2026-11-26 留存修订**：经主代理裁决，每个新 run 仅保留四个 checkpoint，以解决原每 100M nt 留档约 411.27GiB、接近共享盘余量的问题；100M nt 收敛监控和统计判据不变。
- **2026-11-26 iso-budget 追加修订**：经主代理再次裁决，新 run 主终点由名义 2.0B 改为既有 s17 实际使用的 **1,900,122,218 cumulative valid nt**，四留存点相应为 0.5B/1.0B/1.5B/1,900,122,218nt，最后一点为 final。理由是消除新 run 与 s17 历史对照的训练预算差异，实现逐 nt 严格 iso-budget；`max_final_nt` 同值，不再允许 overshoot。本条取代此前 2.0B final 的留存口径。
- 任务：`T-P3.2`。`$B` 为只读备份根 `/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc`；`$P` 为项目内 `补证_P2_20261125/`。

## 1. 保住的主张与边界

目标是把 Q1 的“上段饱和”从单种子观察升级为三种子稳健结论。既有 family-split、1,900,122,218nt、mean-pool probe 主表为：100M 三种子均值 **0.3394±0.0147**（样本 SD，ddof=1），300M s17 **0.3445@L22**，650M s17 **0.3632@L8**；既有斜率

\[
\bar F1_{100M}=(0.3263+0.3365+0.3553)/3=0.3393666667\;(\text{表中显示为 }0.3394),
\qquad
S_{100,650}=\frac{0.3632-0.3393666667}{\log_{10}(650/100)}=0.02931842\approx0.0293<\varepsilon=0.03.
\]

300M/650M 当前均只有 s17，故 0.0293 不是三种子稳健证据。本臂只讨论固定 1,900,122,218nt 下 family-classification 通道的规模饱和，不讨论 5.9B 预算、structure/random 通道、所有表征能力的上限或外部模型。

## 2. 触发条件与授权门

同时满足以下条件才可启动；任一不满足均保持 `NOT_AUTHORIZED / NOT_STARTED`：

1. 主代理在 P2 收口后确认仍要保留“**饱和稳健**”，而不接受降级为“单种子档观察到饱和”。
2. 主代理对本文所列新训练、GPU 预算和产出路径作显式启动确认。用户提出“GPU 填满”和“一月内正结果”是资源偏好与目标，**不等于跳过 P2 裁决、数据验收和启动授权**。
3. 原 `release22_split_8080.parquet` 恢复或通过第 6 节的内容等价验收；P2.5/P2.7 等同数据任务不被本臂挤占或静默降优先级。
4. 两台 5090 的其他课题占用、本项目可用显存和 `/teams` 空间在启动当日重新核查。

## 3. 设计与对照

| 规模 | s17 | s29 | s43 | 合计新训练 |
|---|---|---|---|---:|
| 300M | 已有，不重复训练 | 新训 | 新训 | 2 |
| 650M | 已有，不重复训练 | 新训 | 新训 | 2 |

- run ID：`RNA-Sc-{300M,650M}_s{29,43}`；已有 s17 只读复用权重。
- 对照锚：100M 同训练种子 s17/s29/s43 的既有原始终点 probe 值固定为 **0.3263/0.3365/0.3553**，不因新结果而换锚。
- 主终点是 100M→650M 的同种子配对斜率；300M→650M 是预先指定的辅助上段斜率，不能事后替代主终点。
- 所有新 run 从随机初始化开始，不从 s17 续训，不 Early Stop，不根据 family_test 调参或提前选种子。
- 每个训练种子同时控制模型初始化、数据 mask 和训练流；probe 层种子是另一层随机性，不称为训练重复。

## 4. 训练配方与超参（冻结）

权威实现：`$B/code_git/rna_sc/train.py`、`config.py`、`data.py`、`specs.py`。除 model/seed/device/out-dir 外，不改科学配置。

| 项 | 300M | 650M |
|---|---:|---:|
| 实际参数量（既有 manifest） | 302,098,432 | 666,279,680 |
| d_model / layers / heads / d_ff | 1024 / 24 / 16 / 4096 | 1408 / 28 / 22 / 5632 |
| 位置与 tokenizer | ALiBi；单核苷酸 ACGU | 同左 |
| 目标 | MLM 15%，80% MASK / 10% 随机 ACGU / 10% 保留 | 同左 |
| 总终点 | **1,900,122,218 cumulative valid nt，与 s17 逐 nt 一致** | 同左 |
| context / effective batch | 1024 nt / 16,384 valid nt per optimizer step | 同左 |
| optimizer | AdamW，betas=(0.9,0.95)，weight_decay=0.1 | 同左 |
| base LR | 3e-4（两档均无 scale factor） | 同左 |
| schedule | 保持 s17 原轨迹：warmup 10,000,000 nt，随后按名义 2B nt cosine；在 1,900,122,218nt 精确停止，不改写 schedule budget | 同左 |
| precision / clipping / dropout | BF16 autocast / grad-norm 1.0 / 0.0 | 同左 |
| validation | 原 split `validation`，每 100M nt，masked-target NLL 累计至 4M nt | 同左 |
| checkpoint/validation 节奏 | validation 每 100M nt 并在 budget final 强制补做；仅在跨过 0.5B/1.0B/1.5B/1,900,122,218nt 时保存四个 model+optimizer checkpoint；1,900,122,218nt final 必留，完整 manifest 记录所有 validation 与实际存档 nt | 同左 |
| Early Stop | **关闭，`early_stop_patience=0`** | 同左 |
| CPU fallback | 禁止；GPUGuard 计数必须为 0 | 同左 |

数据流保持 parquet 行序、长序列非重叠 1024-nt chunks、按 valid non-pad nt 计预算；mask 由 `CRC32(canonical sequence) XOR training seed` 确定。追加修订后，新 run 的 `final_nt` 必须**精确等于 1,900,122,218**，与既有 s17 两档用于 probe 的 checkpoint 逐 nt 一致；`max_final_nt` 固定为同值，任何 overshoot 或不足均拒绝验收，不再沿用此前 2.0B 终点或 2,000,003,270nt 的表述。

## 5. Probe 协议（冻结）

权威脚本：`$B/code_git/rna_sc/probe.py`。训练终点是 **1,900,122,218nt**；新 run 的 probe 使用 manifest 中最大 `ckpt_nt` 的 final checkpoint，与既有 s17 两档及旧主表的 1,900,122,218nt 逐 nt 一致。不得改用 best-val、0.5B/1.0B/1.5B、2.0B 或 5.9B/b59 checkpoint，也不得用新留存规则反写旧 manifest。

- 数据流：`family_validation` 顺序前 **20,000** 条训练，`family_test` 顺序前 **4,000** 条评估；ACGU、T→U、截断 256 nt。
- 表示：每层逐 token 隐状态在非 pad 位置 mean-pool；eval、无输入 mask、BF16 autocast；300M 全 24 层、650M 全 28 层。
- 头：普通线性，AdamW lr=1e-3、weight_decay=0.01、8 epochs、batch 256；`layer_seed=17+layer`；训练标签排序映射，test 未见类过滤，macro-F1 只对 test 实际出现类求均值。
- 每个 run 在自己的全层曲线中取最大 macro-F1；这是既有描述性选层协议，不能包装成独立测试集确认。
- 100M 三个旧值作为主锚。为排除环境漂移，执行时重跑 100M 三档及 300M/650M s17 probe 作核验；若四位小数不一致，先裁决差异，不与新种子混成一张“统一协议”表。

## 6. 数据依赖与就绪验收

共同输入为 `release22_split_8080.parquet`。截至本文日期它仍在重建，**文件存在本身不构成就绪**。必须：

1. 具备 29,012,227 行及 `canonical_sequence/rna_type/cluster_id/split_membership` 等原 schema；五 split 计数依次为 train 14,130,321、validation 164,280、test 108,979、family_validation 7,525,752、family_test 7,082,895。
2. 与权威 representative/cluster→split 表双向核对，无簇跨 split、无精确序列跨 split；全表逐行内容摘要和 566,077 条 rfamcap train oracle 交叉核验通过。
3. 原文件 SHA256 目标为 `eaa9e44ff760d79ad0f52debb555ebf808afa6adda7bb09644215bec72586b8a`，但 Parquet 元数据不同可造成文件哈希不同；**内容等价是必要条件，不能只凭文件 SHA 或行数放行**。
4. 若只能构造“同池统计等价 split”，它与旧 s17/100M 可能泄漏或不可比，本协议自动停止，需另立新协议并重训全部对照，不能称为本臂完成。

## 7. 预注册统计判据

对 \(s\in\{17,29,43\}\)：

\[
S_s=\frac{F1_{650M,s}-F1_{100M,s}}{\log_{10}(650/100)},\qquad
\bar S=\frac{1}{3}\sum_sS_s.
\]

主报告同时给出 300M/650M 各三值、三种子均值±**样本 SD**（ddof=1）、三个配对斜率及 \(\bar S\)。训练种子不确定性用配对 Student-t 95% CI：

\[
CI_{95}=\bar S\pm t_{0.975,2}\,SD_{sample}(S_s)/\sqrt3,
\quad t_{0.975,2}=4.302653.
\]

判决在看新 probe 结果前冻结为：

- **饱和稳健通过**：\(CI_{95}\) 上界 **严格小于 0.03**。此时可写“三种子档支持上段饱和”。
- **仅趋势**：\(\bar S<0.03\) 但 CI 跨或触及 0.03。按第 10 节降级，不写“稳健”。
- **未支持饱和**：\(\bar S\ge0.03\)，无论单种子符号如何均否定该强表述。

辅助量 \(S^{300,650}_s=(F1_{650M,s}-F1_{300M,s})/\log_{10}(650/300)\) 同样报告均值、样本 SD 和配对 t CI，不改变主判决；若其均值方向与主终点冲突，必须写成“100M→650M 与 300M→650M 不一致”，禁止概括为整个上段均饱和。序列 bootstrap 可作为评估样本敏感性附表，**不得替代三种子 t CI 或把 n=3 伪增为序列级大样本**。

## 8. 科学终点与工程终点

- 科学终点：四个新 run 均精确完成 1,900,122,218nt，六个 300M/650M run 均有同协议全层 probe，随后一次性计算主/辅助斜率和 CI。不得看到 s29 后决定是否保留 s43。
- 工程终点：4 个新 manifest 均 `status=DONE`、`stop_reason=budget`、`cpu_fallback_count=0`；无 Early Stop、无缺层、无缺种子。
- 本实验不以“必须得到正结果”为完成条件；反对饱和的结果也算协议执行完成，但主张按实收缩。

## 9. 验收与预定产出

未来结果只写 `$P/results/P3_1/`，不覆盖备份或旧账本：

- `training_manifests/`：4 个新 manifest、终 checkpoint 索引、日志与 SHA256。
- `p3_1_family_layers.jsonl`：至少 300M 3×24 + 650M 3×28 = **156 个新正式层行**；100M/s17 核验行另列，不能混入计数。
- `p3_1_seed_summary.csv/json`：各种子 best F1@layer、均值、样本 SD、配对差。
- `p3_1_slope_decision.json`：主/辅助斜率、t CI、ε、判决及公式版本。
- `manifest.json` + `SHA256SUMS`：训练代码、split、权重、probe 代码和派生表哈希；记录实际 nt、峰值显存、吞吐与墙钟。

验收要求数字能从 JSONL 独立重算；只有 summary、缺原始层行或缺任一训练种子均不验收。

## 10. 失败降级

- 未启动、数据未恢复、任一新 run 未完成或 probe 不全：保留“300M/650M 单种子档观察到饱和”，不宣称多种子稳健。
- \(\bar S<0.03\) 但 CI 不满足上界规则：按任务约定写“**单种子档观察到，三种子档支持趋势**”。
- \(\bar S\ge0.03\)：撤回上段饱和强主张，报告实际增长；不得改 ε、换分母、换 300M 辅助斜率或改用序列 bootstrap 挽救。
- OOM 不得缩小 `batch_nt` 改变数学配方；应先串行、减少同卡其他本项目任务。仍无法在 32GB 下运行则停止并登记阻塞，禁止 CPU 训练。

## 11. RTX 5090 资源估算与并行编排

估算非实测承诺。旧 manifest 的 2B 训练基线为 300M 7,953MiB/93.4h、650M 15,579MiB/95.3h（非 5090，且含数据流开销）；5090 规划为：

| 单元 | 预计峰值显存 | 预计单 run 时长 |
|---|---:|---:|
| 300M，1,900,122,218nt | 8–12GB | 36–72h |
| 650M，1,900,122,218nt | 16–24GB | 48–96h |
| 300M/650M 全层 probe | 5–10GB | 各 0.5–2h，另加状态缓存空间 |

- **服务器1**：300M-s29 → 650M-s29 → 对应 probe。
- **服务器2**：300M-s43 → 650M-s43 → 对应 probe。
- 每台同一时刻只跑一个训练；这样两档、两种子都尽早各落一对，四 run 新训练总量 **7.600488872B nt**，预计并行墙钟 **4–8 天**（含 probe 和波动余量），符合一月目标的资源量级但不是结果保证。
- 启动前重新 `nvidia-smi`；650M 不与另一个 650M、P2.5-650M 或其他重 probe 同卡并发。只读监控其他课题，不清理非本项目进程。

## 12. 源码指纹（只读核验时）

| 文件（相对 `$B`） | SHA256 |
|---|---|
| `code_git/rna_sc/train.py` | `4ef53be57ed2c4b996d9a01d7c7d21d06018a2ad32771e8004e8798515fbc6ef` |
| `code_git/rna_sc/config.py` | `e1fef7c37cd1ec2d79f95c872a773859bd517a6a3914e981f7d0557bc10295e6` |
| `code_git/rna_sc/data.py` | `e6355986132944437de73e65b07a55d2360b6674e14ad055c704a62f16e4eafa` |
| `code_git/rna_sc/specs.py` | `6773c6adb54bae6d04ae7fad5b62472ecc2e5299d39e662a7a8376beea309833` |
| `code_git/rna_sc/probe.py` | `b64dc55c4bff7bd1105635dd2a3a097d7d00aeed689d4f379a2f9273ccde1857` |

执行副本须逐文件匹配；任何适配补丁另存新文件并记录哈希，不改备份。
