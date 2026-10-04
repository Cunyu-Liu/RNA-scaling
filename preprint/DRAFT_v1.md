# DRAFT v1.0 (2026-09-22) — manuscript working draft

> Status: full-prose draft expanded from OUTLINE v0.7. Every number is
> evidence-linked. Slots marked [FILLED-650M-v1.1] are filled by the closeout
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
of masked-language-model encoders (1M–650M parameters, identical recipe,
2.0B-nt budget, family-level evaluation on a cluster-isolated
RNAcentral release-22 split) and measure what pretraining actually
transfers. Transfer grows with scale but non-monotonically: a 10M
"attrition valley" falls below the 1M baseline in three-seed mean (negative in 2/3 seeds), driven
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
continuation — verdict: 650M ABOVE 100M (650M F1 0.3632 vs 100M 0.3394, +2.4 pp; slope 100M→650M 0.0293, full-axis 0.0829). Our results argue for
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
(1M/10M/30M/100M/650M [+300M in flight]) on the
cluster-isolated RNAcentral release-22 split, and evaluate with an
explicit two-world design: family-level generalization (sequences from
held-out clusters only) versus random splits (leakage by construction).
Line 1 — external RNA-LM baselines (RiNALMo micro/mega/giga,
journal-published; RNA-FM, arXiv preprint 2204.00300, never
journal-published — see refs note) — is used for external replication;
our causal claims rest on the controlled family. (D1/D2 discipline:
"controlled" qualifies only the self-trained ladder; external models
are reported as baselines with publication status stated.)

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


### Narrative spine (how the eight hypotheses form one story)

The paper is organized as a five-act funnel, each act removing one class
of explanations until a single mechanism remains. **Act I — pose the
question (H1):** a controlled six-scale ladder measures what scale
actually buys; transfer grows non-monotonically to saturation (slope
0.0293 < ε at 650M), so the question shifts from "how much" to "what is
the carrier of the gain". **Act II — exclude the trivial (H2/H3):**
random-init and moment-matched interventions show the carrier is the
learned weight structure, not architecture or weight statistics. **Act
III — locate the structure (H4/H6):** layer-wise probes show where that
structure lives (layer migration endpoints; decoupled families lean
early). **Act IV — separate real from apparent (leakage triangle +
H8):** the Δ-law shows random-split gains are composition-level
leakage with a 30M ceiling, while family-level transfer is the real
signal; RNS shows representation quality saturates before downstream
F1. **Act V — manipulate the corpus (H5 + hypothesis M + P1):** the
corpus axes (quantity, diversity) and the de-rRNA intervention close
the loop — deep-layer capacity is allocated to the corpus-majority
(rRNA) channel as scale grows, which relocates the best probe layer
forward; removing the channel (P1) eliminates the reversal. One
sentence: *RNA-LM scaling is a corpus story, not a parameter story —
within the corpus boundary, scale buys depth; beyond it, scale buys
specialization (rRNA) and artifact (leakage).*

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
1M (d64/L18), 10M (d192/L20), 30M (d480/L12), 100M (d576/L23),
650M (d1408/L28, 666.3M); 2.0B-nt budget each, identical
optimizer/schedule; formal seeds 17/29/43 at 30M/100M (three
seeds), 17 at 1M/10M and 650M (pre-registered); checkpoints every
100M nt (pretraining-time axis). 300M anchor tier (d1024/L24,
302.1M) in training; 650M (666.3M) triggered by the pre-registered
slope rule — complete, final F1 0.3632 (best-layer rel 0.296).

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

### 4.1 Transfer grows with scale 【Act I · H1】 — except a systematic 10M valley

Six-scale family-split probe F1 (300M anchor tier added 2026-09-26):
1M 0.1650±0.0131, 10M 0.1535±0.0173, 30M 0.2651±0.0162,
100M 0.3394±0.0147, 300M 0.3445 (single seed), 650M 0.3632. The 10M mean falls below 1M
(−0.0115): the 1M→10M segment is negative in 2/3 seeds (s29 −0.040, s43 −0.008, s17 +0.013) — mean-level, not per-seed universal.
Pre-registered slope on the 30M→100M segment: 0.142 F1/decade,
bootstrap CI [0.104, 0.180], lower bound 3.5×ε — the 650M continuation
was triggered by rule, not by taste. 650M final: F1 0.3632;
full-axis slope 0.0829 F1/decade; the 10M valley persists in
the 650M era (10M 0.1535 < 1M 0.1650, three-seed means). The 300M
anchor closes the interpolation: 100M→300M only +0.5pp
(near-plateau) vs 300M→650M +1.9pp; the layer-migration endpoint
reverses (rel 0.864@100M → 0.957@300M peak → 0.296@650M) —
non-monotone at six scales.

**Budget axis (3×2 factorial; two points closed 10-03/10-04).** Two
arms retrained at 5.9B nt (≈ full corpus + ~3 epochs, same recipe/
split/protocol; automated closeout chain), against the 2.0B iso-token
main line:

| scale | F1 @2.0B | F1 @5.9B | budget effect |
|---|---|---|---|
| 100M | 0.3263 (L21) | 0.2989 (L16) | **−2.74pp (overtraining)** |
| 300M | 0.3445 (L22) | **0.3821 (L22)** | **+3.76pp (undertraining at 2B)** |

