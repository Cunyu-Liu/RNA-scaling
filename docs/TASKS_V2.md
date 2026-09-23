# RNA-LM 迁移学习机理研究：任务分解（TASKS V2 · 事无巨细版）

> 版本：2.0（2026-09-16 重写：todo-list 级执行计划 + 模型补全 + 任务价值对齐 + 审稿人红队修正）
> 依据：01_SPEC v1.1 + DECISIONS_V1.1_20260915（Q1-Q9 修订）+ 本次模型/任务复查
> 用法：本文件是**唯一执行清单**。每项有 ID、验收物、依赖、状态框 [ ]。
> 状态图例：[ ] 未开始 · [~] 进行中 · [x] 完成（附证据路径）· [!] 受阻/变更

---

## T0 立项与基建（第 0-1 月）——状态：基本完成

### T0.1 导师确认与文档治理
- [x] 00-03 文档体系交接（4 份全读，2026-09-13）
- [x] Q1-Q9 九问修订确认 + DECISIONS_V1.1 归档（/home/cunyuliu/rna-sc/DECISIONS_V1.1_20260915.md）
- [ ] T0.1.1 split 口径勘误待导师拍板：文档写"8/1/1"，实测 TokBench 为
      train 48.7% / family_val 25.9% / family_test 24.4% / val 0.57% / test 0.38%
      ——S0 "held-out 10%" 用 val+test（约 1%）承担，family_* 留给家族级评测
      【验收：导师邮件/会议纪要一句确认，写入 SPEC 勘误节】
- [ ] T0.1.2 两层级发布/投稿渠道等 6 待决项随下一次汇报收口

### T0.2 基建（复用 TokBench）——已验收项
- [x] A3：release22_split_8080 深验证 PASS（29,012,227 行 / 3,357,201 簇 /
      簇泄漏 0 / 序列泄漏 0；证据 evidence/split8080_deep_verify.json）
- [x] A4：全局家族索引（cluster_pure=true；data/release22_cluster_split.parquet）
- [x] A5：ledger 上线（claim 防重 + flock 锁 + upsert 恢复；三事故后实战修复）
- [x] A6：冒烟 ALL PASS（mask 确定性/参数 ±12%/前反向/loss 下降/零 CPU 回退）
- [x] 基建代码：model/config/data/train/ledger/status/supervisor/smoke/
      family_table/probe/subsample（GitHub Cunyu-Liu/RNA-scaling，~20 commits）
- [~] T0.2.5 外部数据集家族分配表 join（stage-2：等 T1.1 数据落地后做，
      用 canonical hash + Infernal 双路对齐 cluster_id_8080）
- [ ] T0.2.6 评测侧统一 runner：eval_matrix.py（模型×任务×协议×切分的
      声明式 spec + ledger 化，防漏测/重测；【验收】单模型冒烟 + ledger 记录）

### T0.3 文献精读上岗（与 T0.2 并行）
- [~] 必读四篇 + REDIAL/Papazoglou（Q9 两篇新参考文已精读归档）
- [ ] T0.3.1 RiNALMo 评测章节复现（A7 验收）：bpRNA 家族级切分二分类，
      复现其 F1 ±0.02 内【验收：单测脚本 + 复现报告入 evidence/】
- [ ] T0.3.2 RNA-FM 评测设置精读笔记（结构 probe 部分，作 S8 对照口径）
- [ ] T0.3.3 Li et al. ICML 2024 实验细节节精读（370 实验因子组合——
      开题前已列"必精读"，至今未完成，阻塞 S4/S5 对照设计的最终冻结）

### T0.4 服务器运维（贯穿）
- [x] 服务器 cron 每 2h + 本地巡检每日 2 次（CPU 回退硬规则/崩溃诊断/
      队列接力/记录推送全自动）
- [x] TRAINING_LOG.md 逐日记录（事故-决策-吞吐-结论四段式）
- [x] 8 起调度/数据事故根治（详见 TRAINING_LOG 事故节）

---

## T1 评测基建与线 1（现成模型，第 1-2 月）——关键路径

