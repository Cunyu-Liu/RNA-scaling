"""DRAFT: 300M@5.9B S7 structure testable-prediction result write-in."""
import io

P = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
s = io.open(P, encoding="utf-8").read()

old = """[Family-F1 update 10-04: the budget×scale sign flip
(§4.1) already shows the corpus lever is real at 300M (+3.76pp);
whether it also moves STRUCTURE readout is the sharper version of
this prediction, queued on the 650M@5.9B closeout.]"""

new = """[Family-F1 update 10-04: the budget×scale sign flip
(§4.1) already shows the corpus lever is real at 300M (+3.76pp).
Structure readout update 10-04: S7 on the same 300M@5.9B final
checkpoint gives pair-position F1 0.6165 (L22, rel 0.957) vs
300M@2B 0.5978 (L22) — a budget gain of +1.87pp that EXCEEDS the
1pp significance bar, with the best layer UNCHANGED (no attrition
migration, unlike the 100M arm's L21→L16 forward shift). So the
Chinchilla-style budget×scale interaction is NOT confined to family
classification: structure readout also eats budget at 300M. The
original prediction ("budget gains are family-classification-only")
is REFUTED at 300M; the 650M@5.9B arm remains the decisive cell
(whether the same +budget gain holds at the largest scale, or
structure saturates there).]"""

assert old in s
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("DRAFT structure-prediction paragraph updated with 300M@5.9B S7 result")