The sign FLIPS across scale: at 100M the 2.0B budget is at/beyond
compute-optimal on a redundant corpus (rRNA 63.6%; Muennighoff-style
"repetition ≈ fresh tokens" does not transfer — the −2.74pp comes with
a best-layer downshift L21→L16, overtraining erosion of §4.3 family,
while the randinit gain is intact at +0.141 vs +0.168); at 300M the
2.0B budget was UNDERtrained — +3.76pp from the fuller corpus, and
0.3821@L22 exceeds the entire 2.0B main line INCLUDING 650M (0.3632):
a 302M-parameter model at the full-corpus budget beats a 666M model
at one-third of it. **The pre-registered Claim-14 boundary test is
FALSIFIED** (pre-registered bar: 300M@5.9B gain < 1.0pp ⇒ corpus-
optimal scale ≈300M; measured +3.76pp, boundary_holds=false) — we
report this as-is: the correct generalization is Chinchilla-style
compute-optimal interaction, not a hard corpus ceiling: each scale
has its own optimal budget position, and the 2.0B iso-token design is
near-optimal only for the smaller scales. Remaining arms (30M/650M
@5.9B) are training under the same automated chain; the completed
table will fill the interaction. (Fig 6.)

### 4.2 The gain is not initialization 【Act II · H2/H3】 or weight statistics

Random-init and moment-matched controls (deterministic protocol,
six scales): trained − randinit = +0.059/+0.043/+0.122/+0.169/+0.133(300M)/+0.151(650M);
trained − moment-matched = +0.029/+0.048/+0.123/+0.167/+0.146(300M)/+0.147(650M). Moment-matched
≈ random-init at every scale: weight statistics explain none of the
transfer gain; the learned weight structure is real and grows with
scale. (H2, H3 excluded.)

### 4.3 Pretraining-time attrition 【Act III · H4 timeline】: a duration-specific valley

Probe trajectories across 37 checkpoints: at 10M, family-discrimination
F1 peaks mid-training (0.2549 at 0.5B nt) and decays to a 0.173 plateau;
the best layer migrates downward (L16→L1) as mid-layer features are
eroded. The attrition reproduces on a 2.2-epoch subsampled corpus
(peak 0.244@0.5B → 0.204@0.7B, layer downshift L16→L6): duration, not
repetition. At 30M/100M the valley is absent or negligible; 1M never
peaks. **Attrition is task-specific**: the structure probe shows no 10M
collapse (paired-position F1 0.553/0.568/0.576/0.589 across scales) —
erosion targets family-discrimination features, not structure features.

### 4.4 Structure probing 【Act III · H4】 — composition floor, three references, multi-dataset (09-28)

**Protocol corrections (self-audit).** (i) The probe-JSON "f1" column
is paired-class F1, previously compared against the macro floor —
metric mismatch; all numbers below are macro-F1. (ii) The 1M
single-set row used a weak training subset (35k tokens vs 1.0M for
other scales); under the full protocol the 1M trained gain is +0.007
(not -0.047). (iii) A first multi-dataset run (v1) was invalidated by
a label-shuffle bug (seqs/pairs shuffled with different seeds) and is
excluded.

**Multi-dataset generalization (user-prompted, three test sets).**
Heads trained once on bpRNA TR0 (8,000 seqs, seed 17), evaluated
unchanged on bpRNA-TS0, bpRNA-val, and ArchiveII (independent source,
10 families). References: GC-rule floor; trigram (L-C-R one-hot)
logistic floor with no model; random-init probed at the trained best
layer. Floors (GC / trigram): TS0 0.576/0.592, val 0.608/0.616,
ArchiveII 0.599/0.621. Trained macro-F1:

| scale | TS0 | val | ArchiveII | TS0−trig | val−trig | Arch−trig |
|---|---|---|---|---|---|---|
| 1M | 0.592 | 0.610 | 0.625 | +0.001 | −0.006 | +0.004 |
| 10M | 0.605 | 0.617 | 0.641 | +0.013 | +0.001 | +0.019 |
| 30M | 0.616 | 0.637 | 0.654 | +0.024 | +0.021 | +0.033 |
| 100M | 0.608 | 0.627 | 0.653 | +0.017 | +0.011 | +0.032 |
| 650M | 0.626 | 0.662 | 0.659 | +0.034 | +0.046 | +0.038 |

The pattern replicates on all three sets: (a) 1M sits at the trigram
floor — linear heads decode local composition only; (b) the increment
above the trigram floor grows with scale (650M +0.034..+0.046); (c)
random-init at the same layer sits at the GC floor for 1M (0.572) and
near the trigram floor for 10M (0.590) — what linear heads read from
untrained networks is composition; pretraining's contribution at this
budget is the increment above the trigram ceiling, not the absolute
score. Random-init on the three sets (completed): 30M 0.596/0.611/
0.623, 100M 0.612/0.630/0.636, and 650M collapses to 0.521/0.542/
0.521 at layer 15 — a deep-layer readability collapse of the large
untrained network. Same-layer trained-minus-randinit: 1M/10M/30M
+0.01..+0.03 (stable small increments), 100M ≈ 0 on TS0/val (+0.017
on ArchiveII only), 650M +0.105/+0.120/+0.138.

