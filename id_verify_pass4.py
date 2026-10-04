"""id-verify pass 4: HydraRNA + BiRNA-BERT."""
import io

LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"
REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"

log_append = """

# [id-verify] pass 4 — HydraRNA + BiRNA-BERT

Date: 2026-10-04.

## HydraRNA
**VERIFIED**

Li, G. et al. HydraRNA: a hybrid architecture based full-length RNA
language model. Genome Biology 26 (2025-11-10), DOI
10.1186/s13059-025-03853-7 (Crossref + Semantic Scholar two-source;
journal version of bioRxiv 2025.03.06.641765).

## BiRNA-BERT
**VERIFIED-WITH-CORRECTION**

Tahmid, M.T. et al. BiRNA-BERT allows efficient RNA language modeling
with adaptive tokenization. Communications Biology 8, 1621
(2025-11-20), DOI 10.1038/s42003-025-08982-0 (PMC12635123 full record
+ bio-trade news corroboration). DRAFT_refs title ("adaptive dual
tokenization for RNA") was a paraphrase — actual title uses
"adaptive tokenization"; first author Tahmid (not in draft).
"""

refs_patch = [
    ("""15. HydraRNA: hybrid-architecture RNA LM. *Genome Biology* (2025-11).
    [memo-verified; id-verify]""",
     """15. Li, G. et al. HydraRNA: a hybrid architecture based full-length
    RNA language model. *Genome Biology* 26 (2025). DOI
    10.1186/s13059-025-03853-7. [Crossref-verified 2026-10-04]"""),
    ("""14. BiRNA-BERT: adaptive dual tokenization for RNA. *Communications
    Biology* (2025-11). [memo-verified; id-verify]""",
     """14. Tahmid, M.T. et al. BiRNA-BERT allows efficient RNA language
    modeling with adaptive tokenization. *Communications Biology* 8,
    1621 (2025). DOI 10.1038/s42003-025-08982-0. [web-verified
    2026-10-04; title and first author corrected]"""),
]

io.open(LOG, "a", encoding="utf-8").write(log_append)
r = io.open(REFS, encoding="utf-8").read()
n = 0
for old, new in refs_patch:
    if old in r:
        r = r.replace(old, new, 1); n += 1
    else:
        print("PATCH MISS:", old[:60])
io.open(REFS, "w", encoding="utf-8").write(r)
print("pass4: refs patched %d/2" % n)
