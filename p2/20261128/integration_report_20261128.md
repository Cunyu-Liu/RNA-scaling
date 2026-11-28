# 呈现增强与补证整合 — 整合报告（2026-11-28）

> 执行合同：执行提示词_呈现增强与补证整合_20261127.md。本轮覆盖任务 A/B/C/D/F（呈现/整合）+ H（P2.12）+ I（P2.13 审计/COV + P2.14 在飞）。
> 纪律：备份盘只读；交接文档由主代理统一更新；负结果不删；证据等级不强行提升；数字逐位溯源；在飞不写成完成。

## 1. 补测结果（数字权威）

### P2.12 四档家族预算效应多种子重测（任务 H+I2-30M，收口）
- 权重来源：服务器1 /root/rnaft_restore/03_…/runs_final2_ckpt/runs/ 本地拷贝至共享 /teams（sha256 与备份逐位一致：100M_b59 c247205b…、30M_b59 9455c11a…）。避开 Mac→集群 ~26KB/s 慢速上传。
- 协议同 P2.11（恢复版 split，mean-pool best-layer macro-F1，19 类，探针种子{17,29,43,61,79}×子样{17,29}=10 配对/档）。
- 四档配对预算效应（均值±SD，SEM，符号一致率）：
  | 尺度 | 效应 pp | SD | SEM | 正比例 | 旧单种子（归档） |
  |---|---|---|---|---|---|
  | 30M | −5.86 | 0.91 | 0.287 | 0/10 | −5.24 |
  | 100M | −1.65 | 1.42 | 0.449 | 1/10 | −2.74 |
  | 300M | −0.74 | 4.38 | 1.384 | 5/10 | +3.76 |
  | 650M | +3.06 | 2.68 | 0.847 | 9/10 | +1.15 |
- 判读：小档过训负效应符号稳健（30M/100M）、大档欠训补偿正稳健（650M）、300M 过渡不确定。跨尺度符号倾向获 3/4 档多种子支持。
- caveat：恢复池≈99.7% 原始，绝对分高 ~0.06，非精确复现。
- 证据：results/P2_11/{30M,100M}_{2B,59B}/summary.json + budget_effect_paired_4scale.json；results/P2_12/p2_12_report.md。

### P2.13 Q5 COV 多种子（任务 I2，收口）
- 5 条件种子{17,29,43,61,79}（独立序列子样+突变采样）：650M 0.0937±0.0097、100M 0.0210±0.0036，5/5 正，randinit≤0.00014；锚点 seed17 复现（650M 差 1.2e-5、100M 差 2.8e-5，<1e-4）。
- 证据：results/P2_13/cov_multiseed/summary.json。"知识在"获测量不确定度，E2 等级不变。

### P2.13 单次测量审计（任务 I1，收口）
- results/P2_13/audit_single_measurement.md：A 级已补（COV/factorial）、A 级在飞（P2.14）、B 级显式 E1 限定（Q1 300M/650M 多训练种子等）、C 级描述性标注（S13b/S6/S12/S14）。

### P2.14 外部 COV + rfamcap 结构多种子（任务 I2，在飞）
- 外部 COV（RiNALMo micro/mega/giga+NB，5 种子+randinit）：服务器1 原 P2.3 环境运行；seed17 锚点 giga 0.2476 复现。
- rfamcap 结构（30M/100M，探针种子{17,29,43,61,79}，sample_seed 17 冻结）：服务器1 GPU 满 OOM 后转服务器2 运行。
- prereg/P2_14.md。回收后补入稿（外部锚点不确定度 + rfamcap 通道特异稳健性）。

## 2. 呈现整合（任务 A/B/C/D/F，收口）

