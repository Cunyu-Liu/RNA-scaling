# Preprint skeleton v0.4 (2026-09-19, deterministic-protocol closeout: S4/S5/S6/S12/c1Mcs all inc12; slope final)

Working title: "Scale-dependent feature attrition in a controlled RNA
language-model family: pretraining dynamics, layer migration, and the
limits of cross-family transfer"

## Status: skeleton — every number below is evidence-linked; NO unverified
claims. Sections marked [PENDING] await runs in flight.

## 1. Abstract (v0.2 draft)

RNA language models promise cross-family transfer, but the scaling
behavior of this transfer is poorly characterized in a domain where
corpora are dominated by a few abundant families (rRNA 56%). We train
a controlled family of MLM encoders (1M-100M params, identical
recipe, 2.0B nt budget, family-level evaluation on RNAcentral
release22) and find: (1) transfer capability grows superlinearly at
30M+ scale (deterministic randinit/moment-matched exclusion: gain
+0.04 -> +0.17, weight statistics account for none of it),
with best-layer depth migrating from early to late layers (rel 0.05
-> 0.86); (2) pretraining-time probe trajectories are non-monotonic
at 10M - cross-family features peak mid-training (0.25 F1 at 0.5B nt)
then attrit to a 0.17 plateau while the dominant-family channel
sharpens (rRNA F1 0.96 -> 0.98, others -> 0) - a scale-specific
erosion we link to corpus bias; (3) the corpus axis is scale-dependent: at 10M it is
U-shaped (mid-corpus collapse), at 30M monotonic - capacity governs
whether mid-size corpora remain viable; small-corpus multi-epoch wins
at both scales, and val-loss rank inverts against transfer F1 - MLM
loss and transferability decouple;
(4) cluster-stratified sampling is not neutral: it shifts family
composition (rRNA 56.4% -> 61.5%); (5) with all scales at 3 seeds, the 10M mean falls
below 1M — the attrition 'valley' is systematic; the random-vs-family
split gap GROWS monotonically with scale (balanced probe DELTA
+0.055 -> +0.434 from 1M to 100M) and k-mer composition baselines reproduce it
(own DELTA +0.355): leakage is a property of the split protocol, not
the model — and under family-level evaluation the LM advantage over a
classical composition baseline collapses to ~zero (+0.007 at 100M). Pre-registered slope analysis
(0.142 F1/decade, bootstrap CI [0.104, 0.180]; 30M/100M each 3
seeds) triggers a 650M continuation (in training).
Results argue for scale- and corpus-aware interpretation of RNA LM
benchmarks.

## 2. Introduction
- Motivation: RNA LM transfer gap (RiNALMo/RNA-FM era results vs small
  RNAGym gaps); controlled-scaling studies absent in RNA domain
- Contribution list (4): (a) S1 scaling family 1M-100M with family-level
  eval; (b) layer-migration law (best rel_depth 0.05→0.86 with scale);
  (c) S6 feature-attrition discovery (10M non-monotonic); (d) corpus
  axis: sampling-method composition shift + diversity metrics;
  (e) DELTA scale law + classical-baseline collapse (protocol x split
  x scale interaction)

## 3. Methods
- Corpus: release22_split_8080, 29,012,227 seqs / 3,357,201 clusters
  [evidence/split8080_deep_verify.json]
- Models: ALiBi MLM encoder, 1M/10M/30M/100M, 2.0B nt budget, seed 17/29/43
- Probe protocol: day-1 pooled probe, 20k/4k family_validation→family_test
  [eval/probe_results.jsonl]
- Diversity metrics: Shannon/GS/Vendi(RBF) [evidence/corpus_diversity.md,
  corpus_vendi.json]

## 4. Results
### 4.1 S1 scaling (ALL-SCALE 3-SEED, inc12 deterministic, 2026-09-20)
- 1M 0.1650±0.0131 / 10M 0.1535±0.0173 / 30M 0.2651±0.0162 /
  100M 0.3394±0.0147 (all n=3, FINAL) [evidence/s1_seed_table.json]
