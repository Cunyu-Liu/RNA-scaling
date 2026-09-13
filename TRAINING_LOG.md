# RNA-Sc 训练记录（TRAINING LOG）

> 项目：RNA-LM 迁移学习机理研究（SPEC v1.1，S0-S12）
> 服务器：A100 集群（bms-18937653-012），用户 cunyuliu
> 代码：/home/cunyuliu/rna-sc（git → github.com/Cunyu-Liu/RNA-scaling）
> 数据/runs：/mnt/cunyuliu/rna-sc；环境：conda toktokenbench（torch 2.6.0+cu124）

## 2026-09-13（Day 0：交接 + 基建 + wave1 启动）

### 交接完成项
- 00-03 全部交接文档通读（备忘录/SPEC/TASKS/CHECKLIST）；
- TokBench 资产定位：~/tokenizer-benchmark（代码）+ /mnt/cunyuliu/tokenizer-benchmark（数据）；
- 切分资产深验证（验收 A3+B1，证据 /mnt/cunyuliu/rna-sc/evidence/split8080_deep_verify.json）：
  29,012,227 行 / 3,357,201 簇 / **簇级泄漏 0 / 序列级泄漏 0 → PASS**；
  split: train 14.13M(48.7%) / family_validation 7.53M(25.9%) / family_test 7.08M(24.4%) / validation 164k / test 109k；
  字母表纯净 ACGU；长度 10-583,414 nt。
  ⚠️ 文档中的"8/1/1 比例"与实际不符——TokBench 真实设计是家族级大 held-out（~50%），
  S0 的"held-out 10%"口径用 validation+test（合计 1%）承担，family_validation/test 留给家族级
  评测切分。待导师确认口径。

### 基建（T0.2）
- /home/cunyuliu/rna-sc：ALiBi MLM encoder（SDPA 显存安全版）/ frozen config / split 流式
  MLM 数据管线（nt 口径）/ 训练 runner（manifest 纪律）/ ledger（Z5）/ status 监控 /
  smoke / supervisor 调度器 / family_table / per-layer probe；
- GitHub：Cunyu-Liu/RNA-scaling（main，2 commits）。

### 验收进度（CHECKLIST 对照）
- A3 split 三查 ✓（深验证 PASS）；A4 家族分配表 ✓（release22_cluster_split.parquet，
  3.36M 簇 cluster_pure=true，覆盖 release22 全量；外部数据集 join 留待评测集接入时做）；
- A5 ledger 单测 ✓（claim 防重复 + adopt 存活进程实测）；A6 冒烟 ✓ ALL PASS；
- A7 文献复现：未完成（列入 Day 1-7）。

### 冒烟测试（A6）— ALL PASS
mask 确定性/15% 比例/四档参数量 ±12%/前向反向/真实 split 批处理/loss 1.956→1.465/零 CPU 回退。

### 事故与决策记录（重要）
1. **架构修订**：SPEC 表格的宽扁架构参数量超目标 2-3 倍（1M 档实际 3.15M）。修订为深窄形态：
   1M=18层/d64(0.89M)、10M=20层/d192(8.86M)、30M=12层/d480(33.2M, +10.7% 容差内)、
   100M=23层/d576(91.6M)。理由：等参数量是 scaling 归因前提（SPEC 7.3 表的层配置是备忘录
   里的近似示意；以参数量目标为准是 Li et al. 惯例）。30M 保留 RiNALMo-micro(33M) 对齐。
2. **wave1 OOM 事故**：nvidia-smi 快照显示 GPU6/7 各 ~2GB 已用（判断 >38GB 空闲），
   实际 GPU6/7 是 5.1GB 物理卡且其他用户进程随后涌入 → 3 run OOM（证据：log 堆栈）。
   **修复**：GPU 选择改 torch.cuda.mem_get_info 真实值；batch_nt 32768→16384；
   supervisor 崩溃自动 --resume-from 最新 ckpt（≤5 次）。
3. **重复启动事故**：supervisor 初版未跳过"running 且 pid 存活"的 ledger 行，重复启动 10M。
   已修复（adopt + skip）。

