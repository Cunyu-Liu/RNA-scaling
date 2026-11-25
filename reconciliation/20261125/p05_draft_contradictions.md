# P0.5 — DRAFT 五条内部矛盾冻结裁决

- 只读对象：`delta_20261014/DRAFT_v1_final_20261014.md`，共 1078 行；行号以该文件为准。
- 裁决原则：较晚、直接干预或 probe-free 的证据优先；旧审计只作 provenance，不与终判并列为当前结论。
- 本任务未修改 DRAFT、账本、evidence 或交接文档。机读版见 `p05_draft_contradictions.csv`；输入哈希见 `p05_draft_contradictions.manifest.json`。

## C1 — §4.4 旧“未学会/四证据汇聚”账户作废

**位置**：旧块 L598-L622；新证据链 L404-L526，另有 L624-L665 的独立 forward/interpretability 支持。

**旧表述原文（精确摘录）**：

> L598: Original audit (superseded numbers, kept for provenance):
> L599: 
> L600: **Composition-floor audit (user-prompted).** A GC-identity-only rule
> L601: (predict paired iff nucleotide in {G, C}) achieves macro-F1 0.576 on
> L602: the bpRNA test set — G paired-rate 0.486 / C 0.449 vs A 0.258 / U 0.356,
> L603: the Watson-Crick pairing prior. Random-init models score 0.53-0.586 at
> L604: every layer because residual pathways preserve nucleotide identity; the
> L605: composition floor, not structure, dominates this task. The trained gain
> L606: over the floor climbs with scale: 1M -0.047 / 10M -0.010 / 30M -0.000 /
> L607: 100M +0.013 / 650M +0.021 — a real but tiny structural increment (2.1pp
> L608: over 650x scale), crossing the floor only at >=100M. The task has the
> L614: **Randinit controls (architecture prior, not pretraining).** 
> L615: Structure-probe randinit controls: |trained − randinit| ≤ 0.02 at all
> L616: six scales (10M: 0.5678 vs 0.5663; 300M/650M arms in fig update). Paired-position linearity comes
> L617: from the ALiBi/encoder prior; pretraining contributes ≈0 on this task
> L618: at this budget — the mirror image of the family-discrimination gains
> L619: (+0.04..+0.17). (Fig 2: layer-wise curves, rna_type vs structure tasks.) Four-way convergence (S7 zero-gain, S12 early-layer
> L620: high-DI families, S13b not-bell, S14 decoupling): at 2.0B nt, RNA MLM
> L621: pretraining transfers family-level sequence statistics; structure
> L622: information is largely not yet learned.
**终判证据**：COV−CTRL 从 1M 的 0.00415 增至 650M 的 0.09572，且 650M randinit 为 0.00004（`covariation_test.json` 与 `covariation_test_650M.json` 的 `cov_minus_ctrl`）；Partner-Oracle 为 0.9996/0.9992/0.9983（`readout_heads_v3.json: models.{30M,100M,650M}.partner_oracle`）；pair AUC 为 0.9319/0.9397/0.9524，但 model-free `dist_ident` 已达 0.922（`pair_probe_v4.json`、`pair_probe_baseline.json`）。因此只能声称配对信息存在且净增量有限，不能声称结构预测已解决。

**裁决**：L619-L622 的 “S7 zero-gain / Four-way convergence / structure information is largely not yet learned” 以及 L614-L618 的 “pretraining contributes ≈0” 作为跨读出方式的全任务终判，均被后续直接证据推翻；≤100M own-best 线性读出近零这一局部结果仍保留。终判统一为：**配对知识在表示与 forward pass 中存在；线性 readout 严重低读，候选配对生成/匹配求解器是结构预测缺口；raw pair probe 还必须扣除 distance+composition prior。**

**重写落点**：§4.4 主文保留 L404-L526 的 COV → remote readout → Oracle/pair probe → matched-prior correction；L598-L622 整段移至 provenance，不在主文保留“旧结论仍有效”的视觉并列。

## C2 — superseded 数字与修正版并存

**行号清单**：修正说明 L345-L352；当前三数据集表 L362-L368；own-best 修正版 L386-L393；重定性 L395-L402；旧值块 L598-L612（核心旧数字 L606-L608）。

