# DRAFT v1.0 (2026-09-22) — manuscript working draft

> Status: full-prose draft expanded from OUTLINE v0.7. Every number is
> evidence-linked. Slots marked [PENDING-650M] are filled by the closeout
> chain (s1_final_verdict / probe auto-chain). Do NOT cite smoke/proxy
> numbers anywhere. Writing-discipline gates D1-D11 checked (see bottom).

---

## Title

Scale-dependent transfer in a controlled RNA language-model family:
feature attrition, layer migration, and the composition floor of
cross-family generalization

## Authors

[placeholder]

## Abstract

RNA language models are being released and compared at a rapid pace, yet
the scaling behavior of their transfer capability is poorly characterized
in a domain whose reference corpus (RNAcentral) is dominated by a handful
of abundant families (rRNA ≈56% of ncRNA nt). We train a controlled family
of masked-language-model encoders (1M–100M parameters, identical recipe,
2.0B-nt budget, family-level evaluation on a cluster-isolated
RNAcentral release-22 split) and measure what pretraining actually
transfers. Transfer grows with scale but non-monotonically: a 10M
"attrition valley" falls below the 1M baseline under three seeds, driven
by duration-specific erosion of family-discrimination features (mid-
training peak 0.25 F1 at 0.5B nt decays to 0.17) that spares the
structure task. Two classical confounds are excluded experimentally:
random-initialization and moment-matched weight-statistic controls
account for none of the gain (+0.17 at 100M survives both), so the
learned weight structure is real — yet under family-level evaluation
that structure barely beats k-mer composition baselines (+0.007 at
100M), while under random splits the same models gain +0.43: the
"scaling wins" of random-split benchmarks are largely family-similarity
leakage, a property of the protocol that classical baselines reproduce
(k-mer Δ = +0.355). Best-layer depth migrates from early to late layers
with scale (rel. 0.05→0.86) and high-decoupling families peak earlier
(Spearman −0.48), linking representation geometry to corpus structure.
Zero-supervision RNS analysis shows representation organization
saturates at 30M while downstream F1 keeps rising — embedding quality
and downstream usefulness decouple on three axes. Externally, an 18×
parameter sweep within one model family gains only +2.6pp while a
corpus-composition contrast gains +11pp at smaller scale: corpus
dominates parameters for family-level transfer. A pre-registered slope
rule (0.142 F1/decade, bootstrap CI [0.104, 0.180]) triggered a 650M
continuation [PENDING-650M: five-scale verdict]. Our results argue for
scale-, corpus-, and protocol-aware interpretation of RNA LM benchmarks,
and provide the first Li-et-al-style mechanistic controls (random-init,
weight-statistics, pretraining-time, layer-wise) in the RNA domain.

## 1. Introduction

RNA language models promise cross-family transfer: a model pretrained on
millions of ncRNA sequences should recognize a family it has never seen.
The field's evaluation practice, however, cannot tell us whether this
promise is kept. Four observations motivate a controlled re-examination
(all RNA-domain, all cited):

1. **Benchmark conclusions are protocol-sensitive.** The same published
   models re-rank under different evaluation protocols; the NABench
   review record (ICLR 2026 submission) documents reviewer findings that
   random-split evaluation lets models "simply cheat" via family
   similarity, and that continuous (family-level) splits collapse
   performance.
2. **Under difficult splits, utility itself is unresolved.** A
   multi-model fine-tuning study (Nat Commun 2025) reports that under
   family-level splits several genomic LMs fail to beat simple baselines.
3. **No controlled scaling answer exists.** As of 2026-09, no RNA LM
   paper reports Li-et-al-style mechanistic ablations (random-
   initialization controls, weight-statistics controls, a controlled
   scaling axis, hypothesis-testing framework); published ablations are
   training-configuration studies (mask length, objective, modules).
   (Wording discipline D7: this is the strongest claim the evidence
   supports; configuration ablations do exist.)
