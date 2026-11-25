# P0.5 — DRAFT 黑名单检索门命中清单

- 范围：DRAFT 全文 L1-L1078；大小写不敏感；APE/RIPE 使用独立词边界，避免误伤普通子串。
- 当前基线：精确字面命中 10 处；另列 8 处同义、跨行或否定语境变体，共 18 条记录。否定语境也列入，因为机械检索不会因 “REFUTED” 自动豁免。
- P1 复核建议同时报告 `exact=0` 与 `semantic review=0`。若旧原文移入同一文件的 provenance 附录，`not yet learned` 等仍会字面命中；若要求全文件清零，应把旧原文归档到 DRAFT 外部。
- 机读版：`p05_blacklist_hits.csv`；输入哈希：`p05_blacklist_hits.manifest.json`。

## 命中明细

### BL-001 — not yet learned — L619-L622
- 类型：`exact`；语境：作废旧审计的终句。
- 处置：主文删除；如要求全文件字面清零，旧原文应归档到 DRAFT 外部而非保留在附录。
> L619: (+0.04..+0.17). (Fig 2: layer-wise curves, rna_type vs structure tasks.) Four-way convergence (S7 zero-gain, S12 early-layer
> L620: high-DI families, S13b not-bell, S14 decoupling): at 2.0B nt, RNA MLM
> L621: pretraining transfers family-level sequence statistics; structure
> L622: information is largely not yet learned.

### BL-002 — zero-gain — L619-L622
- 类型：`exact`；语境：旧 S7 四证据汇聚。
- 处置：删除旧 S7 zero-gain 定性。
> L619: (+0.04..+0.17). (Fig 2: layer-wise curves, rna_type vs structure tasks.) Four-way convergence (S7 zero-gain, S12 early-layer
> L620: high-DI families, S13b not-bell, S14 decoupling): at 2.0B nt, RNA MLM
> L621: pretraining transfers family-level sequence statistics; structure
> L622: information is largely not yet learned.

### BL-003 — corpus composition dominates（无条件式） — L133-L134
- 类型：`exact_unqualified`；语境：Introduction contribution (e)。
- 处置：改为有模型家族、协议及外部观察性限制的结论。
> L133: (e) external replication: corpus composition dominates parameter count
> L134: for family-level transfer.

### BL-004 — corpus composition dominates（无条件式） — L47-L49
- 类型：`semantic_unqualified`；语境：Abstract: corpus dominates parameters。
- 处置：删除抽象中的普遍支配断言；改为受控 corpus-swap 的尺度依赖结果。
> L47: parameter sweep within one model family gains only +2.6pp while a
> L48: corpus-composition contrast gains +11pp at smaller scale: corpus
> L49: dominates parameters for family-level transfer. A pre-registered slope

### BL-005 — corpus composition dominates（无条件式） — L158-L160
- 类型：`semantic_unqualified`；语境：Narrative spine: corpus story, not parameter story。
- 处置：降级为本受控家族/预算内的解释，不作普遍二分。
> L158: sentence: *RNA-LM scaling is a corpus story, not a parameter story —
> L159: within the corpus boundary, scale buys depth; beyond it, scale buys
> L160: specialization (rRNA) and artifact (leakage).*

### BL-006 — corpus composition dominates（无条件式） — L731-L733
- 类型：`semantic_unqualified`；语境：§4.5: scaling is a corpus story。
- 处置：保留 corpus_arm_verdict 的尺度梯度，删除普遍化口号。
> L731: 1.06×/0.92×/1.31×). Combined with §4.1: on this
> L732: corpus family the scale axis saturates because the corpus axis
> L733: saturates — "scaling is a corpus story" (corpus_arm_verdict.json).

### BL-007 — corpus composition dominates（无条件式） — L898-L906
- 类型：`heading_shorthand`；语境：§4.10 标题及外部模型对比。
- 处置：标题标明 external observational contrast；与 §6 L1008-L1023 黑箱限定同置。
> L898: ### 4.10 External replication 【Act V · cross-family】: corpus composition > parameters
> L899: 
> L900: Same pooled probe, family split. RiNALMo micro 36M / mega 148M / giga
> L901: 650M (ncRNA-focused corpus): 0.2407 (L8) / 0.2532 (L25) / 0.2667 (L27)
> L902: — 18× parameters gain +2.6pp (log-flat). RNA-FM 96M (general
> L903: transcriptome): 0.1335 at the embedding layer, monotonic decline —
> L904: a corpus contrast at smaller parameters gains +11pp. Layer-migration
> L905: holds cross-architecture (best rel 0.73/0.86/0.84). De-rRNA
> L906: stratification preserves all layer shapes. (Fig: corpus vs params.)

### BL-008 — 10M valley — L248
- 类型：`exact`；语境：§4.1 标题 systematic。
- 处置：改为 mean-level attrition at 10M，避免 systematic/per-seed universal 暗示。
> L248: ### 4.1 Transfer grows with scale 【Act I · H1】 — except a systematic 10M valley

### BL-009 — 10M valley — L257-L258
- 类型：`exact`；语境：§4.1 650M era。
- 处置：保留 three-seed mean 限定，替换黑名单标签。
> L257: full-axis slope 0.0829 F1/decade; the 10M valley persists in
> L258: the 650M era (10M 0.1535 < 1M 0.1650, three-seed means). The 300M

### BL-010 — 10M valley — L796-L797
- 类型：`exact`；语境：P4 regime transition。
- 处置：改为 10M attrition regime。
> L796: mapping is therefore NOT a simple monotone function: the 10M valley
> L797: (attrition regime) and the 650M reversal are regime transitions, not