> L345: **Protocol corrections (self-audit).** (i) The probe-JSON "f1" column
> L346: is paired-class F1, previously compared against the macro floor —
> L347: metric mismatch; all numbers below are macro-F1. (ii) The 1M
> L348: single-set row used a weak training subset (35k tokens vs 1.0M for
> L349: other scales); under the full protocol the 1M trained gain is +0.007
> L350: (not -0.047). (iii) A first multi-dataset run (v1) was invalidated by
> L351: a label-shuffle bug (seqs/pairs shuffled with different seeds) and is
> L352: excluded.
> L384: Two comparisons, two meanings. (A) Same-layer comparison mixes two
> L385: effects: where the signal is readable and what the network knows.
> L386: (B) Each-at-own-best-layer comparison (single-set full scans): 1M
> L387: +0.007, 10M -0.001, 30M -0.003, 100M +0.004 — pretraining does not
> L388: raise the linear-readout ceiling at <=100M; it relocates readable
> L389: signal (trained 100M best at L22 vs randinit best at L14). The
> L390: 650M +0.10..+0.14 same-layer excess is dominated by the randinit
> L391: deep-layer collapse; the honest scale-dependent signal is the
> L392: trained-minus-trigram increment (+0.034..+0.046 at 650M), which
> L393: replicates on all three sets.
> L598: Original audit (superseded numbers, kept for provenance):
> L599: 
> L600: **Composition-floor audit (user-prompted).** A GC-identity-only rule
> L601: (predict paired iff nucleotide in {G, C}) achieves macro-F1 0.576 on
> L602: the bpRNA test set — G paired-rate 0.486 / C 0.449 vs A 0.258 / U 0.356,
> L603: the Watson-Crick pairing prior. Random-init models score 0.53-0.586 at
> L604: every layer because residual pathways preserve nucleotide identity; the
> L605: composition floor, not structure, dominates this task. The trained gain
> L606: over the floor climbs with scale: 1M -0.047 / 10M -0.010 / 30M -0.000 /
> L607: 100M +0.013 / 650M +0.021 — a real but tiny structural increment (2.1pp
> L608: over 650x scale), crossing the floor only at >=100M. The task has the
**裁决**：旧 `1M −0.047 / 10M −0.010 / 30M −0.000 / 100M +0.013 / 650M +0.021` 不再作为当前结果。修正后的 own-best trained−randinit 是 `1M +0.007, 10M −0.001, 30M −0.003, 100M +0.004`。注意 L364 的 1M `+0.001` 是 **TS0−trigram**，与 L349/L387 的 **own-best trained−randinit +0.007** 比较基准不同，二者都不可混写。

**重写落点**：§4.4 主文只保留修正版及显式 comparator；旧向量整体移 provenance，并标注 weak training subset 与 metric mismatch 已修正。

## C3 — Abstract 超载

**位置**：标题 L20，正文 L22-L75。代表摘录：

