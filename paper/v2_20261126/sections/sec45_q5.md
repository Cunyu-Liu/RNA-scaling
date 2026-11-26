### 4.5 Is structural knowledge absent or inaccessible? Pairing is learned, but partner finding is the bottleneck

The layer relocation in Section 4.4 leaves open whether the small structural-probe increments reflect missing pairing knowledge or a readout failure. The decisive experiments form a five-stage chain: GC and trigram composition floors, probe-free covariation mutations, same-layer readout replacement, a Partner-Oracle, and candidate-pair probes evaluated against a matched composition-and-distance prior. Together they show small but genuine pretraining-derived pairing signal whose measured magnitude depends sharply on the readout channel.

**Composition floors calibrate the linear-probe result.** The S7 task predicts paired positions, so its macro-F1 must first be compared with sequence-composition rules rather than interpreted as a direct measure of structural knowledge. A GC-identity rule attains 0.576/0.608/0.599 on bpRNA-TS0, bpRNA-val, and ArchiveII, respectively, while the stronger left–center–right trigram baseline attains 0.592/0.616/0.621. A probe trained once on bpRNA-TR0 and evaluated unchanged on all three sets leaves the following increments above the corresponding trigram floors:

| Scale | TS0 − trigram | val − trigram | ArchiveII − trigram |
|---|---:|---:|---:|
| 1M | +0.001 | −0.006 | +0.004 |
| 10M | +0.013 | +0.001 | +0.019 |
| 30M | +0.024 | +0.021 | +0.033 |
| 100M | +0.017 | +0.011 | +0.032 |
| 650M | +0.034 | +0.046 | +0.038 |

The increment is therefore small but reappears across all three evaluation sets at 650M. It is also distinct from a same-layer trained-minus-random comparison: when each arm selects its own best layer in the single-set full scans, trained-minus-randinit is +0.007/−0.001/−0.003/+0.004 at 1M/10M/30M/100M. Thus, through 100M, pretraining mainly changes where pairing-related signal is linearly readable rather than raising the best-layer linear ceiling. The much larger same-layer contrast at 650M is not used as a knowledge estimate because the untrained deep representation itself collapses, conflating signal content with layer readability. These single-run probe comparisons calibrate the composition floor; they do not provide training-seed replication for a structural scaling law.

**Forward covariation separates knowledge from linear readability.** The mutation test masks position $j$, changes its true partner $i$ to an alternative nucleotide, and measures the probability shift at $j$ toward the new complement (COV). An unpaired-position control (CTRL) tests the corresponding composition response, with 4,920 mutation events per arm. Random initialization preserves the architecture but removes pretraining.

| Arm | COV − CTRL |
|---|---:|
| 1M trained | +0.00415 |
| 10M trained | +0.00504 |
| 30M trained | +0.01121 |
| 100M trained | +0.02030 |
| 300M trained | +0.04694 |
| 650M trained | +0.09572 |
| 30M randinit | +0.00007 |
| 650M randinit | +0.00004 |

The response increases throughout the controlled ladder and is 4.7-fold larger at 650M than at 100M. At 650M, the probability assigned to the old complement simultaneously falls by 0.10227, approximately balancing the shift toward the new complement. The unpaired control and the near-zero random-initialization responses exclude the tested composition shortcut and architectural prior within this assay. Pairing-dependent probability structure is therefore present in the forward pass and arises from pretraining, even when a per-position linear probe exposes only a small increment; the probe value is a lower bound on readable knowledge, not a measure of all forward-pass knowledge.

**External COV provides observational cross-model corroboration.** Under the same mutation protocol, COV − CTRL is +0.1134/+0.1998/+0.2477 for RiNALMo micro/mega/giga and +0.0108 for NucleicBERT; every corresponding randinit17 control is approximately zero. RNA-Sc-650M's +0.0957 lies between RiNALMo micro and mega, while the RiNALMo gradient rises with external model scale. These are observational anchors across confounded architectures, corpora, and exposures, not controlled scale attribution. The 300M sanity rerun passed protocol-equivalence checks; its small cross-hardware/software residual is reported with a `1e-4` hardware-tolerance note, without claiming a uniquely proven cause because the exact old environment was not retained.

**Replacing the readout locates the wall at partner finding.** Holding the layer, training data, evaluation set, metric, and class weighting fixed, we replace the linear head with local symmetric pooling (pool16), attention, or symmetry-constrained attention (attn_symm). A separate arm unfreezes the final two encoder layers, while Partner-Oracle supplies the true partner state and thus serves only as an information-access upper bound.

