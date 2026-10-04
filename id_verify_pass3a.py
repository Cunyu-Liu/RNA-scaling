"""id-verify pass 3a: Lin ESM-2 + DenAdel corrections to refs + log."""
import io

LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"
REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"

log_append = """

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
"""

refs_patch = [
    ("""8. Lin, Z. et al. Evolutionary-scale prediction of atomic-level
   protein structure (ESM-2). *Science* 377, 112-115 (2023).
   [id-verify]""",
     """8. Lin, Z. et al. Evolutionary-scale prediction of atomic-level
   protein structure with a language model. *Science* 379(6637),
   1123-1130 (2023). DOI 10.1126/science.ade2574. [web-verified
   2026-10-04 three-source; volume/pages corrected]"""),
    ("""7. DenAdel, R. et al. Saturation-point analysis of single-cell
   foundation models. *Nature Methods* (2026). [H5 reverse prior;
   id-verify]""",
     """7. DenAdel, A. et al. Evaluating the role of pretraining dataset
   size and diversity on single-cell foundation model performance.
   *Nature Methods* (2026). DOI 10.1038/s41592-026-03120-y. [H5
   reverse-prior source; web-verified 2026-10-04; title corrected]"""),
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
print("pass3a: refs patched %d/2" % n)
