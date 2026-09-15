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

## 2026-09-14（Day 1 晚：30M main 首个对齐点，四点 scaling 快照齐了）

### 100M-nt 对齐点全家福（S1 早期信号）
| run | val_loss@100M | probe best acc (层) | probe best F1 (层) |
|---|---|---|---|
| RNA-Sc-1M | 1.2851 | 0.917 (L1) | 0.121 (L1) |
| RNA-Sc-10M | 1.2447 | 0.934 (L2) | 0.214 (L7) |
| RNA-Sc-30M (全语料) | **1.1214** | 0.935 (L5) | **0.285** (L4) |
| RNA-Sc-30M (c1M 语料) | 1.1190 | 0.931 (L4) | 0.269 (L5) |

### 中间观察（非科学结论，2B nt 完成后才可写）
1. **困惑度单调改善 1M→30M**（1.285→1.245→1.121）——S1 曲线在 100M-nt 对齐点
   已呈现参数量收益，且 30M 优势明显；
2. **probe F1 随参数量单调改善**（0.121→0.214→0.285），最佳层位随模型加深
   略微后移（L1→L2/L7→L4）；
3. **数据量轴（S2）早期分化**：30M 参数下 1M 语料 vs 全语料的 val loss 几乎
   持平（1.1190 vs 1.1214）且 F1 仅差 0.016 —— 100M-nt 阶段语料还没有成为瓶颈
   （预期：语料效应在更大 exposure 时显现，2B nt 后再判定 H5）；
4. 10M 已进入 540M nt（loss 0.836，val 1.034@300M），预计 ~5h 后完成 2B；
   届时 supervisor 自动启动 100M s17（显存满足时）。

### 运维注记
- supervisor 持续在等 9.5GB 空闲显存启动 100M 档（外部进程占用波动 8.5-13GB
  区间）；这是显存安全判断而非 gate，符合规则；
- 30M main 吞吐回升至 ~10k nt/s（GPU1 竞争缓解）。

## 2026-09-15（Day 2：100M 档启动 + 五点 scaling 快照）

### 队列自动接力成功
- supervisor 在 GPU4/GPU5 出现空闲显存后自动启动 **RNA-Sc-100M s17 与 s29**（双种子并行）；
- 当前 6 训练并行：1M/10M/30M/30M-c1M/100M-s17/100M-s29（多 GPU 并行规则执行中）；
- 100M s17 首个验证点：**val=1.0734@100M nt** —— 100M 档在首个对齐点即给出
  全家族最优困惑度。

### 五点 scaling 快照（100M-nt 对齐，全部同协议）
| model | params | val_loss | best acc (层) | best F1 (层) |
|---|---|---|---|---|
| 1M | 0.89M | 1.2851 | 0.917 (L1) | 0.121 (L1) |
| 10M | 8.86M | 1.2447 | 0.934 (L2) | 0.214 (L7) |
| 30M | 33.2M | 1.1214 | 0.935 (L5) | 0.285 (L4) |
| 30M-c1M | 33.2M | 1.1190 | 0.931 (L4) | 0.269 (L5) |
| 100M | 91.6M | **1.0734** | 0.938 (L5) | 0.289 (L2) |

### 中间观察（早期，非结论）
1. 困惑度随参数量单调改善贯穿 1M→100M（1.285→1.073）；
2. probe F1 在 30M 处增益放缓（0.285→0.289）——若 2B nt 后维持，即"probe 任务
   不随规模继续提升"的 RNA 早期迹象（对应 Li et al. 核心结论，需最终确认）；
3. 100M 的最佳 probe 层在最浅部（L2）出现峰值 F1，深层同样衰减——浅层主导
   信号在 5 个模型一致；
4. 10M 已 690M nt（34.5%），val 轨迹 1.034→0.968 单调降。

### 待办
- 10M 完成 2B 后重跑 probe（关键对比点：2B 完整训练 vs 100M-nt 早期）；
- 100M s43 等待显存接力；A7 文献复现安排在训练后台期。

## 2026-09-15（Day 2 晚：S4 随机初始化对照首批数据）

### S4 对照（H2 排除实验，10M 档，probe 协议完全相同）
| 模型 | best acc | best macro-F1 |
|---|---|---|
| RNA-Sc-10M @100M nt（预训练 5% 预算） | 0.934 | **0.214** |
| RNA-Sc-10M 随机初始化（seed 17） | 0.954 | 0.131 |

### 中间观察（H2 的早期证据，非最终结论）
1. **预训练增益超出归纳偏置**：F1 0.214 vs 0.131（+64%），仅用 5% 训练预算；
2. **acc 指标在类别不平衡下误导**：随机初始化的 acc 反而更高（多数类坍缩），
   预训练模型把概率质量分散到稀有类（F1 升、acc 微降）——确立 macro-F1 为
   probe 主指标的决策依据；
3. 随机初始化 F1=0.131 仍高于"只预测多数类"的理论值（~0.04）：线性头从随机
   特征里读出了序列组成信息（GC 含量等）——这本身是 H2 的量级参照。

### 运维注记
- 100M s43 启动时 OOM 一次（GPU0 被外部 27.6GB 进程挤压）→ supervisor 标记
  pending 自动重试中，符合设计（无人工干预）；
- 10M 预计 ~3h 后完成 2B nt，届时（a）GPU1 释放 ~17GB 供 s43 使用；
  （b）对最终 checkpoint 重跑 probe（完整训练 vs 100M-nt 早期的关键对比）。

## 2026-09-16（Day 3：30M 迁移 + supervisor 修复 + 吞吐账本）

### 运维
1. **30M 主动迁移**：GPU1 上与自家两个 deltaflow 任务（各 8.4GB + 100%util）竞争，
   吞吐仅 ~6k nt/s（ETA 78h）。kill 后 supervisor 自动 --resume-from 续训，
   现迁至 GPU5（与 100M-s29 共享，7.5k nt/s）；
