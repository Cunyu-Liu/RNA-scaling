# arXiv LaTeX package build report

## Result

**PASS — full local TeX/BibTeX compilation succeeded.** Tectonic 0.17.0 generated `main.pdf` (30 pages, A4), including the natbib bibliography and all six PDF figures. No scientific numbers or claims were edited.

- Source: `论文重写_P1_20261125/DRAFT_v2_20261125.md`
- Source SHA256: `9d0ffbc7029121aac1680de1ea09fc01e80fc95b6c111acf1c885fb4596384dc`
- Reference source: `论文/DRAFT_refs.md`
- Figure source: `figs_v6/`
- Build date: 2026-11-26

## Package contents

- `main.tex`: article preamble, title, author placeholders, abstract, natbib configuration, and document entry point.
- `body.tex`: converted body, included by `main.tex` with `\input{body}`.
- `refs.bib`: 19 entries exactly matching the 19 unique in-text citation keys; unavailable metadata is marked `TODO` rather than inferred.
- `main.bbl`: BibTeX-generated bibliography retained for arXiv AutoTeX compatibility.
- `figs/`: six vector PDF figures.
- `arxiv_metadata.md`: title, 154-word abstract under the P4 counting rule (below the 250-word limit), author placeholders, suggested primary `q-bio.BM` and cross-list `cs.LG`, and comments.
- `main.pdf`: local verification build, 30 pages.
- `build_report.md`: this report.

Figures 2, 3, 5, and 6 use their Markdown caption paragraphs. Figures 1 and 4 have no independent caption paragraph in the source; their captions reuse only the corresponding existing section headings, without adding scientific claims.

## Compilation

The machine does not provide `pdflatex`, `bibtex`, `latexmk`, `xelatex`, or `lualatex`, but it does provide Tectonic. The actual verification command was:

```bash
cd 发布_P4_20261126/arxiv_package
tectonic --keep-logs --keep-intermediates main.tex
```

Final result: exit code 0; TeX, BibTeX, reruns, and `xdvipdfmx` completed. The first build identified unescaped underscores in bibliography notes (`DRAFT_refs.md`); these were escaped, and the complete build was rerun successfully.

For a conventional remote TeX Live environment, the equivalent sequence is:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

`main.bbl` is included so the arXiv source upload does not depend on the remote system running BibTeX.

## Final verification

- **Decimal fidelity:** PASS. After removing only automatically generated LaTeX layout numbers and explicit Markdown section numbers, all **519/519 decimal literal occurrences** match the source as a multiset, preserving signs and displayed precision.
- **Additional numeric samples:** PASS, **14/14**. These cover `29,012,227`, `3,357,201`, both probe protocols, percentages, `16,140-fold`, the original-terminal `+1.15 pp` expression, withdrawn Appendix values, `ddof=1`, `0/23`, and `1e-4`.
- **Blacklist:** PASS, **0 violations**, using the P4 rules for prohibited claims and project separation. Historical numeric values remain only in their existing withdrawn/demoted/provenance contexts.
- **Citations:** PASS, **19/19** unique keys mapped to 19 BibTeX entries; 21 `\citep` commands retained. Final PDF text contains `References` and `[19]`, with no undefined-reference markers.
- **Figures:** PASS, **6/6** referenced with `\includegraphics` from `figs/*.pdf`; every file has a PDF header and is byte-identical to its `figs_v6` source.
- **Static syntax:** PASS. Environment nesting, inline-math delimiters, and braces are balanced in `main.tex`, `body.tex`, and `refs.bib`.
- **Compiled PDF:** PASS. `pdfinfo` reports 30 pages; `pdftotext` confirms the title and bibliography and finds no `??` reference markers. The final log contains no errors or undefined citations.

## Non-blocking warnings and required submission metadata

The final log has only layout/engine warnings: two table alignments overfull by 4.35388 pt, one paragraph overfull by 5.04361 pt, three underfull paragraphs, and the expected notice that `inputenc` is ignored by Tectonic's UTF-8 engine. These do not prevent compilation or reference resolution.

Before public submission, replace the author/affiliation/contact placeholders in `main.tex` and `arxiv_metadata.md`. The 22 `TODO` markers in `refs.bib` intentionally identify metadata absent from `DRAFT_refs.md`; they should be completed only from verified bibliographic sources. No unfinished experiment has been relabeled as complete.