### wave1 运行状态（UTC 09:40 启动，全部 2.0B nt 预算）
| run | model | GPU | 角色 | 50min 吞吐 | ETA |
|---|---|---|---|---|---|
| rnasc_10M_s17 | RNA-Sc-10M | 1（共享） | S1 scaling 轴 | 32k nt/s | ~0.7 天 |
| rnasc_30M_s17 | RNA-Sc-30M | 1（共享+3外部进程竞争） | S1 scaling 轴 | 4.3k nt/s | ~5.3 天 |
| rnasc_1M_s17 | RNA-Sc-1M | 7 | S1 scaling 轴 | 10.7k nt/s | ~2.2 天 |
| rnasc_30M_s17c1M | 30M×1M 语料 | 2 | S2 数据量轴 | 10.7k nt/s | ~2.2 天 |

早期 loss（vs 随机基线 ln4≈1.386）：10M 1.27@97M；1M 1.26@32M；30M 1.30@13M；
c1M 1.26@32M —— 全部低于随机基线，学习正常。
30M 主档在 GPU1 与 4 个外部用户进程竞争（100% util 分摊），吞吐仅 4.3k；
若 24h 后仍 <10k nt/s，考虑迁往更空闲的卡（supervisor 支持崩溃迁移，或等 c1M 完成后
用其 GPU2 卡位）。

### 队列（wave.json，supervisor 自动领取）
10M → 100M s17 → 100M s29 → 100M s43 → 30M-c10M（S2 轴第二点）。
首个 100M nt checkpoint 预计今晚落盘（val_interval=100M nt）；到时立即跑 probe 冒烟。

### 监控体系
- 服务器 cron：每 2h rna_sc.status + ledger sync + 告警检查（CPU 回退/停滞）；
- 本地定时任务：每日 08:30/20:30 巡检（读取 status.json，规则含停止 CPU 回退 run、
  追加队列、记录 val loss、git commit）。

### 下一步（Day 1+）
- [ ] 首个 ckpt 落盘后：probe.py 冒烟（rna_type 分类，family_validation→family_test）；
- [ ] 30M 吞吐评估，必要时迁移 GPU；
- [ ] A7 文献复现（RiNALMo 或 RNA-FM 评测设置之一）；
- [ ] S4 随机初始化对照（评测侧，跑同一 probe 协议）；
- [ ] 100M 档 3 种子（已排队）。

## 2026-09-14（Day 1 早：首个 checkpoint + 首个逐层 probe）

### 里程碑
- **RNA-Sc-10M 首个 100M-nt checkpoint + validation 落盘**：val_loss=1.2447（4M nt 验证，
  cpu_fallback=0）。训练 loss 1.27→1.16@127M，持续下降。
- wave1 其余：1M 34M nt / c1M 34M nt / 30M 15M nt（30M 与 GPU1 上 4 个外部进程竞争，
  吞吐 ~4.5k nt/s，24h 后再评估是否迁移）。

### 首个逐层 probe 结果（S7 day-1 协议，非最终科学结论）
- 任务：rna_type 分类（19 类，family_validation 20k → family_test 4k，家族级切分）；
- probe：逐层 mean-pooled states + 线性头（8 epochs）；
- **多数类基线 acc=0.636**；probe 各层 acc 0.90-0.93 —— 显著超基线，家族信息已被编码；
- **acc 随层深单调下降（L0 0.926 → L19 0.896）**：浅层信号强于深层，与 Li et al. 的
  "低层特征主导"方向一致（早期证据，非结论——需 2B nt 完整训练 + 多规模对比后才能写）；
- macro-F1 ~0.2：小类（snRNA/tmRNA/lncRNA 各 <1%）未学好，符合 100M/2000M=5% 训练进度；
- probe 协议 bug 修复记录：v1 的 label 流与 batch 流错位（label_iter yield 整行块导致
  样本只有 64 个）→ 重写为单流配对（sequence/rna_type 同行读取）；v2 结果统计有效。

