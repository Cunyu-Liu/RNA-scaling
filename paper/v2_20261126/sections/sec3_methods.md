# 3. Methods

This section defines the controlled design and reporting calibers used to answer Q1–Q6. The decisive design is a six-scale, iso-token RNA-Sc family evaluated under cluster-isolated and random splits, with matched probing, initialization controls, and corpus and budget interventions. The central methodological observation is that split, readout protocol, seed coverage, and checkpoint selection can change an apparent effect, so these factors are fixed before interpreting scale.

## 3.1 Controlled model family and pretraining

We use standard bidirectional Transformer masked-language-model (MLM) encoders with ALiBi relative-position biases and a tied embedding/output head; no architectural component is introduced as a contribution. The six nominal parameter tiers span three orders of magnitude while retaining the same model class and training rule.

| Nominal tier | Hidden width | Transformer layers |
|---|---:|---:|
| 1M | 64 | 18 |
| 10M | 192 | 20 |
| 30M | 480 | 12 |
| 100M | 576 | 23 |
| 300M | 1024 | 24 |
| 650M | 1408 | 28 |

Sequences are tokenized as single nucleotides over ACGU. Pretraining uses a 1024-nt context and MLM masking of 15% of positions, with the standard 80/10/10 replacement rule. Every main-line run receives the same 2.0B valid-nucleotide exposure (the iso-token budget), with the optimizer and schedule rule held fixed across scales; exposure, rather than epoch count, is the controlled unit.

The main corpus is the non-coding RNA subset of RNAcentral release 22, comprising 29,012,227 sequences grouped into 3,357,201 MMseqs2 80-80 clusters. Three corpus interventions retain the same architecture and iso-token recipe. The **rinalmocorpus** arm reproduces the published corpus-construction recipe—source aggregation, length filtering, deduplication, clustering, and removal of held-out canonical overlaps—at 30M, 100M, and 300M; because the original sequence manifest is unavailable, it is a recipe replica rather than an exact sequence-set reproduction. The **rfamcap** arm retains Rfam-annotated training rows and caps each family at 4,000 sequences, providing an Rfam-enriched contrast at 30M and 100M. The **rw1** arm flattens the sampling prior over family frequencies at 10M, 30M, and 100M, changing the sampling distribution rather than the model or evaluation set. A separate budget intervention repeats the 30M, 100M, 300M, and 650M runs at 5.9B nt without changing architecture, tokenizer, or probe task.

## 3.2 Family-level isolation and the two-world evaluation

The S0 split assigns whole MMseqs2 clusters to training, family-validation, and family-test partitions. Deep verification found zero clusters and zero exact sequences spanning these partitions; family-test clusters are therefore absent from pretraining. This is the isolation statement for the self-trained family, not a claim about the undisclosed pretraining data of external models.

The **family world** trains probes on family-validation sequences and evaluates them on family-test sequences. The **random world** draws both probe partitions from the same pretraining-held-out family-validation pool, assigning every fifth row to evaluation and the remaining rows to probe training; family overlap is thus allowed by construction, but neither side was seen during MLM pretraining. We report \(\Delta_{\mathrm{split}}=F1_{\mathrm{random}}-F1_{\mathrm{family}}\) only within the same model and readout protocol.

Each world is crossed with two classification readouts. The **mean-pool** protocol averages non-padding token states within each sequence and fits a linear head. The **balanced** protocol uses the same pooled representations but fits a class-weighted linear head with deterministic ordering. Balanced and mean-pool scores, and their respective \(\Delta_{\mathrm{split}}\) values, are separate protocol cells and are never substituted for one another.

## 3.3 Downstream probes and non-interchangeable structure metrics

For family-world RNA-type classification, each layer is probed on 20,000 training and 4,000 evaluation sequences, and performance is macro-F1 over 19 classes. Unless a retest protocol is explicitly named, headline values use the terminal pretraining checkpoint and the best layer under the specified protocol; cross-layer maxima are never pooled across checkpoints or readout protocols.