Two comparisons, two meanings. (A) Same-layer comparison mixes two
effects: where the signal is readable and what the network knows.
(B) Each-at-own-best-layer comparison (single-set full scans): 1M
+0.007, 10M -0.001, 30M -0.003, 100M +0.004 — pretraining does not
raise the linear-readout ceiling at <=100M; it relocates readable
signal (trained 100M best at L22 vs randinit best at L14). The
650M +0.10..+0.14 same-layer excess is dominated by the randinit
deep-layer collapse; the honest scale-dependent signal is the
trained-minus-trigram increment (+0.034..+0.046 at 650M), which
replicates on all three sets.

Requalified conclusion: S7 measures "structure beyond local
composition". On three test sets the composition ladder (GC rule →
trigram → model) replicates; the beyond-trigram signal is 0 at 1M,
+0.02..+0.03 at 30M, and +0.03..+0.05 at 650M. Pretraining's role
below 650M is relocating layer-readability, not raising the linear
ceiling; only at 650M does a genuine increment above both the
trigram floor and any randinit layer appear. P3 (no deep migration)
is unaffected: the floor signal is layer-independent.

**Co-variation sensitivity test (user-prompted: is the small probe
increment an artifact?).** The linear-probe increment being tiny has
two possible readings: (A) pairing information is not learned, or
(B) it is learned but not linearly readable. We distinguish them with
a probe-free forward test: mask the paired position j, mutate its
partner i to each alternative base, and measure the probability shift
at j toward the NEW complement (COV), with an unpaired-position
control (CTRL) isolating the composition channel. n=4,920 mutation
events per arm.

| arm | COV−CTRL | old-complement drop |
|---|---|---|
| 1M trained | +0.0042 | −0.007 |
| 10M trained | +0.0050 | −0.007 |
| 30M trained | +0.0112 | −0.015 |
| 100M trained | +0.0203 | −0.025 |
| 650M trained | +0.0957 | −0.102 |
| 30M randinit | +0.0001 | — |
| 650M randinit | +0.00004 | — |

Three findings. (i) The co-variation signal is entirely learned: both
randinit arms are ≈0 (≤0.0001), so the net contribution is the full
trained value. (ii) It grows monotonically and super-linearly with
scale — 650M jumps to +0.096, 4.7× the 100M value, with the
old-complement probability dropping symmetrically (−0.102 ≈ −COV),
the signature of genuine complement tracking. (iii) The linear probe
severely under-reads this knowledge: the probe shows +0.03..+0.05
(650M, three sets) while the forward test shows +0.096, because
pairing requires aggregating a distant position, which a single
linear head cannot do. Probe numbers are a lower bound.

Honest restatement of S7: at 2.0B nt, the model DOES encode pairing
co-variation (probability shifts up to 0.1 at 650M), the knowledge is
invisible to linear probes at ≤100M, and the 650M scale crosses into
probe-visible territory (+0.03..+0.05 over the trigram floor,
replicated on three test sets). "Structure emergence" at our budgets
is a forward-pass phenomenon before it is a linear-readout
phenomenon.

**Remote-context readout heads (user-prompted: replace the linear
head with one that can aggregate remote context).** If the linear
ceiling is an aggregation failure, a head with pairwise interaction
should release the forward-pass knowledge. We swap ONLY the readout
head (same layer, same TR0 train set, same TS0 eval, same macro-F1,
same class weighting; head capacity capped, randinit controlled):
pool16 = symmetric ±16-token mean pooling + MLP; attn = single-head
self-attention column over the sequence; attn_symm = attention with
symmetrized (A+A^T)/2 scores, an inductive bias toward pairing
symmetry.

| scale | linear | pool16 | attn | attn_symm | randinit heads |
|---|---|---|---|---|---|
| 30M L3 | 0.612 | **0.641** | 0.630 | 0.629 | 0.590–0.596 |
| 100M L22 | 0.621 | 0.622 | 0.621 | **0.635** | 0.569–0.594 |
| 650M L15 | 0.610 | 0.615 | 0.629 | **0.635** | 0.50/0.58–0.59 |

Findings: (i) head type that wins depends on layer depth —
window-pooling wins at shallow layers (30M L3: +0.029 over linear),
symmetrized attention wins at deep layers (100M L22 and 650M L15:
+0.014..+0.025); (ii) at 650M the attention head reads +0.043 over
the trigram floor vs linear's +0.018 — 2.4x the linear increment,
releasing a substantial fraction of the +0.096 forward-pass
co-variation signal; (iii) on randinit the attention heads also lift
a collapsed deep layer (0.50 → 0.59 at 650M L15), i.e. part of the
attention gain is generic aggregation, but the trained−randinit gap
at the best head (+0.046) exceeds the linear head's own
trigram-relative increment — the representation and the readout
channel co-determine what is measurable; (iv) all heads sit within
0.007 of each other on randinit at 30M/100M, so gains there are not
head capacity. Protocol conclusion: linear probes systematically
under-measure structural knowledge; structure-probing protocols
should include a remote-interaction (attention) readout head by
default, ideally with the pairing-symmetry inductive bias.

