# P4 数字逐位断言与覆盖率报告

## 输入与规则

- 组装稿：`论文重写_P1_20261125/DRAFT_v2_20261125.md`（SHA256 `290286629dba213b68b05c44cfe035a8c7ae935e831ab51395b8a14c9d086206`）。
- 溯源表：`sections/*_numbers.csv` 共 501 行、14 份；空表也计入。
- 权威源：只读备份 evidence/eval、项目 P0 对账表与已登记文本/代码行段。P2 汇总未被这些表直接引用时不另行推断数值。
- 容差：按正文/登记显示精度采用半单位舍入区间（如三位小数 ±0.0005）；pp、百分数、B/M/k 单位显式换算。派生值只有在公式操作数也能落到声明 evidence 时才通过。
- CSV 中 `missing_registration` 是正文有数字而本节溯源表未登记；`true_error` 是已登记但来源缺失、字段无法解析或值不匹配。脚本不修改论文。

## 总结

- 溯源断言：**499/501 pass**，2 fail；其中 454 行使用显示舍入，39 行使用派生重算。
- 正文数字覆盖率（出现次数）：**1259/1276 = 98.67%**。
- 正文数字覆盖率（本节唯一字面量）：**698/713 = 97.90%**。
- 未覆盖：15 组；真错误：2 条；黑名单违禁命中：**0**。
- 未覆盖项分类：13 组章节编号、2 组旧稿行号定位（L598/L622）；无实验结果数值。
- 旧值 provenance 豁免：3 处（仅记录，不当作违禁）。

## 真错误（交主代理裁决）

以下为断言失败，不自动等同于论文数值错误；当前两条均表现为溯源定位不充分。

| ID | section | item | registered value | reason |
|---|---|---|---|---|
| R0313 | sec46_q6 | extended exposure | 5.9B nt | unmatched registered values: 5.9B |
| R0412 | sec47_crosscut | S13b v1 trained family points | 30 | no resolvable source reference |
- R0313 裁决提示：`factorial_verdict.json:protocol` 只有 `inc12 final-ckpt probe...`，不能证明 5.9B；同文件 L2–L64 的 `f1_5.9B` 字段名支持 nominal 5.9B，建议主代理裁决是否修正溯源字段。
- R0412 裁决提示：旧稿 L888–L896 写明 v2=36 点和顶点 1.745，但未写 v1=30 点；需补充 v1 直接 evidence 或登记可重算的 36−6 派生口径。

## 未覆盖数字清单

以下包含章节号、模型/层/种子标识、图文件名、协议常数等全部数值字面量；它们未被静默排除，是否补登记由主代理裁决。

| ID | section | literal | DRAFT lines | example context |
|---|---|---:|---:|---|
| U0001 | appendix_provenance | `598` | 423;425 | This appendix records which historical numbers were replaced or demoted during P0 adjudication and why they must not be mixed with the current results. The decisive sources are the |
| U0002 | appendix_provenance | `622` | 423;425 | This appendix records which historical numbers were replaced or demoted during P0 adjudication and why they must not be mixed with the current results. The decisive sources are the |
| U0003 | sec3_methods | `3.1` | 63 | ## 3.1 Controlled model family and pretraining |
| U0004 | sec3_methods | `3.2` | 80 | ## 3.2 Family-level isolation and the two-world evaluation |
| U0005 | sec3_methods | `3.3` | 88 | ## 3.3 Downstream probes and non-interchangeable structure metrics |
| U0006 | sec3_methods | `3.4` | 94 | ## 3.4 Controls and comparison boundaries |
| U0007 | sec3_methods | `3.5` | 98 | ## 3.5 Statistical plan and seed coverage |
| U0008 | sec3_methods | `3.6` | 104 | ## 3.6 P0 reporting adjudications |
| U0009 | sec42_q2 | `4.2` | 137 | ### 4.2 Is the gain real? Learned weights outperform architectural and weight-statistic controls |
| U0010 | sec43_q3 | `4.2` | 166 | This section asks how much the learned-weight advantage established in Section 4.2 is worth when evaluation requires generalization to held-out families. The decisive experiments a |
| U0011 | sec44_q4 | `4.4` | 213 | ### 4.4 Where does the signal reside, and why does it erode or return to shallow layers? |
| U0012 | sec45_q5 | `4.4` | 243 | The layer relocation in Section 4.4 leaves open whether the small structural-probe increments reflect missing pairing knowledge or a readout failure. The decisive experiments form  |
| U0013 | sec45_q5 | `4.5` | 241 | ### 4.5 Is structural knowledge absent or inaccessible? Pairing is learned, but partner finding is the bottleneck |
| U0014 | sec46_q6 | `4.5` | 306 | This section asks what determines the supply of transferable knowledge after §4.5 showed that structural knowledge can be present yet gated by readout. The decisive experiments man |
| U0015 | sec46_q6 | `4.6` | 304 | ### 4.6 What determines knowledge supply? Corpus composition, budget position, and scale |