2. **supervisor 修复（关键 bug）**：被 adopt 的 run 进程死亡后永远留在 procs
   字典不被 reap，导致 pending 状态的 run 永不重启。修复：adopted run 每周期
   检查 ledger pid 存活性。此 bug 曾让 30M 卡在 pending ~20 分钟（人为发现）；
3. 100M s43 仍在队列（GPU0 被外部 27.6GB 进程占满）。

### 全局吞吐账本（当前时刻）
| run | GPU | 进度 | 速率 | ETA |
|---|---|---|---|---|
| 10M | 1 | 1181M/2000M (59%) | 47k/s | ~5.9h |
| 30M | 5 (迁移后) | 114M/2000M | 7.5k/s | ~70h |
| 30M-c1M | 2 | 477M/2000M (24%) | ~14k/s | ~30h |
| 1M | 7 | 443M/2000M (22%) | ~11k/s | ~39h |
| 100M-s17 | 4 | ~400M/2000M | ~20k/s | ~22h |
| 100M-s29 | 5 | ~320M/2000M | ~16k/s | ~29h |

### 30M 吞吐的根因分析
30M 主档 12 层 d480 深窄架构 = 每 nt 的 kernel launch 数更多；GPU5 与 100M-s29
共享（双双 100% util）。**两个选项**：
(a) 维持现状：30M 70h ≈ 3 天内完成，可接受（其他 run 更早完成释放卡位）；
(b) 等 10M 完成（5.9h）后独占 GPU1：~10-12k/s，ETA 缩至 ~45h。
**决策：选 (a) 维持现状**，10M 完成后 GPU1 空间留给 100M-s43（优先级更高——
3 种子是 R5 统计计划的硬要求）。30M 非统计关键路径。

### 科学进度（中间观察）
- 10M val 轨迹：0.9350@900M → 0.9253@1B —— 持续下降；
- 30M-c1M 训练 loss 0.82@477M（vs 30M-full 0.90@199M：语料轴分化开始显现，
  全语料 loss 更低但 nt 不对齐，暂不下结论）。

## 2026-09-14（Day 2 深夜事故：ledger 写竞态导致 100M 重复启动 — 已根治）

### 事故时间线
- 22:39/22:55 supervisor 启动 100M s17(GPU4)/s29(GPU5)，ledger 有 running 行；
- 03:54/04:06/04:40 supervisor 又启动了 s17/s29/s43 的**重复进程**（s17 重复进程
  与原进程同卡 GPU4；s29 重复在 GPU0；s43 是首次启动）；
- **根因**：ledger.jsonl 是读-改-写文件（_load→修改→_write 整文件重写），
  monitoring cron 的 `ledger sync`（每 2h）与 supervisor 的 `update` 并发时
  交错执行（读 A / 读 A / 写 B / 写 A′）→ 100M 两行被静默丢弃 →
  supervisor 认为它们未在运行 → 重复启动；
- **影响评估**：s17/s29 的重复进程与原进程写同一 out-dir 约 40/35 分钟。
  由于批流确定性（同 seed 同流同初始化+断点续训轨迹一致），两进程产生的
  checkpoint 在科学上等价；manifest 的 validations 单调一致（s17:
  1.073→0.972→0.926→0.902）。重复进程已 kill，原进程保留继续跑；
  s43 首启无冲突（其重复进程其实是首次启动，被我误杀后现已由修复版
  supervisor 重新启动）。

### 根治措施（87751c1）
1. ledger 所有读-改-写循环加 **fcntl flock 排他锁**（ledger.lock）；
2. 新增 `upsert()` 恢复工具，重建了丢失的 100M 行；
3. supervisor 重启后正确 adopt 全部 6 个存活进程（无重复）。

### 当前并行（8 训练）
1M(GPU7) / 10M(GPU1) / 30M-full(GPU5) / 30M-c1M(GPU2) / 30M-c10M(GPU3, 新)
/ 100M-s17(GPU4) / 100M-s29(GPU5) / 100M-s43(GPU0, 新)

### 教训（写入实验纪律）
- 多写入者的状态文件必须加锁（TokBench closure ledger 单写入者设计的前提
  被我的监控 cron 打破了）；
- 数据完整性检查升级：ckpt 文件冲突时以 manifest validations 的单调性为
  判据（本次用于确认无科学损害）。

## 2026-09-14（巡检简报：100M s29/s43 首个对齐点记录）

### 巡检简报（09:51 CST，规则逐项执行）
- 8 run 全部 RUNNING，无 DONE → wave.json 无需追加（优先级任务 100M s17/s29/s43、30M-c10M 均已入队）；
- cpu_fallback_count 全 0（以各 run manifest.json validations 字段逐一核验，status.json 汇总层该字段为 null 未填充）；
- supervisor 无崩溃（日志无 relaunch / rc!=0 / Traceback）；
- 进度（nt / % / last_val / fallback）：100M-s17 700M/35%/0.8634/0；100M-s29 500M/25%/0.8860/0；100M-s43 200M/10%/0.9687/0；10M-s17 1900M/95%/0.8716/0（接近完成）；1M-s17 700M/35%/1.1748/0；30M-s17 200M/10%/1.0183/0；30M-s17_c10M 100M/5%/1.1198/0；30M-s17_c1M 600M/30%/0.9215/0。
- 首个 100M-nt checkpoint val loss 记录（日期/run_id/nt/val_loss）：
  - 2026-09-14 / RNA-Sc-100M_s29 / nt=100007541 / val_loss=1.0770
  - 2026-09-14 / RNA-Sc-100M_s43 / nt=100007541 / val_loss=1.0699
