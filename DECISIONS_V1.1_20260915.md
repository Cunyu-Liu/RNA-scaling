# 方案修订记录（V1.1 修订包，2026-09-15 导师确认）

> 依据：9 个方法学问题的讨论结论（Q1-Q9）+ 两篇参考文精读
> （Nat Methods s41592-026-03120-y 数据量 scaling；Schmirler et al. 2024
> Fine-tuning protein language models，bioRxiv 2024.05.20.595026）。
> 本文档为 SPEC v1.1 的正式修订包，随代码一同归档。

## 修订 1（Q2）：逐层 probe 层轴改为相对深度
- probe 记录增加 rel_depth=layer_idx/(n_layers-1) 与 depth_band
  （early≤0.33 / middle≤0.66 / late），汇总报告按 band 均值；
- 动机：12 层模型的 L6（相对深度 0.5）≠ 6 层模型的 L6（相对深度 1.0）；
  绝对层号跨模型不可比（Li et al. 标准做法即相对深度）；
- 实测证据：10M（20 层）最佳层 L1、30M-c1M（12 层）最佳层 L7，按绝对
  层号对比会得出错误结论。

## 修订 2（Q3）：S2 数据量轴子采样改为簇级分层随机抽样
- 旧法（前缀采样）：流式读取前 N 行——组成近似保真（rRNA 56.4% 全量
  一致，文件未按类型排序），但有隐性偏置风险（数据库提交顺序/同族半切）；
- 新法：subsample.py——随机抽整簇（seed=17 固定）至序列预算，家族不半切；
- 已完成的 prefix-c1M 保留为采样方式对照（免费稳健性检查）；
- 新 arm：30M-c1Mcs（cluster-stratified 1M）入 wave 队列。

## 修订 3（Q4）：每个下游任务增加传统 ML 基线组（并入 S9）
- k-mer(1-6)+logistic/ridge（组成统计上界）；
- k-mer+LightGBM（轻量集成学习）；
- one-hot CNN（~1M 参数，非预训练神经基线）；
- random-embedding+同 probe 头（控制 probe 头容量）；
- 叙事口径：预训练收益 = LM − 最强传统基线，双切分下分别报告。
- 背书：NABench Reviewer EUvA"缺非基础模型基线"是被拒死因之一；
  良渚 Nat Commun 2025 的核心发现即"困难切分下 gLM 打不过简单基线"。

## 修订 4（Q5）：RiNALMo-arch 同数据自训轴（替代 CNN 对照位）
- 结构：我们的架构×我们的数据（受控段 A）+ RiNALMo 官方代码×我们的
  数据（受控段 B）+ RiNALMo 官方 ckpt×官方数据（线 1）；
- 与 Li et al. 的 ESM vs CARP 双家族结构同构，补上架构轴；
- 官方 ckpt 与复训版的数据差异本身成为可控实验变量（数据配方贡献度）；
- RiNALMo tokenizer 也是单核苷酸（与我们一致，核验过）；
- 排期：100M 三种子之后（2 档 × 2B nt，每卡 3-6 天，fairseq 系工程
  改造约 3-7 天）；替代原"RNA-Sc-CNN 附录级对照"位置。

## 修订 5（Q6）：一期锁定 ncRNA 任务族，二期 mRNA
- 一期（ncRNA，域内）：二级结构预测（bpRNA/ArchiveII）、无监督接触图
  （S8）、Rfam 家族分类（probe 已在跑）、剪接位点（SpliceBERT 任务）；
- 二期（mRNA，跨域）：MRL/翻译效率、半衰期、UTR 变异效应；
- ncRNA/mRNA 语义与任务价值表已入 PPT（结构预测主载体在 ncRNA；
  mRNA 任务与蛋白质耦合更紧，作为协议矩阵第二任务族）。

## 修订 6（Q7）：随机切分 + 家族级切分双测评确认为核心实验
- 每任务×每模型报告"泄漏敏感度 Δ(随机−家族)"；
- 背书：NABench qYsy 原话"some models are simply cheating"；
- 空白点：无人给过 Δ 随规模/协议的变化——本项目独有贡献。

## 修订 7（Q8）：协议矩阵四协议→三协议
- 删除 LoRA；保留 zero-shot / linear probe / full FT；
- 理由：训练自由度谱系更干净（0 / 只训头 / 全更新）；节省 Z2 预算最大头；
- full FT 显存核验：100M 档约 12-16GB，40GB A100 无压力；
- SPEC S9/TASKS T1.2/CHECKLIST Z2-E5 同步修订。

