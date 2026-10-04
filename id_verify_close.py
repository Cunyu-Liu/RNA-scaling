"""Update DRAFT_refs discipline notes to reflect completed id-verify."""
import io

REFS = "/home/cunyuliu/rna-sc/preprint/DRAFT_refs.md"
r = io.open(REFS, encoding="utf-8").read()

old_head = """> verified them; entries marked [id-verify] must have DOI/arXiv
> confirmed in the final bib pass before submission (D6 gate)."""
new_head = """> verified them; the [id-verify] bib pass was COMPLETED 2026-10-04
> (passes 1-5, 14 entries, 12 corrections, all DOIs/arXiv IDs
> web-verified two-source; D6 gate: clean)."""

old_tail = """marked [id-verify] and must be resolved in the final bib pass —"""
new_tail = """COMPLETED 2026-10-04: all 14 [id-verify] entries resolved (12
corrections; see preprint/id_verify_log.md passes 1-5) —"""

assert old_head in r and old_tail in r
r = r.replace(old_head, new_head, 1).replace(old_tail, new_tail, 1)
io.open(REFS, "w", encoding="utf-8").write(r)
print("discipline notes updated to completed state")