- 注：s17 的 100M val（1.0734）已见于前节；100M 三种子首个对齐点 val 1.0734/1.0770/1.0699 相近（运行记录，非科学结论）。

## 2026-09-15（Day 3：RNA-Sc-10M 完整 2.0B nt 训练完成 — 首个完整数据点）

### 10M 完成状态（首个 2B 完整 run）
- final: nt=2,000,017,903 / steps=106,883 / best_val=**0.8716**（@1.9B nt）
  / throughput 34,024 nt/s / peak VRAM 1.1GB / **cpu_fallback=0**（GPU 纪律全程合规）
- val 轨迹（20 点，100M→1.9B）：1.2447 → 0.8716，单调下降，无过拟合迹象
  （held-out 家族级隔离下仍持续改善 = 真实泛化而非记忆）。

### 完整训练后的 probe（vs 100M-nt 早期）——重要中间发现
| 10M checkpoint | best F1 (层) | 深层（L8-19）F1 |
|---|---|---|
| @100M nt（5% 预算） | 0.214 (L7) | 0.20-0.23 |
| @2B nt（完成） | **0.174 (L1)** | **0.11-0.12（塌缩）** |

**观察（中间结论，需 30M/100M 完成后确认）**：
1. 更多预训练 → probe 可分性不升反降，且**最佳层从 L7 前移到 L1**、
   深层线性可分性塌缩（0.2→0.12）；
2. 该模式与 Li et al. "低层特征主导、最后层并非最优" 的方向一致且更强；
3. 候选机制（后续 S5/S7 分析方向）：MLM 专化导致深层表征向重建目标收窄
   （anisotropy 假设），浅层保留更通用的组成统计；
4. 与 val loss 持续下降并存 = "困惑度改善"与"线性可迁移性"脱钩——
   这正是协议矩阵（S9）要量化的核心分离。

⚠️ 纪律检查：以上是中间观察。10M 单模型结论不得写入论文正文；等
30M/100M/c1M/c10M 完成后做规模×训练量的二维对比再定结论。

## 2026-09-14（Day 3 晚：supervisor DONE 检测 bug + 孤儿进程收编）

### 事故与修复（连续第 3 个调度 bug，全部根治）
1. **DONE 误判为死亡**：adopted-run 的 pid 消失后直接置 pending 重启——
   但 10M 是正常 DONE 退出（manifest status=DONE）。被重启了一次
   （重复进程 1936M nt 处被杀，无数据损害：确定性轨迹 + 只 append log）。
   修复：reap 前先查 manifest DONE；ledger status=done 的直接出队；
2. **孤儿进程收编**：supervisor 升级期间被 orphan 化的 s43（1398834，
   293M nt）和 c10M（1398839）没有 ledger 行（行在竞态中丢失/未写过），
   导致新 supervisor 重复启动 c10M。已杀 orphan 重复进程、upsert 登记
   正确 pid。当前 7 训练进程与 ledger 完全一致（30M-full/c1M/c10M、
   1M、100M×3 种子）。

### 修正后的阵列状态（全部 healthy，fallback=0）
| run | GPU | 备注 |
|---|---|---|
| 30M-full | 5 | 与 100M-s29 共卡 |
| 30M-c1M | 2 | 640M nt |
| 30M-c10M | 1 | 101M nt（supervisor 重启后） |
| 1M | 7 | 700M nt（35%） |
| 100M-s17/s29/s43 | 4/5/0 | 700M/500M/295M |

调度器经历 4 轮实战修复（GPU 快照失真→OOM；adopt 死亡 reap；ledger
竞态→重复启动；DONE 误判重启），现在同时满足：真实显存选择、断点续训、
进程死亡检测（含正常完成）、ledger 锁安全。实战检验完成。

## 2026-09-14（Day 3 深夜：对齐 nt 的困惑度阶梯 — S1 强信号）

### @700M nt 对齐困惑度（家族级隔离 held-out）
| model | val@700M |
|---|---|
| 1M | 1.1748 |
| 10M | 0.9554 |
| 30M-c1M | 0.9092 |
| 100M-s17 | **0.8634** |

**关键观察**：100M 在 800M nt（0.8569）已低于 10M 完整 2B nt 训练的最终值
（0.8716）——参数量收益在困惑度维度上强劲且大（非 Li et al. "不 scale"
情形的困惑度侧；他们的 claim 是下游任务侧，正是 probe 矩阵要补的另一半）。

各 run val 轨迹全部单调下降、无过拟合；30M-full 在共享 GPU 上较慢但健康。

## 2026-09-15（Day 4：30M-c1M 完成 + 数据量轴首批对照数据）

### 30M-c1M 完成状态
- DONE @ 849.9M nt（1M 语料自然上限：14.1M 序列流式中止于 corpus_nseq=1M，
  实际暴露 8.5 亿 nt）best_val=**0.8960**，fallback=0；
- 最终 probe（19 类 rna_type，家族级切分）：**best F1=0.315 (L7)**，
  中层（L4-L11）全面 0.28-0.32 —— 显著高于 10M-full 的 0.174！

### 三个完成 run 的对比表（S1/S2 核心数据雏形）
| run | 参数 | 语料 | nt | best val | probe best F1 (层) |
|---|---|---|---|---|---|
| 10M-full | 8.9M | 14.1M 序列 | 2.0B | 0.8716 | 0.174 (L1) |
| 30M-c1M | 33.2M | **1M 序列** | 0.85B | 0.8960 | **0.315 (L7)** |
| (30M-full 训练中，383M nt) | 33.2M | 14.1M | — | val 0.978@300M | — |

