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


# [id-verify] pass 3 (part 1) — ESM-2 + DenAdel

Date: 2026-10-04. Two entries, both VERIFIED-WITH-CORRECTION.

## Lin et al., ESM-2 / ESMFold
**VERIFIED-WITH-CORRECTION**

Science 379(6637), 1123-1130 (2023-03-16), DOI 10.1126/science.ade2574
(science.org + Ovid + RosettaCommons citation, three-source). DRAFT_refs
wrote "Science 377, 112-115 (2023)" — VOLUME AND PAGES BOTH WRONG
(377→379, 112-115→1123-1130). Corrected.

## DenAdel et al. (H5 reverse-prior source)
**VERIFIED-WITH-CORRECTION**

Actual title: "Evaluating the role of pretraining dataset size and
diversity on single-cell foundation model performance". Nature Methods
(2026), DOI 10.1038/s41592-026-03120-y (Broad Institute publications
page + two arXiv citing papers). DRAFT_refs descriptive title
"Saturation-point analysis of single-cell foundation models" is WRONG
as a literal title — the saturation/plateau finding is the content, not
the title. Corrected.


# [id-verify] pass 3 (part 2) — ERNIE-RNA + RNAErnie

Date: 2026-10-04.

## ERNIE-RNA
**VERIFIED-WITH-CORRECTION**

Actual: "ERNIE-RNA: an RNA language model with structure-enhanced
representations". Yin, W. et al. Nature Communications 16, 10076
(2025-11-18), DOI 10.1038/s41467-025-64972-0 (PubMed PMID 41253752 +
PMC12627772 + Semantic Scholar, three-source). DRAFT_refs wrote
"11. Wang, Y. et al. ERNIE-RNA ... ICML 2024" — AUTHOR AND VENUE
BOTH WRONG. The 2024 ICML/bioRxiv version was a preprint; the journal
version (Nat Commun 2025) is the one to cite. Corrected.

## RNAErnie (motif-aware)
**VERIFIED**

Wang, N. et al. Multi-purpose RNA language modelling with motif-aware
pretraining and type-guided fine-tuning. Nature Machine Intelligence 6,
548-557 (2024-05-13), DOI 10.1038/s42256-024-00836-4 (Crossref
authoritative; thenamesdictionary/ICLR-review corroboration).
DRAFT_refs "12. Wang, D." — FIRST INITIAL WRONG (Ning, not D.).
Corrected.


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
