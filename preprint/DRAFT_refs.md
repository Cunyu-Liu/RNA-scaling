## References (full list, v1.0 — 2026-09-22)

> Source discipline: every entry below is drawn from the project memo's
> §9 verified-evidence table (three-source cross-checked during
> 2026-09-10..13 research). Identifiers shown ONLY where the memo
> verified them; the [id-verify] bib pass was COMPLETED 2026-10-04
> (passes 1-5, 14 entries, 12 corrections, all DOIs/arXiv IDs
> web-verified two-source; D6 gate: clean).

### Protein-domain anchors (methods template)

1. Rives, A. et al. Biological structure and function emerge from
   scaling unsupervised learning to 250 million protein sequences.
   *PNAS* 118, e2015679118 (2021). [PMC8053943 — memo-verified]
2. Li, H. et al. Feature Reuse and Scaling: Understanding Transfer
   Learning with Protein Language Models. *ICML 2024*, PMLR
   235:27351-27375. [full text read; zero-self-training fact verified
   via paper + repo + first-author CV — memo §2.3]
3. Hou, C., Liu, D., Zafar, A. & Shen, Y. Understanding language
   model scaling for protein fitness prediction. *Nature Computational
   Science* (2026). DOI 10.1038/s43588-026-01010-z. [S13 method source;
   web-verified 2026-10-04; title corrected, PMID 42443524]
4. Prabakaran, R. & Bromberg, Y. Quantifying uncertainty in protein
   representations across models and tasks. *Nature Methods* 23, 796-804
   (2026). DOI 10.1038/s41592-026-03028-7. [S14 method source; web-verified
   2026-10-04 two-source; coauthor corrected: Bromberg, Y.]
5. Simon, E. & Zou, J. InterPLM: discovering interpretable features
   in protein language models via sparse autoencoders. *Nature Methods*
   22, 2107-2117 (2025). DOI 10.1038/s41592-025-02836-7. [S15 source;
   Crossref-verified 2026-10-04; first name corrected: Elana Pearl Simon]
6. Vishniakov, D. et al. Tokenization to Transfer: Do Genomic
   Foundation Models Learn Good Representations? *ICLR 2026* Poster.
   [m42-health; DNA-domain random-init study; must-cite per SPEC 1.2]
7. DenAdel, A. et al. Evaluating the role of pretraining dataset
   size and diversity on single-cell foundation model performance.
   *Nature Methods* (2026). DOI 10.1038/s41592-026-03120-y. [H5
   reverse-prior source; web-verified 2026-10-04; title corrected]
8. Lin, Z. et al. Evolutionary-scale prediction of atomic-level
   protein structure with a language model. *Science* 379(6637),
   1123-1130 (2023). DOI 10.1126/science.ade2574. [web-verified
   2026-10-04 three-source; volume/pages corrected]

### RNA language models (evaluation targets / same-family series)

9. Penić, R.J., Vlašić, T., Huber, R.G., Wan, Y., Šikić, M. RiNALMo:
   general-purpose RNA language models can generalize well on structure
   prediction tasks. *Nature Communications* 16, 5671 (2025).
   DOI 10.1038/s41467-025-60872-5; arXiv:2403.00043. [web-verified
   2026-10-03, two-source rule; micro/mega/giga checkpoints on Zenodo]
10. Chen, J. et al. Interpretable RNA foundation model from
    unannotated data for highly accurate RNA structure and function
    predictions. arXiv:2204.00300 (2022); bioRxiv 10.1101/2022.08.06.503062.
    [NEVER journal-published — Crossref/Europe-PMC/Semantic-Scholar
    three-source check 2026-10-04; prior 'Nature Methods 2023' and
    'Brief Bioinform bbaad445' claims both WRONG]
11. Yin, W. et al. ERNIE-RNA: an RNA language model with
    structure-enhanced representations. *Nature Communications* 16,
    10076 (2025). DOI 10.1038/s41467-025-64972-0. [web-verified
    2026-10-04; author and venue corrected — cite the journal version]
12. Wang, N. et al. Multi-purpose RNA language modelling with
    motif-aware pretraining and type-guided fine-tuning (RNAErnie).
    *Nature Machine Intelligence* 6, 548-557 (2024). DOI
    10.1038/s42256-024-00836-4. [Crossref-verified 2026-10-04;
    first author corrected: Ning Wang]
13. RiboSpan: long-context (10K nt) 1.61B RNA encoder. arXiv:2608.22849
    (2026). [memo-verified; M4 monitoring list]
14. Tahmid, M.T. et al. BiRNA-BERT allows efficient RNA language
    modeling with adaptive tokenization. *Communications Biology* 8,
    1621 (2025). DOI 10.1038/s42003-025-08982-0. [web-verified
    2026-10-04; title and first author corrected]
15. Li, G. et al. HydraRNA: a hybrid architecture based full-length
    RNA language model. *Genome Biology* 26 (2025). DOI
    10.1186/s13059-025-03853-7. [Crossref-verified 2026-10-04]
16. Shulgina, A. et al. GARNET: generative RNA language models
    validated by ribosome thermotolerance experiments. *Nature
    Communications* 15, 10543 (2024).
    DOI: 10.1038/s41467-024-54812-y. [memo-verified]
17. Papazoglou, I. et al. Predicting RNA structure utilizing
    attention from pretrained language models. *J. Chem. Inf. Model.*
    65, 6483-6498 (2025). DOI 10.1021/acs.jcim.5c02094. [layer-wise
    precedent; web-verified 2026-10-04; title/initial corrected]

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
23. Arora, R. et al. RNAGym: large-scale benchmarks for RNA fitness
    and structure prediction. bioRxiv 10.1101/2025.06.16.660049 (2025).
    [Harvard/Marks Lab; Crossref-verified 2026-10-04; cite preprint
    record — ICLR-workshop attribution unconfirmed]
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
29. Hoffmann, J. et al. Training compute-optimal large language
    models (Chinchilla). arXiv:2203.15556 (2022). [arXiv-API-verified
    2026-10-04]
30. Kaplan, J. et al. Scaling laws for neural language models.
    arXiv:2001.08361 (2020). [arXiv-API-verified 2026-10-04]

### Reference-integrity note (D6 gate)

All in-text citations in DRAFT v1.0 map to this list. The following
were deliberately NOT cited (memo §9 "勿引用" list + discipline):
Deep Research weak matches (flow-matching RNA-FM title confusion;
guided transfer learning for RNA-seq). Unverified identifiers are
COMPLETED 2026-10-04: all 14 [id-verify] entries resolved (12
corrections; see preprint/id_verify_log.md passes 1-5) —
no DOI in this draft is fabricated; only memo-verified DOIs are
printed.
