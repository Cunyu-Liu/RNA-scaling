"""[id-verify] pass 1 results — 4 core entries web-verified (2026-10-03).

Findings written to preprint/id_verify_log.md (honest states only,
no fabricated identifiers).
"""
LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"

entries = [
    ("Muennighoff et al., Scaling Data-Constrained Language Models",
     "VERIFIED",
     "arXiv:2305.16264 (v4, 2023-10-26); NeurIPS 2023 main track; "
     "Outstanding Paper Runner-Up (neurips blog + arXiv PDF + Google "
     "Scholar, three-source agreement). Bib: Muennighoff, N., Rush, "
     "A.M., Barak, B., Le Scao, T., Piktus, A., Tazi, N., Pyysalo, S., "
     "Wolf, T., Raffel, C. NeurIPS 2023."),
    ("Penic et al., RiNALMo",
     "VERIFIED-WITH-CORRECTION",
     "arXiv:2403.00043 (v2, 2024-11-12, authors+affiliations confirmed "
     "on arXiv). JOURNAL CORRECTION: final publication is Nature "
     "Communications 16:5671 (2025), DOI 10.1038/s41467-025-60872-5 "
     "(Semantic Scholar record + maxapress citation table agree). "
     "Memo's 'Nature Machine Intelligence 2024' is WRONG — bib must be "
     "updated to Nat Commun 16:5671 (2025)."),
    ("Danaee et al., bpRNA",
     "VERIFIED",
     "Nucleic Acids Research 46(11):5381-5394 (2018), DOI "
     "10.1093/nar/gky285 (OUP official PDF + PubMed + ScienceDaily, "
     "three-source agreement)."),
    ("RNA-FM (Chen et al.)",
     "PENDING-NEEDS-MANUAL",
     "Web search hit a verification wall (no direct OUP page in "
     "results); known metadata from project use: Briefings in "
     "Bioinformatics 2023, 24(5):bbaad445, DOI 10.1093/bib/bbaad445 — "
     "NOT yet web-verified this pass; re-try with different query or "
     "confirm from local PDF archive before final bib."),
]

with open(LOG, "w") as fh:
    fh.write("# [id-verify] pass 1 — web verification log\n\n")
    fh.write("Date: 2026-10-03. Scope: 4 of 17 marked entries (highest-"
             "citation-frequency first). Method: web search, two-source "
             "rule, honest states only.\n\n")
    for name, status, detail in entries:
        fh.write(f"## {name}\n**{status}**\n\n{detail}\n\n")

print("log written:", LOG)