### T1.0 模型补全（本次复查结论，2026-09-16）

已核查 2025-09 至 2026-09 新发布，评测名单更新：

| 模型 | 状态 | 动作 |
|---|---|---|
| RiNALMo 33M/148M/651M | 已在册 | 主力（Zenodo 全公开）|
| RNA-FM 26M/96M | 已在册 | 第二同源系列 |
| RIBOSPAN 1.61B/10K ctx | 已在监控清单 M4（arXiv 2608.22849，2026-08-24） | **必须入线 1**（自称最强 encoder-only，缺它重蹈 RNAscope 覆辙）|
| BiRNA-BERT 117M | **新增**（Commun Biol 2025-11，自适应双 token 化，开源） | 线 1 补入——正好是"tokenization 变量"的活样本 |
| ChaRNABERT | 复查发现（可学习字符 token 化系列） | 线 1 可选——与 BiRNA-BERT 二选一（tokenization 轴不堆两个）|
| ERNIE-RNA 86M | 已在册 | 结构增强预训练代表 |
| HydraRNA | 已在册（Genome Biol 2025-11） | 观察（hybrid 架构，附录级）|
| Moirain（生成式 DPO，arXiv 2605.23961） | 新见 | **不入线 1**——条件生成模型，与判别式协议矩阵不匹配 |
| GoForth / Designing-RNAs（设计向 LM） | 新见 | 不入线 1（设计任务不在任务三分法内）|

- [ ] T1.0.1 RIBOSPAN + BiRNA-BERT（或 ChaRNABERT）写入 SPEC 5 节模型矩阵
      【验收：SPEC 增补 + 权重落盘 /mnt/cunyuliu/models/，含 SHA256】
- [x] T1.0.2 主流基准侧交叉核对：BEACON/良渚/RNAGym/深圳湾 21 模型清单
      对照完成，无其他遗漏；月度监控 M4 持续兜底

### T1.1 数据接入（事无巨细）
- [ ] T1.1.1 bpRNA(new)：下载 + 解析（bpRNA 描述符 → 配对矩阵 + family 标签）
      【验收：解析单测 + 家族计数表】
- [ ] T1.1.2 ArchiveII：10 家族 3,975 序列（leave-family-out 协议直接复用
      其家族标签）【验收：与 RiNALMo TestSetB 家族名对齐表】
- [ ] T1.1.3 Rfam 家族分类：release22 rna_type 已在跑；升级 clan 层标签
      另行解析（可选）
- [ ] T1.1.4 剪接位点：SpliceBERT 数据（148 物种供体/受体位点）
      【验收：位点提取单测（GT-AG 统计对齐原文）】
- [ ] T1.1.5 家族分配 join（T0.2.5）：四源 → cluster_id_8080，产出
      family_assignment.parquet【验收：无归属冲突断言 + 覆盖率报告
      （PDB-only 家族允许无 join，单独标记 isolated）】
- [ ] T1.1.6 RNAGym DMS 子集（局部变异类，二期可选）：家族分组下载，
      优先级最低

### T1.2 三协议矩阵框架（S9，Q8 修订后）
- [ ] T1.2.1 zero-shot 评估器：encoder 型 masked marginal 口径（Z4）——
      逐位掩盖重打分 vs 一次前向近似两种口径都实现并报告差异（口径差
      异本身就是协议偏差证据）【验收：单模型×单任务冒烟 + 口径差异表】
- [ ] T1.2.2 linear probe 评估器：扩展 probe.py 到任务三分法；**红队修正
      B**：(a) 类别平衡（class-weighted loss + 平衡采样，v1 不平衡口径
      保留为对照）；(b) 序列级头一律 CLS/attention-pool（mean-pool 仅留
      "顺序盲下界"对照）【验收：三任务各一冒烟 + 两口径差异表】
- [ ] T1.2.3 full FT 评估器：统一 attention-pool 分类头，100M 档 +
      RiNALMo-micro 限做（Z2 分层）；评测/微调零重叠运行时断言
      【验收：断言单测（构造故意重叠案例必须报错）】