## 黑名单检索门

| 规则 | 违禁命中 |
|---|---:|
| not yet learned | 0 |
| zero-gain | 0 |
| unqualified corpus dominance | 0 |
| M/机制已证明 | 0 |
| 逐种子谷/10M valley | 0 |
| finite-channel | 0 |
| APE/RIPE | 0 |
| all 3 seeds | 0 |
| old +1.85（非 provenance） | 0 |
| cross-protocol +8.59（非 provenance） | 0 |

### 违禁命中明细

无；组装稿检索门清零。

### 旧值 provenance 语境（豁免）

- old +1.85 L339: **Rfam enrichment supplies an orthogonal but deliberately bounded test.** At matched 1.9B terminal checkpoints and s17-against-s17 coverage, rfamcap changes family F1 from 0.2466 to 0.2880 at 30M (+4.14 pp) and from 0.3263 to 0.3297 at 100M (+0.34 pp). The earlier 100M interim contrast of +1.85 pp mixed a 0.2B arm with a terminal-budget control and is therefore withdrawn from the controlled comparison and reserved for an appendix trajectory. The rfamcap structure contrast is only +0.34 pp (0.5924 versus 0.5890), and its checkpoint field is unresolved; it cannot explain the approximately +0.10 cross-model structure difference. External models remain observational anchors whose architecture, recipe, exposure, and corpus are confounded, so neither that structure gap nor a universal corpus-versus-parameter ranking is attributable from these arms.
- old +1.85 L435: The rfamcap 100M midpoint value `0.3448@L18` at 0.2B nt and its `+1.85 pp` contrast against main-line 100M `0.3263@L21` are **demoted to trajectory observations**. The comparator was a 1.9B terminal checkpoint, so the difference mixed corpus composition with budget; the main arms also lack matched 0.2B checkpoints, preventing a clean midpoint comparison (P0/B1). The adjudicated iso-budget terminal values are rfamcap `0.3297@L13` versus main `0.3263@L21`, giving `+0.34 pp` at 100M; at 30M, the terminal rfamcap value is `0.2880@L8`, giving `+4.14 pp` against `0.2466@L8`.
- cross-protocol +8.59 L449: The descriptive difference `0.4491 − 0.3632 = +8.59 pp` is **invalid as a budget-effect headline** because it crosses probe protocols, sample counts, layer windows, and probe-seed rules. Only `+1.15 pp` enters the original-terminal factorial table; a retest-based budget effect would require applying the same retest protocol to the 2.0B weights. The earlier `+6.5 pp` rendering of the 650M-minus-300M retest difference is also replaced by the correctly rounded `+6.65 pp` (or `+6.6 pp` to one decimal).

## 产物与复跑

- 逐条结果：`发布_P4_20261126/assertion_results.csv`。
- 复跑：`python3 发布_P4_20261126/assert_numbers.py`。
- 脚本以报告生成成功为退出 0；是否有发布阻断以本报告的 true error、missing registration 与 blacklist 计数为准。

## 主代理裁决补记（2026-11-26）

- **R0313（5.9B nt 标签）**：nominal 预算标签，非测量值；factorial_verdict.json 的 `table.*.f1_5.9B` 字段名与 protocol 描述共同支持，实测最佳 ckpt≈5.8B nt 已在正文注明。裁决：**标签类豁免**，不算数值错误。
- **R0412（S13b v1=30 点）**：派生值 36−6（v2=36 点=6 source×6 尺度，旧稿 L893–895 确认；v1 无 650M 一档 6 点）。裁决：**派生登记豁免**，推导链已入 _numbers.csv 备注。
- 15 组 missing_registration 全部为章节编号（3.1/3.2…）与旧稿行号定位（598/622 等），非实验结果数值，豁免。
- 黑名单字面门：**0 命中**（"10M valley" 已改写为 "10M mean-level dip"，sec44 与组装稿同步）。
- 结论：499/501 程序 pass + 2 项显式裁决豁免 + 15 组非结果字面量豁免；数字门达到 P4 可发布状态（待 P2 收口后重跑）。