The secondary-structure classification task is distinct from contact prediction. On bpRNA TR0/TS0, a per-position linear probe predicts whether each nucleotide participates in a base pair. For the new rfamcap structure rerun, the legacy `probe_structure` field `f1` is paired-positive-class F1 (paired-F1), not a two-class macro average; true macro-F1 is recomputed separately as the unweighted mean of paired and unpaired class F1 and stored as `f1_macro`. The rfamcap structure contrasts below therefore use paired-F1, while true macro-F1 is retained as a separate sensitivity metric and is never substituted for it. The contact probe instead combines paired hidden-state features with average-product correction and reports top-L precision for long-range pairs separated by at least 24 nt. Paired-position F1 metrics and contact top-L precision answer different questions, and neither alternate matching tolerances nor one metric's values are used to interpret the other.

## 3.4 Controls and comparison boundaries

Two initialization controls are evaluated at every scale with the same probe pipeline. **Randinit** replaces the trained encoder with an untrained encoder of identical architecture. **Mommatch** reinitializes that architecture and then matches the mean and variance of each eligible tensor to the corresponding trained tensor, testing whether marginal weight statistics alone reproduce transfer. Classical comparisons comprise k-mer features of orders 1–6 with logistic regression or LightGBM, a directly supervised one-hot CNN, and a random-embedding readout. External model rows, where shown, are observational anchors only and do not enter controlled corpus, budget, or architecture contrasts.

## 3.5 Statistical plan and seed coverage

The scale-continuation rule was frozen before training 650M: compute the 30M-to-100M change in family-split macro-F1 per log10 parameter decade and compare it with \(\varepsilon=0.03\). Bootstrap 95% intervals are used for the slope decision, with the resampling unit stated wherever intervals are reported. A sequence bootstrap quantifies evaluation-sample resampling only; it is not a training-seed replicate.

Training seeds s17, s29, and s43 are available at 1M, 10M, 30M, and 100M. The 300M and 650M tiers contain only training seed s17 and are explicitly presented as single-seed results, without fabricated error bars. Probe seeds, training seeds, and sequence resamples are reported as different replication units throughout.

## 3.6 P0 reporting adjudications

Five reporting decisions are fixed for all subsequent results. **Standard deviation.** Every multi-seed summary is mean ± sample standard deviation with ddof=1; scale-family summaries use three training seeds, and no population SD or standard error is silently substituted. **650M at 5.9B nt.** The factorial main table retains only the original terminal protocol—20,000/4,000 sequences, a full-layer scan, and probe seed 17—under which the single-seed E1 budget effect is +1.15 pp (0.3747 versus 0.3632). The separate deep-window 8,000/4,000 retest with probe seeds 29, 43, and 61 on the same s17 weights is demoted to an unreviewed handover-record citation in Appendix A: its summary values lack raw-ledger rows, the original split needed for adjudication is unrecoverable, and P2.5 consolidation is not performed. It therefore supplies neither a current 650M-over-300M claim nor readout-stability evidence. No cross-protocol difference is used as a budget-effect headline. **Classical baselines.** The primary observed-baseline contrast is mean-pool LM minus LightGBM s17, with LightGBM available only at s17 and therefore not a three-seed-versus-three-seed comparison. At the three-seed scales, a separate strict seed-coverage column uses the three-seed one-hot CNN mean, while balanced-probe s17 contrasts are retained as protocol-sensitivity analyses. **Rfamcap.** The main family contrast uses iso-budget terminal checkpoints for both arms (1.9B logged nt, s17 against s17), giving +4.14 pp at 30M and +0.34 pp at 100M; the 0.2B checkpoint is reserved for appendix trajectories and is never compared with a terminal-budget control. The rfamcap structure contrasts use the same terminal-budget rule and paired-F1; the historical checkpoint-unresolved estimate is withdrawn rather than retained as pending. **Structure noise floor.** Approximately 1 pp is a repeat-noise reference only for trained-minus-randinit learning increments in the structure probe, not a universal significance threshold and not a threshold for budget differences.

These controls make the following scale–saturation analysis a within-protocol comparison and lead directly to Q1: what does increasing parameter count buy under family-level generalization? They do not establish training-seed robustness at 300M or 650M, turn probe-seed repetition into independent pretraining replication, separate every composition-based shortcut from learned weight structure, or license causal comparisons with external models.