| Scale (layer) | Linear | pool16 | attn | attn_symm | Fine-tune top 2 | Partner-Oracle |
|---|---:|---:|---:|---:|---:|---:|
| 30M (L3) | 0.6120 | 0.6413 | 0.6295 | 0.6285 | 0.6260 | 0.9996 |
| 100M (L22) | 0.6212 | 0.6218 | 0.6214 | 0.6354 | 0.6368 | 0.9992 |
| 650M (L15) | 0.6101 | 0.6151 | 0.6291 | 0.6348 | 0.6405 | 0.9983 |

Remote interaction improves readout, with pool16 preferred at the shallow 30M layer and symmetrized attention preferred at the two deeper layers. Yet every method that must identify the partner remains near 0.64, including end-to-end adaptation of the top two layers, whereas supplying the true partner raises macro-F1 to at least 0.998 at every tested scale. This controlled contrast localizes the immediate bottleneck: the two endpoints jointly contain information sufficient for the Oracle readout, but generic per-position heads and limited fine-tuning do not recover the partner search. The Oracle is not a deployable predictor, and its ceiling does not imply that an automatically generated partner set will retain the same accuracy.

**Candidate-pair scoring confirms the diagnosis after prior correction.** The pair-level probe changes the task from isolated position classification to scoring $(h_i,h_j,|i-j|)$ as paired or unpaired. Raw candidate-ranking AUC is high, but a model-free baseline using distance, endpoint positions, nucleotide identities, and complement status already reaches 0.922; the meaningful model contribution is the increment above this matched prior.

| Scale | Pair AUC | AUC − matched prior | Pair-probe top-L precision |
|---|---:|---:|---:|
| 30M | 0.9319 | +0.0099 | 0.0319 |
| 100M | 0.9397 | +0.0177 | 0.0563 |
| 650M | 0.9524 | +0.0304 | 0.0641 |

Candidate conditioning therefore reveals a real, scale-increasing increment that the per-position wall conceals, with the largest net gain at 650M. Within these assays, the immediate missing component is a pairing solver for candidate generation and matching, not simply additional pretraining; this diagnoses the present bottleneck without predicting how accurate such a solver would be. It does not solve structure prediction: top-L precision remains low, and the 650M dynamic-programming pair-F1 of 0.2000 does not exceed its randinit value of 0.2104, confirming that the downstream pairing solution remains prior-dominated. Pair AUC, pair-probe top-L precision, dynamic-programming pair-F1, and paired-position macro-F1 are kept as distinct metrics rather than treated as interchangeable structure scores.

An independent long-range contact probe gives the same qualified conclusion under yet another metric. For pairs separated by at least 24 nt, APC-corrected top-L precision reaches 1.19/1.28/1.53 times chance at 30M/100M/650M, compared with 1.06/0.92/1.31 for randinit; thus the 650M trained-minus-randinit excess is 0.22-fold chance. The absolute values remain close to chance under this sequence-level bpRNA split, so the result supports weak pretraining-derived pairing geometry, not accurate long-range contact prediction.

**Probe-free batteries corroborate coupling but retain their boundary results.** On 80 bpRNA-TS0 sequences of length at most 128 nt, masked-logit interaction (MLI) at RNA-Sc-650M averages +0.158 for paired positions versus −0.001 for distance-matched controls, giving pair-versus-control AUC 0.743; randinit yields AUC 0.492. This independently supports learned pairwise coupling without training a structural probe. Attention provides descriptive rather than causal localization: the strongest pair-tracking ratio occurs early in the ALiBi model (L6-H0, 16,140-fold), whereas a learned-positional-encoding external anchor shows its reported maximum in a deep head (L27-H8, 617-fold). This observational contrast warns against treating a universal layer location as the mechanism. Finally, boundary saliency is weak in RNA-Sc-650M (0.000174 at boundaries versus 0.000166 in interiors) and shows no zero-shot boundary elevation in the external anchor. That negative result bounds the interpretability claim: input-gradient magnitude need not register a distributed partner-matching computation, so weak saliency does not overturn the controlled covariation and MLI evidence, but neither does it provide independent support for boundary encoding. Figure 4 summarizes the full chain from composition floors to prior-corrected pair readout.

Having established that structural knowledge can be present yet hidden by partner finding, the next question is what controls its supply: does family-channel saturation also bound structure, or do corpus composition and budget affect the two channels differently? This section does not show that current representations suffice for accurate structure prediction, that adding a pairing solver will close the gap, or that the readout wall generalizes across architectures and external pretraining corpora.

![Figure 4](../../figs_v6/fig4_q5_readout_chain.png)
