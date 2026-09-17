# Preprint skeleton v0.3 (2026-09-17, corpus-axis two-scale + attrition attribution + probe determinism)

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
30M+ scale (randinit exclusion: gain +0.04 -> +0.21 across scales),
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
composition (rRNA 56.4% -> 61.5%). Pre-registered slope analysis
(0.107 F1/decade, CI [0.088, 0.131]) triggers a 650M continuation.
Results argue for scale- and corpus-aware interpretation of RNA LM
benchmarks.

## 2. Introduction
- Motivation: RNA LM transfer gap (RiNALMo/RNA-FM era results vs small
  RNAGym gaps); controlled-scaling studies absent in RNA domain
- Contribution list (4): (a) S1 scaling family 1M-100M with family-level
  eval; (b) layer-migration law (best rel_depth 0.05→0.86 with scale);
  (c) S6 feature-attrition discovery (10M non-monotonic); (d) corpus
  axis: sampling-method composition shift + diversity metrics

## 3. Methods
- Corpus: release22_split_8080, 29,012,227 seqs / 3,357,201 clusters
  [evidence/split8080_deep_verify.json]
- Models: ALiBi MLM encoder, 1M/10M/30M/100M, 2.0B nt budget, seed 17/29/43
- Probe protocol: day-1 pooled probe, 20k/4k family_validation→family_test
  [eval/probe_results.jsonl]
- Diversity metrics: Shannon/GS/Vendi(RBF) [evidence/corpus_diversity.md,
  corpus_vendi.json]

## 4. Results
### 4.1 S1 scaling (Table 1 = s1_seed_table; Fig 1 = fig1_layer_migration)
- 1M 0.1517 / 10M 0.1725 / 30M [PENDING 3-seed in flight] / 100M
  0.3396±0.0117 (n=3, FINAL)
- Seed spread: 100M ±0.0125 vs 30M-c1Mcs ±0.0341 (small-corpus +
  cluster-sampling inflates variance)
### 4.2 S4 exclusion (Table = s4_randinit_table)
- Trained-randinit: 1M +0.05 / 10M +0.04 / 30M +0.16 / 100M +0.21
  [evidence/s4_randinit_table.md]
### 4.3 S6 emergence timeline (Fig = fig_s6_cross_scale)
- Four-scale four-dynamics; 10M attrition unique: peak 0.2497@0.5B →
  0.1741@1.9B, best-layer late→early [evidence/s6_timeline.json,
  s6_cross_scale.json]
- 30M weak attrition hint (late band -0.013 0.7B→0.9B) dwarfed by rise
### 4.4 Corpus axis: c1Mcs F1=0.1878 (best L9 middle) vs full 0.1725
  (best L1 early) — small-corpus multi-epoch wins at same params
  [PENDING c5Mcs ~1.5h]
- Composition shift: prefix arms keep full-56.4% rRNA; cs arms 59-61.5%
  [evidence/corpus_diversity.md]
- Vendi: full 9.53 > c10M 9.47 ≈ c5Mcs 9.48 > c1M 9.19 > c1Mcs 8.96
### 4.5 S12 decoupling (30M-c1Mcs, n=10 fams)
- Spearman(DI, best-layer) = -0.64 [evidence/s12_linkage.json]
  [PENDING: full-127-family rerun on 100M]
### 4.6 S5 moment-matched control [PENDING T2.2.2]

## 5. Discussion
- Attrition-capacity account; rRNA-bias causal chain (per-class
  decomposition); sampling method ≠ neutral (methods section)
- Comparison to BERT probe mid-training peak literature [PENDING refs]

## 6. Limitations
- Day-1 pooled probe protocol (upgrade planned T1.2.2)
- Seed imbalance (100M n=2→3; 30M full n=1→3 in flight)
- rRNA 56.4% corpus bias; epoch-coverage differences on corpus axis
  (red-team A)
- Attrition shown for rna_type task only [PENDING structure task]

## 7. Repro
- Cunyu-Liu/RNA-scaling; ledger + manifest + probe jsonl; all commits
  f9abf37..7a8dcd4