**Wall diagnosis and the pair-level probe (v3/v4, user-prompted
"think again").** Three diagnostic arms locate the readout wall
precisely. (a) Partner-Oracle (hand the head the true partner's
state): 0.998-0.9996 at all scales — the representation jointly
encodes pairing at both endpoints. (b) Finetune-top2 (unfreeze last
two layers end-to-end): 0.626/0.637/0.641 — the SAME ~0.64 wall as
every readout head, so the wall is not the head or the training
protocol. (c) Pair-level probe v4 (redefine the task from per-
position classification to candidate-pair scoring: input (h_i, h_j,
|i-j|), output paired?, trained on sampled positive/negative pairs):
pair AUC 0.932 (30M) / 0.938 (100M) — far above the per-position
wall, though top-L pair retrieval remains weak (P@L 0.04-0.05).

Conclusion: the model's pairing knowledge is stored jointly at pair
endpoints, not per-position. Any method that must FIND the partner
(per-position heads, generic interaction heads, even top-2
fine-tuning) hits ~0.64; a method given the candidate pair decodes
it at 0.93+ AUC. The missing component for structure prediction
from general RNA LMs is a pairing SOLVER (a candidate-generation /
matching module, as in contact-map architectures), not more
pretraining. This also reframes "structure emergence": at 2.0B nt
the knowledge exists; what emerges with scale is the front-pass
co-variation strength (Q10: +0.004 → +0.096), while the readout
path determines what is measurable.

**Composition-prior correction for the pair-level probe (self-audit,
same lesson as the GC floor).** The 650M-randinit DP pair-F1 (0.210)
matching the trained value (0.200) exposed a confound: the pair
probe's features (|i-j|, position, endpoint states) allow a strong
distance+composition shortcut. A model-FREE baseline on the same
protocol (features: log|i-j|, positions, one-hot nucleotide
identities at both endpoints, complement indicator) reaches pair
AUC 0.922 — versus 0.932 (30M), 0.938 (100M), 0.952 (650M), 0.881
(RNA-FM L0, BELOW baseline). Net pretraining contribution above the
composition+distance prior: +0.010 (30M), +0.016 (100M), +0.030
(650M), −0.041 (RNA-FM). The parallel with the per-position floor
is exact: composition ladders dominate both task formulations, and
the honest structure signal is the increment above the matched
prior — small, scale-dependent, and largest at 650M, consistent
with the forward co-variation test (+0.096 at 650M) and invisible
in a published 96M model. The DP solver result (pair-F1 0.17-0.20)
is likewise prior-dominated and is NOT claimed as model knowledge;
we report it as the methodological ceiling of prior-only pairing.
Revised statement: general RNA LMs at our budgets encode pairing
knowledge at the pair-endpoint level that is (i) real (+0.03 over
matched composition prior at 650M), (ii) far from sufficient for
structure prediction, and (iii) accessible only through matched-
prior-controlled pair probes or forward co-variation tests, never
through raw per-position or uncontrolled pair probes.

**External-model structure results (user-prompted comparison) and
the parameter-count relation, stated carefully.** Under the same S7
protocol: RNA-FM-96M best 0.587 (embedding layer L0; deep layers
collapse to 0.37), RiNALMo-micro-33M 0.594 (L2), RiNALMo-mega-148M
0.607 (L14), RiNALMo-micro randinit 0.380 (floor-level). Within the
RiNALMo family a MILD parameter-count relation exists (micro→mega
+0.013), and the self-trained net increment also grows with scale
(1M +0.00 → 650M +0.030); both are far smaller than the family-
classification gains at the same scales (+0.33 at 650M) — structure
signal grows slowly with parameters and is suppressed by the
composition floor. Cross-family numbers (RNA-FM vs RiNALMo) are NOT
comparable on a parameter axis (architecture/corpus/training
confounded) — the same混杂 criticism we apply to mixed-model
benchmarks. The 650M forward co-variation (+0.096) remains the only
scale where the structure signal is simultaneously strong across
measures; external-model forward co-variation tests are queued.

**RiNALMo-giga result and the corpus factor (full scan completed
10-01).** The complete RiNALMo family under S7: micro(33M) 0.653
(L11), mega(148M) 0.607 (L14), giga(650M) 0.728 (L32, last layer,
deep-late surge L27→L32 0.678→0.728); every randinit arm flat at
0.380 (L0). Two readings. (i) The parameter relation is NON-monotone
(U-shape): micro > mega, giga recovers only via deep layers. (ii)
The decisive cross-model cell: RiNALMo-giga (650M) 0.728 vs our
RNA-Sc-650M 0.6255 at the SAME parameter count — a +0.10 gap. The
pretraining corpus is the most salient difference (RiNALMo's
structured ncRNA/Rfam corpus vs our 2.0B-nt general corpus), but
architecture and recipe co-vary (RoPE/33x1280/ESM-2-style multi-epoch
on 36M sequences vs ALiBi/28x1408/single-pass 2.0B nt), so the gap
is a JOINT corpus-architecture-recipe effect, with corpus as the
leading suspect (Q18 qualification; within the RiNALMo family the
U-shape and giga deep surge occur under fixed architecture). Within
our controlled family the same parameters moved structure F1 by
+0.03. Testable predictions for the 5.9B full-data arms (if corpus,
not scale, is the lever, 650M@5.9B should gain little structure,
while an Rfam-enriched corpus arm on OUR architecture should gain
much — the orthogonal test that isolates corpus with architecture
held fixed). [Family-F1 update 10-04: the budget×scale sign flip
(§4.1) already shows the corpus lever is real at 300M (+3.76pp).
Structure readout update 10-04: S7 on the same 300M@5.9B final
checkpoint gives pair-position F1 0.6165 (L22, rel 0.957) vs
300M@2B 0.5978 (L22) — a budget gain of +1.87pp that EXCEEDS the
1pp significance bar, with the best layer UNCHANGED (no attrition
migration, unlike the 100M arm's L21→L16 forward shift). So the
Chinchilla-style budget×scale interaction is NOT confined to family
classification: structure readout also eats budget at 300M. The
original prediction ("budget gains are family-classification-only")
is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there).]

