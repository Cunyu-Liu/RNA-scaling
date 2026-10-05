"""Patch DRAFT: 30M@5.9B closeout — budget table 3rd row + S7 structure null."""
P = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
src = open(P).read()

old_tbl = """| scale | F1 @2.0B | F1 @5.9B | budget effect |
|---|---|---|---|
| 100M | 0.3263 (L21) | 0.2989 (L16) | **−2.74pp (overtraining)** |
| 300M | 0.3445 (L22) | **0.3821 (L22)** | **+3.76pp (undertraining at 2B)** |"""

new_tbl = """| scale | F1 @2.0B | F1 @5.9B | budget effect |
|---|---|---|---|
| 30M | 0.2466 (L8) | 0.1942 (L10) | **−5.24pp (overtraining, deepest)** |
| 100M | 0.3263 (L21) | 0.2989 (L16) | **−2.74pp (overtraining)** |
| 300M | 0.3445 (L22) | **0.3821 (L22)** | **+3.76pp (undertraining at 2B)** |"""

assert old_tbl in src, "table anchor not found"
src = src.replace(old_tbl, new_tbl)

old_note = """Remaining arms (30M/650M
@5.9B) are training under the same automated chain; the completed
table will fill the interaction. (Fig 6.)"""

new_note = """The 30M row (closed 10-05) makes the flip
MONOTONE in scale: −5.24 / −2.74 / +3.76 pp — the smaller the model,
the deeper the overtraining deficit on the redundant corpus, and the
crossover sits between 100M and 300M. Remaining arm (650M @5.9B) is
training under the same automated chain; it completes the interaction.
(Fig 6.)"""

assert old_note in src, "note anchor not found"
src = src.replace(old_note, new_note)

old_s7 = """is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there).]"""

new_s7 = """is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there). 30M update 10-05: S7 on the 30M@5.9B
final checkpoint gives pair-position F1 0.5765 (L3) vs 30M@2B 0.5756
(L3) — Δ +0.09pp, BELOW the randinit17 control (0.5786): at 30M the
structure channel shows NO budget effect at all. So the two readout
channels have different budget thresholds: family F1 already turns
negative at 30M (−5.24pp) while structure needs 300M before any
significant gain (+1.87pp) — full matrix in
evidence/s7_structure_budget_matrix.json.]"""

assert old_s7 in src, "s7 anchor not found"
src = src.replace(old_s7, new_s7)

open(P, "w").write(src)
print("patched: table row + monotone note + s7 30M null")