- [ ] T1.2.4 双切分（Q7 核心）：random split seed 隔离 + 家族级 split
      用 T1.1.5 分配表；Δ(随机−家族) 每组合必报【验收：Δ 汇总表初版】
- [ ] T1.2.5 传统基线组（Q4）：k-mer(1-6)+logistic / k-mer+LightGBM /
      one-hot CNN / random-emb+头【验收：每任务基线表 + 收益口径列
      （LM−最强基线）】
- [x] T1.2.6 低数据 regime（S10）：10²/10³/10⁴ 采样曲线（probe 与
      full FT 两条线）【验收：三任务学习曲线图 v1】
      probe 线 + 10M/100M full-FT 两档完成（f93ec82/a90ff13，
      evidence/t126_fullft.json：full-FT 上升 vs probe 平坦）；
      **650M 扩档已完成（2026-09-23 22:41）**：v1 watcher 19:29 GPU0
      OOM（rc=1 19:42:04）→ attempt 1 20:23 GPU2 OOM（rc=1 20:30:47）
      → attempt 2 22:22:55 GPU1 启动，**22:41:45 rc=0 完成**
      （650M 档三点 n=100/1000/10000 → f1 0.0947/0.1212/0.1564，
      全三档 10M/100M/650M × 3 点落 evidence/t126_fullft.json，
      logs/t126_fullft_650m.done 已落盘，watcher 单次退出）；
      结论：650M full-FT 依旧最低数据最大优势（0.0947 vs 10M
      0.0585 @n=100），full-FT 升 vs probe 平坦结论在五档口径下
      成立。DRAFT_v1.md §4.11 已回填三档数字
      【证据：evidence/t126_fullft.json + logs/t126_fullft_650m.log +
      TRAINING_LOG Day 13 补六】

### T1.3 逐层 probe 全矩阵（S7）
- [x] T1.3.1 rel_depth 层轴 + depth_band 汇总（已上线）
- [ ] T1.3.2 外部模型逐层 probe：RiNALMo 三档 / RNA-FM 两档 / BiRNA-BERT
      【验收：跨模型 early/middle/late 可比表 + "低层主导"初步曲线 +
      **红队修正 E：去 rRNA 分层重跑强制项**】
- [ ] T1.3.3 length_bin 分箱报告（Z3）：16-127/128-511/512-4096 三箱
      （外评序列短只留三箱）【验收：分箱 probe 表】

---

## T2 线 2：自训受控家族（第 2-3 月）——执行中

### T2.1 主 scaling 轴（S1）
- [x] 10M 完整 2.0B nt（best_val 0.8716，fallback=0，34k nt/s）
- [x] 30M-c1M 完整（850M nt 语料上限，best_val 0.8960）
- [~] 1M（~90%）/ 30M-full（~25%）/ 30M-c10M / 100M s17/s29/s43 运行中
- [~] T2.1.1 c1Mcs（簇级分层 Q3）：已生成（1,000,011 序列/190,917 簇）入队
- [ ] T2.1.2 **红队修正 A**：语料轴三点曲线改为 10M 档 × {c1Mcs, c5Mcs,
      full}（原 c40M 接近全量无意义）；epoch 覆盖差异显式入方法节
      （c1M ≈2.4 epoch vs full ≈34% 新鲜度，不假装同质）
- [x] T2.1.3 100M 处斜率判定（R1 预设规则）：slope>ε → 650M；≤ε → 止步
      【验收：slope 含 CI + 判定报告入 evidence/ + TRAINING_LOG 决策记录】
      —— ✅ 已收口（2026-09-23）：触发判定 evidence/s1_slope_decision.json
      （slope 0.142/decade，CI [0.104, 0.180]，decision=650M）；
      终判 evidence/s1_final_verdict.json（650M F1 0.3632 > 100M 0.3394，
      +2.4pp；slope 100M→650M 0.0293 < ε=0.03 → scaling 饱和，五档终局）；
      650M 自动 probe evidence：eval/probe_results.jsonl 28/28 层全覆盖
      （final_nt=1900122218，best L8）；TRAINING_LOG.md Day 13 落款。