Original audit (superseded numbers, kept for provenance):

**Composition-floor audit (user-prompted).** A GC-identity-only rule
(predict paired iff nucleotide in {G, C}) achieves macro-F1 0.576 on
the bpRNA test set — G paired-rate 0.486 / C 0.449 vs A 0.258 / U 0.356,
the Watson-Crick pairing prior. Random-init models score 0.53-0.586 at
every layer because residual pathways preserve nucleotide identity; the
composition floor, not structure, dominates this task. The trained gain
over the floor climbs with scale: 1M -0.047 / 10M -0.010 / 30M -0.000 /
100M +0.013 / 650M +0.021 — a real but tiny structural increment (2.1pp
over 650x scale), crossing the floor only at >=100M. The task has the
same composition shortcut as rna_type leakage (k-mer), and conclusions
are requalified accordingly: S7 measures "structure beyond composition",
not raw structure emergence. P3 (no deep migration of the best layer)
is unaffected: the floor signal is layer-independent.

**Randinit controls (architecture prior, not pretraining).** 
Structure-probe randinit controls: |trained − randinit| ≤ 0.02 at all
six scales (10M: 0.5678 vs 0.5663; 300M/650M arms in fig update). Paired-position linearity comes
from the ALiBi/encoder prior; pretraining contributes ≈0 on this task
at this budget — the mirror image of the family-discrimination gains
(+0.04..+0.17). Four-way convergence (S7 zero-gain, S12 early-layer
high-DI families, S13b not-bell, S14 decoupling): at 2.0B nt, RNA MLM
pretraining transfers family-level sequence statistics; structure
information is largely not yet learned.

**S4.4.9 NucleicBERT-style interpretability battery (10-01).** To test
whether the "information present but not linearly readable" picture
holds under forward, probe-free evidence — and to benchmark the
NucleicBERT (Nat MI 2026) claims on our protocol — we ran a three-battery
zero-supervision suite on NucleicBERT-404M and our RNA-Sc-650M, each with
a random-init control (bpRNA TS0, n=80, len<=128, seed 17):

(i) **MLI coupling** (paper Fig 5 counterpart): I_j->i = logp(x_i|x\i)
- logp(x_i|x\i,x\j), paired positions vs distance-matched control
positions. NucleicBERT: +0.030 vs -0.001, pair-vs-ctrl AUC 0.653;
NB-randinit: exactly 0.0 (the cleanest negative control we have
recorded). Our RNA-Sc-650M: +0.158 vs -0.001, AUC 0.743; its randinit
0.492. Pairwise coupling is REAL, PRESENT IN BOTH CORPORA (ncRNA
NucleicBERT and our general corpus), and STRONGER in our model —
while the linear paired-position probe reads out only ~0.59-0.63 in
both. The readout wall is not a corpus artifact.

(ii) **Attention pair-tracking heads** (paper Fig 4d-f counterpart,
pretraining-only): per (layer, head), attention mass from paired
positions to their partner / to random positions. NucleicBERT
concentrates pair-tracking heads in DEEP layers (L27-H8 ratio 617,
L24-H28 150; band means early/mid/late = 1.5/1.1/3.3); our
RNA-Sc-650M concentrates them in EARLY layers (L6-H0 ratio 16,140,
L5-H1 2,784, L4-H19 460; band means = 104/1.4/1.4). The layer
placement of pair-tracking heads is ARCHITECTURE-DEPENDENT (learned
positional encodings vs ALiBi distance bias) — a novel contrast that
the original paper's fine-tuned analysis does not surface.

(iii) **Saliency at structure boundaries** (paper Fig 4b counterpart):
under zero-supervision teacher-forced gradients, NucleicBERT shows NO
boundary elevation (boundary 0.00049 < interior 0.00055) — the paper's
boundary-peak claim does not replicate without fine-tuning; our 650M
shows a weak boundary elevation (0.000174 vs 0.000166). We report this
battery as the weakest of the three.

Verdict: NucleicBERT's own interpretability evidence (saliency,
attention, MLI) transfers to our protocol partially — its MLI claim
replicates (and is stronger in our model), its boundary-saliency claim
does not replicate zero-shot, and its attention analysis gains a new
architecture contrast. Structure "emergence" in the forward sense
(coupling) is present at both corpora; the linear-readout wall
(~0.59-0.64) is the binding constraint.
**Attribution qualification (corpus vs architecture, 10-02).** The
+0.10 gap at 650M (RiNALMo-giga 0.728 vs ours 0.6255) must NOT be
read as a pure corpus effect: the two models differ in positional
encoding (RoPE vs ALiBi), depth/width ratio (33x1280 vs 28x1408),
training recipes (ZLoss-style ESM-2 recipe vs ours), exposure regime
(36M ncRNA sequences multi-epoch vs 2.0B-nt single pass), and
tokenizer. Three observations bound the confound: (i) within the
RiNALMo family the U-shape and the giga deep-layer surge (L27 0.678
-> L32 0.728) occur under a FIXED architecture, so corpus/exposure
remains the dominant within-family variable; (ii) our own battery
(Q17) shows architecture determines WHERE pair-tracking heads live
(early under ALiBi, deep under learned-PE) — architecture shapes
readability, corpus shapes the learned increment; (iii) the
pre-registered Rfam-enriched corpus arm on OUR architecture is the
orthogonal test: if it reproduces a large structure gain, the corpus
factor is confirmed with architecture held fixed. Until then the
honest statement is: corpus is the leading SUSPECT, not the isolated
cause.