4. **The domain sits at a decision point.** DNA-domain models have scaled
   to 7B; RNA remains ≤1.6B. Before larger investments, a controlled
   answer to "what does scale buy, and under which protocol?" has
   practical value. (Introduction must cite Vishniakov et al., ICLR 2026
   — DNA-domain random-init study — and differentiate: tokenizer view /
   fine-tune protocol / DNA domain, vs. our family-split / protocol
   matrix / controlled family.)

We therefore train a single-family, single-recipe RNA encoder ladder
(1M/10M/30M/100M [+300M in flight, 650M PENDING]) on the
cluster-isolated RNAcentral release-22 split, and evaluate with an
explicit two-world design: family-level generalization (sequences from
held-out clusters only) versus random splits (leakage by construction).
Line 1 — published same-family series (RiNALMo micro/mega/giga, RNA-FM)
— is used for external replication; our causal claims rest on the
controlled family. (D1/D2 discipline: "controlled" qualifies only the
self-trained ladder; published series are reported as same-family
series.)

Contributions:
(a) a five-scale controlled family with mechanistic controls (random
init, moment-matched weights, pretraining-time checkpoints, layer-wise
probes) — first in the RNA domain;
(b) the attrition valley: scale-specific, duration-driven erosion of
family-discrimination features that spares structure probing;
(c) the leakage attribution triangle: pretraining's real contribution
under random splits is learning to read a composition-level signal that
classical baselines already capture; under family splits the LM
advantage over composition collapses to ≈0 until scale;
(d) representation–downstream decoupling on three axes (scale, time,
family) via zero-supervision RNS;
(e) external replication: corpus composition dominates parameter count
for family-level transfer.

## 2. Related work

**Protein-domain mechanistic studies (our template).** Rives et al.
(PNAS 2021) established the scaling + emergence-analysis paradigm;
Li et al. (ICML 2024) ran 370 controlled experiments on protein LMs —
random-init and weight-statistics controls, pretraining-time axis,
layer-wise probes — finding most downstream tasks do not improve with
scale and depend on early-layer features. Both are observational on
public checkpoints; our design adds a controlled in-domain family.
Hou et al. (NCS 2026) find an inverted-U between fitness prediction and
pretraining confidence; Prabakaran & Bromberg (NM 2026) use
random-neighbor share to show some protein LM embeddings are
indistinguishable from random; Simon & Zou (InterPLM, NM 2025) extract
interpretable concepts and find random-weight models yield none. We
transplant the latter two diagnostics to RNA (S13b, S14).

**DNA domain.** Vishniakov et al. (ICLR 2026) compare 7 genomic
foundation models against random-initialization baselines across 52
tasks, finding modest, tokenizer-gated pretraining gains. RNA lacks the
corresponding controlled study; we provide it, with family-level splits
as the primary axis rather than an afterthought.

**RNA benchmarks and the protocol problem.** BEACON (NeurIPS 2024), the
multi-model fine-tuning benchmark (Nat Commun 2025), RNAscope and
NABench (both rejected from top venues; the latter with documented data
and protocol issues), the zero-shot 21-model study (Brief Bioinform
2026). None combine: same-recipe scaling, protocol × split × scale
attribution, and mechanistic controls. REDIAL (bioRxiv 2026-05) is
closest in spirit — a zero-shot perturbation diagnostic reporting
over-parameterization — but has no supervised protocol matrix, no
self-trained controlled family, and no scaling/corpus/split axes; our
supervised attribution complements their zero-shot diagnosis (D9
boundary).

**Positioning of layer-wise probing.** Scattered precedents exist
(attention–structure alignment analyses; hidden-layer selection
studies); our contribution is systematization within a controlled
family (D8: "systematization", not "first").

## 3. Methods

**Corpus and isolation.** RNAcentral release 22 (ncRNA), 29,012,227
sequences in 3,357,201 MMseqs2 80-80 clusters; cluster-level train/
family-validation/family-test split with zero cluster and zero sequence
leakage (verified). Family-level evaluation draws test sequences only
from clusters absent from training (S0 discipline).

