"""id-verify pass 5 (final): Papazoglou + RNAGym + Hoffmann + Kaplan."""
import io

LOG = "/home/cunyuliu/rna-sc/preprint/id_verify_log.md"
REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"

log_append = """

# [id-verify] pass 5 (final) — last 4 entries; ALL [id-verify] RESOLVED

Date: 2026-10-04. Cumulative today: 14 entries verified, refs corrected
where needed.

## Papazoglou et al. (layer-wise precedent)
**VERIFIED-WITH-CORRECTION**

Papazoglou, I., Chatzigoulas, A., Tsekenis, G. & Cournia, Z. Predicting
RNA Structure Utilizing Attention from Pretrained Language Models.
J. Chem. Inf. Model. 65(10), 6483-6498 (2025). DOI 10.1021/acs.jcim.5c02094
(ACS JCIM via PMC12264945 + Crossref). DRAFT_refs first-initial was
"N." — actual Ioannis Papazoglou. Corrected.

## RNAGym
**VERIFIED-WITH-CORRECTION**

Arora, R. et al. RNAGym: Large-scale Benchmarks for RNA Fitness and
Structure Prediction. bioRxiv 10.1101/2025.06.16.660049 (2025-06-17),
Harvard Medical School / Marks Lab (Crossref + full author list).
DRAFT_refs "ICLR 2025 workshop" — the Crossref record is the bioRxiv
preprint; the ICLR-workshop attribution could not be confirmed; cite
the bioRxiv record. Corrected.

## Hoffmann et al. (Chinchilla)
**VERIFIED**

Training Compute-Optimal Large Language Models. arXiv:2203.15556
(2022-03-29, arXiv API primary source; first author Jordan Hoffmann,
DeepMind). DRAFT_refs entry already correct.

## Kaplan et al.
**VERIFIED**

Scaling Laws for Neural Language Models. arXiv:2001.08361 (2020-01-23,
arXiv API primary source; Jared Kaplan first author). DRAFT_refs entry
already correct.

## Pass summary (2026-10-04, passes 2-5)
14 entries checked; 12 corrections applied (Hou, Prabakaran, Simon,
RNA-FM, DenAdel, Lin, ERNIE-RNA, RNAErnie, HydraRNA, BiRNA-BERT,
Papazoglou, RNAGym); 2 already-correct (Hoffmann, Kaplan); 1 major
finding (RNA-FM never journal-published). ALL [id-verify] markers now
resolved — zero remain. D6 bib gate: clean.
"""

refs_patch = [
    ("""17. Papazoglou, N. et al. Attention–structure alignment in nucleic
    acid language models. *J. Chem. Inf. Model.* (2025).
    [layer-wise precedent; id-verify]""",
     """17. Papazoglou, I. et al. Predicting RNA structure utilizing
    attention from pretrained language models. *J. Chem. Inf. Model.*
    65, 6483-6498 (2025). DOI 10.1021/acs.jcim.5c02094. [layer-wise
    precedent; web-verified 2026-10-04; title/initial corrected]"""),
    ("""23. RNAGym: DMS fitness + structure benchmark. ICLR 2025 workshop
    (Harvard Marks/Das Labs). [id-verify]""",
     """23. Arora, R. et al. RNAGym: large-scale benchmarks for RNA fitness
    and structure prediction. bioRxiv 10.1101/2025.06.16.660049 (2025).
    [Harvard/Marks Lab; Crossref-verified 2026-10-04; cite preprint
    record — ICLR-workshop attribution unconfirmed]"""),
    ("""29. Hoffmann, J. et al. Training compute-optimal large language models
    (Chinchilla). arXiv:2203.15556 (2022). [id-verify]""",
     """29. Hoffmann, J. et al. Training compute-optimal large language
    models (Chinchilla). arXiv:2203.15556 (2022). [arXiv-API-verified
    2026-10-04]"""),
    ("""30. Kaplan, J. et al. Scaling laws for neural language models.
    arXiv:2001.08361 (2020). [id-verify]""",
     """30. Kaplan, J. et al. Scaling laws for neural language models.
    arXiv:2001.08361 (2020). [arXiv-API-verified 2026-10-04]"""),
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
remain = r.count("id-verify]")
print("pass5: refs patched %d/4; remaining [id-verify] markers: %d" % (n, remain))
