# refs.bib 文献核验记录

核验日期：2026-11-26  
对象：`refs.bib` 的 19 个引用键及 `论文/DRAFT_refs.md` 中特别指定的 DenAdel 文献。  
原则：优先采用出版商、正式 proceedings、arXiv、bioRxiv、PMC 和 Crossref 注册记录；未可靠确认的字段不猜测。此次只改文献元数据，未改正文科学数字或主张。

## 汇总结论

- 原有 22 处 `TODO` 中，18 处已用可靠来源补齐；当前剩 4 处 `TODO`，均标注“待用户确认”。
- 未解决项仅为：RNAscope 的作者及 OpenReview URL、Vishniakov 条目的 ICLR 2026 OpenReview 标识/接收状态、NABench 的 ICLR 2026 拒稿状态。OpenReview API 对这些匿名请求返回 403，不能据此推断或伪造论坛 ID。
- 另修正了 TODO 之外的书目错误：Rives 的文章号、Li 的首作者、GARNET 的题名/首作者/文章号、Papazoglou 的 DOI、Zablocki 的正式题名。
- DenAdel 文献已独立核验，但它不属于当前 `refs.bib` 的 19 个条目；未新增未被正文引用的条目。

## 逐条核验

### 1. `rives_biological`

- 原值：`PNAS 118, e2015679118 (2021)`；DOI 为 TODO。
- 核验值：*Proceedings of the National Academy of Sciences* 118(15), **e2016239118** (2021)；DOI **10.1073/pnas.2016239118**。原文章号有转置错误。
- 来源：https://api.crossref.org/works/10.1073/pnas.2016239118 ；https://doi.org/10.1073/pnas.2016239118
- 状态：**已核验并纠错**。

### 2. `li_feature`

- 原值：`Li, H. and others`；出版者与标识符为 TODO；PMLR 235:27351–27375。
- 核验值：Francesca-Zhoufan Li, Ava P. Amini, Yisong Yue, Kevin K. Yang, Alex Xijie Lu；出版者 **PMLR**；稳定记录 `pmlr-v235-li24a`；URL https://proceedings.mlr.press/v235/li24a.html 。原首作者缩写 `H.` 错误。
- 来源：https://proceedings.mlr.press/v235/li24a.html
- 状态：**已核验并纠错**。

### 3. `hou_scaling`（重点移植引用）

- 原值：Hou, C.; Liu, D.; Zafar, A.; Shen, Y.；*Nature Computational Science* (2026)；卷页为 TODO。
- 核验值：Chao Hou, Di Liu, Aziz Zafar, Yufeng Shen；**6(7), 778–788 (2026)**；DOI 10.1038/s43588-026-01010-z。
- 来源：https://www.nature.com/articles/s43588-026-01010-z ；https://api.crossref.org/works/10.1038/s43588-026-01010-z
- 状态：**已核验并补齐**。

### 4. `prabakaran_uncertainty`

- 原值：Prabakaran, R. & Bromberg, Y.；*Nature Methods* 23, 796–804 (2026)。
- 核验值：R. Prabakaran, **Yana Bromberg**；23(4), 796–804 (2026)；DOI 10.1038/s41592-026-03028-7。卷页年均一致。
- 来源：https://api.crossref.org/works/10.1038/s41592-026-03028-7
- 状态：**已核验；补全第二作者名和期号**。

### 5. `simon_interplm`（重点移植引用）

- 原值：Simon, E. & Zou, J.；*Nature Methods* 22, 2107–2117 (2025)。
- 核验值：**Elana Simon, James Zou**；22(10), 2107–2117 (2025)；DOI 10.1038/s41592-025-02836-7。原卷页年及 DOI 一致。
- 来源：https://www.nature.com/articles/s41592-025-02836-7 ；https://api.crossref.org/works/10.1038/s41592-025-02836-7
- 状态：**已核验；补全作者名和期号**。

### 6. `vishniakov_tokenization`

