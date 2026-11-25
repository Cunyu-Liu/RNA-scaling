# P0.2c 逐位比对报告

## 总结

共执行 **31** 项目标复算，**31 项一致，0 项不符**。差异定义为 evidence−复算；NA 表示该扩展值只能由账本/任务指定值复核，evidence 未提供对应字段。

核心裁决：family 单种子 −5.24/−2.74/+3.76/+1.15pp 全部一致，Claim-14 `boundary_holds=false`；650M probe-seed 重测均值 0.4491、样本 SD 0.0147、预算差 +8.59pp。random +0.65/−0.60/+4.10/−1.85pp 数字一致，但 650M 是 5B midpoint 口径。结构 +0.09/+0.85/+1.87pp 单调正仅覆盖 30M/100M/300M。语料复刻、rw1、rfamcap 指定值全部一致。

## 逐项比对

| 项目 | 复算 | evidence | 任务预期 | evidence−复算 | 结论 |
|---|---|---|---|---|---|
| family 30M 单种子预算差 | -5.24 | -5.24 | -5.24 | +0.00 | 一致 |
| family 100M 单种子预算差 | -2.74 | -2.74 | -2.74 | +0.00 | 一致 |
| family 300M 单种子预算差 | +3.76 | +3.76 | +3.76 | +0.00 | 一致 |
| family 650M 单种子预算差 | +1.15 | +1.15 | +1.15 | +0.00 | 一致 |
| family 650M probe-seed重测均值 | 0.4491 | NA | 0.4491 | NA | 一致 |
| family 650M probe-seed重测预算差 | +8.59 | NA | +8.59 | NA | 一致 |
| random 30M 预算差 | +0.65 | +0.65 | +0.65 | +0.00 | 一致 |
| random 100M 预算差 | -0.60 | -0.60 | -0.60 | +0.00 | 一致 |
| random 300M 预算差 | +4.10 | +4.10 | +4.10 | +0.00 | 一致 |
| random 650M 预算差 | -1.85 | NA | -1.85 | NA | 一致 |
| structure 30M 预算差 | +0.09 | +0.09 | +0.09 | +0.00 | 一致 |
| structure 100M 预算差 | +0.85 | +0.85 | +0.85 | +0.00 | 一致 |
| structure 300M 预算差 | +1.87 | +1.87 | +1.87 | +0.00 | 一致 |
| rinalmo_corpus_replica 30M family_f1 | +7.93 | +7.93 | +7.93 | +0.00 | 一致 |
| rinalmo_corpus_replica 100M family_f1 | +2.33 | +2.33 | +2.33 | +0.00 | 一致 |
| rinalmo_corpus_replica 300M family_f1 | +0.63 | +0.63 | +0.63 | +0.00 | 一致 |
| rw1_reweighting 10M family_f1 | +0.15 | +0.15 | +0.15 | +0.00 | 一致 |
| rw1_reweighting 30M family_f1 | -0.58 | -0.58 | -0.58 | +0.00 | 一致 |
| rw1_reweighting 100M family_f1 | -4.29 | -4.29 | -4.29 | +0.00 | 一致 |
| rfamcap_family_cap 30M family_f1 | +4.14 | NA | +4.14 | NA | 一致 |
| rfamcap_family_cap 100M family_f1 | +1.85 | NA | +1.85 | NA | 一致 |
| rfamcap 100M structure_f1 | +0.34 | NA | +0.34 | NA | 一致 |
| corpus3 10M-c1Mcs best_f1 | 0.1862 | 0.1862 | 0.1862 | +0.0000 | 一致 |
| corpus3 10M-c5Mcs best_f1 | 0.1519 | 0.1519 | 0.1519 | +0.0000 | 一致 |
| corpus3 10M-full best_f1 | 0.1731 | 0.1731 | 0.1731 | +0.0000 | 一致 |
| corpus3 30M-c1Mcs best_f1 | 0.3016 | 0.3016 | 0.3016 | +0.0000 | 一致 |
| corpus3 30M-c1M best_f1 | 0.3160 | 0.3160 | 0.3160 | +0.0000 | 一致 |
| corpus3 30M-c10M best_f1 | 0.2865 | 0.2865 | 0.2865 | +0.0000 | 一致 |
| corpus3 30M-full best_f1 | 0.2466 | 0.2466 | 0.2466 | +0.0000 | 一致 |
| corpus_saturation 10M target_f1 | 0.1769 | 0.1769 | 0.1769 | +0.0000 | 一致 |
| corpus_saturation 30M target_f1 | 0.3002 | 0.3002 | 0.3002 | +0.0000 | 一致 |

## 异常与口径边界

- **目标数值无不符项**。以下为覆盖或协议异常，不改写为数值误差。
1. **650M family 双口径**：单种子 final 0.3747@L25（`probe_results_b59_family.jsonl` L509；L537 是重复扫描同值），Δ=+1.15pp；重测为 probe seeds 29/43/61 各自最佳层的均值 0.4491，样本 SD 0.0147，Δ=+8.59pp。两者不可平均、不可把 probe seed 当训练种子。
2. **650M random 非同预算 final**：−1.85pp 使用 5B midpoint 0.6067@L24（`random_midpoints_results.jsonl` L12）与 2B 0.6252；`b59_random_delta.json` 的 pending 仍含 650M。前三个 random 值的 final 汇总也不应被 5B midpoint 覆盖。
3. **结构单调范围**：`s7_structure_budget_matrix.json` 只有 30M/100M/300M 的 b59 预算差；账本另有 650M +0.84pp，纳入后非单调。学习增量多数不超过约 1pp 噪声参考，不能把预算差单调直接写成预训练学习显著增强。
4. **rfamcap checkpoint**：指定 family 数字取 200006790，而非最终 1900086380。100M final 降至 0.3297@L13（对 main +0.34pp）；30M final F1 同为 0.2880 但最佳层变 L8。
5. **重复与多 checkpoint**：650M b59 family 有 56 行，即两遍完全相同的 28 层扫描；脚本验证逐字段相同后去重。所有通用 final 选择均按最大 ckpt_nt，rfamcap 指定 cap 行则显式固定 200006790。
6. **rw1 验证伪影**：`h5_rw_multiscale.json` 明确 best_val=0 源自验证流 0 行；本复算未使用 val_loss。

## 可复算性

运行：`/usr/bin/python3 p02c_regen.py`。所有输入绝对路径、字节数、JSONL 行数与 SHA-256，以及脚本和输出哈希见 `p02c_manifest.json`。三张表均同时提供 `.md` 与 `.csv`。
