# X-final-verify：P4 发布门终验报告

- 日期：2026-11-26
- 审查对象：`论文重写_P1_20261125/DRAFT_v2_20261125.md`（466 行）
- 对象 SHA256：`d43909731a0d6cb29ca4beb09d978e16048d14ffb2d89e9876005d42e567261f`
- 方式：本地 CPU；只读检查论文、分节源、参考文献与只读备份证据；复跑既有数字断言脚本；未修改论文、分节源、参考文献或交接文档。
- **总体判定：FAIL。** D1–D11、数字门（两项既定豁免）、分节组装、摘要、降级一致性和引用映射均通过；**Fig.1–6 的六个相对链接目标全部不存在，构成发布阻塞。**

## 1. 终态总表

| 检查域 | 终态 | 核心结果 |
|---|---|---|
| D1–D11 写作纪律 | PASS | 11/11 PASS；前次 D4/D6/D7/D9/D10/D11 六项缺口均有正文修复。 |
| 数字溯源与黑名单 | PASS（保留两项既定豁免） | 513/515 registry pass；仅 5.9B 标签与 S13b v1=30 派生两项失败；黑名单 0。 |
| 分节源与组装稿 | PASS | 14/14 节整节逐字节一致；首三句/末两句锚点 14/14 通过。 |
| 摘要 | PASS | 154 词；6 个数字表达；满足 ≤250 词、≤6 数字。 |
| Fig.1–6 链接 | **FAIL** | 六链均多退一级，按草稿位置解析的目标全部不存在。 |
| 降级一致性 | PASS | 650M 重测值、RNS 分箱历史值只在附录；random 预算结论限三尺度；饱和限单种子档。 |
| 引用键映射 | PASS | 21 个 `\citep` 命令、19 个唯一键；19/19 映射 `论文/DRAFT_refs.md`。 |

## 2. 判定口径

D1–D11 的权威定义来自只读备份：

- `delta_20261014/交接文档_20261014/03_CHECKLIST_验收清单.md:95-107`；
- D7 冻结边界：`01_SPEC_项目规格说明书.md:27-32`；
- D9 REDIAL 分界：`01_SPEC_项目规格说明书.md:36-38`；
- 写作任务入口：`02_TASKS_任务分解.md:655-684`；
- `code_git/REVIEW_DISCIPLINE.md:1-10` 规定原始数据重算、显式选行/去重及禁止把 smoke/proxy 写成终论，并不含 D1–D11 的逐条定义。

本轮沿用 `发布_P4_20261126/discipline_gate.md` 的严格原则：必需要素缺失即 FAIL，但不把旧稿自检结论直接继承到当前稿。以下行号均指当前 466 行 DRAFT_v2。

## 3. D1–D11 逐条终验