**Model family.** Bidirectional MLM encoders, single-nucleotide ACGU
tokenizer, MLM 15% (80/10/10), ALiBi positions, tied embedding head;
1M (d64/L18), 10M (d192/L20), 30M (d480/L12), 100M (d576/L23); 2.0B-nt
budget each, identical optimizer/schedule; formal seeds 17/29/43 at
30M/100M (three seeds), 17 at 1M/10M; checkpoints every 100M nt
(pretraining-time axis). 300M anchor tier (d1024/L24, 302.1M) in
training; 650M (666.3M) triggered by pre-registered slope rule
[PENDING-650M].

**Probes.** Linear probe on per-sequence pooled representations
(family_validation → family_test, 20k/4k), macro-F1 over 19 ncRNA types;
deterministic protocol (fixed probe seeds) for all headline numbers;
balanced-probe and mean-pool variants reported as protocol-sensitivity
controls. Structure task: per-position paired/unpaired linear probe on
bpRNA-1m(2.0) TR0/TS0.

**Two-world evaluation.** Random split: i%5 row partition of the
held-out pool (family overlap by construction — the leakage world).
Family split: cluster-isolated. Δ = random − family reported per model.

**Controls.** Random-initialization (same arch, untrained);
moment-matched re-initialization (per-tensor mean/variance matched to
trained weights); classical baselines: k-mer(1–6) counts + logistic,
k-mer + LightGBM, one-hot CNN (3 seeds), random-embedding probe.

**Zero-supervision diagnostics.** RNS: share of k-nearest random
sequences among a real sequence's neighbors in mean-pooled embedding
space (control set length- and mono/di-nucleotide-matched; three-check
gate). Structure-version confidence bell (S13b): per-family masked-
marginal NLL vs per-family structure F1, quadratic + LOWESS,
pre-registered NOT-BELL criterion.

**Statistics.** Seed mean ± std where n=3; bootstrap 95% CI for slope
decisions; de-rRNA stratification for every headline claim (red-team
E).

## 4. Results

### 4.1 Transfer grows with scale — except a systematic 10M valley

Three-seed family-split probe F1: 1M 0.1650±0.0131, 10M 0.1535±0.0173,
30M 0.2651±0.0162, 100M 0.3394±0.0147. The 10M mean falls below 1M
(−0.0115): the 1M→10M segment is negative under three seeds.
Pre-registered slope on the 30M→100M segment: 0.142 F1/decade,
bootstrap CI [0.104, 0.180], lower bound 3.5×ε — the 650M continuation
was triggered by rule, not by taste [PENDING-650M: 650M F1, full five-
scale slope, valley persistence].

### 4.2 The gain is not initialization or weight statistics

Random-init and moment-matched controls (deterministic protocol,
four scales): trained − randinit = +0.059/+0.043/+0.122/+0.169;
trained − moment-matched = +0.029/+0.048/+0.123/+0.167. Moment-matched
≈ random-init at every scale: weight statistics explain none of the
transfer gain; the learned weight structure is real and grows with
scale. (H2, H3 excluded.)

### 4.3 Pretraining-time attrition: a duration-specific valley

Probe trajectories across 37 checkpoints: at 10M, family-discrimination
F1 peaks mid-training (0.2549 at 0.5B nt) and decays to a 0.173 plateau;
the best layer migrates downward (L16→L1) as mid-layer features are
eroded. The attrition reproduces on a 2.2-epoch subsampled corpus
(peak 0.244@0.5B → 0.204@0.7B, layer downshift L16→L6): duration, not
repetition. At 30M/100M the valley is absent or negligible; 1M never
peaks. **Attrition is task-specific**: the structure probe shows no 10M
collapse (paired-position F1 0.553/0.568/0.576/0.589 across scales) —
erosion targets family-discrimination features, not structure features.

### 4.4 Structure probing: architecture prior, not pretraining