> L29: transfers. Transfer grows with scale but non-monotonically: a 10M
> L30: "attrition valley" falls below the 1M baseline in three-seed mean (negative in 2/3 seeds), driven
> L31: by duration-specific erosion of family-discrimination features (mid-
> L32: training peak 0.25 F1 at 0.5B nt decays to 0.17) that spares the
> L33: structure task. Two classical confounds are excluded experimentally:
> L34: random-initialization and moment-matched weight-statistic controls
> L35: account for none of the gain (+0.17 at 100M survives both), so the
> L36: learned weight structure is real — yet under family-level evaluation
> L37: that structure barely beats k-mer composition baselines (+0.007 at
> L38: 100M), while under random splits the same models gain +0.43: the
> L39: "scaling wins" of random-split benchmarks are largely family-similarity
> L40: leakage, a property of the protocol that classical baselines reproduce
> L41: (k-mer Δ = +0.355). Best-layer depth migrates from early to late layers
> L47: parameter sweep within one model family gains only +2.6pp while a
> L48: corpus-composition contrast gains +11pp at smaller scale: corpus
> L49: dominates parameters for family-level transfer. A pre-registered slope
> L50: rule (0.142 F1/decade, bootstrap CI [0.104, 0.180]) triggered a 650M
> L51: continuation — verdict: 650M ABOVE 100M (650M F1 0.3632 vs 100M 0.3394, +2.4 pp; slope 100M→650M 0.0293, full-axis 0.0829).
> L52: A pre-registered 3x2 budget-by-scale factorial (four arms retrained at
> L53: the full 5.9B-nt corpus) then refutes the pre-registered corpus-ceiling
> L54: claim (Claim-14: 300M@5.9B gain < 1.0 pp) and replaces it with a
> L55: Chinchilla-style compute-optimal interaction: the budget effect on
> L56: family-level transfer FLIPS sign monotonically across scale (−5.24 /
> L57: −2.74 / +3.76 / +1.15 pp at 30M/100M/300M/650M; probe-seed retest at
> L58: 650M: 0.4491±0.015 across 3 seeds, +6.5pp over 300M@5.9B), and a 302M
> L59: model at the full-corpus budget (0.3821) beats the entire 2.0B main
> L60: line including 650M (0.3632). The interaction is readout-channel-
**实测**：空白分词 **526 words**；连字符/撇号合并的 regex 口径 **563 words**。含至少一个数字的空白 token **73 个**；数值字面量 regex **80 个**。主报告采用前一种词数与“含数字 token”口径，后两者用于复核，避免把 `0.4491±0.015` 等如何切分隐藏起来。

**裁决**：符合“约 550 词、15+ 数字”的超载预期。当前摘要混入完整预算矩阵、probe-seed retest、多个对照增量及机制解释，且 L47-L49 仍含无条件 corpus-dominance 断言。

**重写落点**：重写 Abstract L22-L75，只保留研究设计、主要标度/协议结论和最关键的受控预算/语料结果；逐尺度矩阵回到 §4.1/§4.5/§4.7，probe-seed 细节回到 §4.1，结构读出回到 §4.4。

## C4 — §5.1 强 finite-channel 已证伪；修订账户升格 Q6 主结果

**位置**：§5.1 全段 L959-L997；旧强账户 L961-L980，其中 leading explanation 在 L968-L976；预注册判据 L977-L980；终判与修订账户 L981-L997。

> L961: Three channels plateau together at 30M under the 2.0B-nt budget: the
> L962: leakage dividend (Delta), representation organisation (RNS), and the
> L963: rRNA shuffle separation (P5). We test three candidate causes against
> L964: existing intervention evidence. **Data quantity is excluded**: the S3
> L965: corpus axis shows SMALLER unique corpora beat the full 14.1B-unique
> L966: corpus at both 10M and 30M (c1M 0.316 vs full 0.247 at 30M), and 30M
> L967: sits at 67 tokens/param — 3.3x above the Chinchilla optimum, so tokens
> L968: are not the binding constraint. **A finite task-information channel is
> L969: the leading explanation**: a zero-capacity k-mer baseline already
> L970: reaches 0.518 random-split F1 (86% of the ~0.60 ceiling); twenty-fold
> L971: capacity growth (30M -> 650M) moves neither the Delta plateau
> L972: (0.605 -> 0.625) nor the rRNA separation (+5%) — the channel is capped
> L973: by task structure (19-class family overlap with rRNA at 63.6% of
> L974: corpus), not by model capacity or data volume. **A capacity gate
> L975: complements it**: 30M is the smallest config that absorbs the full
> L976: channel (10M sits below it, producing the attrition valley). The
> L977: The decisive intervention was pre-registered: 30M@5.9B (tokens x3,
> L978: unique sequence exposure 0.14 -> 0.42 epoch) — if all three plateaus
> L979: persist unchanged, the data-quantity explanation is finally excluded
> L980: and the finite-channel account closes; if any plateau moves, data
> L981: quantity re-enters. **RESULT (10-05, extended 10-13; b59 3-channel matrix,
> L982: evidence/p5rns_b59_verdict.json + b59_random_delta.json): the
> L983: finite-channel account is REFUTED in its strong form.** Two of three
> L984: channels MOVE with budget and the movement is scale-amplified:
> L985: RNS@10 tightens (100M 0.0828 → 0.0515, 300M 0.0668 → 0.0425); P5
> L986: non-rRNA shuffle separation grows +0.11/+0.29/+0.36 nats/token at
> L987: 30M/100M/300M (0.08→0.19, 0.14→0.43, 0.23→0.59) while rRNA
> L988: separation plateaus ~0.9 as predicted. Only the family-Delta channel
> L989: follows the finite-channel story (it moves NEGATIVELY below 300M);
> L990: its random-split counterpart is budget-IMMUNE (§4.7 fourth link:
> L991: +0.65/−0.60/+4.10/−1.85pp, all four scales now closed 10-13).
> L992: Revised account: the 30M triple-plateau is a FAMILY-CHANNEL
> L993: phenomenon — zero-supervision structural statistics keep eating
> L994: budget at every scale (Chinchilla-style), and the k-mer-reachable
> L995: classification channel saturates. The S7 structure matrix
> L996: (+0.09/+0.85/+1.87pp monotone) agrees with the P5 channel; the two
> L997: zero-supervision and two readout views converge.
**裁决**：`p5rns_b59_verdict.json: verdict` 明确 “TWO of three channels MOVE … family-channel story, not a global representation story”；`matrix` 给出 non-rRNA budget delta 0.1093/0.2908/0.3629，RNS delta −0.0105/−0.0313/−0.0243。故 “Data quantity is excluded” 与 “finite task-information channel is the leading explanation” 只能保留为被检验并否决的历史账户； family-classification channel 可保留有限饱和解释，不可外推为全局表示上限。