### 新图（figs_v6/，各 py+png+pdf，输入 sha256，/usr/bin/python3，300dpi，英文，灰色随机对照）
- fig3b_depth_scale_heatmap：Q4 深度×规模热图，最佳层 rel_mean 1M 0.471/10M 0.141/30M 0.788/100M 0.864/300M 0.957/650M 0.296（小尺度三种子均值，300M/650M 单种子空心标记）。
- fig4b_readout_positions：Q5 读出位置面板，绝对 F1（trained+randinit 灰）+净增量条形；650M attn_query 0.5835>残差 0.5562 但净增量≤0.021，旋转对照 0.5478。
- fig7_convergence_vs_transfer：收敛 vs 迁移三面板（轨迹/末端斜率/Δval-ΔF1 散点）；2B ~−0.003 vs 5.9B ~−0.0005/100M；100M 反转象限。

### DRAFT 入稿（论文重写_P1_20261125/sections/ + 重组装 DRAFT_v2）
- sec45_q5：两问修辞（B）+ 读出位置/探针纪律/擦除段（A1，P2.8=E2 佐证/P2.9=E1/P2.10 纪律）+ COV 多种子 + Fig.4b。
- sec46_q6：四档多次测量新表 headline（H2/H3）+ 单种子量级降级 + Claim-14 软化 + 收敛句（F3）+ Fig.7。
- sec6_limitations：per-token 地板/擦除不完全/子样敏感+恢复池/iso-token 权衡 四条（A2/G1/F3）。
- appendix_provenance：A.8 探针收敛口径（0.5973/0.6101 作废，0.5562 为准）+ A.9 四档单种子归档。
- sec41_q1/sec3_methods：近收敛 650M 句 + iso-token 设计权衡（F3）。
- sec44_q4：Fig.3b mention + 图注。
- 数字登记 sections/*_numbers.csv（含 convergence_evidence.json 派生斜率溯源）。

### 组会 PPT（交接文档/组会PPT_build/build_deck.py 重跑，15 页）
- Q4 页 fig3b、Q5 两问副标题+读出位置解读、新增 fig4b 读出位置与探针纪律页（含擦除边界）、Q6 页四档新表、新增 fig7"收敛了吗"页、status 更新。
- 修改前备份：规模的两道门_组会汇报_20261127_补证整合前备份_20261128.pptx。

## 3. 质检（验收）
- assert_numbers：registry fail=2（仅既有裁决豁免 5.9B 标签 R0346/S13b v1=30 R0457，**无新增**）、黑名单 0、正文覆盖 99.25%（1584/1596）。
- 组装一致性：分节源与 DRAFT_v2 逐字节一致；图链接 6+3 新图目标存在。
- 新图脚本实跑成功 + 输入哈希校验 + 数字与权威证据逐位一致（脚本内 assert 三遍核验）。
- PPT：文本溢出 audit 0、pptx typeface 全 Microsoft YaHei、pdftotext 新页数字核验、几何 0 越界（3 处文本框边界重叠经坐标核算字形无碰撞）。PDF 渲染字体替换为 LibreOffice fontconfig 行为（pptx 在装雅黑环境正常）。
- 数字溯源：每个新数字→results/P2_* summary→（如适用）账本/manifest，登记 _numbers.csv。

## 4. 主张变更与诚实边界
- Q6 预算 headline 改四档多次测量均值±SD（恢复池 caveat）；精确单种子量级降级近似值；"小档过训"升级多种子符号稳健（30M/100M）；300M 标不确定；Claim-14 软化。
- Q5 COV"知识在"获测量不确定度（E2 不变）；读出位置排除位置伪影（E2 佐证）；擦除 E1 弱佐证。
- 无主张被推翻；无负结果删除；无证据等级强行提升；恢复池值不冒充原始精确复现。

## 5. 待办（在飞/二期）
- P2.14 外部 COV + rfamcap 结构多种子回收→补入稿 sec45（外部锚点±SD）/sec46（rfamcap 结构±SD）+ PPT。
- 二期（需授权）：原始池精确复现（需 member→cluster 映射）；Q5 配对 AUC 多种子；增强擦除。
- 用户侧：arXiv 账号+作者信息+4 处 OpenReview 文献确认。