### 中间观察（S2 数据量轴 + H4 层位）
1. **30M 参数 × 小语料（1M 序列）的 probe F1（0.315）远超 10M × 全语料
   （0.174）**——参数量对下游线性可分性的贡献大于语料量（需 30M-full
   落盘后定稿对比）；
2. **层位模式相反**：10M 完整训练后最佳层塌到 L1（深层塌缩）；
   c1M 的最佳层在 L7 且中层保持高值——**语料受限（约 5 个 epoch 等效
   重复）时深层仍可分**。两种"训练量饱和"的形态完全不同：
   - 大语料充分训练 → 深层向 MLM 专化（可分性降）
   - 小语料重复暴露 → 深层保持可分性（但 val loss 差：0.896 vs 0.872）
   - 支持"困惑度与迁移性脱钩"，且给出第二个维度（数据量）的调制；
3. c1M@100M-nt 早期 probe F1=0.269 → final 0.315（上升）：小语料下
   继续训练 probe 改善——与 10M（0.214→0.174 下降）方向相反。
   **这是 S2（语料构成假设 H5）的核心早期证据。**

## 2026-09-15（Day 4 晚：Q1-Q9 方案修订落地）

### 代码落地
1. **probe 层轴改相对深度（Q2 执行）**：rel_depth + depth_band
   （early/middle/late）写入 probe_results.jsonl，汇总报 band 均值；
2. **簇级分层抽样（Q3 执行）**：subsample.py 上线，c1Mcs arm 已生成
   （1,000,011 序列 / 190,917 完整簇，seed=17）并加入 wave 队列；
   prefix-c1M 保留为采样方式对照；
3. data.py 支持 cluster_allowlist 流式过滤；train.py/supervisor 透传。

### 两个新 arm 状态
- c1Mcs（cluster-stratified 1M 语料）排队中（等 GPU 显存）；
- RiNALMo-arch 轴（Q5）：排 100M 三种子之后，工程改造 3-7 天。

### 两篇参考文精读结论（详见 DECISIONS_V1.1_20260915.md）
- Nat Methods 数据量文：learning saturation point 分析框架直接采用
  （S2 曲线标准统计量）；三多样性指标（Shannon/Gini-Simpson/Vendi）作为
  S3 量化口径；其"多样性提升不改善性能"是 H5 的反向先验；
- Schmirler 微调文：其"微调几乎总是赢"结论成为我们三协议矩阵的待检验
  对象（Claim 2 组成部分）；删除 LoRA 的决策由其"LoRA≈全参微调"结论背书。

## 2026-09-15（Day 4 夜：例行巡检——全队列健康，无硬规则触发）

### 巡检快照（status 生成 2026-09-14 20:34 服务器本地）
| run | 状态/GPU | nt 进度 | best/last val | fallback |
|---|---|---|---|---|
| 30M-full | RUNNING GPU5 | 500M/2000M（25%） | last 0.937 | — |
| 10M-full | **DONE** | 2000M/2000M（100%） | best 0.8716 | 0 |
| 30M-c1M | **DONE**（1M 语料自然耗尽） | 850M | best 0.8960 | 0 |
| 1M-full | RUNNING GPU7 | 1100M/2000M（55%） | last 1.137 | — |
| 100M-s17 | RUNNING GPU4 | 1400M/2000M（70%） | last 0.818 | — |
| 100M-s29 | RUNNING GPU5 | 900M/2000M（45%） | last 0.851 | — |
| 100M-s43 | RUNNING GPU0 | 700M/2000M（35%） | last 0.863 | — |
| 30M-c10M | RUNNING GPU1 | 300M/2000M（15%） | last 0.978 | — |
| 30M-c1Mcs | RUNNING GPU3（wave 第 9 项，19:53 起） | 31M+ | loss 1.16 | — |

### 规则执行结果
1. **CPU fallback：零事件**（硬规则未触发）。两个 DONE run 的 manifest 全程
   fallback=0（10M 19 次验证 / c1M 8 次）；全部训练日志无非零 fallback 行；
2. **崩溃/重启：零**。supervisor 收编 6 个存活 run 并新启 c1Mcs（共 7 个训练
   进程，CPU 99%+），supervisor.log 无 attempt/relaunch 循环，无需日志诊断；
3. **最终 probe 覆盖：已满足，无需补跑**：
   - 10M-full：probe_results.jsonl 已含 ckpt_nt=2000M（200008867）全量协议
     记录（n_train=20000/n_eval=4000，20 层），best F1=0.2347@L19；
     1900M best_val ckpt 的 probe best F1=0.174@L1（Day 4 已记）；
   - 30M-c1M：最终 ckpt（800M，best_val ckpt）probe 已有，best F1=0.315@L7；
   - ⚠ probe_results.jsonl 中 10M@2000M 混有一组 n_train=64/n_eval=31 的
     smoke 记录（含 F1=1.0 小样本假象），汇总分析必须按 n_train/n_eval
     过滤排除，不得作为科学结论；
4. **wave.json**：8 基础 run + c1Mcs 均在队；c1Mcs 已启动（簇级分层 1M 语料：
   1,000,011 序列 / 190,917 完整簇 / seed=17）。6/8 未 DONE，本轮不追加；
5. 预计完成顺序：100M-s17（剩 600M，约 9h）→ 1M（约 22h）→ 100M-s29 /
   30M-full → 100M-s43 / 30M-c10M。

（规则 6 未触发：尚有 6/8 未 DONE，S1 scaling 对比表待全量完成后定稿。）

## 2026-09-15（Day 4 深夜：PPT 重做——原风格对齐 + 9 问全覆盖）

- 删除首轮 4 页未对齐风格的页面；
- 按原 PPT 视觉规格解剖后重做 6 页（"08 · 方案修订 1/6 ~ 6/6"）：
  kicker 11pt 金 #8A6D1F / 标题 23pt #1A1A1A / 分栏卡片 #F7F5F0 / 卡头
  #2B4C7E / 高亮条 #FDF9F0 / Microsoft YaHei / 分隔线 / 页脚页码全套一致；