### T2.2 对照实验（S4/S5/S6）
- [x] S4 随机初始化对照（10M 档 probe：0.131 vs 0.214）
- [ ] T2.2.1 S4 扩面：四档全做 randinit probe + 三协议版
      【验收：H2 排除性证据表全家族版】
- [ ] T2.2.2 S5 权重统计重采样对照（H3）：一阶/二阶矩匹配的随机初始化
      （~0.5 天实现）【验收：H3 排除表】
- [x] S6 中途 checkpoint（每 100M nt 自动落盘，全部 run 生效）
- [ ] T2.2.3 S6 涌现时间轴：10M 的 20 ckpt × probe/接触图完整轨迹
      （100M-nt 对齐快照已有 4 模型）【验收：pretraining-time 曲线（线 2 版）】

### T2.3 语料轴（S2/S3，H5）
- [~] c1M(prefix)/c1Mcs/c10M/full 采样方式对照 + 数据量曲线
- [ ] T2.3.1 saturation point 统计量（借鉴 Nat Methods 文）：95% 阈值 +
      每 arm 计算；**只在同 epoch 覆盖的 arm 间比较**（红队修正 A）
      【验收：饱和点表】
- [ ] T2.3.2 三多样性指标（Shannon/Gini-Simpson/Vendi）：对全部语料变体
      计算（Vendi 用 10M 嵌入抽样 5k 序列）【验收：语料-指标表】
- [ ] T2.3.3 S3 多样性 arm（家族重加权语料）：设计冻结 + 训练 1 档
      【验收：H5 双轴分解结论 v1（与 rRNA 56% 偏置交叉验证，红队 E）】
- [ ] T2.3.4 spike-in RNA 二期设计（掺 mRNA 对照，仅设计文档不训练）

---

## T3 线 3：涌现分析（与 T1/T2 并行）

### T3.1 无监督接触预测（S8）
- [ ] T3.1.1 结构数据：PDB RNA 链 C4'/P 距离矩阵 + bpRNA 配对标签对齐
      （家族切分沿用 T1.1.5）【验收：接触数据集 + 家族数报告（E2）】
- [ ] T3.1.2 logistic 接触头：拟合/测试严格分离 + APC + top-L（≥24nt
      长程）；**红队修正 E：接触定义双口径**（蛋白式 8Å C4' 与 RNA
      文献口径并列，差异入附录）【验收：Rao 2020 协议单测 + RiNALMo
      官方口径对照】
- [ ] T3.1.3 涌现时间线：自训家族 × S6 ckpt × 接触精度（length_bin 分箱）
      【验收：涌现曲线 + bootstrap CI（E3）】
- [ ] T3.1.4 注意力直读对照：注意力图 vs 头部 logit 两口径（与
      Papazoglou 2025 对话）【验收：两口径对比表】

### T3.2 家族解耦指数（S12，H6）——**红队修正 D：提前，CPU 并行本周启动**
- [ ] T3.2.1 Infernal cmscan 跑 Rfam 家族（服务器装 Infernal，CPU 任务
      不等 GPU）【验收：家族协方差得分表】
- [ ] T3.2.2 解耦指数 = 家族内序列一致性 / 协方差得分；按指数分层涌现
      早晚【验收：H6 相关性 + CI（E3）】

### T3.3 二级结构
- [ ] T3.3.1 bpRNA 家族级切分三协议 + 双切分（并入 T1.2 矩阵结构类行）
      【验收：结构类矩阵行完整】

---

## T4 预印本与发布（第 3 月末起）

### T4.1 图表工程（论文核心资产）
- [ ] T4.1.1 图 1：S1 scaling 主图（困惑度 + probe 双 y 轴 + 100M 斜率
      标注；**红队修正 C：跨模型趋势线与 100M 种子 CI 分列，不画
      per-model 伪误差棒**）
- [ ] T4.1.2 图 2：逐层涌现（rel_depth × 任务三分法，5 模型 × 协议；
      含去 rRNA 分层版）