## 修订 8（Q9a）：Nat Methods 数据量文的借鉴点
> DenAdel et al. (Microsoft), "scFM pretraining dataset size and diversity",
> Nat Methods 2026（400 模型 × 6400 实验，scTab 22.2M 细胞）。

| 借鉴点 | 融入方式 |
|---|---|
| **learning saturation point 分析框架**（95% 最大性能阈值→最小数据量） | 直接采用为 S2 曲线的标准统计量：每条数据量曲线报 saturation point（含 95% 阈值定义），使 RNA vs 蛋白 vs 单细胞可横向对话 |
| 三种降采样方案（随机/类型重加权/几何 sketching）对照设计 | 我们已有随机（簇级）vs 前缀对照；类型重加权≈我们的家族重加权（S3 多样性轴）；"几何 sketching"对应嵌入空间均匀采样——列入 S3 二期选项 |
| 固定训练步数（compute-normalized）而非 epoch 数 | 我们已天然满足（2.0B nt 固定预算=固定 compute）——写进方法节作为设计声明 |
| 多样性指标三件套（Shannon/Gini-Simpson/Vendi） | S3 多样性轴的量化口径：语料变体构造后必报这三个指标（Vendi 用嵌入空间） |
| "更大模型仍然小数据饱和，但绝对性能更好" | 与我们 c1M 发现（30M×小语料 probe F1 0.315 > 10M×全语料 0.174）形成跨域对照——两者都在"参数有效、数据饱和"方向，可互相引用 |
| 非预训练（随机初始化）对照组设计 | 我们 S4 已实现（F1 0.131 vs 0.214），方法同构 |
| spike-in 实验（掺入扰动数据不改善） | RNA 对应物：往 ncRNA 语料掺 mRNA/结构化 RNA 的二期实验设计参考 |
| 主要发现"多样性提升不改善下游性能" | 直接作为 H5（语料构成）的**反向先验**：若 RNA 上多样性重加权有效，即为跨域反例发现；若无效，则与单细胞域一致——两种结果都可写（对齐备忘录"低风险选题结构"） |

**风险提示（引用纪律）**：该文是单细胞域（非 RNA LM），相关工作引用时
明确域差异；其"饱和"结论在 RNA 4 字母表小语料上先验不必然成立。

## 修订 9（Q9b）：Schmirler et al. 微调方法文的借鉴点
> Schmirler, Heinzinger, Rost, "Fine-tuning protein language models boosts
> predictions across diverse tasks"（bioRxiv 2024.05.20.595026）。
> 3 个 SOTA pLM（ESM2/ProtT5/Ankh）× 8 任务，微调 vs 冻结嵌入系统对比。

| 借鉴点 | 融入方式 |
|---|---|
| 核心结论"监督微调几乎总是提升，尤其小数据任务" | 我们的 zero-shot/probe/full FT 三协议矩阵（修订 7）正好把该结论作为待检验对象——RNA 上是否复现"微调几乎总是赢"是 Claim 2 的一部分 |
| 微调 vs 冻结嵌入的系统对比协议 | full FT vs linear probe 的差值（"微调增量"）按任务/数据量/切分分解报告——直接对齐其 Fig 设计 |
| 分层头设计（小任务头、统一架构跨模型可比） | 我们的 probe 头协议已是统一线性头；full FT 头也统一（attention-pool 分类头），跨模型可比性写进协议 |
| 数据量分层（小数据任务收益更大） | 与 S10 低数据 regime（10²/10³/10⁴ 学习曲线）直接对接：微调增量×数据量交互是我们的预设分析 |
| LoRA 在其结论中"接近全参微调但省资源" | 已按导师决定删 LoRA；但引用其结论作为"删 LoRA 不损失科学性"的支撑（full FT 覆盖上界，probe 覆盖下界，LoRA 在中间无独有信息） |

**引用定位**：Schmirler 文是蛋白域微调协议基准——我们 RNA 协议矩阵的
蛋白对照锚点之三（Rives/Li/Schmirler），引言动机链可用。

## 排期影响评估
- 本周：cluster-strat c1Mcs arm 入队（30M 档 ~1-2 天）；
- 100M 三种子完成后启动 RiNALMo-arch 轴（工程改造 3-7 天 + 训练 3-6 天/档）；
- 传统基线组随 T1 评测框架一起实现（k-mer/LightGBM/CNN 各 ~0.5 天）；
- 预印本时间线不变（第 3 月末 arXiv），RiNALMo-arch 轴若挤压时间可降级为
  附录（其位置原为"可砍"的 CNN 对照）。
