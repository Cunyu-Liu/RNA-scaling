# 预注册 P2.13（COV 部分）— Q5 自训家族 COV−CTRL 多种子补测

> 冻结时间：2026-11-28。强化 Q5"配对知识在"主证据（E2 突变干预）的测量稳健性。
> 审计 I1 标记：Q5 COV−CTRL 原为单探针种子 seed17（100 TS0 序列）。

## 模型
- RNA-Sc-650M_s17、RNA-Sc-100M_s17（服务器2 weights/）+ 各 randinit17 对照（同架构 manual_seed(17)）。

## 协议（复用 P2.3 已验证 COV 实现 run_p2_3_cov.py）
- bpRNA test 1305 序列中抽 N_SEQ=100，MAX_PAIRS=20，MAX_NT=256；COV 配对突变 vs CTRL 未配对对照。
- 多种子设计：条件生成种子 {17,29,43,61,79}（每个种子独立抽取序列子样＋突变采样）= 5 次独立测量/模型。
  COV 为 probe-free 前向测试，"探针种子"在此即条件生成种子；seed17 必须复现原锚点。
- 锚点（seed17，容差 5e-4，证据值四舍五入）：650M COV−CTRL=0.09572，100M=0.0203（covariation_test*.json，n=4920）。
- randinit17 地板：预期 ≤0.0001。

## 度量与判据
- 每模型报：5 次 COV−CTRL 均值±样本 SD（ddof=1）、符号一致率（5 次中正比例）、randinit 均值/最大。
- 判据：符号一致率 5/5 且 mean≫SD → 稳健；SD≳mean → 量级不可靠仅符号可议（降级）。
- 锚点不復现（>5e-4）→ 停止查协议/硬件原因，不得继续。

## 诚实边界
- 本补测强化"知识在"的测量稳健性，不改变 E2 等级（突变干预本身是 E2）；多种子仅给不确定度。
- 若多种子推翻 COV 正信号 → 按停止规则撤回"知识在"主张回上一证据门，不得硬撑。

## 产出
- results/P2_13/cov_multiseed/：conditions_seed{17,29,43,61,79}.jsonl + freeze_seed*.json +
  per_condition_{scale}_{mode}_seed*.jsonl + {scale}_{mode}_seed*.json + summary.json + manifest。
- 同步本地 results/P2_13/cov_multiseed/ 与 staging/p2_13_cov_multiseed.py。