- 9 个问题全覆盖：Q1+Q2（页 19）、Q3+Q4（页 20）、Q5（页 21）、
  Q6（页 22）、Q7+Q8（页 23）、Q9 两篇参考文（页 24）；
- PPT 同步回交接目录（共 23 页）。

## 2026-09-16（Day 5：模型复查 + TASKS V2 + 红队自批）

### 模型复查（Q-复查 1）
- 补入线 1：RIBOSPAN（1.61B，已在监控清单 M4）、BiRNA-BERT（117M，双 token 化）；
- 排除：Moirain（生成式）、设计向 LM（GoForth 等）——与判别式协议矩阵不匹配；
- 主流基准侧交叉核对（BEACON/良渚/RNAGym/深圳湾 21 模型）无其他遗漏。

### 下游任务价值对齐（Q-复查 2）
- 一期 ncRNA 四任务全部为主流基准标配（BEACON+RiNALMo 官方评测全覆盖）；
- 局部变异类（RNAGym DMS）对标 Li et al. GB1/AAV 范式，二期。

### TASKS V2（Q-复查 3）：事无巨细 todo-list 版
- 每项任务带 ID/验收物/依赖/状态框；六个阶段 T0-T5 全量细化至 ~50 项原子任务；
- 红队 5 审稿人 9 条意见全部成立或部分成立，修正并入对应任务项。

### 红队修正行动项（本周）
- S12 解耦指数提前（Infernal cmscan CPU 任务与训练并行）；
- c1Mcs-s29 第二种子入队（采样对照归因严谨性）；
- probe 类别平衡 + CLS/attention-pool 头升级列入 T1.2.2。

## 2026-09-16（Day 5 深夜：100M-s17 完成 + 层位-规模交互首个完整数据点）

### RNA-Sc-100M s17 完成状态
- DONE：nt=2,000,003,270 / steps=213,514 / best_val=**0.7964** / 18.4k nt/s /
  peak 3.1GB / **fallback=0**（GPU 纪律全程合规）；
- val 轨迹 20 点单调降：1.0734@100M → 0.7964@1.9B（无过拟合）。

### 最终 probe 的层带（band）模式 —— S1×S7 交互核心发现（中间结论）
| 模型 | best F1 | 主导层带 | 逐层形态 |
|---|---|---|---|
| 10M-full | 0.174 (L1) | **early** | 深层塌缩（0.11-0.12）|
| 30M-c1M | 0.315 (L7) | **middle** | 中层宽带高位 |
| 100M-s17 | 0.303（late band 均值）| **late** | 随深度单调上升（0.223→0.260→0.303）|

**中间结论（需 30M-full/1M 完成后确认）**：
1. **可用表征的层位随参数量后移**（early→middle→late）——规模不仅提升
   绝对性能，还改变"信息所在层"的分布。这是 S1（scaling）×S7（逐层）
   的交互效应，Li et al. 蛋白域报告"低层主导"，RNA 100M 档呈现相反
   方向（**若最终确认即为跨域差异发现，论文 Claim 1 候选**）；
2. 100M 是唯一"用满深度"的模型：23 层全部参与表征构建（F1 单调升），
   而 10M 只有浅层可用（深层 MLM 专化塌缩）；
3. 困惑度阶梯（1M 1.1557@800M / 10M 0.8716 / 30M-c1M 0.8960 /
   100M 0.7964）与层位后移同步——"更大模型=更深的有效表征"。

⚠️ 纪律：以上为 3/8 模型的中间观察；1M/30M-full/c10M/s29/s43 完成后
重跑汇总（含红队 C/E 修正：去 rRNA 分层 + CI 语义）才可写入论文。

### 红队修正落地状态
- [x] c1Mcs-s29 第二种子已入队（wave.json 10 runs）；
- [x] S12 提前：infernal 环境装好，家族一致性表完成（2000 家族，
  evidence/s12_family_identity.json）；Rfam.cm 下载后补 CM 得分半轴；
- [~] probe 类别平衡 + attention-pool 头：列入 T1.2.2（随三任务扩展一起）。

## Day 6 (2026-09-15 上午) — T1 评测线推进

### SSP (secondary-structure) 评测线落地
- 数据: BEACON secondary-structure (bpRNA) 完整接入
  - bpRNA.csv (13419 seqs, 含 dot-bracket) + TR0/VL0/TS0 npy pair matrices
  - HF 分页修复: tree API 逐页 1000 → 13420 files 全枚举 (cursor 域名回写 hf-mirror)
  - 校验: 50 样本 dot-bracket ↔ npy 矩阵 100% 一致 (agree=50, disagree=0)
  - 下载并行化 16 threads, TS0 优先 (1305/1305), VL0, TR0 补全中
- 代码: rnafteval 新增 tasks/ssp.py, finetune_ssp.py (PairHead 对称双头), baselines_ssp.py
  - smoke PASS (GPU7, 46.3s, 350MB): ledger/F1/数据链路全通
- v1 传统基线 (random split, n_test=300, max_len=192):
  - bracket_prior: F1=0.0146 (P=0.0073/R=0.892) — 互补碱基先验
  - kmer_lgbm_pair: F1=0.0427 (P=0.022/R=0.598) — local pair 特征 LGBM
  - 结论: 局部特征天花板极低 → SSP 必须全局/层级证据 (LM 的价值空间)
- 正式矩阵启动: RNA-Sc-10M × {frozen, head-only, lora} (GPU6/7) random split

