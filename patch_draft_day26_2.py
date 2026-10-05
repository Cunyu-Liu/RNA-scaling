"""Patch DRAFT day26-2: S7 100M row + 3-channel pre-registered verdict + P5/RNS budget matrix."""
P = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
src = open(P).read()

old_s7 = """is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there). 30M update 10-05: S7 on the 30M@5.9B
final checkpoint gives pair-position F1 0.5765 (L3) vs 30M@2B 0.5756
(L3) — Δ +0.09pp, BELOW the randinit17 control (0.5786): at 30M the
structure channel shows NO budget effect at all. So the two readout
channels have different budget thresholds: family F1 already turns
negative at 30M (−5.24pp) while structure needs 300M before any
significant gain (+1.87pp) — full matrix in
evidence/s7_structure_budget_matrix.json.]"""

new_s7 = """is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there). 30M/100M updates 10-05: S7 on the
30M@5.9B final checkpoint gives pair-position F1 0.5765 (L3) vs
30M@2B 0.5756 (L3) — Δ +0.09pp, BELOW the b59-arm randinit17 control
(0.586): no budget effect at 30M. The 100M@5.9B arm closes the 4th
matrix cell: F1 0.5975 (L21) vs 100M@2B 0.5890 (L22) — Δ +0.85pp
(below the 1pp bar but above its randinit 0.5855, best layer stable).
So the structure-channel budget effect is MONOTONE in scale (+0.09
→ +0.85 → +1.87pp at 30M/100M/300M) — NO sign flip, unlike the
family channel (−5.24 → −2.74 → +3.76pp). The two readout
channels answer budget in opposite regimes: family classification is
a small-scale overtraining story; structure readout is a scale-gated
undertraining story. Full matrix incl. randinit controls:
evidence/s7_structure_budget_matrix.json.]"""

assert old_s7 in src, "s7 anchor not found"
src = src.replace(old_s7, new_s7)

old_p5 = """The decisive intervention is pre-registered: 30M@5.9B (tokens x3, unique
sequence exposure 0.14 -> 0.42 epoch, queued) — if all three plateaus
persist unchanged, the data-quantity explanation is finally excluded
and the finite-channel account closes; if any plateau moves, data
quantity re-enters."""

new_p5 = """The decisive intervention was pre-registered: 30M@5.9B (tokens x3,
unique sequence exposure 0.14 -> 0.42 epoch) — if all three plateaus
persist unchanged, the data-quantity explanation is finally excluded
and the finite-channel account closes; if any plateau moves, data
quantity re-enters. **RESULT (10-05, b59 3-channel matrix,
evidence/p5rns_b59_verdict.json): the finite-channel account is
REFUTED in its strong form.** Two of three channels MOVE with budget
and the movement is scale-amplified: RNS@10 tightens (100M 0.083 →
0.052, 300M 0.067 → 0.043); P5 non-rRNA shuffle separation grows
+0.11/+0.29/+0.36 nats/token at 30M/100M/300M (0.08→0.19, 0.14→0.43,
0.23→0.59) while rRNA separation plateaus ~0.9 as predicted. Only
the family-Delta channel follows the finite-channel story (it moves
NEGATIVELY below 300M). Revised account: the 30M triple-plateau is a
FAMILY-CHANNEL phenomenon — zero-supervision structural statistics
keep eating budget at every scale (Chinchilla-style), and the
k-mer-reachable classification channel saturates. The S7 structure
matrix (+0.09/+0.85/+1.87pp monotone) agrees with the P5 channel;
the two zero-supervision and two readout views converge."""

assert old_p5 in src, "p5 anchor not found"
src = src.replace(old_p5, new_p5)

open(P, "w").write(src)
print("patched: s7 100M cell + 3-channel pre-registered verdict")
