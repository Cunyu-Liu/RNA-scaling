# 全项目"单次测量出结论"审计清单（任务 I1，2026-11-28）

> 只读系统排查：备份 evidence/*.json + eval/*.jsonl、对账_P0_20261125/、补证_P2_20261125/results/、论文分节源。
> 分级：A=支撑主文主张且已有权重/数据可补测；B=需原 split/新训练（不可行）→显式限定 E1+不确定度；C=纯描述性横切（E1 可接受）→标注。
> 纪律：负结果不删；不强行升 E2/E3；补测推翻主张则撤回回上一证据门。在飞/已完成分开标注。

## 审计表

| 项 | 证据路径 | 单次维度 | 分级 | 处置 | 状态 |
|---|---|---|---|---|---|
| Q1 300M/650M 家族 F1（0.3445/0.3632） | evidence/s1_final_verdict.json; eval/probe_results.jsonl | 单训练种子 s17 | B | 多种子补训需原 train split（P3.1 终裁不触发）；显式限定单种子档观察+三种子档支持趋势，无伪误差棒 | 已入 sec6 limitation |
| Q1 10M 谷 | evidence/s1_seed_table.json | 均值级（2/3 种子负） | B | 已限定均值级现象，非逐种子普遍；黑名单"10M valley"清零（改 mean-level dip） | 已入稿 |
| Q5 COV−CTRL（650M +0.09572/100M +0.0203） | evidence/covariation_test*.json | 单条件种子 seed17（100 TS0） | A | **P2.13 多种子补测完成**：5 条件种子{17,29,43,61,79}，均值±SD+符号一致率+randinit 地板；锚点 seed17 复现 | **完成（P2_13/cov_multiseed）** |
| Q5 配对 AUC（0.952@650M） | evidence/pair_probe_v4.json | 单探针种子 | A | 可补测（bpRNA 在）；主证据为匹配先验净增量+0.030（已扣先验）；多种子补测列二期优先 | 待补（A 级，未跑） |
| Q5 readout_heads（~0.64 墙） | evidence/readout_heads_*.json; v5_readout_head.json | 单探针种子+旧未收敛 | A | P2.10 确立收敛纪律（旧 0.5973/0.6101 作废，0.5562 为准）；P2.8 读出位置排除位置伪影；多种子未跑 | 部分（收敛/位置已补，多种子待） |
| Q5 Partner-Oracle（0.998） | evidence/readout_heads_*.json | 单种子 | C | 信息访问上界，非 deployable 预测器；描述性上界，E1 标注即可 | 已限定 |
| P2.1 rfamcap 结构（30M +1.77/100M +0.14pp） | results/P2_1/ | 单探针种子 s17 | A | **P2.14 rfamcap 结构多种子**（探针种子×子样，randinit 对照） | 立项待跑（P2_14） |
| P2.3 外部 COV（micro/mega/giga/NB） | results/P2_3/ | 单条件种子 seed17 | A | **P2.14 外部 COV 多种子**（5 种子+randinit，观察性锚点） | 立项待跑（P2_14） |
| P2.8 读出位置 | results/P2_8/ | 单探针种子 | A | 净增量结论由 randinit+旋转对照支撑（E2 佐证）；多种子可补但非主张级缺口 | 已收口（对照在位） |
| Q6 factorial 家族预算（−5.24/−2.74/+3.76/+1.15） | evidence/factorial_verdict.json | 单训练种子×单探针种子×单池 | A | **P2.11/P2.12 四档多种子重测完成**：30M −5.86±0.91(0/10)、100M −1.65±1.42(1/10)、300M −0.74±4.38(5/10)、650M +3.06±2.68(9/10)；headline 改多次测量均值±SD，旧值归档 A.9 | **完成（P2_11/P2_12）** |
| Q6 结构预算矩阵（+0.09/+0.85/+1.87） | evidence/s7_structure_budget_matrix.json | 单种子 | B | 三尺度单调正限定；randinit 噪声地板~1pp 扣除；多种子需结构探针补测（列二期） | 已限定三尺度 |
| Q6 random 预算免疫（+0.65/−0.60/+4.10） | evidence/b59_random_delta.json | 单种子，三尺度终值 | B | 限三尺度终值 E2；650M 终值未评估（P2.7 终裁不做），midpoint 入附录 | 已限定 |
| Q6 语料复刻臂（+7.93/+2.33/+0.63） | evidence/corpus_arm_verdict.json | 单种子 s17 | B | 受控干预 E2（同架构）；单种子限定；de-rRNA 全过（P2.6） | 已限定+de-rRNA |
| Q6 rw1 展平（+0.15/−0.58/−4.29） | evidence/h5_rw_multiscale.json | 单种子 | B | 10M 正效应<种子 SD 标中性；容量门控符号翻转 E2 | 已限定 |
| S13b NOT-BELL | evidence/s13b_bell.json | 单次拟合（v1 30/v2 36 点） | C | 预注册负结果，峰在 NLL 范围外；描述性 E1，配机制解释 | 已入稿（负结果纪律） |
| S6 时间轴磨蚀 | evidence/s6_timeline.json | 单运行 s17 | C | 描述性时间轴 E1；c1Mcs 复现时长驱动；非逐种子普遍 | 已限定 |
| S12 DI 分层（ρ −0.478→−0.222） | evidence/s12_linkage_*.json | 类级 n=10 | C | 类级口径 E1，非家族级；描述性横切 | 已限定 n=10 |
| S14 RNS 各轴 | evidence/s14_rns*.json | 单运行/模型级 | C | 模型级可靠性指标 E1；分箱轴旧值撤回（P2.4 终裁不做） | 已限定 |
| P2.2 RNS×COV（ρ −0.2966） | results/P2_2/ | n=108 序列，单种子 | C | 弱-中等描述性相关 E1；RNS 不作强结构代理 | 已限定 |

## 汇总
- **A 级已补测完成**：Q5 COV（P2.13）、Q6 factorial 四档（P2.11/P2.12）。
- **A 级立项待跑**：P2.14 外部 COV 多种子 + rfamcap 结构多种子；Q5 配对 AUC 多种子（二期优先）。
- **B 级（不可行，显式 E1 限定）**：Q1 300M/650M 多训练种子、结构/random/语料/rw1 单种子臂——均已入 sec6 limitation 或正文限定语。
- **C 级（描述性横切，标注即可）**：S13b/S6/S12/S14/P2.2/Oracle——均 E1 标注，不强行补。

## 主张影响
- Q6 跨尺度符号倾向获 3/4 档多种子支持（30M/100M 负稳健、650M 正稳健），由单种子观察升级；300M 标不确定。
- Q5 COV"知识在"主证据获多种子不确定度（P2.13），E2 突变干预等级不变。
- 无主张被推翻；无负结果删除；无证据等级强行提升。