### S12 decoupling index 完成 (2026-09-15 08:30)
- cmscan 5401 seqs (2000 fams × ~20) vs Rfam.cm, --cut_ga: 127 家族 GA 级命中
- 解析修复: cmscan tblout target=CM/query=seq (与 cmsearch 相反); 驱动超时被
  setsid 孤儿进程救回 (tbl 完整 2692 行)
- Top decoupled: RF00163 DI=4.23 (id=0.62, cm=49.1 bits), RF04021 DI=3.81,
  RF01787 DI=3.69 — 高 DI = 序列分歧但 CM 结构保守
- 产物: evidence/s12_decoupling_index.json (+_full.json)
- 待办: H6 验证需要把 DI 与 probe 层位/接触涌现对齐 (S12×S7 关联分析)

### SSP v1 结论与 v2 修复
- v1 random arm: frozen F1=0.0 — 无加权 BCE 在 ~1.5% 正对率下坍缩到负类
  (loss 0.077→0.027 但模型只学 "无对") — 方法论教训, 已记录
- v2: pos_weight BCE + VL0 阈值校准 (0.3-0.8 扫描)
- family 基线修复: 用 mmseqs2 cluster parquet 而非 source-tag 分组
- family split: 10647 seqs → 10257 簇 (train 8518/val 1065/test 1064)
- family 基线 (v2): bracket_prior F1=0.0152, lgbm_pair F1=0.0465
  (vs random: 0.0146/0.0427 — 家族级泛化轻微下降, 基线层面)

## 2026-09-15（Day 6 上午：例行巡检——队列健康，无硬规则触发；100M-s17 probe 覆盖核查事故与口径更正）

### 巡检快照（status 生成 2026-09-15 08:34 服务器本地）
| run | 状态/GPU | nt 进度 | best/last val | fallback |
|---|---|---|---|---|
| 10M-full | **DONE** | 2000M/2000M（100%） | best 0.8716 | 0 |
| 30M-c1M | **DONE**（1M 语料自然耗尽） | 850M | best 0.8960 | 0 |
| 100M-s17 | **DONE** | 2000M/2000M（100%） | best 0.7964 | 0 |
| 1M-full | RUNNING GPU7 | 1600M/2000M（80%） | last 1.0976 | — |
| 100M-s29 | RUNNING GPU5 | 1300M/2000M（65%） | last 0.8260 | — |
| 100M-s43 | RUNNING GPU0 | 1300M/2000M（65%） | last 0.8240 | — |
| 30M-full | RUNNING GPU5 | 800M/2000M（40%） | last 0.8992 | — |
| 30M-c10M | RUNNING GPU1 | 700M/2000M（35%） | last 0.9087 | — |
| 30M-c1Mcs | RUNNING GPU3 | 500M/2000M（25%） | last 0.9491 | — |
| 30M-c1Mcs-s29 | RUNNING GPU4（supervisor 08:31 启动） | 100M/2000M（5%） | last 1.1016 | — |

### 规则执行结果
1. **CPU fallback：零事件**。3 个 DONE run 的 manifest fallback=0；RUNNING run 无告警；check.sh 输出 no alerts。硬规则未触发；
2. **崩溃/重启：零**。supervisor.log 全程无 attempt/relaunch/crash 记录；supervisor 已将 100M-s17（manifest DONE）收编，并于 08:31 启动 wave 第 10 项 c1Mcs-s29（GPU4）；
3. **最终 probe 覆盖：实质已满足（附一处历史口径更正）**：
   - 训练器在 2.0B 预算终点不落盘 ckpt（cadence=100M → 最后 ckpt=1900M，恰为 best_val ckpt；10M 与 100M-s17 各 19 个 ckpt、最大 1.9B，与 manifest nt_done≈2.0B 一致）——故 "probe_results.jsonl 中 ckpt_nt=2000M 记录" 对 DONE run 天然不存在；最终 probe 的正确判据 = **最后一个可用 ckpt（1.9B）上存在全量协议记录**；
   - 按此判据：10M@1.9B（1900171155）✓、100M-s17@1.9B（1900122218）✓（即 Day 5 深夜已提交的 final probe，23 层全量 n_train=20000/n_eval=4000）、30M-c1M@800M（best_val ckpt，语料耗尽提前停）✓；
   - **更正 Day 4 巡检笔误**：当时记 "10M 已含 ckpt_nt=2000M（200008867）"——200008867 实为 **200M**（0.2B，Day 1 首探点），非 2000M。本次巡检更正存档；
4. **wave.json**：8 基础 run + 2 个 c1Mcs 后续任务共 10 项在队；未全部 DONE 且已含后续任务 → 不追加。

### 事故记录：probe 误判两连 OOM + 一次冗余重复 probe（巡检操作失误，全程留痕）
- 起因：将 ckpt_nt200013675（**200M**，主轨迹第 2 个 ckpt）误读为 2.0B，误判 100M-s17 缺最终 probe；
- 尝试 1（GPU1）：误用 supervisor.log 中过期的 free 读数（15.4GB；彼时 GPU1 已被 editflow 等进程占满至 39.4GB）→ 状态收集阶段 OOM；证据日志：logs/probe_RNA-Sc-100M_s17_final_gpu1_oom_evidence.log；
- 尝试 2（GPU6）：CUDA 设备 6 实为 **MIG 1g.5gb（4.75GB）实例**而非整卡（物理 GPU6/7 已开 MIG，torch 枚举 4.75GB；nvidia-smi 的 40GB 是整卡口径，与 CUDA 可分配容量不同）→ 再次 OOM；
- 尝试 3（GPU5，约 8.4GB 整卡空闲）：运行成功，probe 加载最大 nt ckpt（1.9B）跑完 23 层全量协议，guard 校验 cpu_fallback=0 通过；
- **结果定性**：该 probe 与已存在的 final probe（同一 1.9B ckpt、同全量协议）构成 **冗余重复记录**。probe 头部含 RNG（per-class 采样/线性头初始化），故 f1 与已有记录存在微小数值差（late-band 均值 0.3008 vs 0.3031，方向性结论一致）；
- **数据处置**：遵循本文件对 smoke 记录的既有纪律——jsonl 为 append-only，**不删除**；下游汇总按 (run, ckpt_nt, n_train>=20000) 取**最新一条**记录去重，重复记录不得当作独立科学证据；
- 教训入规程：选卡前必须 ① 用 torch device_count+get_device_properties 校验 CUDA 设备真实容量（MIG/整卡），② 以 nvidia-smi 实时查询（而非 supervisor 历史日志）计算 used/total 空闲额，③ 若 cuda:N 不存在或为 MIG 实例需换卡，GPU 6/7 不可作为整卡 ≥3GB 候选。

