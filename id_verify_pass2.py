"""id-verify pass 2: 4 method-source/RNA-LM entries + DRAFT_refs corrections."""
import io

LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"
REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"

log_append = """

# [id-verify] pass 2 — method-source citations (S13/S14/S15) + RNA-FM terminal check

Date: 2026-10-04. Scope: 4 of 13 remaining [id-verify] entries (method-source
priority). Method: web two-source rule + Crossref/Semantic-Scholar/Europe-PMC
structured APIs. Honest states only.

## Hou et al. (S13 method source)
**VERIFIED-WITH-CORRECTION**

Actual title: "Understanding language model scaling for protein fitness
prediction". Nat Comput Sci (2026), DOI 10.1038/s43588-026-01010-z, PMID
42443524; preprint bioRxiv 2025.04.25.650688 (PMC12330683). Three-source
(Semantic Scholar + bioengineer citation line + PMC banner). DRAFT_refs entry
3 currently uses a descriptive phrase ("Fitness prediction through
confidence-bounded pretraining likelihood") as the title — must be replaced
with the actual title.

## Prabakaran & Bromberg (S14 method source, RNS)
**VERIFIED**

Nat Methods 23, 796-804 (2026), DOI 10.1038/s41592-026-03028-7
(bromberglab.org publication page + author homepage rpkarandev.github.io,
two-source; RNS bitbucket repo confirmed).

## Simon & Zou InterPLM (S15 source)
**VERIFIED-WITH-CORRECTION**

Nat Methods 22, 2107-2117 (2025), DOI 10.1038/s41592-025-02836-7 (Crossref
authoritative + PNAS-citing-paper agreement). CORRECTION: first author is
Simon, E. (Elana Pearl Simon) — DRAFT_refs wrote "Simon, J.".

## RNA-FM (Chen et al.)
**VERIFIED-WITH-MAJOR-CORRECTION — NEVER JOURNAL-PUBLISHED**

Three structured sources agree (Semantic Scholar API: bioRxiv only;
Crossref full-library query: no journal DOI exists; Europe PMC: PPR
preprint records only): RNA-FM has NO peer-reviewed journal version as of
2026-10. Candidate DOIs tested and rejected: 10.1093/bib/bbaad445 (not in
Crossref — fabricated or confused), 10.1093/bib/bbad170 (exists but is
ATTIC, a different paper). DRAFT_refs "Nature Methods (2023)" is WRONG;
pass-1 memo "Brief Bioinform 24(5):bbaad445" is WRONG. Honest citation:
arXiv:2204.00300 (2022); bioRxiv 10.1101/2022.08.06.503062. NOTE: this also
qualifies every RNA-FM comparison in the paper — it is a 2022 preprint-era
96M model; keep as external baseline but do not cite as journal-published.

Remaining [id-verify]: 9 entries (DenAdel, Lin ESM-2, Wang ERNIE-RNA,
Wang RNAErnie, BiRNA-BERT, HydraRNA, + others).
"""

refs_patch = [
    # (old snippet, new snippet)
    ("""3. Hou, F. et al. Fitness prediction through confidence-bounded
   pretraining likelihood (inverted-U). *Nature Computational Science*
   (2026). [S13 method source; id-verify]""",
     """3. Hou, C., Liu, D., Zafar, A. & Shen, Y. Understanding language
   model scaling for protein fitness prediction. *Nature Computational
   Science* (2026). DOI 10.1038/s43588-026-01010-z. [S13 method source;
   web-verified 2026-10-04; title corrected, PMID 42443524]"""),
    ("""4. Prabakaran, R. & Bromberg, S. Quantifying uncertainty in protein
   representations across models and tasks. *Nature Methods* (2026).
   [S14 method source; PDF in 论文/ local archive; id-verify]""",
     """4. Prabakaran, R. & Bromberg, Y. Quantifying uncertainty in protein
   representations across models and tasks. *Nature Methods* 23, 796-804
   (2026). DOI 10.1038/s41592-026-03028-7. [S14 method source; web-verified
   2026-10-04 two-source; coauthor corrected: Bromberg, Y.]"""),
    ("""5. Simon, J. & Zou, J. InterPLM: interpretable protein language model
   concepts. *Nature Methods* (2025). [S15 source; PDF in 论文/
   local archive; id-verify]""",
     """5. Simon, E. & Zou, J. InterPLM: discovering interpretable features
   in protein language models via sparse autoencoders. *Nature Methods*
   22, 2107-2117 (2025). DOI 10.1038/s41592-025-02836-7. [S15 source;
   Crossref-verified 2026-10-04; first name corrected: Elana Pearl Simon]"""),
    ("""10. Chen, Z. et al. RNA-FM: a deep language model for RNA structure
    and function prediction. *Nature Methods* (2023). [id-verify]""",
     """10. Chen, J. et al. Interpretable RNA foundation model from
    unannotated data for highly accurate RNA structure and function
    predictions. arXiv:2204.00300 (2022); bioRxiv 10.1101/2022.08.06.503062.
    [NEVER journal-published — Crossref/Europe-PMC/Semantic-Scholar
    three-source check 2026-10-04; prior 'Nature Methods 2023' and
    'Brief Bioinform bbaad445' claims both WRONG]"""),
]

s = io.open(LOG, encoding="utf-8").read()
io.open(LOG, "a", encoding="utf-8").write(log_append)

r = io.open(REFS, encoding="utf-8").read()
n_ok = 0
for old, new in refs_patch:
    if old in r:
        r = r.replace(old, new, 1)
        n_ok += 1
    else:
        print("PATCH MISS:", old[:60])
io.open(REFS, "w", encoding="utf-8").write(r)
print("log appended; refs patched %d/4" % n_ok)
