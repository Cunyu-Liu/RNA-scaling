# arXiv submission metadata

## Title

What scale buys in RNA language models: protocol-gated transfer, corpus-gated supply, and the readout gap of structural knowledge

## Authors

- TODO: Author Name(s)
- TODO: Affiliation(s)
- TODO: Contact email and ORCID(s), if applicable

Replace the corresponding author placeholders in `main.tex` before submission.

## Abstract (154 words by the P4 numeric-token counting rule)

Across a controlled six-scale family of RNA masked-language models and a two-world evaluation contrasting cluster-isolated family splits with random splits, we ask what scale buys, what pretraining supplies, and what downstream readouts can access. Most of the apparent scale dividend is protocol-realized, composition-level memory: a k-mer baseline reproduces a random-minus-family gain of Δ=+0.355, initialization controls recover only 11–18% of that dividend, and additional training budget leaves the random-split channel largely unchanged at the three completed terminal comparisons. Nevertheless, learned knowledge is real: controlled initialization and mutation tests, forward covariation (+0.096), and a matched-prior pair probe (+0.030) establish pretraining-derived structural signal, while budget-by-scale interventions reverse the sign of family-transfer gains but monotonically improve structure transfer over three scales, and partner-dependent readouts stall near 0.64 despite a Partner-Oracle of 0.998. For model development within this setting, corpus composition and budget placement should precede parameter count, while evaluation protocols and readout heads should precede absolute scores.

## Suggested classification

- Primary: **q-bio.BM** (Biomolecules)
- Cross-list: **cs.LG** (Machine Learning)

## Comments

- 30 pages in the local Tectonic 0.17.0 verification build.
- Six figures; bibliography generated from `refs.bib` using natbib.
- Pure evaluation study; no new model architecture is claimed.
- Author metadata remains a required pre-submission replacement.
