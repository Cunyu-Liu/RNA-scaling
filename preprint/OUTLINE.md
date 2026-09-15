# Preprint skeleton v0.1 (2026-09-16, generated from verified evidence)

Working title: "Scale-dependent feature attrition in a controlled RNA
language-model family: pretraining dynamics, layer migration, and the
limits of cross-family transfer"

## Status: skeleton — every number below is evidence-linked; NO unverified
claims. Sections marked [PENDING] await runs in flight.

## 1. Abstract (draft after S1 3-seed + corpus 3-point complete)

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
- 1M 0.1517 / 10M 0.1725 / 30M [PENDING s17 mid-train] / 100M
  0.3440±0.0125 (n=2, s29 in flight)
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
### 4.4 Corpus axis (diversity + 3-point curve) [PENDING 10M c5Mcs/c1Mcs]
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