- [ ] T4.1.3 图 3：协议×切分热图（Δ 泄漏敏感度）
- [ ] T4.1.4 图 4：语料轴（saturation point + 三多样性指标 + epoch
      覆盖标注）
- [ ] T4.1.5 图 5：S4/S5 对照 + 时间轴涌现（线 2 独有）
- [ ] T4.1.6 表 1：基线组总表（LM−最强基线口径）
【验收：每图对应 S0-S12 映射行（C7 纪律）；无表外实验】

### T4.2 写作与 arXiv
- [ ] T4.2.1 引言四点动机（D10：每点 RNA 证据引用）
- [ ] T4.2.2 相关工作：REDIAL 三分界（D9）/ 深圳湾差异化表（D4）/
      良渚三轴差异化 / Schmirler+Nat Methods 两新锚点入动机链
- [ ] T4.2.3 claim 措辞全文检索（D1-D8 逐条过）
- [ ] T4.2.4 limitation：线 1 泄漏疑虑（B3）/ epoch 覆盖约束（红队 A）/
      架构受控范围 / 种子不平衡 / rRNA 语料偏置（红队 E）
- [ ] T4.2.5 **arXiv 挂出（完整核心实验，非占位）★关键节点**
- [ ] T4.2.6 仓库整理发布（MIT license + 数据/权重清单）

### T4.3 第二阶段（条件触发）
- [ ] T4.3.1 650M 触发判定（T2.1.3 输出；4×A100 DP 预算已测算）
- [ ] T4.3.2 RiNALMo-arch 轴（Q5 受控段 B）：fairseq 适配 release22 →
      2 档训练【验收：B 段 2 ckpt + A/B/C 三段对比表 v1】（挤压则降级附录）

### T4.4 投稿
- [ ] T4.4.1 层级 1 转投（Brief Bioinform / Bioinformatics）
- [ ] T4.4.2 层级 2 完整版（NeurIPS/ICML 或 Nat Commun）

---

## T5 运维（贯穿）

- [x] 月度竞争监控制度化（M1-M4 清单 + 触发响应）
- [~] T5.1 自动巡检（每日 2 次；DONE run 自动补 probe 已生效）
- [ ] T5.2 2026-10-01 月度监控第 1 轮执行【验收：备忘录 5.4 表更新+日期戳】

---

## 依赖图（关键路径加粗）

```
T0.2.6(评测runner) ──→ **T1.2(三协议矩阵)** ──→ **T1.3(逐层probe)** ──┐
T1.1(数据接入)   ──↗        │                                        ├─→ **T4.1(图)** ─→ **T4.2.5(arXiv)**
T2.1(S1 训练)     ──→ T2.2(对照) ──→ T1.2 扩面                         │
T3.1/T3.2(涌现)   ─────────────────────────────────────────────────────┘
T3.2.1(Infernal, CPU) 与主线并行 ｜ T5（监控，独立）
```

## 里程碑硬验收

| 时间 | 里程碑 | 硬验收 |
|---|---|---|
| 第 1 月末 | 基建+模型接入+评测 runner | A3-A6 ✓ + T1.0/T0.2.6 |
| 第 2 月末 | 线 1 三协议矩阵+逐层 probe | T1.2 四项 + T1.3.2/3 初版结论 |
| 第 3 月末 | **arXiv 挂出** | T4.1 六图 + T4.2 写作纪律全过 |
| 每月 1 日 | 竞争监控 | 5.4 表更新+日期戳 |

---

## 附：审稿人红队自批（2026-09-16，毫不留情版）

**审稿人 A（方法论）**：
> "自训家族 2.0B nt 预算？RiNALMo 官方用了远大于此的训练量。你们拿训了
> 一半的模型家族谈'涌现饱和'，就像跑了半程马拉松宣布破纪录。更糟的是
> 语料上限：release22 train 总量约 5.9B nt，你们最大的语料 arm 实际
> 见到的新鲜数据约 2B——**'数据量 axis'根本没跑到全量一个 epoch**，
> 还谈什么 scaling law？"

