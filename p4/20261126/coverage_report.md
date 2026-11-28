# P4 数字逐位断言与覆盖率报告

## 输入与规则

- 组装稿：`论文重写_P1_20261125/DRAFT_v2_20261125.md`（SHA256 `48a838381b98ef5e91d65edd5ab678466f432815d67ef9ca8e136a535c01e4c9`）。
- 溯源表：`sections/*_numbers.csv` 共 585 行、14 份；空表也计入。
- 权威源：只读备份 evidence/eval、项目 P0 对账表与已登记文本/代码行段。P2 汇总未被这些表直接引用时不另行推断数值。
- 容差：按正文/登记显示精度采用半单位舍入区间（如三位小数 ±0.0005）；pp、百分数、B/M/k 单位显式换算。派生值只有在公式操作数也能落到声明 evidence 时才通过。
- CSV 中 `missing_registration` 是正文有数字而本节溯源表未登记；`true_error` 是已登记但来源缺失、字段无法解析或值不匹配。脚本不修改论文。

## 总结

- 溯源断言：**583/585 pass**，2 fail；其中 535 行使用显示舍入，39 行使用派生重算。
- 正文数字覆盖率（出现次数）：**1584/1596 = 99.25%**。
- 正文数字覆盖率（本节唯一字面量）：**832/842 = 98.81%**。
- 未覆盖：10 组；真错误：2 条；黑名单违禁命中：**0**。
- 未覆盖项分类：13 组章节编号、2 组旧稿行号定位（L598/L622）；无实验结果数值。
- 旧值 provenance 豁免：3 处（仅记录，不当作违禁）。

## 真错误（交主代理裁决）

以下为断言失败，不自动等同于论文数值错误；当前两条均表现为溯源定位不充分。

| ID | section | item | registered value | reason |
|---|---|---|---|---|
| R0346 | sec46_q6 | extended exposure | 5.9B nt | unmatched registered values: 5.9B |
| R0457 | sec47_crosscut | S13b v1 trained family points | 30 | no resolvable source reference |

## 未覆盖数字清单

以下包含章节号、模型/层/种子标识、图文件名、协议常数等全部数值字面量；它们未被静默排除，是否补登记由主代理裁决。

| ID | section | literal | DRAFT lines | example context |
|---|---|---:|---:|---|
| U0001 | appendix_provenance | `598` | 449;451 | This appendix records which historical numbers were replaced or demoted during P0 adjudication and why they must not be mixed with the current results. The decisive sources are the |
| U0002 | appendix_provenance | `622` | 449;451 | This appendix records which historical numbers were replaced or demoted during P0 adjudication and why they must not be mixed with the current results. The decisive sources are the |
| U0003 | sec3_methods | `3.2` | 80 | ## 3.2 Family-level isolation and the two-world evaluation |
| U0004 | sec3_methods | `3.3` | 88 | ## 3.3 Downstream probes and non-interchangeable structure metrics |
| U0005 | sec3_methods | `3.4` | 94 | ## 3.4 Controls and comparison boundaries |
| U0006 | sec3_methods | `3.5` | 98 | ## 3.5 Statistical plan and seed coverage |
| U0007 | sec3_methods | `3.6` | 104 | ## 3.6 P0 reporting adjudications |
| U0008 | sec42_q2 | `4.2` | 137 | ### 4.2 Is the gain real? Learned weights outperform architectural and weight-statistic controls |
| U0009 | sec43_q3 | `4.2` | 164 | This section asks how much the learned-weight advantage established in Section 4.2 is worth when evaluation requires generalization to held-out families. The decisive experiments a |
| U0010 | sec46_q6 | `4.6` | 308 | ### 4.6 What determines knowledge supply? Corpus composition, budget position, and scale |

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

- old +1.85 L358: **Rfam enrichment supplies an orthogonal but deliberately bounded test.** At matched 1.9B terminal checkpoints and s17-against-s17 coverage, rfamcap changes family F1 from 0.2466 to 0.2880 at 30M (+4.14 pp) and from 0.3263 to 0.3297 at 100M (+0.34 pp). The terminal structure contrasts now use paired-F1, not true macro-F1: rfamcap-minus-main is +1.77 pp at 30M (0.5933@L11 versus 0.5756@L3) and +0.14 pp at 100M (0.5904@L22 versus 0.5890@L22), with randinit floors of 0.5794 and 0.5875, respectively. Together with family +4.14/+0.34 pp, this gives channel-specific two-scale decay: both channels shrink with capacity, but the family lever remains larger than the structure lever. De-rRNA reaggregation retains the rfamcap family effects at +4.49/+0.32 pp at 30M/100M, independently supporting the headline direction in non-rRNA families. The earlier 100M family interim contrast of +1.85 pp mixed a 0.2B arm with a terminal-budget control and remains withdrawn from the controlled comparison and reserved for an appendix trajectory; the old checkpoint-unresolved structure estimate is likewise withdrawn and documented in Appendix A. The adjudicated structure effect cannot explain the approximately +0.10 cross-model structure difference. These rfamcap results remain E1 single-seed orthogonal evidence, separate from the E2 controlled corpus contrasts and E3 pre-registered budget decisions above. External models remain observational anchors whose architecture, recipe, exposure, and corpus are confounded, so neither that structure gap nor a universal corpus-versus-parameter ranking is attributable from these arms.
- old +1.85 L461: The rfamcap 100M midpoint value `0.3448@L18` at 0.2B nt and its `+1.85 pp` contrast against main-line 100M `0.3263@L21` are **demoted to trajectory observations**. The comparator was a 1.9B terminal checkpoint, so the difference mixed corpus composition with budget; the main arms also lack matched 0.2B checkpoints, preventing a clean midpoint comparison (P0/B1). The adjudicated iso-budget terminal values are rfamcap `0.3297@L13` versus main `0.3263@L21`, giving `+0.34 pp` at 100M; at 30M, the terminal rfamcap value is `0.2880@L8`, giving `+4.14 pp` against `0.2466@L8`.
- cross-protocol +8.59 L475: The descriptive difference `0.4491 − 0.3632 = +8.59 pp` is **invalid as a budget-effect headline** because it crosses probe protocols, sample counts, layer windows, and probe-seed rules. Only `+1.15 pp` enters the original-terminal factorial table; a retest-based budget effect would require applying the same retest protocol to the 2.0B weights. The earlier `+6.5 pp` rendering of the 650M-minus-300M retest difference is also replaced by the correctly rounded `+6.65 pp` (or `+6.6 pp` to one decimal).

## 产物与复跑

- 逐条结果：`发布_P4_20261126/assertion_results.csv`。
- 复跑：`python3 发布_P4_20261126/assert_numbers.py`。
- 脚本以报告生成成功为退出 0；是否有发布阻断以本报告的 true error、missing registration 与 blacklist 计数为准。