- 原值：`Vishniakov, D. and others`；ICLR 2026 Poster；页码和标识符为 TODO。
- 核验值：**Kirill Vishniakov**, Karthik Viswanathan, Aleksandr Medvedev, Praveenkumar Kanithi, Marco A. F. Pimentel, Ronnie Rajan, Shadab Khan；相关 bioRxiv DOI **10.1101/2024.12.18.628606**。会议论文无 proceedings 页码，未虚构页码。原首作者缩写 `D.` 错误。
- 来源：https://api.crossref.org/works/10.1101/2024.12.18.628606 ；https://www.biorxiv.org/content/10.1101/2024.12.18.628606v2.full
- 状态：**部分核验，待用户确认**。Crossref 保留 “Tokenization to Transfer” 题名；bioRxiv v2 改题为 “Genomic Foundationless Models: Pretraining Does Not Promise Performance”。ICLR 2026 OpenReview 标识及 Poster 状态未能从可访问官方记录独立确认，保留 TODO。

### 7. `garnet`（重点出处）

- 原值：Shulgina, A. et al.；“GARNET: generative RNA language models validated by ribosome thermotolerance experiments”；15, **10543** (2024)；DOI 10.1038/s41467-024-54812-y。
- 核验值：**Yekaterina Shulgina** et al.；正式题名 **“RNA language models predict mutations that improve RNA function”**；15(1), **10627** (2024)；DOI 不变。出版商正文明确关联 GARNET Database 与 `GARNET_DL` 代码，因此这是同一工作的真实出版记录，原题名与文章号不准确。
- 来源：https://www.nature.com/articles/s41467-024-54812-y ；https://api.crossref.org/works/10.1038/s41467-024-54812-y
- 状态：**已核验并纠错**。

### 8. `papazoglou_attention`

- 原值：Papazoglou, I. et al.；65, 6483–6498 (2025)；DOI **10.1021/acs.jcim.5c02094**。
- 核验值：Ioannis Papazoglou, Alexios Chatzigoulas, George Tsekenis, Zoe Cournia；65(13), 6483–6498 (2025)；DOI **10.1021/acs.jcim.4c02094**。原 DOI 的年份段 `4c` 被误写为 `5c`；`5c02094` 实际对应另一篇 ADMET 论文。
- 来源：https://api.crossref.org/works/10.1021/acs.jcim.4c02094 ；错误 DOI 对照：https://api.crossref.org/works/10.1021/acs.jcim.5c02094
- 状态：**已核验并纠错**。

### 9. `beacon`

- 原值：作者为 TODO；描述性题名 “BEACON: a comprehensive benchmark for RNA language models”；页码和 arXiv 主分类为 TODO；arXiv:2406.10391。
- 核验值：Yuchen Ren, Zhiyuan Chen, Lifeng Qiao, Hongtai Jing, Yuchen Cai, Sheng Xu, Peng Ye, Xinzhu Ma, Siqi Sun, Hongliang Yan, Dong Yuan, Wanli Ouyang, Xihui Liu；正式题名 **“BEACON: Benchmark for Comprehensive RNA Tasks and Language Models”**；*Advances in Neural Information Processing Systems 37*, **92891–92921** (2024)；DOI **10.52202/079017-2949**；arXiv 主分类 **q-bio.QM**。
- 来源：https://arxiv.org/abs/2406.10391 ；https://api.crossref.org/works/10.52202/079017-2949
- 状态：**已核验并补齐**。

### 10. `genomic_finetuning`

- 原值：作者为 TODO；描述性题名 “Multi-model fine-tuning benchmark: unified evaluation of genomic language models”；卷与文章号为 TODO。
- 核验值：Ningyuan You, Chang Liu, Hai Lin, Sai Wu, Gang Chen, Ning Shen；正式题名 **“Benchmarking pre-trained genomic language models for RNA sequence-related predictive applications”**；*Nature Communications* **17(1), 223**；线上发表日期 2025-12-07；DOI 10.1038/s41467-025-66899-y。
- 来源：https://www.nature.com/articles/s41467-025-66899-y ；https://api.crossref.org/works/10.1038/s41467-025-66899-y
- 状态：**已核验并补齐**。

### 11. `rnascope`