**修正 A**（成立）：(1) epoch 覆盖差异显式入方法节（c1M ≈2.4 epoch vs
full ≈34% 新鲜度，不假装同质）；(2) saturation point 只在同覆盖 arm 间
比较；(3) limitation 明写"预算受语料规模约束，与蛋白域 UniRef 不可比
——这正是 RNA 语料小一个数量级的题设本身"。T2.1.2 已改三点曲线。

**审稿人 B（实验设计）**：
> "probe 主指标 macro-F1？19 类里 rRNA 占 63.6%——probe 头连类别平衡
> 都没做，你们测的是表征还是标签分布？还有，逐层 probe 用 mean-pool
> 收集态——SPEC 自己写了'禁 mean-pool（顺序盲）'，你们第一天就违反
> 自己的规程，就加了个括号说'后面改'。"

**修正 B**（两条都成立）：(1) class-weighted loss + 平衡采样（v1 不平衡
口径保留为对照——顺带量化平衡影响，本身是协议偏差证据）；(2) 序列级
头一律 CLS/attention-pool（与 full FT 头统一），mean-pool 仅留"顺序盲
下界"对照。列入 T1.2.2 验收。

**审稿人 C（统计）**：
> "3 种子只在 100M 档？其他档单种子然后画带'置信区间'的 scaling 曲线？
> 横轴不同模型的误差棒——这是伪统计。还有 c1Mcs vs prefix-c1M 的'采样
> 方式对照'：两个 arm 各单种子，观察到的差异你打算归因给采样方式还是
> 种子噪声？"

**修正 C**（成立）：(1) 跨模型曲线不标 per-model CI，改"趋势线 + 100M
种子 CI"分列；(2) 采样对照 arm 补第 2 种子（c1Mcs-s29 入队）；(3) 单
种子档差异说明进 limitation。T4.1.1 验收已含。

**审稿人 D（定位）**：
> "'独有贡献'清单我逐条核过：深圳湾做了 21 模型零样本；良渚做了统一
> 微调+困难切分；你们把别人的协议拼起来加一个自训家族就叫'机理研究'？
> S12 解耦指数是唯一真正新的东西，它排在 T3.2——排期最晚、无备份。
> 主菜的工期给了配菜的三个对照。"

**修正 D**（部分成立——核心贡献排期风险真实）：(1) S12 提前：Infernal
cmscan 是 CPU 任务，与 GPU 训练完全并行，本周启动；(2) 三协议矩阵的
"新"收缩为"协议×切分×规模的交互归因"（写作层面防 D2 违规）；(3) 良
渚差异化写入相关工作（他们：统一微调×困难切分；我们：规模/层/语料三轴）。

**审稿人 E（生物）**：
> "接触图 ≥24nt、C4'/P 阈值——这是蛋白 8Å 的换算还是 RNA 文献口径？
> PDB RNA 条目才 7k，family-level 切分后每家族剩几条？统计功效何在。
> 另外 rRNA 占语料 56%，你们所有涌现结论会不会只是'rRNA 结构规律性'
> 的另一种说法？"

**修正 E**（成立）：(1) 接触定义双口径并报（差异入附录）；(2) 家族 n
报告 + 家族数下限预警（E2 强化）；(3) **所有涌现/probe 分析强制加"去
rRNA"分层重跑**（T1.3.2 验收增加）；语料端 rRNA 偏置与 T2.3.3 家族
重加权 arm 交叉验证。

**总修正跟踪表**（全部已并入上文对应任务项）：

| 红队项 | 修正 | 落点 |
|---|---|---|
| A 预算/语料 | epoch 覆盖显式化 + 同覆盖比较 | T2.1.2 / T2.3.1 |
| B probe 平衡 | class-weighted + attention-pool 头 | T1.2.2 |
| C 伪统计 | CI 语义修正 + 对照补种子 | T4.1.1 + c1Mcs-s29 |
| D 排期 | S12 提前（CPU 并行本周启动） | T3.2.1 |
| E rRNA 偏置 | 去 rRNA 分层强制 + 接触双口径 | T1.3.2 / T3.1.2 |

---

*执行人每日对照本清单勾选并推送；任何 [!] 变更需在 TRAINING_LOG 记录原因。*