**Q6 升格落点建议**：在现 §4.5 后、现 §4.6 前新增 Results 小节 **“Budget moves representation channels: the 30M plateau is family-channel-specific 【Q6】”**。将 L981-L997 的判据、三通道矩阵和修订结论前移为该节主体；§5.1 只保留一段 Discussion 解释与回指。S7 的 +0.09/+0.85/+1.87pp 用 `s7_structure_budget_matrix.json: budget_effect_monotone_note` 作交叉支持，不重复堆表。

## C5 — 假说 M：链 b 支持不等于三链定量账户成立

**所有直接/延伸位置**：叙事主线 L153-L157；M 与三链账户 L747-L760；P5b L769-L774；P1/chain b L776-L783；P3/P4 及总判 L785-L801；§4.11 延伸账户 L913-L915。关键原文：

> L153: F1. **Act V — manipulate the corpus (H5 + hypothesis M + P1):** the
> L154: corpus axes (quantity, diversity) and the de-rRNA intervention close
> L155: the loop — deep-layer capacity is allocated to the corpus-majority
> L156: (rRNA) channel as scale grows, which relocates the best probe layer
> L157: forward; removing the channel (P1) eliminates the reversal. One
> L747: **Hypothesis M (post-hoc, grade-B evidence).** The reversal is not
> L748: deep-layer degradation: the 650M late band holds F1 0.348 vs best 0.3632.
> L749: We propose a three-chain account, stated explicitly as a hypothesis
> L750: (unlike H1–H8, which were pre-registered): (a) the marginal non-rRNA
> L751: gain of depth, (late−mid)/mid, decays with scale (+18% at 30M → +3% at
> L752: 300M → +2% at 650M) — family features are already extracted by mid
> L753: layers; (b) the rRNA channel (56% of corpus) is decodable at ~0.97 F1
> L754: at every depth, so larger models fill deep capacity with corpus-
> L755: majority tasks earlier (L8); (c) the random-mixing floor rises with
> L756: depth (randinit non-rRNA floor 0.023 early → 0.049 late; mommatch
> L757: 0.029 → 0.062) — deeper stacks mix more random channels, lowering
> L758: deep-layer SNR. Net: the best-SNR layer migrates forward as capacity
> L759: grows (0.957 at 300M → 0.296 at 650M) — a corpus-supply-limited
> L760: capacity reallocation, not a depth pathology.
> L762: **P5 (TESTED 09-27, zero-supervision shuffle separation).**
> L763: MLM likelihood separation (native minus position-shuffled, nats/token,
> L764: same mask positions, family_test): rRNA 0.47 (1M) -> 1.07 (30M) -> 1.12
> L765: (650M) — a strict post-30M plateau; non-rRNA 0.05 -> 0.31 (monotone);
> L766: randinit control 0.002 (structure required). Verdict: P5a partially
> L767: confirmed — the corpus-majority channel saturates by 30M while
> L768: family-sequence statistics keep deepening, adding a third independent
> L769: 30M phenomenon (with the Delta-law plateau and the RNS plateau). P5b
> L770: REFUTED: the rRNA-over-non-rRNA gap NARROWS (0.94 -> 0.81) rather than
> L771: widens — chain (b) must be refined: rRNA-channel occupation completes
> L772: by 30M; the capacity 650M reallocates to deeper layers carries finer
> L773: long-range sequence constraints, not more rRNA statistics. We report
> L774: this boundary honestly.
> L776: Falsifiable predictions (discriminating experiments): **P1 (CONFIRMED,
> L777: 09-27)** de-rRNA stratified probe (18 classes, rRNA excluded from
> L778: train/eval): 100M best L16 (rel 0.73) / 300M L18 (0.78) / 650M L27
> L779: (rel 1.00, F1 0.4585 — monotone above 300M 0.4026 and 100M 0.3192).
> L780: With the rRNA class removed, the 650M reversal disappears entirely and
> L781: the best layer returns to the deepest position — chain (b) is
> L782: intervention-grade confirmed (B → A−), and family features are intact
> L783: in deep layers (0.4585 is the highest de-rRNA F1 at any scale). **P2** 650M@5.9B (3× corpus, training) — the
> L791: outlier, not a trend. **P4 (TESTED, partially refuted)** quantitative
> L792: leave-one-out extrapolation: a linear map from de-rRNA best-layer
> L793: position to full-class position has LOO error 0.305 (acceptable only
> L794: for 100M-650M: 0.10-0.26); a capacity-shift model fails outright (LOO
> L795: 0.745, errors >1.0 at both 10M and 650M). The capacity-to-layer
> L796: mapping is therefore NOT a simple monotone function: the 10M valley
> L797: (attrition regime) and the 650M reversal are regime transitions, not
> L798: points on a line. Honest verdict: hypothesis M survives qualitatively
> L799: (P1 intervention confirms chain b; P3 consistent), but its quantitative
> L800: form is refuted — the corpus-capacity interaction is nonlinear, which
> L801: we report as a boundary of the current account.
**裁决**：统一措辞冻结为 **“链 b 干预支持、定量形式证伪、post-hoc grade-B”**。P1 的 de-rRNA 干预支持 chain b，但不能把整体三链账户升为 A−；P5b 的 gap 从 0.9401 降至 0.8086（`p5_shuffle_threshold.json: scales.30M.gap` 与 `scales.650M.gap`）证伪“随规模扩大”的预测；P4 的 `mean_err_1=0.3046`、`mean_err_2=0.7447`（`p4_loo_test.json`）否定简单线性/capacity-shift 定量形式。