| 门 | 终态 | 当前稿行号证据与判定 |
|---|---|---|
| D1 受控仅自训、外部仅观察 | PASS | L31 明确只有 self-trained family 与 matched interventions 支持因果主张；L47/L50/L55、L96 延续边界；外部 RiNALMo/RNA-FM（L205）、外部 COV（L270）和跨模型 RNS（L359）均标 observational anchors；L389/L406 禁止外部受控归因。 |
| D2 引言写死线 1/线 2 主从 | PASS | L31 在 Introduction 内直接写死自训家族为归因载体、外部模型为观察锚点，并限制跨架构外推。 |
| D3 负结果配机制 | PASS | 结构 probe 弱增量以层可读性和 candidate generation/matching 解释（L253/L268/L280/L290）；saliency 弱结果以分布式计算不一定由输入梯度登记解释（L294）；rw1 负效应有 capacity-dependent composition 解释且 10M 为 neutral（L316）；NOT-BELL 有未采样高 NLL 区域的机制边界（L369）。 |
| D4 深圳湾 21 模型差异化表 | PASS | L43 引出差异化；L45-L50 在 Related Work 内给出四行对照表，覆盖比较对象、受控干预、评估设计和归因边界。 |
| D5 Li et al. 对照锚点、非复刻、零自训事实准确 | PASS | L37/L39 将 Li et al. 定位为方法模板，提供 initialization、pretraining-time、layer-wise probe 等方法；未声称复刻，也未把其写成自训模型家族。 |
| D6 必引工作齐全 | PASS | GARNET 已在 L42 正文引用；BEACON/RNAGym/NABench/RNAscope 见 L15/L19/L42；五项均进入正文而非仅存在于文献池。 |
| D7 Claim 冻结边界 | PASS | L19 含 `as of 2026-09`，并完整列出 random-initialization、weight-statistic、controlled scaling、hypothesis-testing 四要素；同时明确不是“完全没有 ablations”，承认训练配置类消融存在。 |
| D8 逐层 probe 系统化、非首创 | PASS | L40 明确 `rather than claiming the first layer-wise study`，引用 Papazoglou 与 Zablocki，将贡献限定为 controlled family 内的 systematic comparison。 |
| D9 REDIAL 三分界及事前决策点 | PASS | L52 专门段完整列出：无 supervised split-by-protocol matrix、无 self-trained controlled scale family、无 controlled scaling/corpus-composition/split axis；L21 使用进一步投资前的决策框架；全文无 `widely deployed`。 |
| D10 四点动机且逐点 RNA 证据 | PASS | 排名不可靠：L15 引 NABench/RNAscope；家族切分下效用未决：L17 引 genomic fine-tuning；无联合机制 scaling 答案：L19 引 BEACON/21-model/RNAGym 作为 RNA 领域边界；协议切分可颠覆结论：L21 引 NABench/RNAscope。投资动机另列，未顶替第四点。 |
| D11 Hou/Prabakaran/InterPLM 对话 | PASS | L39 引 Hou 的 confidence–fitness 与 Prabakaran 的 random-neighbor share，L351/L367 分别进入 S14/S13b 分析；L39 明写 InterPLM 在 random-weight models 中发现 zero biological concepts，并连接 S4 预期和条件性 S15 随机编码器对照。 |

**纪律门结论：11/11 PASS；前次六项 FAIL 均已修复，无遗留纪律 FAIL。**

## 4. 数字门复跑

执行命令：

```bash
/usr/bin/python3 发布_P4_20261126/assert_numbers.py
```

退出码为 0；脚本标准输出与本轮生成的 `coverage_report.md`、`assertion_results.csv` 一致：

- registry：515 行，**513 pass / 2 fail**；467 行显示舍入，37 行派生重算；
- 正文数字出现次数覆盖：**1309/1323 = 98.94%**；
- 本节唯一字面量覆盖：**718/730 = 98.36%**；
- 未覆盖：12 组，为 10 组章节编号/交叉引用和 2 组旧稿行号定位（L598/L622），无实验结果数值；
- 黑名单违禁命中：**0**；provenance 允许项 3 处（L337/L436 的旧 +1.85 与 L450 的跨协议 +8.59）。

### 4.1 两项失败与豁免身份

| 科学对象 | 任务给定旧 ID | 本轮实际 ID | 溯源位置 | 本轮失败原因 | 裁决 |
|---|---|---|---|---|---|
| extended exposure = 5.9B nt | R0323 | **R0318** | `sec46_q6_numbers.csv` 第 3 行；`assertion_results.csv` 第 319 行 | selector 指向 `table.650M.f1_5.9B`，读到嵌套测量值，标签 5.9B 本身未成为数值证据 | 与既定“5.9B 标签”豁免为同一对象，保留豁免 |
| S13b v1 trained family points = 30 | R0428 | **R0410** | `sec47_crosscut_numbers.csv` 第 23 行；`assertion_results.csv` 第 411 行 | `derived:s13b_bell.json n_points=36 (v2...` 不是可解析来源；属 v1=30 的派生定位问题 | 与既定“v1=30 派生”豁免为同一对象，保留豁免 |

**ID 漂移必须显式保留：** 本轮 CSV 中 R0323 和 R0428 已是其他通过记录，不能用旧 ID 定位当前失败。数字门按“科学对象 + 溯源表行”确认仅有上述两类既定豁免，没有新增 registry 失败。

### 4.2 自动报告文案备注

`coverage_report.md:16` 的计数和表内 12 个 U 项正确，但 `coverage_report.md:17` 及 `assert_numbers.py:763` 的硬编码分类仍写“13 组章节编号、2 组旧稿行号”，与实际“10+2=12 组”不符。这是报告文案陈旧，不改变 513/515、12 组未覆盖或黑名单 0 的实测结果，建议后续修正。