### 4.5 Corpus axis 【Act V · H5】: capacity gates mid-size corpora

**Reweighting chain closed at three scales (10-03).** Cluster-level
flattening of the rRNA-dominant prior (alpha=1.0), same budget/
recipe/protocol: family-split probe F1 10M 0.1746 (L14) vs 0.1731
full (+0.15pp), 30M 0.2408 vs 0.2466 (−0.58pp), 100M 0.2834 vs
0.3263 (−4.29pp) — a cross-scale SIGN FLIP. The 10M increment is
below seed-level std (three-seed spread ≈0.017), so the reading is
"neutral-to-slightly-positive", not a positive effect claim; the
scientific content is the three-point gradient. Mechanism —
capacity-gated prior utility: when capacity is the binding constraint
(10M), flattening a redundant prior frees effective capacity for
underrepresented families; once capacity is sufficient (100M), the
family-frequency distribution itself is learnable signal, and
flattening it removes input the larger model was exploiting. This
intersects the corpus-composition axis (§4.10: large-model gains come
from corpus distribution information) and the capacity gate (§4.3/
§4.8): the same intervention flips sign across the gate. (Protocol
artifact noted: the reweighted corpus parquet ships train-only rows,
so validate() logs 0/0 = best_val 0.0000 on all rw arms — training
health verified by throughput, checkpointing, and probe behavior.)


10M: U-shape (c1Mcs 0.186 > full 0.173 > c5Mcs 0.152). 30M: monotone
(c1M 0.316 global best). Small-corpus multi-epoch wins at both scales;
val-loss rank inverts against transfer F1 (MLM loss and transferability
decouple). Sampling method is not neutral: cluster-stratified sampling
shifts family composition (rRNA 56.4%→61.5%). Saturation analysis: no
classic upward saturation point; both scales peak at the smallest
unique-corpus arm. Family-flattening reweighting (alpha=1.0, 57.7M
effective rows) HURTS family-level transfer: 0.2408 vs 0.2651 raw —
the corpus axis is governed by effective repetition of high-signal
families, not coverage diversity (DenAdel single-cell negative result
replicates cross-domain).

### 4.6 Decoupling families 【Act III · H6】 peak in early layers

Spearman(family decoupling index, best-layer), six scales complete:
−0.478 (30M-c1Mcs) → −0.384 (100M) → −0.339 (300M) → −0.222 (650M) —
monotone decay with scale. High-decoupling families
(structure-conserved, sequence-divergent) peak earlier, but the
effect dilutes as capacity parks family statistics in mid-early
layers — mechanistically tied to the layer-endpoint reversal (4.1).
**Hypothesis M (post-hoc, grade-B evidence).** The reversal is not
deep-layer degradation: the 650M late band holds F1 0.348 vs best 0.3632.
We propose a three-chain account, stated explicitly as a hypothesis
(unlike H1–H8, which were pre-registered): (a) the marginal non-rRNA
gain of depth, (late−mid)/mid, decays with scale (+18% at 30M → +3% at
300M → +2% at 650M) — family features are already extracted by mid
layers; (b) the rRNA channel (56% of corpus) is decodable at ~0.97 F1
at every depth, so larger models fill deep capacity with corpus-
majority tasks earlier (L8); (c) the random-mixing floor rises with
depth (randinit non-rRNA floor 0.023 early → 0.049 late; mommatch
0.029 → 0.062) — deeper stacks mix more random channels, lowering
deep-layer SNR. Net: the best-SNR layer migrates forward as capacity
grows (0.957 at 300M → 0.296 at 650M) — a corpus-supply-limited
capacity reallocation, not a depth pathology.

**P5 (TESTED 09-27, zero-supervision shuffle separation).**
MLM likelihood separation (native minus position-shuffled, nats/token,
same mask positions, family_test): rRNA 0.47 (1M) -> 1.07 (30M) -> 1.12
(650M) — a strict post-30M plateau; non-rRNA 0.05 -> 0.31 (monotone);
randinit control 0.002 (structure required). Verdict: P5a partially
confirmed — the corpus-majority channel saturates by 30M while
family-sequence statistics keep deepening, adding a third independent
30M phenomenon (with the Delta-law plateau and the RNS plateau). P5b
REFUTED: the rRNA-over-non-rRNA gap NARROWS (0.94 -> 0.81) rather than
widens — chain (b) must be refined: rRNA-channel occupation completes
by 30M; the capacity 650M reallocates to deeper layers carries finer
long-range sequence constraints, not more rRNA statistics. We report
this boundary honestly.

