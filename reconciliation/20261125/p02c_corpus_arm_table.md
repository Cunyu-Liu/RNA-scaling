# P0.2c 语料臂表

主比较均为 arm−baseline，单位 pp；完整 run、checkpoint、账本行和 evidence 字段见 CSV。

## RiNALMo 语料复刻

| 规模 | baseline | arm | 复算Δpp | evidenceΔpp | 预期Δpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 30M | 0.2466@L8 | 0.3259@L9 | +7.93 | +7.93 | +7.93 | 一致 | family split；best layer |
| 100M | 0.3263@L21 | 0.3496@L17 | +2.33 | +2.33 | +2.33 | 一致 | family split；best layer |
| 300M | 0.3445@L22 | 0.3508@L22 | +0.63 | +0.63 | +0.63 | 一致 | family split；best layer |

## rw1 重加权

| 规模 | baseline | arm | 复算Δpp | evidenceΔpp | 预期Δpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 10M | 0.1731@L1 | 0.1746@L14 | +0.15 | +0.15 | +0.15 | 一致 | rw1 val_loss=0为验证流空读协议伪影；只用probe F1 |
| 30M | 0.2466@L8 | 0.2408@L11 | -0.58 | -0.58 | -0.58 | 一致 | rw1 val_loss=0为验证流空读协议伪影；只用probe F1 |
| 100M | 0.3263@L21 | 0.2834@L21 | -4.29 | -4.29 | -4.29 | 一致 | rw1 val_loss=0为验证流空读协议伪影；只用probe F1 |

## rfamcap family（指定 200006790 checkpoint）

| 规模 | baseline | arm | 复算Δpp | evidenceΔpp | 预期Δpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 30M | 0.2466@L8 | 0.2880@L7 | +4.14 | NA | +4.14 | 一致 | rfamcap指定值为200006790 checkpoint，非1900086380最终checkpoint |
| 100M | 0.3263@L21 | 0.3448@L18 | +1.85 | NA | +1.85 | 一致 | rfamcap指定值为200006790 checkpoint，非1900086380最终checkpoint |

## rfamcap 结构

| 规模 | baseline | arm | 复算Δpp | evidenceΔpp | 预期Δpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 100M | 0.5890@L22 | 0.5924@L20 | +0.34 | NA | +0.34 | 一致 | 0.5924@L20−0.5890@L22 |

## rfamcap final checkpoint 补充（非指定口径）

| 规模 | baseline | arm | 复算Δpp | evidenceΔpp | 预期Δpp | 比对 | 备注 |
|---|---|---|---|---|---|---|---|
| 30M | 0.2466@L8 | 0.2880@L8 | +4.14 | NA | NA | 补充；非指定cap口径 | 仅用于说明checkpoint差异，不替代指定cap值 |
| 100M | 0.3263@L21 | 0.3297@L13 | +0.34 | NA | NA | 补充；非指定cap口径 | 仅用于说明checkpoint差异，不替代指定cap值 |

## corpus3 语料规模臂

| 规模 | run | unique nt(B) | epochs | best F1 | evidence比对 | 账本行 |
|---|---|---|---|---|---|---|
| 10M | RNA-Sc-10M_s17_c1Mcs | 0.9 | 2.22 | 0.1862@L9 | 一致 | probe_results.jsonl:L242 |
| 10M | RNA-Sc-10M_s17_c5Mcs | 2.4 | 0.83 | 0.1519@L4 | 一致 | probe_results.jsonl:L257 |
| 10M | RNA-Sc-10M_s17 | 14.13 | 0.14 | 0.1731@L1 | 一致 | probe_results.jsonl:L97 |
| 30M | RNA-Sc-30M_s17_c1Mcs | 0.9 | 2.22 | 0.3016@L9 | 一致 | probe_results.jsonl:L149 |
| 30M | RNA-Sc-30M_s17_c1M | 0.85 | 2.35 | 0.3160@L8 | 一致 | probe_results.jsonl:L136 |
| 30M | RNA-Sc-30M_s17_c10M | 3.87 | 0.52 | 0.2865@L11 | 一致 | probe_results.jsonl:L77 |
| 30M | RNA-Sc-30M_s17 | 14.13 | 0.14 | 0.2466@L8 | 一致 | probe_results.jsonl:L124 |

## corpus saturation

| 规模 | 最大值臂 | 95% target F1 | saturation nt(B) | 比对 | 说明 |
|---|---|---|---|---|---|
| 10M | 10M-c1Mcs | 0.1769 | 0.9 | 一致 | shape=mixed；max_f1=0.1862@10M-c1Mcs；target=0.95*max；saturation_nt取最大值臂的unique nt |
| 30M | 30M-c1M | 0.3002 | 0.85 | 一致 | shape=monotone-fall；max_f1=0.3160@30M-c1M；target=0.95*max；saturation_nt取最大值臂的unique nt |

rfamcap 指定数字来自 `ckpt_nt=200006790`：30M 0.2880@L7、100M 0.3448@L18。最终 1900086380 下二者分别为 0.2880@L8 与 0.3297@L13，故 checkpoint 不可混写。rw1 的 val_loss=0 是空验证流伪影，本表仅使用 probe F1。
