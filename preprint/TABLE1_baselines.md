# Table 1 — Baseline summary (rna_type, balanced probe protocol)

Strongest classical: family = LightGBM 0.1760; random = one-hot CNN 0.5343±0.0207 (3 seeds).

| model / baseline | family F1 | random F1 | Δ(rand−fam) | LM − strongest classical (family) |
|---|---|---|---|---|
| RNA-Sc-1M | 0.1650 | 0.153 | +-0.012 | -0.011 |
| RNA-Sc-10M | 0.1535 | 0.4928 | +0.339 | -0.022 |
| RNA-Sc-30M | 0.2651±0.0162 | 0.605 | +0.340 | +0.089 |
| RNA-Sc-100M | 0.3394±0.0147 | 0.604 | +0.265 | +0.163 |
| randinit-100M (control) | 0.1577 | — | — | — |
| k-mer(1-6)+logistic | 0.1630 | 0.5180 | +0.355 | — |
| k-mer+LightGBM | 0.1760 | 0.5485 | +0.372 | — |
| one-hot CNN (3 seeds) | 0.1725 | 0.5343±0.0207 | +0.362 | — |
| random-emb+probe head | 0.0702 | 0.0557 | -0.014 | — |

Sources: s1_seed_table.json / classical_baselines.json / classical_baselines_extra{,_s29,_s43}.json / s4_randinit_table.json — all deterministic (inc12) protocol; random-split numbers from eval_matrix v1 (i%%5 held-out pool partition).
Reading: under family-level evaluation the LM edge over the strongest classical baseline is negative at small scale and +0.16 at 100M; under random splits classical models reproduce most of the 'LM gain' (protocol property).