Falsifiable predictions (discriminating experiments): **P1 (CONFIRMED,
09-27)** de-rRNA stratified probe (18 classes, rRNA excluded from
train/eval): 100M best L16 (rel 0.73) / 300M L18 (0.78) / 650M L27
(rel 1.00, F1 0.4585 — monotone above 300M 0.4026 and 100M 0.3192).
With the rRNA class removed, the 650M reversal disappears entirely and
the best layer returns to the deepest position — chain (b) is
intervention-grade confirmed (B → A−), and family features are intact
in deep layers (0.4585 is the highest de-rRNA F1 at any scale). **P2** 650M@5.9B (3× corpus, training) — the
marginal depth gain should partially recover; if (late−mid)/mid stays
≤2%, chain (a) is weakened. **P3 (650M done, 300M rerunning)** structure-pairing
probes — best-layer trajectory across scales 0.765 (1M) / 0.316 (10M) /
0.273 (30M) / 1.000 (100M) / 0.556 (650M, L15, F1 0.597): no monotone
deep migration, and structure F1 grows only +6.8pp over 650x scale —
consistent with P3 (structure tasks do not participate in the
corpus-occupancy mechanism); the 100M endpoint is a non-monotone
outlier, not a trend. **P4 (TESTED, partially refuted)** quantitative
leave-one-out extrapolation: a linear map from de-rRNA best-layer
position to full-class position has LOO error 0.305 (acceptable only
for 100M-650M: 0.10-0.26); a capacity-shift model fails outright (LOO
0.745, errors >1.0 at both 10M and 650M). The capacity-to-layer
mapping is therefore NOT a simple monotone function: the 10M valley
(attrition regime) and the 650M reversal are regime transitions, not
points on a line. Honest verdict: hypothesis M survives qualitatively
(P1 intervention confirms chain b; P3 consistent), but its quantitative
form is refuted — the corpus-capacity interaction is nonlinear, which
we report as a boundary of the current account.

### 4.7 Protocol × split × scale 【Act IV · leakage】: the leakage attribution triangle

Δ(random − family) under balanced probes grows with scale and
saturates and closes at six scales: +0.055 (1M) → +0.337 (10M) → +0.438 (30M) → +0.434 (100M) → +0.416 (300M) → +0.436 (650M); a strict post-30M plateau (random-split 650M 0.625 vs 30M 0.605, within +2pp);
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

### 4.8 Representation quality saturates 【Act IV · H8】 before downstream F1 (RNS)

RNS@10: 1M 0.172 → 10M 0.104 → 30M 0.078 → 100M 0.077 → 300M 0.067
→ 650M 0.062 (scale-axis endpoints from s14_rns.json; 300M/650M from
the one-by-one re-runs s14_rns_{300m,650m}.json), against randinit
0.54–0.58. Representation organization improves and plateaus at 30M
while downstream F1 keeps rising 30M→100M. Time axis: at 10M RNS peaks
at 1.0B while transfer F1 peaks at 0.5B; at 300M/650M RNS declines
monotonically through training (no mid-training peak) — the 10M
peak-then-drop is a capacity-insufficiency phenomenon, parallel to the
F1 attrition valley: the capacity gate is the common root of both.
(Fig 5c.)

**Protocol note (vs Prabakaran & Bromberg).** We use k ∈ {10, 50, 100}
(pools of 4,500 random / 1,500 real make k=1000 geometrically
uninformative) and a single full-pool computation instead of 100
subsampled repeats; a 10× random-pool regeneration bootstrap gives
std ≤ 0.005 at every scale (1M 0.2247±0.0049, 30M 0.0934±0.0037,
100M 0.0949±0.0041) — 26× smaller than the 1M→30M scale gap, so
single-run conclusions stand (s14_rns_bootstrap.json).

**Cross-model RNS (10-02).** On the same pools, published models
split sharply: RiNALMo micro/mega/giga reach RNS 0.026/0.017/0.015 —
below our entire controlled family (≥0.09), consistent with the
ncRNA-focused corpus advantage (§4.10) — while RNA-FM-96M at 0.693
is worse than our random-initialized controls (0.54–0.58). Across 8
models (ours ×4, RiNALMo ×3, RNA-FM), Spearman(RNS@10, random-split
family F1) = −0.60 (Pearson −0.84; excluding the RNA-FM outlier
−0.39): at the model level RNS predicts random-split performance in
the direction reported for proteins (their RNS–TM-score −0.70), but
at the family level within one model the relation is weak (−0.19)
and at the sequence level it is axis-dependent (below) — RNS is a
model-level reliability indicator, not a sequence-level one.
(Fig 7.)

**RNS-binned structure evaluation (axis-dependence).** Binning TS0
sequences into RNS terciles (same head, same layer): pair-F1
low/mid/high = 0.4005/0.5011/0.4727 and long-range (≥24) F1 =
0.5735/0.7430/0.7414 — the high-RNS bin is +18%/+29% vs the low bin,
the OPPOSITE direction of the protein finding (−40%/−60%). A length
confound is excluded (Spearman(length, RNS) = +0.19 points the wrong
way; s14_bin_diag.json). Two candidate mechanisms: (i) the composition
channel — high-RNS sequences are longer ncRNAs with stronger stem-GC
statistics, and at 100M the structure readout is composition-dominated
(§4.4); (ii) in the RNA domain high RNS marks "long and common"
rather than "difficult". The family axis does NOT invert
(sRNA/snoRNA: high RNS with probe F1 ≈ 0, the protein direction):
which covarying axis dominates decides the sign — a methodological
caution for using RNS as a per-sequence uncertainty proxy.
Additionally, family-level RNS is uncorrelated with masked-marginal
NLL (Spearman +0.14, Pearson −0.02): representation geometry,
likelihood confidence, and downstream utility form a three-way
decoupling (s14_rns_cov.json).

