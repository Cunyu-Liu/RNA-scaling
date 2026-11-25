# P2.1 RFamCap 结构探针执行汇总

- 六个单元、105 个层行全部完成；8000/1305 序列（test 请求 1500，实际全集 1305），1,006,208/164,418 token，6 epochs，token batch=512。
- 所有预测已从 NPZ 逐层重算 paired/unpaired/macro-F1 与 accuracy，结果与 JSONL 一致；CPU fallback=0。
- checkpoint 裁决：**not_reproduced**；来源 ckpt_nt=None，文件=None。
- legacy 指标为 paired 正类 F1；真 macro-F1 为新增敏感性口径，不能与旧 main macro 称呼混用。

| 尺度 | 条件 | ckpt_nt | best layer | paired F1 | macro-F1 | trained−randinit (pp) | RFamCap−main (pp) |
|---|---|---:|---:|---:|---:|---:|---:|
| 100M | trained_early_1.8B | 1800083135 | 21 | 0.5941 | 0.634701 | +0.6549 |  |
| 100M | trained_final_1.9B | 1900086380 | 22 | 0.5904 | 0.638123 | +0.2890 | +0.1393 |
| 30M | trained_final_1.9B | 1900086380 | 11 | 0.5933 | 0.636140 | +1.3835 | +1.7681 |
| 30M | trained_early_1.8B | 1800083135 | 11 | 0.5974 | 0.635035 | +1.7933 |  |
| 100M | randinit17 | 0 | 21 | 0.5875 | 0.513081 |  |  |
| 30M | randinit17 | 0 | 9 | 0.5794 | 0.574260 |  |  |

终预算 family 对照仍采用预注册既有值：30M +4.14pp、100M +0.34pp；本任务未重跑 family。
1.8B 是近终点轨迹，不是旧 family 账本的 0.2B；结构曲线与差值均为 TS0 选层的描述性结果。