- 原值：作者及 OpenReview URL 为 TODO；ICML 2025 submission #2439, rejected。
- 核验值：未获得可独立核验的作者名单或论坛 URL；保留原有描述性题名和会议投稿信息，不填充猜测值。
- 来源：尝试官方 API https://api2.openreview.net/notes?number=2439&content.venueid=ICML.cc%2F2025%2FConference 及旧 API 入口，均返回 403；arXiv 题名检索未定位该评测论文。
- 状态：**待用户确认**。作者与 URL 两处 TODO 保留。

### 12. `nabench`

- 原值：作者及 URL 为 TODO；描述性题名 “NABench: large-scale RNA fitness benchmark”；年份 2026；ICLR 2026 submission #9519, rejected。
- 核验值：Zhongmin Li, Runze Ma, Jiahao Tan, Chengzi Tan, Shuangjia Zheng；正式题名 **“NABench: Large-Scale Benchmarks of Nucleotide Foundation Models for Fitness Prediction”**；arXiv:**2511.02888 [q-bio.GN]**，提交于 **2025-11-04**；DOI 10.48550/arXiv.2511.02888；URL https://arxiv.org/abs/2511.02888 。
- 来源：https://arxiv.org/abs/2511.02888
- 状态：**部分核验，待用户确认**。作者、题名、arXiv 标识与 URL 已补齐；ICLR 2026 拒稿状态因 OpenReview 不可访问而保留 TODO。条目年份按实际 arXiv 记录改为 2025。

### 13. `zero_shot_rna`（深圳湾基准，重点出处）

- 原值：作者为 TODO；描述性题名 “Zero-shot 21-model RNA benchmark”；卷与文章号为 TODO。
- 核验值：He Wang, Yikun Zhang, Jie Chen, Jian Zhan, Yaoqi Zhou；正式题名 **“Zero-shot benchmarking of RNA language models in structural, functional, and evolutionary learning”**；*Briefings in Bioinformatics* **27(2), bbag098** (2026)；DOI 10.1093/bib/bbag098。Crossref 作者单位包含 Shenzhen Bay Laboratory。
- 来源：https://api.crossref.org/works/10.1093/bib/bbag098 ；https://doi.org/10.1093/bib/bbag098
- 状态：**已核验并补齐**。

### 14. `rnagym`

- 原值：Arora, R. et al.；bioRxiv DOI 10.1101/2025.06.16.660049；URL 为 TODO。
- 核验值：Rohit Arora et al.；题名及 DOI 一致；稳定 URL https://doi.org/10.1101/2025.06.16.660049 。
- 来源：https://api.crossref.org/works/10.1101/2025.06.16.660049 ；https://doi.org/10.1101/2025.06.16.660049
- 状态：**已核验并补齐**。

### 15. `mrnabench`

- 原值：作者、正式题名、DOI、URL 均为 TODO；bioRxiv 2025-07。
- 核验值：Ruian (Ian) Shi, Taykhoom Dalal, Philip Fradkin, Divya Koyyalagunta, Simran Chhabria, Andrew Jung, Cyrus Tam, Defne Ceyhan, Jessica Lin, Kaitlin U. Laverty, Ilyes Baali, Bo Wang, Quaid Morris；正式题名 **“mRNABench: A curated benchmark for mature mRNA property and function prediction”**；DOI **10.1101/2025.07.05.662870**；2025-07-08。
- 来源：https://www.biorxiv.org/content/10.1101/2025.07.05.662870v1.full ；https://api.crossref.org/works/10.1101/2025.07.05.662870
- 状态：**已核验并补齐**。

### 16. `zablocki_structure`

- 原值：Zablocki, D. et al.；描述性题名 “Comparative evaluation of RNA LLMs on secondary-structure prediction”；26(2), bbaf137 (2025)；DOI 为 TODO。
- 核验值：**Luciano I. Zablocki**, Leandro A. Bugnon, Matias Gerard, Leandro Di Persia, Georgina Stegmayer, Diego H. Milone；正式题名 **“Comprehensive benchmarking of large language models for RNA secondary structure prediction”**；26(2), bbaf137 (2025)；DOI **10.1093/bib/bbaf137**。
- 来源：https://pmc.ncbi.nlm.nih.gov/articles/PMC11982019/ ；https://api.crossref.org/works/10.1093/bib/bbaf137
- 状态：**已核验并纠错**。