（规则 6 未触发：8 个基础 run 中 5 个未 DONE；S1 scaling 对比表待全量完成 + 全部最终 probe 后定稿。10M/100M-s17/30M-c1M 的 probe F1 与 val 见 Day 5 深夜条目。）

## Day 6 (2026-09-15 09:20) — 自动化链路收尾

### 今日新增自动化
1. watch_1m 守护: 1M DONE → 自动 20k/4k 最终 probe + s12_linkage + 日志
2. probe per-class F1 (补丁): 每 rna_type 类别逐层 F1 → DI×层位联动数据
3. acc2type.json: 3292 RF accession → rna_type 映射 (命名空间桥接)
4. s12_linkage v2: type 级 DI 聚合 + Spearman (30M-c1M: 8 types, ρ=0.05 弱,
   正式口径待 20k 样本 probe)

### 进行中 (无人值守)
- 1M 训练 1655/2000M nt (~83%, ETA ~今晚)
- 100M-s29 1390M, 100M-s43 ~1360M (ETA 明晨)
- 30M-full / c10M / c1Mcs / c1Mcs-s29 (supervisor 队列)
- SSP v2 矩阵 wave2/3 (GPU5/6/7): 3策略×2切分
- 训练巡检 cron 每 30min

### S1 汇总表 v1 (2026-09-15 09:35, 自动化 s1_summary)
| run | 状态 | nt | best_val | probe 最优层 | F1 | 层带均值 |
|---|---|---|---|---|---|---|
| 100M_s17 | done | 2.00B | 0.7964 | L19/22 (late) | 0.331 | E.219 M.270 L.301 |
| 30M_s17 | running | 0.84B | - | L4/11 | 0.285 | E.195 L.237 |
| 30M_c1M | done | 0.85B | 0.8960 | L7/11 | 0.315 | E.164 L.273 |
| 10M_s17 | done | 2.00B | 0.8716 | L1/19 (early) | 0.174 | E.131 L.128 |
| 1M_s17 | running | 1.66B | - | L1/17 (early) | 0.121 | E.120 L.118 |

核心结论不变且更稳: **最优层随规模单调加深 (1M/10M→L1, 30M→L4-7, 100M→L19)**,
100M 的 late 带均值 F1 (0.301) 超过 early (0.219) — 与 Li et al. 蛋白质
LM "低层主导" 相反方向。

### C4 核心发现: 微调在家族切分下灾难性坍缩 (2026-09-15 10:20)

ncRNA-family 任务 (13 类), RNA-Sc-10M 与 RiNALMo-micro 对照:

| 模型 | 策略 | random ACC | family ACC | Δ(随机−家族) |
|---|---|---|---|---|
| RiNALMo-micro | frozen | 0.817±0.018 (n=3) | 0.696 | 0.12 |
| RiNALMo-micro | lora | 0.923 | 0.084 | **0.84 (坍缩!)** |
| RNA-Sc-10M | frozen | 0.375 | 0.214±0.018 (n=3) | 0.16 |
| RNA-Sc-10M | lora | 0.745 | 0.072±0.006 (n=3) | **0.67 (坍缩!)** |
| RNA-Sc-10M | full | 0.660 | 0.065±0.001 (n=3) | 0.59 (坍缩) |

解读 (初步, 待 SSP/modification 任务交叉验证):
- 参数高效/全量微调在 random split 上收益巨大 (lora +0.11~0.35 over frozen)
- 但在 family split 上, 微调记住的是家族内序列相似性, 对未见家族
  完全不迁移 → frozen 表征泛化性 > 微调表征 (C4 假设的直接证据)
- RiNALMo frozen 家族 ACC (0.696) vs RNA-Sc frozen (0.214): 预训练数据
  多样性差距 (36M vs 10M 语料) — 支撑 S2 数据轴假设
- modification 任务 family split 下 frozen 0.72 vs random 0.68 —
  无坍缩 (m6A 位点特征家族间共享) → 坍缩是任务依赖的

### SSP v2 首批正式结果 (2026-09-15 11:05, random split, n=3000/500)

| 策略 | pair-F1 | precision | recall | 墙钟 |
|---|---|---|---|---|
| LoRA | **0.0825** | 0.058 | 0.143 | 96min |
| frozen | 0.0342 | 0.024 | 0.062 | 112min |
| LGBM-pair 基线 | 0.0427 | 0.022 | 0.598 | ~6min |
| bracket-prior 基线 | 0.0146 | 0.007 | 0.892 | <1min |

初步解读:
- LoRA > 基线 +0.04, > frozen 2.4x: LM 全局注意力确实编码配对证据
  (frozen 表征 10M 模型上配对几何尚未线性可分 — 层带涌现前兆?)
- 绝对值低是协议口径 (pair-level 严格, max_len=192 截断, 3 epochs):
  BEACON 原文 SOTA ~0.25-0.3 (专用 CNN + 全量 10 epochs + 640 len)