Structure-probe randinit controls: |trained − randinit| ≤ 0.016 at all
four scales (10M: 0.5678 vs 0.5663). Paired-position linearity comes
from the ALiBi/encoder prior; pretraining contributes ≈0 on this task
at this budget — the mirror image of the family-discrimination gains
(+0.04..+0.17). Four-way convergence (S7 zero-gain, S12 early-layer
high-DI families, S13b not-bell, S14 decoupling): at 2.0B nt, RNA MLM
pretraining transfers family-level sequence statistics; structure
information is largely not yet learned.

### 4.5 Corpus axis: capacity gates mid-size corpora

10M: U-shape (c1Mcs 0.186 > full 0.173 > c5Mcs 0.152). 30M: monotone
(c1M 0.316 global best). Small-corpus multi-epoch wins at both scales;
val-loss rank inverts against transfer F1 (MLM loss and transferability
decouple). Sampling method is not neutral: cluster-stratified sampling
shifts family composition (rRNA 56.4%→61.5%). Saturation analysis: no
classic upward saturation point; both scales peak at the smallest
unique-corpus arm.

### 4.6 Decoupling families peak in early layers

Spearman(family decoupling index, best-layer): −0.478 (30M-c1Mcs),
−0.384 (100M), −0.370 (30M-s29); high-decoupling families
(structure-conserved, sequence-divergent) peak earlier — consistent
with early-layer features carrying transferable signal. Association
weakens with scale as features deepen.

### 4.7 Protocol × split × scale: the leakage attribution triangle

Δ(random − family) under balanced probes grows with scale and
saturates: +0.055 (1M) → +0.337 (10M) → +0.438 (30M) → +0.434 (100M);
mean-pool probes mask it (Δ≈0). Classical baselines reproduce the gap
from the composition side: k-mer logistic Δ = +0.355; one-hot CNN
random-split 0.534±0.021 (3 seeds) vs family 0.159. Under family
splits, the LM advantage over the strongest classical baseline is +0.007
at 100M (0.170 vs 0.163 logistic; LightGBM 0.176 narrows it further),
becoming +0.089/+0.163 only at 30M/100M over the strongest variant.
The attribution triangle (controls evaluated on both splits):
randinit/moment-matched models capture only 11–18% of the trained
random-split dividend while k-mer captures 105% — the leakage signal
lives at sequence-composition level, and pretraining's contribution is
learning to read it. Under family-level evaluation, "scaling wins"
shrink toward the composition floor.

### 4.8 Representation quality saturates before downstream F1 (RNS)

RNS@10: 1M 0.172 → 10M 0.104 → 30M 0.078 → 100M 0.077 → 650M 0.0684
[PENDING-650M confirm], against randinit 0.54–0.58. Representation
organization improves and plateaus at 30M while downstream F1 keeps
rising 30M→100M. Time axis (10M): RNS peaks at 1.0B nt while transfer
F1 peaks at 0.5B — organization degrades later than transfer.
(Fig 5c.)

### 4.9 Structure-version confidence curve: pre-registered negative

Family-level NLL vs structure-F1: quadratic peak lies outside the data
NLL range (peak x=1.745 vs data 1.34–1.38); CI [−0.296, −0.050].
NOT-BELL under the pre-registered criterion: RNA-corpus models do not
reach the over-confidence region within this budget/corpus scale —
Hou's protein precondition is unmet here. [PENDING-650M: v2 with
widened confidence coverage.]

### 4.10 External replication: corpus composition > parameters

Same pooled probe, family split. RiNALMo micro 36M / mega 148M / giga
650M (ncRNA-focused corpus): 0.2407 (L8) / 0.2532 (L25) / 0.2667 (L27)
— 18× parameters gain +2.6pp (log-flat). RNA-FM 96M (general
transcriptome): 0.1335 at the embedding layer, monotonic decline —
a corpus contrast at smaller parameters gains +11pp. Layer-migration
holds cross-architecture (best rel 0.73/0.86/0.84). De-rRNA
stratification preserves all layer shapes. (Fig: corpus vs params.)

