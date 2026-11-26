# REPRODUCE.md — RNA-Sc 训练与测评全量复现命令目录

> 目的：任何人拿到 orico 备份（或 GitHub 仓库）后，能独立复现本项目**全部已得出**的训练与测评结果。
> 权威源约定：**GitHub 仓库 = 代码权威源**；**runs/&lt;RUN_ID&gt;/manifest.json = 每个 run 的配置地面真值**（arch/seed/全部超参/val 曲线/best ckpt，本文件表格仅为索引）；**eval/*.jsonl = 测评结果地面真值**（可逐行 diff）。
> 2026-11-26 发布盘点见 [`repo_manifest.md`](repo_manifest.md)；其中权重、数据可读性和未收口臂状态优先于本文件的历史快照。

## 0. 前置条件

- **环境**：历史 conda env `toktokenbench`（python 3.10, torch 2.6.0+cu124）。旧文档引用的 orico `09_env_exports/toktokenbench.yml` / `toktokenbench.pip.txt` 不在本轮核实的备份根内，故不能把 `conda env create -f toktokenbench.yml` 当作已验证的一键命令；须先找回环境导出或按历史版本重建并记录新环境哈希。
- **代码**：`git clone` 本仓库，checkout 到本文件所在提交（服务器 /home/cunyuliu/rna-sc，GitHub 为权威源；orico `03_RNA迁移学习_rna-sc/code_git` 为离线快照）。
- **训练数据依赖与边界**：
  - A. 从 orico 恢复**可读子集**：`release22_cluster_split.parquet`、`r22_train_rfamcap.parquet` 及测评数据集（bpRNA_parsed / archiveii / Rfam.cm 六件套等）。2026-11-26 实测 `r22_train_reweighted.parquet`、`rinalmo_corpus_v1.parquet`、`mars_corpus.parquet` 均为 footer 不可读残片，不能再宣称可直接恢复全部训练语料；逐文件状态见 `p2/20261126/evidence/split_rebuild/source_inventory.csv`。
  - B. **原 split8080 缺失，当前不能等价重建**：`release22_split_8080.parquet` 未备份，备份与两台远端均无精确命中。`release22_cluster_split.parquet` 只有 `cluster_id,split`，不能单独恢复 29,012,227 条序列。2026-11-26 全量重建虽完成 canonical/dedup 和 MMseqs2 聚类，但新代表 3,334,304 ≠ 旧代表 3,357,201，且出现旧 train 序列进入新 family held-out 的泄漏，故重建产物不得替代原文件。P2.5/P2.7/P2.4 按终裁不做，P3 多种子与曝光臂不触发。证据与完整边界见 `repo_manifest.md` §4–§5；不要沿用旧版“约 40–60 min 确定性重建”命令。
  - C. 语料 parquet 重建：`build_rinalmo_corpus.py` / `build_corpus_mars.py` / `build_corpus_rnacentral.py` / `s3_reweight_corpus.py`（原始公开源：Rfam release、RiNALMo recipe、MARS OMIX003037、RNAcentral FTP）。
- **外部基线权重**：
  - RiNALMo（giga/mega/micro）+ NucleicBERT：orico `03_RNA迁移学习_rna-sc/ext_baselines/`（4.6G，已含 model.safetensors / pretrained.pt）。
  - **RNA-FM：本项目唯一未随备份携带的外部权重**，官方 GitHub `ml4bio/RNA-FM` 下载 `RNA-FM_pretrained.pth`（1.19GB），放至 `probe_rnafm.py:CKPT` 指定路径（或改该常量）。

## 1. 训练复现

### 1.1 通用命令模板

```bash
python -m rna_sc.train --model <MODEL> --seed <SEED> --device <GPU_ID> \
  --out-dir /mnt/<...>/runs/<RUN_ID> \
  [--corpus-tag <tag>] [--train-parquet <corpus.parquet>] \
  [--corpus-nseq <N> | --cluster-allowlist <allowlist>] \
  [--budget-nt <NT>] [--early-stop-patience 5] [--resume-from <ckpt>]
```

默认超参 = `rna_sc/config.py` 冻结配方：budget 2.0B nt / batch 16384 nt / context 1024 / lr 3e-4（1M-30M ×2.0）/ warmup 0.5% / MLM 15%(80/10/10) / ckpt+val 每 100M nt / val 4M nt（validation split）。**逐 run 的权威配置以 manifest.json 为准**。

### 1.2 已完成 32 run 清单（orico `runs_final2_ckpt/runs/` 共 38 目录：32 终态 + 2 MARS 中间臂 + 4 空目录）

以下 32 个终态 run 各含终态 ckpt + manifest.json；完整分组、权重位置和远端三份上传清单见 `repo_manifest.md` §3。

| 轴 | run | 特殊参数 |
|---|---|---|
| 主家族·种子 | 1M/10M/30M/100M × s17/s29/s43 | 无（默认全量 2B） |
| 主家族·大模型 | 300M/650M × s17 | 无 |
| 预算臂 b59 | 30M/100M/300M/650M × _b59 | `--budget-nt 5900000000 --corpus-tag b59` |
| 语料规模 S2 | 30M_c1M/_c10M、10M_c1Mcs/_c5Mcs、30M_s29_c1Mcs | `--corpus-nseq N`（c 系）或 `--cluster-allowlist`（cs 系）；精确值见各 manifest `corpus_nseq`/`cluster_allowlist` 字段 |
| 语料族 | 30M/100M _rfamcap、10M/30M/100M/300M _rinalmocorpus | `--train-parquet r22_train_rfamcap.parquet` / `--train-parquet rinalmo_corpus_v1.parquet` + 对应 `--corpus-tag` |
| 多样性 rw | 10M/30M/100M _rw1 | 先 `s3_reweight_corpus.py`（产出 r22_train_reweighted.parquet + 权重 json）再 `train_s3_rw.py` |

（同表可由 `for d in runs/*/; do jq -r '[.model_id,.seed,.config.corpus_tag,.config.budget_nt] @csv' $d/manifest.json; done` 机器生成。）

### 1.3 未完成 6 臂（语谱实验，停机中断）

- MARS 100M/300M：备份分别保留至 400,023,183 nt（4 ckpt）和 200,010,618 nt（2 ckpt），只能复测中间点，不能冒充 2B 终态。
- MARS 30M、RNAcentral 30M/100M/300M：备份目录为空。RNAcentral 100M/300M 的旧状态快照与空目录不一致，须找回权重或重训。
- **这 6 臂没有已完成的正式探针结果，不能登记为完成。** MARS、RiNALMo、reweighted parquet 备份残片不可读，RNAcentral 大语料缺失，因此 `resume_or_restore.sh` 只是历史恢复入口，不代表数据和权重已齐备；逐项边界见 `repo_manifest.md` §4、§6。

## 2. 测评复现（确定性推理，可精确复现论文全部表格数字）

```bash
python -m rna_sc.probe --run-dir runs/<RUN_ID> --device <GPU_ID>          # 主链（n-train 20000 / n-eval 4000）
python -m rna_sc.probe --run-dir runs/<RUN_ID> --random-init 3            # 随机初始化对照（B 系证据）
python -m rna_sc.probe --run-dir runs/<RUN_ID> --moment-matched 3         # 动量匹配对照
python -m rna_sc.eval_matrix --device <GPU_ID> [--model <MODEL>]          # 全矩阵（flock 账本防并发）
```

- 注意：eval_matrix 的 `--device` 旧默认 6 是 cgroup 陷阱卡，新集群须换卡并重验（详见 06 指南陷阱清单）。
- 结果落 `eval/*.jsonl`；orico 备份内同名文件可逐行 diff（probe_results / probe_results_ext / probe_structure_results / eval_matrix_results 及全部 .bak 历史版）。
- 外部基线：`probe_rnafm.py`（RNA-FM）/ `probe_rinalmo.py`（RiNALMo）/ `s14_rns_ext.py`（NucleicBERT 等扩展集）。

## 3. 结果核对（三层）

1. 训练侧：`manifest.json` 的 `best_val_loss`、checkpoints val 曲线、`params` 与 arch 一致性。
2. 测评侧：重放后 `eval/*.jsonl` 与 orico 备份 md5/逐行比对。
3. 论文数字门：当前发布脚本为 `p4/20261126/assert_numbers.py`，输入与结果见同目录 `coverage_report.md`、`assertion_results.csv`。旧版 `redteam_numbers.py` / `redteam_final.py` 不在当前仓库，不再作为可执行命令宣称。

## 4. 已知偏差声明（诚实边界）

- **训练跨硬件非比特级一致**（CUDA 归约顺序差异，行业标准事实）：同种子+同数据+同配置在异型 GPU 上 val_loss 复现到 ~1e-3 量级，最佳 ckpt 选择可能翻转相邻 val 点；不影响结论方向。
- **测评侧精确复现**：probe 为确定性推理（固定数据子样 + 推理无 dropout），配合已备份 ckpt，论文数字可逐位重放（同卡型）或到浮点聚合容差（跨卡型）。
- 30M 语谱两臂从零重训与"假如不停机"轨迹有 RNG 顺序差异——无已得出的结果，不在复现范围内。

## 5. 快速通道（不重训，直接复核论文数字）

orico 的已有测评资产构成最小复核包：`runs_final2_ckpt`（32 终态 ckpt+manifest）+ `eval/*.jsonl` + `code_git` + 测评数据集（`data_corpus/` 等）；环境按 §0 重建，历史 `09_env_exports` 仍需另行定位。
只需：重建 conda 环境 → clone 代码（或用快照）→ 恢复测评数据集 → 跑 §2 三条 probe 命令 → 与备份 jsonl diff。**对已有普通 probe 复核无需 split8080 或训练语料 parquet；RNA-FM 仅外部基线需要。** 需要原 `family_validation/family_test` 流的 P2.5/P2.7 不在此快速通道内，且已因原 split 缺失按终裁不做。