- 收益口径 (B5): LM − 最强基线 = 0.0825 − 0.0427 = +0.040

### SSP 矩阵 v1 完整结果 (2026-09-15 14:00, RNA-Sc-10M, n=3000/500)

| 策略 | random F1 | family F1 | Δ |
|---|---|---|---|
| full | 0.0963 | (queued) | |
| lora | 0.0825 | (running) | |
| frozen | 0.0342 | 0.0306 | 0.004 |
| head-only | 0.0327 | 0.0320 | 0.001 |
| LGBM 基线 | 0.0427 | 0.0465 | -0.004 |
| bracket 基线 | 0.0146 | 0.0152 | -0.001 |

核心对比 (vs ncrna 的灾难坍缩):
- ncrna: lora random 0.745 → family 0.072 (Δ=0.67 坍缩)
- SSP: frozen/head Δ≈0.004 (无损), lora 待出
- 微调收益排序 (random): full 0.096 > lora 0.082 >> frozen 0.034
  → 配对几何需要梯度进入骨干 (与层带涌现假设一致: 10M 模型深层
  接触证据弱, 需微调放大)

结论: C4 (随机-家族差距) 是**任务依赖**的:
  - 家族记忆型任务 (ncrna 分类): 微调坍缩
  - 物理规律型任务 (SSP 碱基配对): 无坍缩

### SSP lora-family 结果: C4 任务依赖性定论 (2026-09-15 15:10)

lora random 0.0825 → family 0.0754 (Δ=0.007, 保留 92% 性能)

**论文级对照 (同 RNA-Sc-10M, 同微调协议):**
| 任务 | lora random | lora family | 保留率 |
|---|---|---|---|
| ncRNA 家族分类 | 0.745 | 0.072 | 10% (坍缩) |
| SSP 碱基配对 | 0.0825 | 0.0754 | 92% (稳健) |

机制解读:
- ncrna 的类别证据 = 家族特异性序列 motif → 微调学到的判别面
  是家族内序列相似性, 对未见家族负迁移
- SSP 的配对证据 = Watson-Crick/GU 物理互补 + 全局折叠约束 →
  家族无关的普适规律, 微调可迁移
- frozen 在两任务上都不坍缩 (ncrna 0.375→0.214, SSP 0.034→0.031):
  表征本身的泛化性 > 微调后的判别面

full-family 补跑中 (GPU7), 完成后 SSP 3协议×2切分矩阵完整。

### 三遍复查记录 (2026-09-15 16:30, 用户新规: 每步 3+ 遍)

对象: S1 汇总表 (s1_summary.json) 的 best-layer / F1 / 层带均值
- PASS 1: 原始 probe JSONL 独立重算 → 发现 s1_summary 有 2 个选行 bug
  (a) 没按最终 ckpt (ckpt_nt) 选行, 中途 probe 污染 (100M 曾显示 best=L2)
  (b) 旧行 fallback 公式 n_layers 缺失时用 2, band 归类错 (c1M 曾缺 middle)
- PASS 2-5: 修复+复算, 锁定官方口径 = 最终 ckpt + n_train>=4000
- PASS 6: 全量 5-run 对照手算参考, ALL OK

修正后的层带均值 (final ckpt, 20k probe):
| run | best | E/M/L band F1 |
|---|---|---|
| 100M | L19 0.3311 | 0.219/0.270/0.301 (late>early +0.082) |
| 30M-c1M | L7 0.3150 | 0.201/0.296/0.296 (middle=late>early) |
| 30M | L4 0.2846 | 0.208/0.261/0.230 (middle 峰) |
| 10M | L1 0.1741 | 0.144/0.120/0.118 (early 峰) |
| 1M | L1 0.1210 | 0.119/0.117/0.117 (平) |

核心结论复核后不变且增强:
1. 最优层随规模加深: L1(1M/10M) → L4-7(30M) → L19(100M)
2. 新发现 (时间轴): 100M run 内 100M-nt 时 best=L2, 1.9B-nt 时 best=L19
   → 层带迁移是训练动力学现象, 不只是参数规模现象
3. 10M/1M 的 late 带轻微下降 (0.120→0.118), 100M 反转 (+0.082)
   → "深层表征劣化" 在 100M 尺度被逆转

结论纪律: 30M-full/c1Mcs 等仍在跑, 以上仅覆盖已完成 run, 不外推。

### SSP 4策略×2切分完整矩阵 (终版, 2026-09-15 17:30)

| 策略 | random F1 | family F1 | 保留率 |
|---|---|---|---|
| full | 0.0963 | 0.0721 | 75% |
| lora | 0.0825 | 0.0754 | 92% |
| frozen | 0.0342 | 0.0306 | 90% |
| head-only | 0.0327 | 0.0320 | 98% |

vs ncrna 的 10% 保留率 → C4 任务依赖性确认。
(此为微调方法测评线资产, 主线机理研究引用对照即可, 后续由该线自行扩展)

### watch_all 通用守护上线 (2026-09-15 19:00)
- 功能: 任意 run DONE -> 自动 final probe (20k/4k) + s12_linkage + s1_summary + 日志
- 幂等: 通过 probe JSONL 的 final-ckpt 全层覆盖判定, 重启安全
- 修复过程记录 (3 遍原则现场应用): ROOT 路径 /home->/mnt 错误, stdout
  缓冲假象, 逐函数隔离验证定位
- 当前: 100M-s17 正式 probe 重跑中 (GPU2); 1M 91.5% ETA ~2h;
  100M-s29 78%/s43 81% ETA ~5-6h; 30M 线队列中

- [auto] rnasc_100M_s17 complete: nt=2.00B best_val=0.7964 fallback=0; final probe+linkage+s1_summary done
