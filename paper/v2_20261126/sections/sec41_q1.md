### 4.1 What does scale buy? Bounded, non-monotone family transfer

This section asks what increasing parameter count buys for family-level transfer. The decisive experiment is S1, a six-point controlled ladder from 1M to 650M parameters trained with the same recipe at a 2.0B-nt budget and evaluated with the same family-held-out, mean-pooled linear probe, together with a pre-registered slope rule. Family macro-F1 increases overall, but the trend is non-monotone; saturation is observed in the single-seed tier (300M/650M), while the three-training-seed tier (1M–100M) supports the preceding growth trend.

| Parameters | Family macro-F1 | Training-seed coverage |
|---|---:|---|
| 1M | 0.1650 ± 0.0131 | three seeds |
| 10M | 0.1535 ± 0.0173 | three seeds |
| 30M | 0.2651 ± 0.0162 | three seeds |
| 100M | 0.3394 ± 0.0147 | three seeds |
| 300M | 0.3445 | single seed, s17 |
| 650M | 0.3632 | single seed, s17 |

The first four entries are means ± sample standard deviations across three training seeds; the two largest models are single runs and therefore have no training-seed uncertainty estimate. Each value is the best-layer macro-F1 at the final checkpoint under the common mean-pool protocol. These coverage distinctions are retained in Figure 1 rather than replaced by uniform error bars.

The increase is not monotone at small scale. The 10M mean is 0.0115 below the 1M mean, and the paired 1M-to-10M change is negative in two of the three training seeds. This is a mean-level attrition phenomenon, not a per-seed universal effect; training-seed variation remains the strongest immediate alternative explanation for its magnitude.

The pre-registered decision rule separates the growing and saturating regimes. The 30M-to-100M slope is 0.142 macro-F1 per decade, with a sequence-bootstrap 95% confidence interval of [0.104, 0.180], exceeding the saturation threshold ε = 0.03 and triggering the 650M continuation. In contrast, the 100M-to-650M slope is 0.0293 macro-F1 per decade, just below that threshold. Thus, additional parameters still yield a higher endpoint score, but the upper segment meets the pre-registered saturation criterion in the single-seed 300M/650M tier. The three-training-seed 1M–100M tier supports the trend leading into that observation, not training-seed-robust saturation. This statement concerns the family-classification channel at the fixed training budget, not a ceiling on all representations or on performance under other budgets; P3.1 multi-seed supplementation is not triggered under the final split adjudication. Saturation is not an undertraining artifact: the near-converged 650M at 5.9B nt (validation loss 0.7491, terminal slope −0.0004 per 100M nt) reaches family F1 0.3747, only +1.15 pp above the 2B value 0.3632 (single-seed E1), so added budget that nearly flattens validation loss barely moves transfer; the precise magnitude is single-seed unreliable (P2.11).

Readout depth also fails to follow a monotone deepening trend. The best-layer relative depth reaches 0.957 at 300M and then falls to 0.296 at 650M, even as endpoint macro-F1 increases. The largest model therefore does not simply move its best family representation deeper; scale changes both how much signal is available and where the probe can recover it.

This single-seed saturation observation and shallow-endpoint reversal force the next question: is the remaining advantage learned in the weights, or merely produced by architecture and initialization? This section establishes neither training-seed-robust saturation at the largest scales nor the origin of the gain or a mechanism for saturation or layer relocation.
