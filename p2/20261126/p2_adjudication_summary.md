# P2 补证裁决汇总（2026-11-26，持续更新）

> 预注册：补证_P2_20261125/prereg/；证据：补证_P2_20261125/results/。备份盘只读；远端仅本项目目录。

## 已完成与裁决

### P2.1 rfamcap 结构通道（results/P2_1/，105 层行+randinit 对照）
- **旧值 0.5924@L20（100M）not_reproduced**：1.8B/1.9B 两 ckpt 均 0/23 层逐位一致，来源未明（0.2B ckpt 权重未备份，无法追查）。按停止规则旧结构 +0.34pp 主张**冻结撤回**，改用可复现新值。
- **新终预算结构效应（1.9B，paired-F1 口径，trained−main）**：30M **+1.77pp**（0.5933−0.5756）/ 100M **+0.14pp**（0.5904−0.5890）；randinit 地板 30M 0.5794 / 100M 0.5875；学习增量 30M +1.38pp / 100M +0.29pp。
- 通道特异性双尺度成立：family +4.14/+0.34pp vs 结构 +1.77/+0.14pp，两通道均随容量衰减；**"+0.10 跨模型结构差距归因语料"更加不支持**（结构杠杆 100M 仅 +0.14pp）。
- 口径注意：probe_structure 落盘 f1=paired 正类 F1（非真 macro-F1），新证据两口径分列（真 macro-F1 另存）。

### P2.3 外部模型 COV（results/P2_3/，观察性锚点）
- COV−CTRL（seed17、100 TS0、4920 mutations/臂）：RiNALMo micro **+0.1134** / mega **+0.1998** / giga **+0.2477**；NucleicBERT **+0.0108**；各 randinit17 ≈0（|·|≤2.2e-5）。RNA-FM 权重缺失 NOT_RUN_WEIGHT_MISSING。
- 含义：配对知识前向级存在**跨模型复现**且随外部规模单调增强；RNA-Sc 650M +0.0957 介于 micro 与 mega 之间。Q5"知识在"主张获跨模型互证（观察性，非受控归因）。
- **sanity300 裁决（results/sanity300/）**：主臂 300M 复跑 COV−CTRL=0.04689801 vs 旧锚 0.04693655，差 −3.85e-5（相对 0.08%）。排查：condition payload 完全一致；迁移脚本 batch=1 与备份原脚本 evaluate_model **逐位一致**；batch16→1 漂移 2e-5 证明数值敏感性。裁决：**协议等价性验证通过，残差归因 A100→RTX5090/torch 版本硬件数值差，容差 1e-4 放行**；外部 COV 表解冻，标注硬件容差。旧锚精确环境未留存，不宣称唯一已证原因。

### P2.2 RNS×COV（results/P2_2/，30M 主臂）
- 逐序列 Spearman ρ=**−0.2966**，bootstrap 95% CI [−0.4732,−0.1128]（n=108，不跨 0）；source 等权 ρ=−0.80（n=5，仅描述）。
- 裁决：方向支持"RNS 越低、COV−CTRL 越强"，但弱-中等强度——**RNS 不作强结构可靠性代理**（横切主张按此限定）；旧 s14_rns_cov.json 实为 masked NLL，不得冒充 COV（已登记）。

### P2.6 新臂 de-rRNA（results/P2_6/，纯 CPU，18/18 run）
- rfamcap **+4.49/+0.32pp**、复刻 **+8.80/+2.57/+0.70pp**、b59 **−5.80/−3.08/+4.17/+1.27pp**——符号模式全保留，新臂 headline 均由非 rRNA 家族独立支撑。**红队 E 扩展面通过**。
- 缺口：P2.5 的 8k/4k de-rRNA 小节 PENDING_P2_5；rfamcap 1.8B 缺旧 family 层行 NOT_EVALUABLE。

## 阻塞中

- **P2.5/P2.7/P2.4 共同阻塞**：release22_split_8080.parquet（29,012,227 行，split_membership/canonical_sequence/rna_type）未备份，两台远端均无。重建线索：rinalmo_corpus_work/mmseqs_out_cluster.tsv（28,922,968 行簇映射）+release22_cluster_split.parquet（3,357,201 簇→split，计数与 family_index_summary 全一致）+本地 tokenizer-benchmark 管线代码（canonicalize/dedup/split.py，SPLIT_SEED=20260808）+split8080_deep_verify.json 验收统计量。X-split2 重建中。
- P2.4 管线已就绪（坐标修正+头种子固定+合成测试全过），权威 parquet 到位即可自动跑。
- 服务器2 已就绪（torch2.8 cu128，权重/代码同步，650M 冒烟过），可作第二 GPU 泳道。

## 主张变更

| 主张 | 变更 | 理由 |
|---|---|---|
| rfamcap 结构 +0.34pp@100M（旧 0.5924） | **撤回**，改 +0.14pp@100M/+1.77pp@30M（可复现终预算） | 旧值两 ckpt 均不重现 |
| 语料效应通道特异 | **升级双尺度**（E2，randinit 对照在位） | P2.1 |
| 配对知识跨模型存在 | **新增观察性互证**（外部 COV 单调梯度） | P2.3+sanity300 容差放行 |
| RNS 作结构代理 | **限定**：弱-中等负相关，不作强代理 | P2.2 |
| 新臂 headline 抗 rRNA | **通过** | P2.6 |