### 4.9 Structure-version confidence 【Act III · H7】 curve: pre-registered negative

Family-level NLL vs structure-F1: quadratic peak lies outside the data
NLL range (peak x=1.745 vs data 1.34–1.38); CI [−0.296, −0.050].
NOT-BELL under the pre-registered criterion: RNA-corpus models do not
reach the over-confidence region within this budget/corpus scale —
Hou's protein precondition is unmet here. v2 (with 650M: 36 family
points, NLL range widened to 1.03-1.37): still NOT-BELL - the
negative result is robust to the widened confidence coverage.

### 4.10 External replication 【Act V · cross-family】: corpus composition > parameters

Same pooled probe, family split. RiNALMo micro 36M / mega 148M / giga
650M (ncRNA-focused corpus): 0.2407 (L8) / 0.2532 (L25) / 0.2667 (L27)
— 18× parameters gain +2.6pp (log-flat). RNA-FM 96M (general
transcriptome): 0.1335 at the embedding layer, monotonic decline —
a corpus contrast at smaller parameters gains +11pp. Layer-migration
holds cross-architecture (best rel 0.73/0.86/0.84). De-rRNA
stratification preserves all layer shapes. (Fig: corpus vs params.)

### 4.11 Length and data regimes 【Act IV/V · regimes】

Short sequences (16–127nt) collapse at all scales (0.02–0.06); 512+
bin scale-differentiates (30M 0.116 / 100M 0.106 / 300M 0.123 / 650M
0.169 vs 1M/10M ≈0.05) — the long-sequence bin is the only one where
650M extends beyond the 30M plateau, consistent with the capacity-
redistribution account of the layer reversal; scale gains concentrate
on long sequences. In the low-data regime
(10²/10³/10⁴ family-split samples), linear-probe curves are flat
(<5pp per 100× samples) at all scales, while full fine-tuning
rises: at 10² samples full-FT reaches 0.059/0.064/0.095
(10M/100M/650M) and at 10⁴ reaches 0.131/0.136/0.156 — the
650M tier holds the largest low-data advantage (0.095 vs 0.059
at 10²), and the low-data bottleneck is probe-head capacity,
not representation (evidence/t126_fullft.json,
evidence/t126_lowdata.json).

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
The 10M valley is robust at the three-seed mean level (2/3 seeds negative), duration-driven (subsampled-
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

### 5.1 What causes the three 30M plateaus? (added 09-27)

Three channels plateau together at 30M under the 2.0B-nt budget: the
leakage dividend (Delta), representation organisation (RNS), and the
rRNA shuffle separation (P5). We test three candidate causes against
existing intervention evidence. **Data quantity is excluded**: the S3
corpus axis shows SMALLER unique corpora beat the full 14.1B-unique
corpus at both 10M and 30M (c1M 0.316 vs full 0.247 at 30M), and 30M
sits at 67 tokens/param — 3.3x above the Chinchilla optimum, so tokens
are not the binding constraint. **A finite task-information channel is
the leading explanation**: a zero-capacity k-mer baseline already
reaches 0.518 random-split F1 (86% of the ~0.60 ceiling); twenty-fold
capacity growth (30M -> 650M) moves neither the Delta plateau
(0.605 -> 0.625) nor the rRNA separation (+5%) — the channel is capped
by task structure (19-class family overlap with rRNA at 63.6% of
corpus), not by model capacity or data volume. **A capacity gate
complements it**: 30M is the smallest config that absorbs the full
channel (10M sits below it, producing the attrition valley). The
decisive intervention is pre-registered: 30M@5.9B (tokens x3, unique
sequence exposure 0.14 -> 0.42 epoch, queued) — if all three plateaus
persist unchanged, the data-quantity explanation is finally excluded
and the finite-channel account closes; if any plateau moves, data
quantity re-enters.

## 6. Limitations

- Story-1 leakage residue (red-team B3): the control-excluded gain
  (+0.17 at 100M) is defined against random-init and moment-matched
  controls, which do not read sequence composition; k-mer logistic
  (0.163) and LightGBM (0.176) sit within ±0.01 of the 100M
  family-split LM (0.170), so "real, weight-structured signal" and
  composition reading are not separable by our controls — the
  beyond-composition margin is +0.007 (negative vs LightGBM).
- Architecture scope: the ladder is a single encoder recipe (width/
  depth scaling only); architecture×scale interactions are untested
  (RiNALMo-arch axis Q5 remains open), so scale claims are
  within-family by construction.
- Corpus-axis epoch-coverage differences are explicit (red-team A);
  saturation comparisons only within matched coverage.
- Seed imbalance: 3 seeds at 30M/100M, single seed elsewhere; 650M
  single seed (pre-registered).
- rRNA 56.4% corpus bias: every headline claim re-verified under
  de-rRNA stratification (all survive; absolute F1 shrinks ≈25%).
- Pooled day-1 probe protocol (upgrade to per-task protocol matrix
  planned); mean-pool axes are reported as relative conclusions only.
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
