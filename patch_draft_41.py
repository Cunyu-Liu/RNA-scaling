"""Patch DRAFT §4.1: add 100M@5.9B row + budget-effect paragraph."""
P = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
src = open(P).read()

old = """### 4.1 Transfer grows with scale 【Act I · H1】 — except a systematic 10M valley

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
non-monotone at six scales."""

new = """### 4.1 Transfer grows with scale 【Act I · H1】 — except a systematic 10M valley

Six-scale family-split probe F1 (300M anchor tier added 2026-09-26):
1M 0.1650±0.0131, 10M 0.1535±0.0173, 30M 0.2651±0.0162,
100M 0.3394±0.0147, 300M 0.3445 (single seed), 650M 0.3632. The 10M mean falls below 1M
(−0.0115): the 1M→10M segment is negative in 2/3 seeds (s29 −0.040, s43 −0.080, s17 +0.013) — mean-level, not per-seed universal.
Pre-registered slope on the 30M→100M segment: 0.142 F1/decade,
bootstrap CI [0.104, 0.180], lower bound 3.5×ε — the 650M continuation
was triggered by rule, not by taste. 650M final: F1 0.3632;
full-axis slope 0.0829 F1/decade; the 10M valley persists in
the 650M era (10M 0.1535 < 1M 0.1650, three-seed means). The 300M
anchor closes the interpolation: 100M→300M only +0.5pp
(near-plateau) vs 300M→650M +1.9pp; the layer-migration endpoint
reverses (rel 0.864@100M → 0.957@300M peak → 0.296@650M) —
non-monotone at six scales.

**Budget axis (3×2 factorial, first point closed 10-03).** 100M
retrained at 5.9B nt (≈ full corpus + 3 epochs of repetition, same
recipe/split/protocol; automated closeout chain): final F1 0.2989@L16
vs 0.3263@L21 at 2.0B — **doubling-to-tripling the budget beyond the
corpus is a −2.74pp NEGATIVE effect** at 100M. The 2.0B iso-token
budget sits at or beyond this scale's compute-optimal point on a
redundant ncRNA corpus (rRNA 63.6%): Muennighoff-style "repetition ≈
fresh tokens" does not transfer to this regime. The best layer
migrates down (L21→L16) — overtraining erosion, same family as the
10M mid-training attrition (§4.3). The randinit control gain is intact
(+0.141 vs +0.168 at 2B): the deficit lives inside the pretraining
gain, not the control. Remaining arms (30M/300M/650M @5.9B) are
training under the same automated chain; the pre-registered Claim-14
verdict (corpus-optimal scale bound) reads from the completed 3×2
table."""

# fix the accidental s43 number change back to original (-0.008)
# by using a second replace on the new text
new = new.replace("s43 −0.080", "s43 −0.008")

assert old in src, "4.1 block not found"
src = src.replace(old, new)
open(P, "w").write(src)
print("DRAFT 4.1 patched: 100M@5.9B row + budget paragraph")