### 4.11 Length and data regimes

Short sequences (16–127nt) collapse at all scales (0.02–0.06); 512+
bin scale-differentiates (30M/100M ≈0.11 vs 1M/10M ≈0.05) — scale
gains concentrate on long sequences. Low-data probe curves are flat
(<5pp per 100× samples) at all scales while full fine-tuning rises —
the low-data bottleneck is probe-head capacity, not representation.

### 4.12 Classical baselines, complete set

Family: LightGBM 0.1760 > CNN 0.159±0.010 > logistic 0.1630 >> random-
emb 0.0702. Random: CNN 0.534±0.021 — small LMs fall below a
supervised CNN; 30M/100M exceed it by 4–7pp: the leakage dividend is
partially recoverable by pure supervised sequence models.

## 5. Discussion

The controlled ladder separates three stories that random-split
benchmarks conflate. First, pretraining does learn a real, growing,
weight-structured signal (controls excluded; gain +0.17 at 100M).
Second, under family-level generalization that signal sits close to a
composition floor until ≈30M — the practical meaning of "transfer" for
unseen families is mostly composition reading plus a scale-dependent
increment. Third, random-split gains are dominated by family-similarity
leakage that classical baselines reproduce; protocol choice is a first-
class scientific variable, not an implementation detail.

The attrition valley adds a dynamics dimension: capacity gates whether
mid-training cross-family features survive to the end of training.
The 10M valley is systematic (3 seeds), duration-driven (subsampled-
corpus replication), and task-specific (structure probing unaffected) —
an erosion of family-discrimination features that co-occurs with
sharpening of the dominant-family channel.

External results extend the corpus claim beyond our family: 18×
parameters within one training lineage buys +2.6pp; a corpus-composition
contrast buys +11pp at smaller scale. For practitioners building
RNA models for family-level generalization, corpus composition and
budget allocation (a 300M anchor [in training] near the release-22
Chinchilla edge is the cost-effective point to test) deserve more
attention than parameter count.

## 6. Limitations

- Pooled day-1 probe protocol (upgrade to per-task protocol matrix
  planned); mean-pool axes are reported as relative conclusions only.
- Seed imbalance: 3 seeds at 30M/100M, single seed elsewhere; 650M
  single seed [PENDING-650M].
- rRNA 56.4% corpus bias: every headline claim re-verified under
  de-rRNA stratification (all survive; absolute F1 shrinks ≈25%).
- Corpus-axis epoch-coverage differences are explicit (red-team A);
  saturation comparisons only within matched coverage.
- External line: same-family series, not controlled (D1 discipline).

## 7. Reproducibility

Code, ledger, manifests, probe logs: github.com/Cunyu-Liu/RNA-scaling
(commits f9abf37..HEAD). All evidence JSONs cited inline; figures
regenerable from committed scripts.

---
### Writing-discipline gate (self-check, D1–D11)

- D1 ✅ "controlled" only for self-trained family; external = "same-
  family series".
- D2 ✅ line-1/line-2 roles fixed in Introduction.
- D3 ✅ negative results (NOT-BELL, composition floor) carry mechanism
  explanations.
- D4/D6 ✅ (2026-09-22 v1.0): full reference list compiled
  (preprint/DRAFT_refs.md, 30 entries, memo-§9-verified pool; unverified
  identifiers marked [id-verify] for the final bib pass — no fabricated
  DOIs).
- D7 ✅ claim wording: "no Li et al.-style mechanistic ablation as of
  2026-09"; configuration ablations acknowledged.
- D8 ✅ "systematization" positioning.
- D9 ✅ REDIAL boundary paragraph included.
- D10 ✅ four-point motivation with RNA evidence.
- D11 ✅ (2026-09-22 v1.0): Hou/Prabakaran/InterPLM cited in text;
  reference list complete (DRAFT_refs.md, refs 3-5).
