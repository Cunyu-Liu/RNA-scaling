# P0.2c 预算析因表

复算规则：family 为同一 run 的最终 checkpoint 完整层扫描中 `f1_macro` 最大值，Δpp=(5.9B−2B)×100。650M 重测另行按 probe seed 内跨层取最大后求三 seed 均值。

## Family 通道

| 规模 | 口径 | 2B F1 | 5.9B F1 | 复算Δpp | evidenceΔpp | 比对 | 账本/证据定位 |
|---|---|---|---|---|---|---|---|
| 30M | single_seed_s17_final | 0.2466@L8 | 0.1942@L10 | -5.24 | -5.24 | 一致 | probe_results.jsonl:L124；probe_results_b59_family.jsonl:L175 |
| 100M | single_seed_s17_final | 0.3263@L21 | 0.2989@L16 | -2.74 | -2.74 | 一致 | probe_results.jsonl:L185；probe_results_b59_family.jsonl:L17 |
| 300M | single_seed_s17_final | 0.3445@L22 | 0.3821@L22 | +3.76 | +3.76 | 一致 | probe_results.jsonl:L1355；probe_results_b59_family.jsonl:L115 |
| 650M | single_seed_s17_final | 0.3632@L8 | 0.3747@L25 | +1.15 | +1.15 | 一致 | probe_results.jsonl:L1301；probe_results_b59_family.jsonl:L509 |
| 650M | probe_seed_retest_29_43_61_best_per_seed | 0.3632@L8 | 0.4491±0.0147；seeds 29/43/61→L27/L24/L26 | +8.59 | NA | 一致 | probe_results.jsonl:L1301；b59_reseed_300vs650.json:RNA-Sc-650M_s17_b59.{29,43,61} |

650M 重测三个 probe seed 的最佳值分别为 0.4648@L27、0.4468@L24、0.4357@L26；均值 **0.4491**，样本 SD **0.0147**（两位展示 0.015），相对 2B 单种子为 **+8.59pp**（一位展示 +8.6pp）。这不是训练种子重复，也不是序列 bootstrap。

Claim-14：300M Δ=+3.76pp，bar=1.00pp；因 3.76≥1.00，`boundary_holds=false`，复算一致。650M headline 采用哪一口径不在本任务裁决范围内。

## Random 通道

| 规模 | 口径 | 2B F1 | 5.9B F1 | 复算Δpp | evidenceΔpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 30M | random_probe_balanced_final_evidence | 0.6053 | 0.6118 | +0.65 | +0.65 | 一致 | final汇总口径；5B midpoint只作旁证，不覆盖此值 |
| 100M | random_probe_balanced_final_evidence | 0.6040 | 0.5980 | -0.60 | -0.60 | 一致 | final汇总口径；5B midpoint只作旁证，不覆盖此值 |
| 300M | random_probe_balanced_final_evidence | 0.5870 | 0.6280 | +4.10 | +4.10 | 一致 | final汇总口径；5B midpoint只作旁证，不覆盖此值 |
| 650M | random_probe_balanced_5B_midpoint | 0.6252 | 0.6067@L24 | -1.85 | NA | 一致 | 5B midpoint对2B final，非5.8B final同预算比较；b59_random_delta.json仍将650M列为pending |

30M/100M/300M 使用 `b59_random_delta.json` final 汇总；650M 的 −1.85pp 是 **5B midpoint 0.6067 对 2B 0.6252**，不能写成 5.8B final。random 的“约平坦”仅限前三个尺度；300M +4.10pp 本身超过 |Δ|<2pp，不能泛化成四尺度均平坦。

输入哈希见 `p02c_manifest.json`；逐位比对见 `p02c_report.md`。