### 17. `redial`（重点出处）

- 原值：作者、正式题名、DOI、URL 为 TODO；描述性题名 “REDIAL: over-parametrization diagnostics for RNA language models”；bioRxiv 2026-05-12。
- 核验值：Da Teng, Yunrui Qiu, Gokulakannan Sakthivel, Akashnathan Aranganathan, Lukas Herron, Pratyush Tiwary；正式题名 **“Detecting and quantifying overparametrization in RNA language models with REDIAL”**；DOI **10.64898/2026.05.11.724344**；发布日期 2026-05-12。
- 来源：https://www.biorxiv.org/content/10.64898/2026.05.11.724344v1.full ；https://api.crossref.org/works/10.64898/2026.05.11.724344
- 状态：**已核验并补齐**。

### 18. `muennighoff_data`

- 原值：Muennighoff, N. et al.；NeurIPS 2023；页码与标识符为 TODO。
- 核验值：Niklas Muennighoff, Alexander Rush, Boaz Barak, Teven Le Scao, Nouamane Tazi, Aleksandra Piktus, Sampo Pyysalo, Thomas Wolf, Colin Raffel；*Advances in Neural Information Processing Systems* **36**, **50358–50376** (2023)；DOI **10.52202/075280-2191**。
- 来源：https://papers.nips.cc/paper_files/paper/2023/hash/9d89448b63ce1e2e8dc7af72c984c196-Abstract-Conference.html
- 状态：**已核验并补齐**。

### 19. `hoffmann_chinchilla`

- 原值：Hoffmann, J. et al.；题名附说明 “(Chinchilla)”；arXiv:2203.15556；主分类为 TODO。
- 核验值：正式题名 **“Training Compute-Optimal Large Language Models”**；Jordan Hoffmann et al.；arXiv:2203.15556 **[cs.CL]**；DOI 10.48550/arXiv.2203.15556；2022。
- 来源：https://arxiv.org/abs/2203.15556
- 状态：**已核验并补齐**。

## 特别补充：DenAdel 单细胞移植引用（不在当前 19 条中）

- 原值：DenAdel, A. et al.；*Nature Methods* (2026)；DOI 10.1038/s41592-026-03120-y。
- 核验值：Alan DenAdel, Madeline Hughes, Akshaya Thoutam, Anay Gupta, Andrew W. Navia, Nicolo Fusi, Srivatsan Raghavan, Peter S. Winter, Ava P. Amini, Lorin Crawford；“Evaluating the role of pretraining dataset size and diversity on single-cell foundation model performance”；*Nature Methods* **23(7), 1447–1457** (2026)；DOI 一致。
- 来源：https://www.nature.com/articles/s41592-026-03120-y ；https://api.crossref.org/works/10.1038/s41592-026-03120-y
- 状态：**已核验；未加入 `refs.bib`**。当前 arXiv 包的 19 个正文引用键不含 DenAdel，新增会使文献集合脱离正文引用映射。

## 编译验收记录

- 命令：`tectonic --keep-logs --keep-intermediates main.tex`（在 `arxiv_package` 目录运行），最终退出码 0。
- 产物：`main.pdf` 共 30 页；`main.bbl` 已同步更新。
- 引用闭合：正文 19 个唯一引用键、`refs.bib` 19 个条目、`main.bbl` 19 个 `\bibitem` 三者集合完全一致，19/19 PASS。
- 日志：无 undefined citation、无 LaTeX error、无缺字警告；仅有原构建报告已记录的版面 overfull/underfull 警告。
- PDF：`References` 与 `[19]` 均存在，`??` 未定义引用标记为 0；Rives、Papazoglou、Zablocki、REDIAL 的修正标识符均出现在最终 PDF 中。
- 待确认项：`refs.bib` 剩 4 处 `TODO`，均以 `pending user confirmation` 标注，含义为本报告的“待用户确认”；bib 内使用英文是为了避免原 LaTeX 字体缺字。