### BL-011 — 10M valley — L946-L949
- 类型：`exact`；语境：Discussion；虽有 three-seed mean 限定仍命中字面门。
- 处置：替换标签，保留 2/3 seeds negative 与非逐种子普遍限定。
> L946: The 10M valley is robust at the three-seed mean level (2/3 seeds negative), duration-driven (subsampled-
> L947: corpus replication), and task-specific (structure probing unaffected) —
> L948: an erosion of family-discrimination features that co-occurs with
> L949: sharpening of the dominant-family channel.

### BL-012 — 10M valley — L29-L32
- 类型：`semantic_variant`；语境：Abstract: 10M attrition valley。
- 处置：同步替换，避免只清精确字符串而留下同义标签。
> L29: transfers. Transfer grows with scale but non-monotonically: a 10M
> L30: "attrition valley" falls below the 1M baseline in three-seed mean (negative in 2/3 seeds), driven
> L31: by duration-specific erosion of family-discrimination features (mid-
> L32: training peak 0.25 F1 at 0.5B nt decays to 0.17) that spares the

### BL-013A — all 3 seeds — L298-L302
- 类型：`near_variant_probe_seed`；语境：精确式 0 命中；此处为 3/3 probe seeds。
- 处置：明确写成 3/3 probe seeds (29/43/61)，不得暗示三个训练种子。
> L298: undertrained. A probe-seed retest (3 seeds, 29/43/61, 8000/4000
> L299: samples) confirms 650M@5.9B > 300M@5.9B at 3/3 seeds (0.4491±0.015
> L300: vs 0.3826±0.013, +6.5pp; the single-seed 0.3747<0.3821 inversion
> L301: was probe-head initialization noise, corrected 10-12), and the 650M
> L302: budget effect under the retest protocol is +8.6pp (0.3632→0.4491).

### BL-013B — all 3 seeds — L57-L58
- 类型：`near_variant_probe_seed`；语境：Abstract 的 across 3 seeds 与 L298-L302 是同一次 probe-seed retest。
- 处置：保留 probe-seed 限定并压缩摘要，不得暗示三个训练种子。
> L57: −2.74 / +3.76 / +1.15 pp at 30M/100M/300M/650M; probe-seed retest at
> L58: 650M: 0.4491±0.015 across 3 seeds, +6.5pp over 300M@5.9B), and a 302M

### BL-014 — finite channel — L968-L976
- 类型：`lexical_variant_strong_account`；语境：finite task-information channel 是 leading explanation。
- 处置：强账户已证伪，撤下 leading explanation。
> L968: are not the binding constraint. **A finite task-information channel is
> L969: the leading explanation**: a zero-capacity k-mer baseline already
> L970: reaches 0.518 random-split F1 (86% of the ~0.60 ceiling); twenty-fold
> L971: capacity growth (30M -> 650M) moves neither the Delta plateau
> L972: (0.605 -> 0.625) nor the rRNA separation (+5%) — the channel is capped
> L973: by task structure (19-class family overlap with rRNA at 63.6% of
> L974: corpus), not by model capacity or data volume. **A capacity gate
> L975: complements it**: 30M is the smallest config that absorbs the full
> L976: channel (10M sits below it, producing the attrition valley). The

### BL-015 — finite channel — L977-L980
- 类型：`exact_preregistered_history`；语境：原预注册判据；有限通道账户 closes。
- 处置：如保留历史，只放 Methods/provenance 且明确后续证伪；字面清零需改名。
> L977: The decisive intervention was pre-registered: 30M@5.9B (tokens x3,
> L978: unique sequence exposure 0.14 -> 0.42 epoch) — if all three plateaus
> L979: persist unchanged, the data-quantity explanation is finally excluded
> L980: and the finite-channel account closes; if any plateau moves, data

### BL-016 — finite channel — L981-L984
- 类型：`exact_negated`；语境：REFUTED 否定语境，仍会被机械检索命中。
- 处置：科学结论保留；P1 若执行字面零命中，改写为 strong account is refuted。
> L981: quantity re-enters. **RESULT (10-05, extended 10-13; b59 3-channel matrix,
> L982: evidence/p5rns_b59_verdict.json + b59_random_delta.json): the
> L983: finite-channel account is REFUTED in its strong form.** Two of three
> L984: channels MOVE with budget and the movement is scale-amplified:

### BL-017 — finite channel — L988-L991
- 类型：`exact_limited_residual`；语境：仅 family-Delta channel 的残余账户。
- 处置：改成 family-classification-channel-specific saturation，删除通用标签。
> L988: separation plateaus ~0.9 as predicted. Only the family-Delta channel
> L989: follows the finite-channel story (it moves NEGATIVELY below 300M);
> L990: its random-split counterpart is budget-IMMUNE (§4.7 fourth link:
> L991: +0.65/−0.60/+4.10/−1.85pp, all four scales now closed 10-13).

## 精确零命中规则

- `all 3 seeds（精确式）`：**0 命中**。
- `机制已证明`：**0 命中**。
- `APE/RIPE（独立词，忽略大小写）`：**0 命中**。

## P1 清零复核口径

1. 逐字重扫 `not yet learned`、`zero-gain`、`corpus composition dominates`、`10M valley`、`all 3 seeds`、`finite-channel`、`机制已证明`、独立词 `APE/RIPE`。
2. 人工复查本文件的 8 条扩展变体，尤其是 Abstract 的 `corpus dominates parameters`、`10M attrition valley`、`across 3 seeds` 和 Results 的 `3/3 seeds`。
3. `finite-channel` 的 L981-L984 虽为证伪句，仍是字面命中；按项目选择的“全文零命中”或“肯定式零命中”口径处理，并在复核结果中注明。
4. 不把 probe-seed retest 改成训练种子重复，也不为清词而删除必要的否定结果；可改写标签并保留科学含义。