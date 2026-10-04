"""id-verify pass 3: ERNIE-RNA + RNAErnie (+ Lin/DenAdel if not yet applied)."""
import io

LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"
REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"

log_append = """

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
"""

refs_patch = [
    ("""11. Wang, Y. et al. ERNIE-RNA: an enhanced RNA language model.
    *ICML 2024* (also *Nature Communications* 2025 version).
    [id-verify]""",
     """11. Yin, W. et al. ERNIE-RNA: an RNA language model with
    structure-enhanced representations. *Nature Communications* 16,
    10076 (2025). DOI 10.1038/s41467-025-64972-0. [web-verified
    2026-10-04; author and venue corrected — cite the journal version]"""),
    ("""12. Wang, D. et al. Multi-purpose RNA language modelling with
    motif-aware pretraining (RNAErnie). *Nature Machine
    Intelligence* (2024). [id-verify]""",
     """12. Wang, N. et al. Multi-purpose RNA language modelling with
    motif-aware pretraining and type-guided fine-tuning (RNAErnie).
    *Nature Machine Intelligence* 6, 548-557 (2024). DOI
    10.1038/s42256-024-00836-4. [Crossref-verified 2026-10-04;
    first author corrected: Ning Wang]"""),
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
print("pass3b: refs patched %d/2" % n)
