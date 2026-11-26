# 切分文件重建终裁与主张降级（2026-11-26）

> 调查链：X-split（备份/远端无现成文件）→ X-split2（源=RNAcentral 22.0，需重跑管线）→ X-split3（下载+canonical/dedup 29,012,227 行精确命中+MMseqs2 聚类）→ X-split4（代表集/簇拓扑差异分析）。证据：补证_P2_20261125/results/split_rebuild{,2,3,4}/。

## 终裁：原 release22_split_8080.parquet 不可精确恢复

- 重建聚类 member 覆盖完整（29,012,227），dedup 表与 rfamcap train oracle 566,077/566,077 hash+六字段全一致——**序列内容管线正确**。
- 但簇拓扑真实变化：15,231 新簇含多旧代表（并簇）、3,550 新簇无旧代表（拆簇）、1,126 新簇混旧 split 标签；新代表 3,334,304 vs 旧 3,357,201。输入顺序/cluster-mode/cov-mode/版本均已排除为根因；原二进制哈希与运行日志缺失，无法 further 区分（不伪定唯一根因）。
- **致命问题——train 泄漏**：≥340 条旧 train 序列落入新 family_validation、≥219 条落入新 family_test（可观测下界）。用重建 split 探针旧 checkpoint 违反 pretraining-held-out 前提。
- family-only 重建亦不可行：eligibility 簇数依赖 member→cluster；新 family_validation 7,525,341（−411）/family_test 7,086,474（+3,579）；±1 簇扰动翻转 4 个 family。
- 原 member→rep 映射、原聚类 parquet、原二进制、完整运行日志均缺失；两台远端+备份+本地 tokenizer-benchmark 副本（含 git-lfs）均已穷尽搜索。

## 按预注册停止规则执行降级（不缩水数据、不伪造等价）

| 项 | 降级 | 论文落点 |
|---|---|---|
| **P2.5 650M@5.9B 重测固化** | 不做。"650M>300M@5.9B（+6.65pp，3/3 probe seeds）"降为**交接记录引用、未复核**（重测 30 值无账本原始行且无法重跑），移附录；Q6 预算主表 650M 用原始终值协议 **+1.15pp（单种子，E1）**，"预算助欠训尺度@650M"限定为单种子观察 | sec46/sec3/appendix |
| **P2.7 650M random 终值** | 不做。random 预算免疫主张**限三尺度终值**（+0.65/−0.60/+4.10pp，E2）；650M −1.85pp 保留 5B midpoint 标签入附录 | sec46/limitations |
| **P2.4 RNS 分箱控长度** | 不做。旧 +18%/+29% 因 pair 索引 1-based 错位+头未设种子**撤回为历史参照**；轴依赖机制**未裁决**，RNS 分箱方向主张撤回 | sec47/limitations |
| **P3.1 多种子补训** | **不触发**：训练流需原 train split，重建 split 有泄漏不可比；另立新数据版本需重训全部比较臂（超一月期限）。饱和表述限"单种子档观察到，三种子档（1M–100M）支持趋势" | sec41/limitations |
| **P3.2 曝光臂** | 维持不触发（29–116 天超期限） | — |

## 不受影响的主张（核心正结果完整）

Q1 阶梯/饱和（E3 斜率规则+三种子档）、Q2 双对照排除（E2）、Q3 泄漏三角+协议依赖地板（E2）、Q4 P1 干预（E2）、Q5 读出链+外部 COV 互证（E2+观察性）、Q6 预算符号翻转/结构单调正/语料衰减梯度/rw1 容量门控/finite-channel 证伪（E2/E3）、rfamcap 双尺度通道特异（P2.1 新值 E2）、de-rRNA 全过（P2.6）、RNS×COV 弱-中等（P2.2）、五处负结果配机制解释。

## 资产保留

重建管线代码+dedup 表（内容验证正确）+聚类 TSV 保留远端/本地，供未来若找回原 member 映射时验收复用；若另立数据版本实验须重新预注册+重训比较臂（X-split4 报告）。