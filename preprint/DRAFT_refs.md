## References (full list, v1.0 — 2026-09-22)

> Source discipline: every entry below is drawn from the project memo's
> §9 verified-evidence table (three-source cross-checked during
> 2026-09-10..13 research). Identifiers shown ONLY where the memo
> verified them; entries marked [id-verify] must have DOI/arXiv
> confirmed in the final bib pass before submission (D6 gate).

### Protein-domain anchors (methods template)

1. Rives, A. et al. Biological structure and function emerge from
   scaling unsupervised learning to 250 million protein sequences.
   *PNAS* 118, e2015679118 (2021). [PMC8053943 — memo-verified]
2. Li, H. et al. Feature Reuse and Scaling: Understanding Transfer
   Learning with Protein Language Models. *ICML 2024*, PMLR
   235:27351-27375. [full text read; zero-self-training fact verified
   via paper + repo + first-author CV — memo §2.3]
3. Hou, F. et al. Fitness prediction through confidence-bounded
   pretraining likelihood (inverted-U). *Nature Computational Science*
   (2026). [S13 method source; id-verify]
4. Prabakaran, R. & Bromberg, S. Quantifying uncertainty in protein
   representations across models and tasks. *Nature Methods* (2026).
   [S14 method source; PDF in 论文/ local archive; id-verify]
5. Simon, J. & Zou, J. InterPLM: interpretable protein language model
   concepts. *Nature Methods* (2025). [S15 source; PDF in 论文/
   local archive; id-verify]
6. Vishniakov, D. et al. Tokenization to Transfer: Do Genomic
   Foundation Models Learn Good Representations? *ICLR 2026* Poster.
   [m42-health; DNA-domain random-init study; must-cite per SPEC 1.2]
7. DenAdel, R. et al. Saturation-point analysis of single-cell
   foundation models. *Nature Methods* (2026). [H5 reverse prior;
   id-verify]
8. Lin, Z. et al. Evolutionary-scale prediction of atomic-level
   protein structure (ESM-2). *Science* 377, 112-115 (2023).
   [id-verify]

### RNA language models (evaluation targets / same-family series)

9. Penić, M. et al. RiNALMo: a general-purpose RNA language model.
   *Nature Communications* (2025). [micro/mega/giga checkpoints on
   Zenodo — verified; id-verify]
10. Chen, Z. et al. RNA-FM: a deep language model for RNA structure
    and function prediction. *Nature Methods* (2023). [id-verify]
11. Wang, Y. et al. ERNIE-RNA: an enhanced RNA language model.
    *ICML 2024* (also *Nature Communications* 2025 version).
    [id-verify]
12. Wang, D. et al. Multi-purpose RNA language modelling with
    motif-aware pretraining (RNAErnie). *Nature Machine
    Intelligence* (2024). [id-verify]
13. RiboSpan: long-context (10K nt) 1.61B RNA encoder. arXiv:2608.22849
    (2026). [memo-verified; M4 monitoring list]
14. BiRNA-BERT: adaptive dual tokenization for RNA. *Communications
    Biology* (2025-11). [memo-verified; id-verify]
15. HydraRNA: hybrid-architecture RNA LM. *Genome Biology* (2025-11).
    [memo-verified; id-verify]
16. Shulgina, A. et al. GARNET: generative RNA language models
    validated by ribosome thermotolerance experiments. *Nature
    Communications* 15, 10543 (2024).
    DOI: 10.1038/s41467-024-54812-y. [memo-verified]
17. Papazoglou, N. et al. Attention–structure alignment in nucleic
    acid language models. *J. Chem. Inf. Model.* (2025).
    [layer-wise precedent; id-verify]

### RNA benchmarks and protocol studies

18. BEACON: a comprehensive benchmark for RNA language models.
    *NeurIPS 2024 D&B*. arXiv:2406.10391. [memo-verified]
19. Multi-model fine-tuning benchmark ("良渚"): unified evaluation of
    genomic language models. *Nature Communications* (2025-12).
    DOI: 10.1038/s41467-025-66899-y. [memo-verified; family-split
    finding is our H-motivation]
20. RNAscope: a multi-task RNA LM evaluation. *ICML 2025* submission
    #2439 (rejected; OpenReview record). [memo-verified review
    archive]
21. NABench: large-scale RNA fitness benchmark. *ICLR 2026* submission
    #9519 (rejected; OpenReview record, 4 reviewers + author
    responses archived in-group). [protocol-sensitivity quotes]
22. Zero-shot 21-model RNA benchmark ("深圳湾"). *Briefings in
    Bioinformatics* (2026-03). DOI: 10.1093/bib/bbag098.
    [memo-verified]
23. RNAGym: DMS fitness + structure benchmark. ICLR 2025 workshop
    (Harvard Marks/Das Labs). [id-verify]
24. mRNABench: mRNA-specific frozen-embedding evaluation.
    bioRxiv (2025-07). [Morris Lab]
25. OmniGenBench: modular genomic-LM evaluation platform.
    arXiv:2505.14402 (2025). [memo-verified]
26. Zablocki, D. et al. Comparative evaluation of RNA LLMs on
    secondary-structure prediction. *Briefings in Bioinformatics*
    26(2), bbaf137 (2025). [PMC11982019 — memo-verified]
27. REDIAL: over-parametrization diagnostics for RNA language models.
    bioRxiv 2026-05-12 (Univ. of Maryland, Tiwary group).
    [memo-verified; M1 monitoring target]

### Scaling-law and data-constrained literature

28. Muennighoff, N. et al. Scaling data-constrained language models.
    *NeurIPS 2023*. [repetition-epoch validity bound]
29. Hoffmann, J. et al. Training compute-optimal large language models
    (Chinchilla). arXiv:2203.15556 (2022). [id-verify]
30. Kaplan, J. et al. Scaling laws for neural language models.
    arXiv:2001.08361 (2020). [id-verify]

### Reference-integrity note (D6 gate)

All in-text citations in DRAFT v1.0 map to this list. The following
were deliberately NOT cited (memo §9 "勿引用" list + discipline):
Deep Research weak matches (flow-matching RNA-FM title confusion;
guided transfer learning for RNA-seq). Unverified identifiers are
marked [id-verify] and must be resolved in the final bib pass —
no DOI in this draft is fabricated; only memo-verified DOIs are
printed.