## 5. 组装完整性

### 5.1 分节源、组装稿及首尾句锚点

以固定顺序读取 14 份 `sections/*.md`，去除各文件末尾换行后用 `\n\n---\n\n` 连接，并保留草稿元注释前缀，所得内容与组装稿**逐字节完全一致**。因此各节首三句和末两句天然全部一致；另以排除标题、表格和图链的散文句锚点独立检查，14/14 节均为 first-3 PASS、last-2 PASS。

| 分节源 | 组装稿行范围 | 整节一致 | 首三句 | 末两句 |
|---|---:|---:|---:|---:|
| `sec0_abstract.md` | L3-L7 | PASS | PASS | PASS |
| `sec1_intro.md` | L11-L31 | PASS | PASS | PASS |
| `sec2_related.md` | L35-L55 | PASS | PASS | PASS |
| `sec3_methods.md` | L59-L108 | PASS | PASS | PASS |
| `sec41_q1.md` | L112-L133 | PASS | PASS | PASS |
| `sec42_q2.md` | L137-L158 | PASS | PASS | PASS |
| `sec43_q3.md` | L162-L207 | PASS | PASS | PASS |
| `sec44_q4.md` | L211-L235 | PASS | PASS | PASS |
| `sec45_q5.md` | L239-L298 | PASS | PASS | PASS |
| `sec46_q6.md` | L302-L345 | PASS | PASS | PASS |
| `sec47_crosscut.md` | L349-L375 | PASS | PASS | PASS |
| `sec5_discussion.md` | L379-L395 | PASS | PASS | PASS |
| `sec6_limitations.md` | L399-L418 | PASS | PASS | PASS |
| `appendix_provenance.md` | L422-L466 | PASS | PASS | PASS |

### 5.2 摘要

摘要正文为 **154 词**（英文词及数字 token 的正则计数），远低于 250 词上限。按显示表达计数共 **6 个数字**：`+0.355`、`11–18%`、`+0.096`、`+0.030`、`0.64`、`0.998`，满足 ≤6；其中 `11–18%` 作为一个范围表达计数。

### 5.3 Fig.1–6 链接目标：FAIL

草稿位于项目根的 `论文重写_P1_20261125/`。当前链接以 `../../figs_v6/` 开头，会解析到项目根之外的 `RNA 相关模型/figs_v6/`；六个目标均不存在。项目内预期图文件 `RNA_LM_迁移学习机理研究/figs_v6/` 则全部存在且非空。

| 图 | 草稿行 | 当前链接 | 当前目标 | 项目内预期文件 |
|---|---:|---|---|---|
| Fig.1 | L158 | `../../figs_v6/fig1_q1q2_transfer_controls.png` | **不存在** | 存在，260,143 bytes |
| Fig.2 | L203 | `../../figs_v6/fig2_q3_dualworld.png` | **不存在** | 存在，647,582 bytes |
| Fig.3 | L231 | `../../figs_v6/fig3_q4.png` | **不存在** | 存在，455,291 bytes |
| Fig.4 | L298 | `../../figs_v6/fig4_q5_readout_chain.png` | **不存在** | 存在，647,328 bytes |
| Fig.5 | L339 | `../../figs_v6/fig5_q6_supply.png` | **不存在** | 存在，605,588 bytes |
| Fig.6 | L371 | `../../figs_v6/fig6_crosscut.png` | **不存在** | 存在，675,124 bytes |

**发布阻塞：0/6 当前链接可解析。** 若主代理决定修复，应把六链改为 `../figs_v6/...`，并同步修改对应分节源和组装稿，之后重跑组装一致性；本轮未擅自改论文。

## 6. 降级一致性与主文残留检索