### 结论（记录，非科学声明）
1. 管线全链路验证通过：训练 → checkpoint → 逐层 probe → 家族级评测；
2. 监控/记录/推送闭环运转正常；
3. 下一步：等 10M 完整 2B nt 后重跑 probe（同协议），观察曲线变化；30M/1M 到 100M nt
   后各跑一次；100M 三种子入队自动接力。

### 20:35 巡检简报（2026-09-13 20:30 定时巡检）

- 简报：4 run 全部正常训练；cpu_fallback_count 全 0（逐一核验各 run manifest.json 的 validations；status.json 汇总层该字段为 null 未填充，"no alerts" 无法区分 null/0，故以 manifest 为准）；supervisor 无崩溃（无 relaunch/Traceback 记录，ledger attempts=1）；无 run DONE → wave.json 无需追加（8 任务已全在队列，含 100M s17/s29/s43 与 30M-c10M）；100M_s17 正在等待 ≥8GB+1.5GB margin 的空闲 GPU（supervisor 正常排队行为）。
- 各 run 进度（nt / % / best_val_loss / cpu_fallback）：10M_s17 319M/2.0B / 16.0% / 1.0338@300M / 0；1M_s17 129M/2.0B / 6.5% / 1.2851@100M / 0；30M_s17_c1M 141M/2.0B / 7.0% / 1.1190@100M / 0；30M_s17 60M/2.0B / 3.0% / 首个 ckpt（100M nt）未落盘 / 0。吞吐按日志时间戳估算：10M ~40k、c1M ~16k、1M ~13k、30M ~5.8k nt/s（30M 仍受 GPU1 外部进程挤占；24h 吞吐评估点为 09-14 傍晚，届时决定是否迁移）。
- 新落盘首个 100M-nt ckpt 记录（日期/run_id/nt/val_loss）：
  - 2026-09-13 / rnasc_1M_s17 / nt=100007541 / val_loss=1.2851
  - 2026-09-13 / rnasc_30M_s17c1M / nt=100007541 / val_loss=1.1190
- 10M_s17 后续 ckpt：200M val=1.0966、300M val=1.0338（训练 val 持续下降；以上为运行数据记录，非科学结论）。
- 注：上一小节标题日期"2026-09-14"与服务器时钟（Sun Sep 13 20:35 CST 2026）不一致，本节按服务器时钟如实记录；未改动历史小节。

## 2026-09-14（Day 1：跨规模早期信号 @ 100M-nt 对齐点）

### 三个 run 的 100M-nt 对齐快照（S1 scaling 轴第一个可比点）
| run | val_loss@100M | probe acc（最佳层） | probe macro-F1（最佳层） |
|---|---|---|---|
| RNA-Sc-1M | 1.2851 | 0.917 (L1) | 0.121 (L1) |
| RNA-Sc-10M | 1.2447 | 0.934 (L2) | 0.214 (L7) |
| RNA-Sc-30M-c1M（1M 语料） | 1.1190 | 0.931 (L4) | 0.269 (L5) |

10M 验证轨迹：1.2447@100M → 1.0966@200M → 1.0338@300M（稳定下降）。

### 早期信号（均为中间观察，非最终结论；完整 2B nt 后才可写进论文）
1. **困惑度随参数量单调改善**（1.285 → 1.245 → 1.119）——S1 预期方向；
2. **probe macro-F1 随参数量提升**（0.121 → 0.214 → 0.269）且 30M 在浅中层数值更平稳；
3. **三个模型 acc 均随层深下降**（浅层 > 深层），与 Li et al. 蛋白域"低层特征主导"
   方向一致的早期证据（H4）；
4. c1M（30M 参数 × 1M 语料）与 10M（8.9M 参数 × 全语料）对比：语料受限下 30M 参数
   仍有更好 val loss（1.119 vs 1.245）——数据量轴的早期分化点，等 c10M/full 落盘后
   才能下结论（S2）。

### 待办
- 30M main（65M nt，吞吐 ~8k nt/s，GPU 竞争缓解后回升）到 100M 后跑同协议 probe；
- 10M 完成（~8h）后自动启动 100M s17（wave.json 接力）；
- 所有 probe 结果持续追加 /mnt/cunyuliu/rna-sc/eval/probe_results.jsonl。
