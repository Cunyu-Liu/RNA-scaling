"""DRAFT line-93 fix: RNA-FM is not journal-published; reword the external
baseline sentence honestly (refs entry 10 already corrected)."""
import io

P = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
s = io.open(P, encoding="utf-8").read()

old = """Line 1 — published same-family series (RiNALMo micro/mega/giga, RNA-FM)
— is used for external replication; our causal claims rest on the
controlled family. (D1/D2 discipline: "controlled" qualifies only the
self-trained ladder; published series are reported as same-family
series.)"""

new = """Line 1 — external RNA-LM baselines (RiNALMo micro/mega/giga,
journal-published; RNA-FM, arXiv preprint 2204.00300, never
journal-published — see refs note) — is used for external replication;
our causal claims rest on the controlled family. (D1/D2 discipline:
"controlled" qualifies only the self-trained ladder; external models
are reported as baselines with publication status stated.)"""

assert old in s
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("DRAFT line-93 baseline sentence fixed")