| 约束 | 终态 | 全文检索证据 |
|---|---|---|
| 650M 重测值仅附录且标未复核 | PASS | `0.4491/0.3826/0.0159/+6.65/+8.59/+6.5 pp` 只命中 Appendix A 的 L448/L450；L448 明标 `unreviewed handover-record citation`，L450 明标跨协议差值 invalid as a budget-effect headline。主文 L106/L331/L415 只说明协议和降级，不拿重测值作当前结果。 |
| random 预算免疫限三尺度 | PASS | 摘要 L7 限 `three completed terminal comparisons`；L29 同限三终点并排除未测 650M；L329 明写 `budget-insensitive` 仅指 three-scale terminal pattern，650M terminal unknown；L383 限 three smaller scales；L452 将 650M −1.85 pp 标为 demoted historical 5B midpoint。 |
| 分箱 +18%/+29% 仅附录历史参照 | PASS | 精确值 `+18.0%/+29.3%` 及历史分箱向量只命中 L456，标为 `withdrawn to historical reference only`；主文 L361/L373/L391 只保留撤回与机制未决，不报方向或效应值。 |
| 饱和限单种子档 | PASS | L114/L129 将饱和观察明确限于 single-seed 300M/650M tier，三种子 1M–100M 只支持前段增长；L133 明确不建立 training-seed-robust saturation；L410 再次限制大档无训练种子不确定度。 |
| 主文无残留强主张 | PASS | 黑名单 0；无 `not yet learned`、`zero-gain`、无限定 corpus dominance、机制已证明、10M valley、finite-channel、APE/RIPE、`all 3 seeds`；`first layer-wise` 仅在 L40 的明确非首创否定句中出现。 |

## 7. 引用键映射

自动抽取得到 **21 个 `\citep` 命令、19 个唯一键**。`DRAFT_refs.md` 是编号条目而非 BibTeX 数据库，因此下表为引用键到作者/标题/用途条目的语义映射，不声称已完成 `.bib` 编译解析。19/19 均有对应条目，无未映射键。

| 引用键 | DRAFT 行 | `论文/DRAFT_refs.md` 行 | 对应条目 |
|---|---|---|---|
| `nabench` | 15, 21, 42 | 94-96 | NABench |
| `rnascope` | 15, 21, 42 | 91-93 | RNAscope |
| `genomic_finetuning` | 17, 42 | 87-90 | Multi-model fine-tuning benchmark |
| `li_feature` | 19, 37, 39 | 15-18 | Li et al., Feature Reuse and Scaling |
| `beacon` | 19, 42 | 85-86 | BEACON |
| `zero_shot_rna` | 19, 42, 43 | 97-99 | Zero-shot 21-model RNA benchmark |
| `rnagym` | 19, 42 | 100-103 | RNAGym |
| `vishniakov_tokenization` | 21, 37, 54 | 31-33 | Tokenization to Transfer |
| `rives_biological` | 37, 39 | 12-14 | Rives et al. |
| `redial` | 37, 52 | 111-113 | REDIAL |
| `hou_scaling` | 39, 367 | 19-22 | Hou et al. |
| `prabakaran_uncertainty` | 39 | 23-26 | Prabakaran & Bromberg |
| `simon_interplm` | 39 | 27-30 | Simon & Zou, InterPLM |
| `papazoglou_attention` | 40 | 78-81 | Papazoglou et al. |
| `zablocki_structure` | 40 | 108-110 | Zablocki et al. |
| `mrnabench` | 42 | 104-105 | mRNABench |
| `garnet` | 42 | 74-77 | GARNET |
| `muennighoff_data` | 54 | 117-118 | Scaling Data-Constrained Language Models |
| `hoffmann_chinchilla` | 54 | 119-121 | Chinchilla |

## 8. 总体结论与剩余清单

### 总体：**FAIL（仅图链构成实质发布阻塞）**

1. **阻塞：修复六个图链。** 当前 Fig.1–6 链接目标 0/6 存在；应将 `../../figs_v6/` 修为 `../figs_v6/`，同步分节源与组装稿后复验。该修复未在本轮执行。
2. **非阻塞审计备注：豁免 ID 已漂移。** 当前两项失败是 R0318/R0410；旧称 R0323/R0428 在当前 CSV 中对应其他通过记录。后续发布说明应按科学对象定位，或更新豁免 ID。
3. **非阻塞报告卫生：修正未覆盖分类文案。** 实际为 12 组（10 组章节编号/交叉引用 + 2 组旧稿行号），自动报告仍写“13 组章节编号、2 组旧稿行号”。

除上述事项外，本轮没有发现新的纪律、科学数字、降级一致性或引用映射阻塞。650M 重测、650M random terminal、RNS 分箱控长度及多种子补训仍按稿中状态保持未复核、停止或不触发，未被写成已完成。
