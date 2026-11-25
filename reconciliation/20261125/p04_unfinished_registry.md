# P0.4 未完成臂登记

- 生成时间：`2026-11-25T17:03:47+08:00`
- 备份根（只读）：`/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc`
- 范围：RNA-Sc 受控家族纯测评证据对账；未修改备份或交接文档。
- 检索范围：`eval_evidence_logs/eval/*.jsonl` 共 11 个文件（含 2 个 AppleDouble 元数据文件）；对全部文件做不区分大小写的原始字节检索，`marscorpus` 与 `rnacentral` 均为 **0 命中**。

## 三列表

| 未完成臂/证据缺口 | 权重位置 | 可复测性 |
|---|---|---|
| MARS 30M（训练与探针均未完成；status.md 无此行） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-30M_s17_marscorpus：目录为空，无 ckpt | 不可从备份复测；须先训练并产生权重。全量 eval/*.jsonl 的 marscorpus 原始字节检索为 0 行。 |
| MARS 100M（状态快照 400M/2000M，20.0%；无探针） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-100M_s17_marscorpus：4 个 ckpt，最新 ckpt_nt400023183_step041442.pt | 可复测现有 400,023,183 nt 中间权重；不能冒充完整 2B 臂。全量探针检索为 0 行。 |
| MARS 300M（状态快照 200M/2000M，10.0%；无探针） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-300M_s17_marscorpus：2 个 ckpt，最新 ckpt_nt200010618_step020735.pt | 可复测现有 200,010,618 nt 中间权重；不能冒充完整 2B 臂。全量探针检索为 0 行。 |
| RNAcentral 30M（训练与探针均未完成；status.md 无此行） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-30M_s17_rnacentral：目录为空，无 ckpt | 不可从备份复测；须先训练并产生权重。全量 eval/*.jsonl 的 rnacentral 原始字节检索为 0 行。 |
| RNAcentral 100M（状态快照 300M/2000M，15.0%，但备份无权重；无探针） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-100M_s17_rnacentral：目录为空，无 ckpt | 不可从备份复测。状态快照称 ckpts=3，与本地空目录不符；须找回权重或重训，不能登记为可复测。 |
| RNAcentral 300M（状态快照 200M/2000M，10.0%，但备份无权重；无探针） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-300M_s17_rnacentral：目录为空，无 ckpt | 不可从备份复测。状态快照称 ckpts=2，与本地空目录不符；须找回权重或重训，不能登记为可复测。 |
| RFamCap 30M：bpRNA 结构探针缺口（训练 DONE；分类探针已在位） | /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-30M_s17_rfamcap：2 个留存 ckpt，最新 ckpt_nt1900086380_step250287.pt | 可用 1,900,086,380 nt 权重补测 bpRNA；现有 rna_type 为 24 行，bpRNA 为 0 行。此项是探针缺口，不是训练未完成。 |

## RFamCap 30M/100M 对照核查

- 两者训练 manifest 均为 `DONE`，`final_nt=2000003378`；备份各留存 1,800,083,135 与 1,900,086,380 nt 两个检查点（manifest 历史记录各 17 个）。探针使用的最终留存点为 1,900,086,380 nt。
- 30M：`rna_type` 24 行，覆盖 `ckpt_nt=200006790` 与 `1900086380`；`bpRNA paired-position` 0 行，因此只登记结构探针缺口。
- 100M：`rna_type` 46 行（两个 ckpt 各 23 行），`bpRNA paired-position` 23 行；分类与结构探针均在位，不列入未完成表。
- 计数来源：`probe_results.jsonl` 与 `probe_structure_results.jsonl` 中按 `run`、`task` 全量解析计数；具体行号见两个 manifest 的 `rfamcap_evidence_lines`。不是训练种子重复，也不涉及 bootstrap。

## 停机状态与判读边界

- `status.md:3` 快照生成于 `2026-10-14T12:20:03`；第 7、10、25、27 行分别保留 MARS 100M、RNAcentral 100M、MARS 300M、RNAcentral 300M 的 `RUNNING`，均为 `thr=0 nt/s`，末尾汇总为 4 个非 DONE。
- `ledger.jsonl` 共 26 行，尾部 5 行均为 DONE，最新一行是第 26 行 `rnasc_30M_s17b59`，`updated_utc=2026-10-04T19:30:22.447398Z`；全账本 MARS/RNAcentral 记录为 0 行。具体尾部记录见 manifest。
- 裁决：文件支持“训练已停滞的停机快照”判读，不支持把这些臂写成已完成；旧 `RUNNING` 不是 2026-11-25 的实时进程证据。远端当日 `nvidia-smi` 仅见 codonflow/llr 两个 Python 进程，未见 RNA-Sc 进程（详见 `p04_remote_check.md`）。

## 异常

- RNAcentral 100M/300M 的 `status.md` 分别称已有 3/2 个 ckpt，但备份对应目录为空；不能推定权重可复测。
- MARS 30M 与 RNAcentral 30M 目录也为空，且未进入 `status.md`；不能将 30M 视作已有中间权重。
- RFamCap 30M 缺 bpRNA 结构探针，而 RFamCap 100M 在位。

## 复现

```bash
/usr/bin/python3 '/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125/p04_unfinished_registry.py'
```

输入哈希、逐文件检索结果、权重目录清单和探针行号见 `p04_manifest.json` 与 `p04_unfinished_registry.manifest.json`。