- **10M valley**: under 3 seeds the 10M mean falls BELOW 1M
  (-0.0115): the mid-training peak (0.2549@0.5B) attrits to
  below-1M level by 2.0B — attrition is systematic (all 3 seeds),
  not seed noise; the 1M->10M segment is NEGATIVE growth
- Slope decision reads 30M->100M only (pre-registered):
  0.142 CI [0.104, 0.180] -> 650M triggered (in training, ~35%)
  [evidence/s1_slope_decision.json]
### 4.2 S4 exclusion (Table = s4_randinit_table)
- Trained-randinit (inc12, FINAL): 1M +0.0593 / 10M +0.0430 /
  30M +0.1221 / 100M +0.1686; monotone in scale
  [evidence/s4_randinit_table.md, rna_sc/s4_randinit_table.py]
### 4.3 S6 emergence timeline (Fig = fig_s6_cross_scale)
- Four-scale four-dynamics; 10M attrition unique (inc12 FINAL):
  peak 0.2549@0.5B → 0.1731@1.9B plateau, best-layer late→early;
  attrition is duration-driven, NOT corpus-repetition: c1Mcs
  (2.2-epoch) timeline reproduces it (peak 0.244@0.5B → 0.204@0.7B,
  layer downshift L16→L6) [evidence/s6_timeline.json,
  s6_cross_scale.json, v0.4 c1Mcs rerun 2026-09-19]
- 30M weak attrition hint (late band -0.013 0.7B→0.9B) dwarfed by rise
- **Attrition is task-specific (S7 bpRNA structure probe, 2026-09-20)**:
  paired-position F1 1M 0.553 / 10M 0.568 / 30M 0.576 / 100M 0.589
  — NO 10M layer-collapse on the structure task (best layers
  mid-early, no L16->L1 downshift): attrition erodes family-
  discrimination features, NOT structure features
  [eval/probe_structure_results.jsonl, evidence/s7_structure_probe.json]
- **Pretraining gain ~ ZERO on the structure task (CONTROL)**: 10M
  randinit 0.5678 vs trained 0.5663 — paired-position linearity comes
  from the architecture prior (ALiBi positional geometry), not
  pretraining; CONTRAST with rna_type gains +0.04..+0.17 (S4).
  Four-way convergence: S7 zero-gain + S12 high-DI-early-layer +
  S13b not-bell + S14 rep/downstream decoupling -> at the 2.0B-nt
  budget, RNA MLM pretraining transfers family-level sequence
  statistics; structure information is largely NOT yet learned
- **De-rRNA robustness (red-team E, 2026-09-21)**: recomputing
  macro-F1 over non-rRNA classes only — the scale trend, the 10M
  valley (sharper: 0.062 < 0.074), and the layer-migration direction
  ALL survive; absolute F1 shrinks ~25% (rRNA carries most absolute
  performance) but every structural conclusion is independently
  supported by non-rRNA families [evidence/derRNA_stratified.json]
### 4.4 Corpus axis (FINAL, inc12): c1Mcs 0.1862 (best L9) vs
  c5Mcs 0.1519 vs full 0.1731 (best L1) — 10M U-shape; 30M four-arm
  monotone-fall c1M 0.316 global best; saturation analysis: no classic
  upward saturation, both scales peak at smallest unique-corpus arm
  [evidence/corpus3.json, corpus_saturation.json]
- Composition shift: prefix arms keep full-56.4% rRNA; cs arms 59-61.5%
  [evidence/corpus_diversity.md]
- Vendi: full 9.53 > c10M 9.47 ≈ c5Mcs 9.48 > c1M 9.19 > c1Mcs 8.96
### 4.5 S12 decoupling (30M-c1Mcs, n=10 fams)
- Spearman(DI, best-layer), inc12 FINAL: 30M-c1Mcs -0.478 /
  100M -0.384 / 30M-s29 -0.370 (n=10 types; high-DI families peak
  EARLIER; association weakens with scale)
  [evidence/s12_linkage_30M_s17_c1Mcs.json, s12_linkage_100M_s17.json]
