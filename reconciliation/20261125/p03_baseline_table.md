# P0.3 六档 family 切分 LM−最强基线主表

统一比较边界：`rna_type`、19 类 macro-F1、`family_validation→family_test`、20,000/4,000；LM 一律用最终 checkpoint 的 `probe-meanpool` 最佳层。这里的“同协议”指相同样本切分与评价指标；经典模型是各自直接监督训练，并非 LM 的 mean-pool linear probe。

观测最强基线是 LightGBM s17（0.1760）。但它没有 s29/s43 证据，所以三种子档的 `Δ_obs` 不是完整三种子对三种子比较；`Δ_strict` 改用具有相同种子覆盖的 CNN。两列回答不同问题，不得混称。

| 档位 | LM F1（种子） | 观测最强基线 F1（种子） | Δ_obs=LM−观测最强 | 同种子覆盖基线 F1（种子） | Δ_strict=LM−同覆盖最强 |
|---|---:|---:|---:|---:|---:|
| 1M | 0.1650±0.0131（s17/29/43） | 0.1760 LightGBM（s17） | -0.0110 | 0.1589±0.0119 one-hot CNN（s17/29/43） | +0.0061 |
| 10M | 0.1535±0.0173（s17/29/43） | 0.1760 LightGBM（s17） | -0.0225 | 0.1589±0.0119 one-hot CNN（s17/29/43） | -0.0054 |
| 30M | 0.2651±0.0162（s17/29/43） | 0.1760 LightGBM（s17） | +0.0891 | 0.1589±0.0119 one-hot CNN（s17/29/43） | +0.1062 |
| 100M | 0.3394±0.0147（s17/29/43） | 0.1760 LightGBM（s17） | +0.1634 | 0.1589±0.0119 one-hot CNN（s17/29/43） | +0.1804 |
| 300M | 0.3445（单种子）（s17） | 0.1760 LightGBM（s17） | +0.1685 | 0.1760 k-mer(1–6)+LightGBM（s17） | +0.1685 |
| 650M | 0.3632（单种子）（s17） | 0.1760 LightGBM（s17） | +0.1872 | 0.1760 k-mer(1–6)+LightGBM（s17） | +0.1872 |

注：LM 与 CNN 的 ± 为三种子样本标准差（ddof=1）；单种子档不报告标准差。`Δ` 用未四舍五入均值计算，再显示四位小数。严格列仅是种子覆盖一致，不声称不同模型之间是配对种子实验。

## 逐种子追溯

| 档位 | 最终 checkpoint 的 mean-pool 最佳层 F1 与账本行 |
|---|---|
| 1M | s17=probe_results.jsonl:86；s29=probe_results.jsonl:1243；s43=probe_results.jsonl:1225 |
| 10M | s17=probe_results.jsonl:97；s29=probe_results.jsonl:1279；s43=probe_results.jsonl:1254 |
| 30M | s17=probe_results.jsonl:124；s29=probe_results.jsonl:990；s43=probe_results.jsonl:974 |
| 100M | s17=probe_results.jsonl:185；s29=probe_results.jsonl:204；s43=probe_results.jsonl:229 |
| 300M | s17=eval_matrix_results.jsonl:31 |
| 650M | s17=eval_matrix_results.jsonl:35 |

基线字段：`classical_baselines_extra.json family.kmer_lgbm.f1_macro=0.1760`；`classical_baselines_extra{,_s29,_s43}.json family.onehot_cnn.f1_macro=[0.1725,0.1502,0.1541]`。k-mer logistic 的 0.1630 来自 `classical_baselines.json family.f1_macro`，因仅固定 s17 单次结果而不进入三种子严格列。

复算规则与完整旧口径裁决见 `p03_caliber_adjudication.md`；机读全精度结果见 `p03_baseline_table.csv`。