**重写落点**：L153-L157 改为待检验解释；L747-L760 保留 post-hoc grade-B 标签并预告两个证伪分支；L781-L783 删除整体 `B → A−`；L798-L801 用上述冻结句替换 “survives qualitatively”；L913-L915 改为 “consistent with the still-post-hoc account”，不得当作独立验证。

## 对账顺带发现的异常（不并入五条裁决）

- `pair_probe_v4.json` 的 100M AUC 是 **0.9397**，DRAFT L488/L510 写 **0.938**；不是四位小数直接舍入，需要 P1 回账本确认，不能强行凑数。
- `b59_random_delta.json` 仍只含 30M/100M/300M，且 `pending=["650M"]`；DRAFT L823-L829、L990-L991 却写四尺度及 650M −1.85pp。Q6 的 RNS/P5 主裁决有独立 evidence 支持，但该 650M random cell 需另补权威账本/evidence 后才能保留。
- `hypothesis_evidence_audit.json` 的 M 项仍写 P2/P3/P4 在途和 “主链证实”，属于较早审计状态；本裁决采用较晚的 `p4_loo_test.json` 与 `p5_shuffle_threshold.json`，不沿用其整体升级措辞。
- `b59_reseed_300vs650.json` 的键为模型训练 run、内层键 29/43/61 为 probe seeds；它支持 L298-L302 的 probe-head retest，不构成三个独立训练种子。