### 4.6 S5 moment-matched control (FINAL, inc12)
- Trained-mommatch: 1M +0.0286 / 10M +0.0478 / 30M +0.1233 /
  100M +0.1668; mommatch ~ randinit level (0.12-0.16) — weight
  statistics explain NONE of the transfer gain; H2+H3 both excluded
  [evidence/s5_mommatch_table.md]

### 4.7 Protocol x split x scale: DELTA law + classical baselines (NEW 2026-09-19)
- eval_matrix v1 (16 cells, flock ledger): DELTA(random-family) rises
  monotonically with scale (balanced +0.055/+0.337/+0.438/+0.434);
  meanpool DELTA ~ 0 (10M) / negative (1M) - protocol choice
  systematically masks or amplifies leakage
  [evidence/eval_matrix_v1_delta.json, figs/fig_eval_matrix_delta.png]
- k-mer(1-6)+balanced logistic: family 0.1630 vs LM family 0.098/
  0.156/0.168/0.170 — pretraining gain over composition baseline ~ 0
  (Liangzhu NatCommun 2025 reproduces in a CONTROLLED RNA family);
  k-mer own random 0.5180 (DELTA +0.355): composition statistics alone
  eat the leakage — "bigger is better" under random splits is largely
  family-similarity leakage, and it is a protocol property
  [evidence/classical_baselines.json]
- Narrative three-parter: S4/S5 show the trained weight STRUCTURE is
  real (randinit/moment-matched excluded), but under family-level
  generalization that structure does not yet beat composition stats
  on rna_type; random-split "gains" are protocol artifacts
- S4xS9 attribution triangle (controls on both splits): randinit/
  mommatch capture only 11-18% of the trained random-split dividend
  (10M +0.038/+0.041 vs +0.337; 100M-randinit +0.080 vs +0.434, RISING
  with scale) while k-mer captures 105% — the leakage signal lives at
  sequence-composition level; pretraining's contribution is learning
  to READ it (signal x reader x protocol decomposition)
  [evidence/s4x9_leakage_attribution.json]

### 4.8 S14 RNS representation-quality (H8 first evidence, 2026-09-20)
- Control set three-checks pass (KS p=1.0, mono dev 0.0006, 3x);
  RNS@10: 1M 0.172 / 10M 0.104 / 30M 0.078 / 100M 0.077 vs
  randinit 0.54-0.58 [evidence/s14_rns.json]
- **Decoupling**: representation organization (RNS) saturates at 30M
  while downstream F1 keeps rising 30M->100M — embedding-neighborhood
  quality is NOT downstream usefulness (E14 direction; Prabakaran
  cross-domain validation)

### 4.9 S13b structure-version bell curve (H7 main test, 2026-09-20)
- PRE-REGISTERED NEGATIVE RESULT: NOT-BELL (E13b-b path) — quadratic
  peak x=1.745 outside the data NLL range (1.34-1.38): RNA-corpus
  models never reach the over-confidence region; Hou's protein-domain
  precondition is unmet at this corpus scale
- 30 family points (5 models x 6 bpRNA sources); CI [-0.296, -0.050]
  (family confounding: tmRNA low-NLL low-F1)
  [evidence/s13b_bell.json] — v2 re-test when 650M widens the
  confidence axis; limitation: corpus-scale constraint on confidence

## 5. Discussion
- Attrition-capacity account; rRNA-bias causal chain (per-class
  decomposition); sampling method ≠ neutral (methods section)
- Comparison to BERT probe mid-training peak literature [PENDING refs]

## 6. Limitations
- Day-1 pooled probe protocol (upgrade planned T1.2.2)
- Seed imbalance (1M/10M single-seed; 30M/100M 3-seed complete)
- rRNA 56.4% corpus bias; epoch-coverage differences on corpus axis
  (red-team A)
- (RESOLVED 2026-09-20) Attrition task-specificity: structure task
  shows NO 10M collapse — attrition is family-discrimination-specific
  (4.3)

## 7. Repro
- Cunyu-Liu/RNA-scaling; ledger + manifest + probe jsonl; all commits
  f9abf37..b228809
