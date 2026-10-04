# [id-verify] pass 1 — web verification log

Date: 2026-10-03. Scope: 4 of 17 marked entries (highest-citation-frequency first). Method: web search, two-source rule, honest states only.

## Muennighoff et al., Scaling Data-Constrained Language Models
**VERIFIED**

arXiv:2305.16264 (v4, 2023-10-26); NeurIPS 2023 main track; Outstanding Paper Runner-Up (neurips blog + arXiv PDF + Google Scholar, three-source agreement). Bib: Muennighoff, N., Rush, A.M., Barak, B., Le Scao, T., Piktus, A., Tazi, N., Pyysalo, S., Wolf, T., Raffel, C. NeurIPS 2023.

## Penic et al., RiNALMo
**VERIFIED-WITH-CORRECTION**

arXiv:2403.00043 (v2, 2024-11-12, authors+affiliations confirmed on arXiv). JOURNAL CORRECTION: final publication is Nature Communications 16:5671 (2025), DOI 10.1038/s41467-025-60872-5 (Semantic Scholar record + maxapress citation table agree). Memo's 'Nature Machine Intelligence 2024' is WRONG — bib must be updated to Nat Commun 16:5671 (2025).

## Danaee et al., bpRNA
**VERIFIED**

Nucleic Acids Research 46(11):5381-5394 (2018), DOI 10.1093/nar/gky285 (OUP official PDF + PubMed + ScienceDaily, three-source agreement).

## RNA-FM (Chen et al.)
**PENDING-NEEDS-MANUAL**

Web search hit a verification wall (no direct OUP page in results); known metadata from project use: Briefings in Bioinformatics 2023, 24(5):bbaad445, DOI 10.1093/bib/bbaad445 — NOT yet web-verified this pass; re-try with different query or confirm from local PDF archive before final bib.



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
