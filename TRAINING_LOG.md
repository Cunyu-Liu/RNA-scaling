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

### watch_all 修复闭环 (2026-09-15 20:30)
- 根因链: (1) ROOT 路径错 (2) ssh 会话退出 SIGHUP 杀后台进程组 (3) 无异常守卫
- 修复: cycle try/except + 每小时心跳 + cron */2min 保活 (monitoring/keep_watch_all.sh)
- 端到端验证: 100M-s17 自动 probe 完成 (BAND E/M/L = 0.215/0.278/0.311,
  late>early +0.096, 与手跑一致), 自动转 c1M
- 全部后续 DONE run 均将自动: probe(20k/4k) -> s12_linkage -> s1_summary -> 日志

- [auto] rnasc_30M_s17_c1M complete: nt=0.85B best_val=0.8960 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_10M_s17 complete: nt=2.00B best_val=0.8716 fallback=0; final probe+linkage+s1_summary done

### Day 6 夜间收尾 (2026-09-15 22:30)

watch_all 已自动完成 3 个正式 probe: 100M-s17 (E/M/L=0.215/0.278/0.311),
c1M (0.219/0.296/0.295), 10M (0.145/0.120/0.119) — 全部与独立手算一致。

s1_seed_table (论文主表生成器) 上线: 命名空间桥 (rnasc_/RNA-Sc-) 修复后,
三行骨架已可复现, s29/s43/1M 完成后自动补全为 mean±std。

进行中: 1M 93.5% (ETA ~1.5h); 100M-s29 80%/s43 83% (ETA ~4-5h);
30M-full 49%/c10M 45%/c1Mcs 43%/c1Mcs-s29 25%。

### 事故 #9: 1M GPU 上下文静默丢失 (2026-09-15 17:25, 已根治)
- 症状: 进程 R 态 CPU 100%, 日志 4min 前有更新但 GPU compute-apps 无此 PID,
  /proc fd 无 nvidia 设备 → GPU 上下文丢失, CPU 空转假训练
- 取证: evidence/1M_gpu_stall_20260915.txt
- 处置: kill -> supervisor 5min 内自动 resume-from ckpt_1.8B GPU2, 损失 ~70M nt
- 教训: "日志在更新"不等于"GPU 在算" — 巡检必须查 compute-apps 匹配

- [auto] rnasc_30M_s17_c1Mcs complete: nt=0.90B best_val=0.9142 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_1M_s17 complete: nt=2.00B best_val=1.0824 fallback=0; final probe+linkage+s1_summary done

### 1M + 30M-c1Mcs 完成并自动 probe (2026-09-16 02:00, watch_all)

| run | best_val | probe best | rel-depth | E/M/L 带均值 | 备注 |
|---|---|---|---|---|---|
| 1M_s17 | 1.0824 | L6 0.1539 | 0.353 | 0.122/0.097/0.130 | 层曲线噪音大 (L8=0.009, L11=0.045), rel=0.353 证据弱; best_val 高 = 容量瓶颈 |
| 30M-c1Mcs | 0.9142 | L6 0.2971 | 0.545 | 0.206/0.260/0.265 | 簇级抽样 c1Mcs (vs c1M prefix 0.636) |

对比 c1M(prefix) vs c1Mcs(簇级): probe F1 0.310 vs 0.297, best-rel 0.636 vs
0.545 — 前缀抽样稍优但同量级 (语料上限同为 ~0.85B nt)。
1M 时间轴内部: 中途 probe best=L1 (100M-nt) -> final best=L6 (1.9B-nt),
与 100M 的 L2->L19 一致 — 层带随训练推进加深跨尺度成立。

S1 主表状态: 5/11 行就位 (1M/10M/100M×1/30M-c1M/30M-c1Mcs);
100M-s29/s43 完成后 100M 行变 3-seed mean±std; 30M-full/c10M 队列中。

### Figure 1 preprint main figure (2026-09-16 04:40)
- figs/fig1_layer_migration.png/.pdf: 7 curves + best-layer stars
- data audit 7/7 vs probe JSONL recompute
- watch_all post-chain: probe->linkage->summary->seed_table->fig1 auto

- [auto] rnasc_100M_s17 complete: nt=2.00B best_val=0.7964 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_1M_s17 complete: nt=2.00B best_val=1.0824 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_30M_s17_c1M complete: nt=0.85B best_val=0.8960 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_30M_s17_c1Mcs complete: nt=0.90B best_val=0.9142 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_10M_s17 complete: nt=2.00B best_val=0.8716 fallback=0; final probe+linkage+s1_summary done

### 巡检 + 事故#10 处置 (2026-09-15 22:30)

**巡检汇总** (status.txt @20:34): 10 run = 5 DONE (100M-s17 2.00B/10M 2.00B/1M
2.00B/30M-c1M 0.85B/30M-c1Mcs 0.90B) + 5 running (100M-s29 80%/s43 85%/30M-full
50%/c10M 45%/c1Mcs-s29 30%)。cpu_fallback 全 0；无崩溃重试 (事故#9 已根治)；
wave 8 基础 run 全在队未全 DONE, 不追加。

**事故#10: c1Mcs-s17 supervisor 循环重拉 + probe 数据污染 (发现 20:50, 修复 21:35)**
- 根因链: (1) supervisor `launch_one` 用 `ledger.update` (只改不建) -> wave 队列
  拉起的 c1Mcs 两 run 从未有 ledger 行 (2) DONE 后 wave 循环查不到 done 状态
  -> 18:03 从 900M ckpt 循环重拉第二 epoch (3) 第二 epoch 写出 1.0B ckpt +
  覆盖 manifest DONE 帧 (4) 20:42 watch_all 命名空间 bug (scan_done 键 rnasc_*
  vs probed_runs 键 RNA-Sc-*) -> 重启即全量重 probe, 用了被污染的 1.0B ckpt
  写入 jsonl (12 行) + s1_scaling_summary (21:17)
- 危害: 若不处置, c1Mcs 将跑到 2.0B (4 个 epoch) 且 S1 表 c1Mcs 行被第二
  epoch 污染, 破坏 c1M(prefix, 1 epoch) vs c1Mcs(cluster, 1 epoch) 对照
- 证据: evidence/c1Mcs_relaunch_20260915.txt; evidence/quarantine/ (隔离的
  1.0B ckpt); probe_results.pre_inc10clean_20260915.jsonl (清理前快照)
- 处置: (1) ledger 补 2 行 (s17=done/nt 902M, s29=running) (2) kill 第二
  epoch 进程 (408190/1519987), manifest 从日志帧重建 (9 ckpt + 9 VAL, status
  DONE/902M/0.9142, 原 running 帧备份 .bak) (3) jsonl 删 12 行污染 (4) 补丁
  supervisor: upsert 建行 + adopted-DONE 回填日志 DONE 帧 (防 watch_all 漏
  事件) (5) 补丁 watch_all: 命名空间桥修复 (6) s1_summary/s1_seed_table 重跑
- 验证: supervisor 重启后 adopt 5 合法 run 且不再重拉 c1Mcs-s17 (观察 3 个
  poll 周期); watch_all 补丁版运行 5min+ 无重 probe (jsonl mtime 不变);
  S1 表 c1Mcs 行恢复 0.2971@0.9B (与 02:00 记录一致)

S1 主表 (s1_seed_table, 清理后): 1M 0.1517 / 10M 0.1725 / 100M-s17 0.3352 /
30M-c1M 0.3027 / 30M-c1Mcs 0.2971 (5/11 行; s29/s43 完成后补 mean±std)。

巡检者注: 本次为操作型巡检 (非科学结论); probe 数字均为 probe (day-1
pooled) 结果, 最终科学结论待全量 runs + 严格 probe 后汇总。

### T2.1.2 红队修正 A 执行: 语料轴三点曲线任务入队 (2026-09-16 06:50)
- c5Mcs 生成: 5,000,013 seqs / 975,339 簇 (cluster-stratified, seed 17)
- wave.json 新增: 10M×{c5Mcs, c1Mcs} — 与 10M-full 组成同模型三点
  (语料 ~0.5B / ~1.2B / 2.0B nt 视语料实际大小), supervisor 自动调度
- 目的: 语料量-性能曲线 + epoch 覆盖差异显式化 (红队 A 修正)

### 2026-09-16 (Day 7) 夜巡: 多样性指标完成 + 30M 三-seed 补齐 (01:40-02:00)
- **T2.3.2 语料多样性指标 (验收达成)**: 新增 rna_sc/corpus_diversity.py;
  5 arms 全出表 (evidence/corpus_diversity.md/.json), commit f9abf37
  - 关键发现 1 (方法学): prefix 采样 (c1M/c10M) seq-level 构成与 full
    完全一致 (rRNA=56.4%), 但整簇采样 cs 臂 rRNA 更高 (c1Mcs 61.5%,
    c5Mcs 59.0%) — 大簇按整簇保留; 采样方式本身改变家族构成, c1M vs
    c1Mcs 对比 = 数据量 + 构成双重差异 (方法节显式声明)
  - 关键发现 2: cluster-level 熵 c1M (1.9139) 反而最高 (prefix 切大簇
    半, 小簇相对更丰富); cs 臂簇构成与 full 一致 (1.786 vs 1.785) —
    整簇采样忠实保持了簇分布 (设计目的达成)
  - 红队 E 交叉验证: full rRNA=56.4% 与交档记载一致 ✓
- **30M 三-seed 补齐 (T2.1.3 关键路径)**: wave.json +30M-s29/s43-full
  (14 条总); 三遍验证: 14 entries ✓ / 30M 条目 7 个 ✓ / supervisor 每周
  期重读 wave.json (源码确认) ✓
- **100M 三-seed 一致性**: 1.8B nt 处 val: s17 0.7985 / s29 0.7977 /
  s43 0.7967 (散布 0.002) — seed 方差很小, slope 判定将很稳
- **事故修复 (cron typo)**: keep_watch_all cron 误写 /mnt/cunyul2u/ 路径
  (多打 2), 立即清除; /home 版为权威; /mnt 冗余副本删除
- s43 99.1% (1982M/2B), DONE 后 watch_all 自动 probe; s29 90%;
  10M-c5Mcs 23%, 10M-c1Mcs 10%

- [auto] rnasc_100M_s43 complete: nt=2.00B best_val=0.7939 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_30M_s29_c1Mcs complete: nt=0.90B best_val=0.9129 fallback=0; final probe+linkage+s1_summary done

### 2026-09-16 02:45: 100M 三-seed 关键节点 + T2.3.2b vendi 完成 (夜巡续)
- **100M-s43 DONE + 自动 probe 完成**: nt=2.0B best_val=0.7939 (s17 0.7964
  / s29 ~0.7977@1.8B); probe late band f1=0.3411, best layer late — 与 s17
  (0.3352, late) 一致; seed_table 100M 行: n=2, F1=0.3440±0.0125
- **100M 三-seed 一致性确认 (三遍)**: (1) val@1.8B: 0.7985/0.7977/0.7967
  (散布 0.002); (2) final best_val: 0.7964/0.7939; (3) probe band 结构:
  late>middle>early 两 seed 同型 — slope 判定输入稳定
- **30M-s29-c1Mcs DONE + 自动 probe**: val=0.9129 (vs s17 0.9142); probe
  F1=0.3453 (vs s17 0.2971) — c1Mcs 臂 seed 散布 ±0.034 显著大于 100M-full
  ±0.0125: **小语料 + 簇采样的种子方差更大** (方法节 + limitation 记入);
  best-layer 位置 s17 rel=0.545 vs s29 rel=0.91 — 层迁移位置在该臂不稳定
- **T2.3.2b vendi 完成 (5/5 arms)**: full 9.53 / c10M 9.47 / c5Mcs 9.48 /
  c1M 9.19 / c1Mcs 8.96 — c5Mcs 多样性几乎追平 full; c1Mcs 双重压低
  (数据量小+构成偏移); commit 82cd846
- **30M 三-seed 全部在途**: s29@GPU0 (fresh), s43@GPU4 (fresh),
  s17@GPU5 (53%, resume); 预计 ~2 天齐
- 当前 7 训练进程并行: 30M×{s17,s29,s43,c10M} + 10M×{c5Mcs,c1Mcs} +
  100M-s29 (90%)

### 2026-09-16 03:10: T2.2.1 S4 randinit 四档扩面完成 (H2 排除性证据表)
- 四档 randinit17 probe (1M/10M/30M/100M, 全层, 20k/4k family split):
  trained - randinit = 1M +0.051 / 10M +0.042 / 30M +0.161 / 100M +0.208
- **科学发现**: 预训练增益随规模单调扩大, 30M 处陡增 (0.04→0.16) —
  与 S1 主表的 F1 跳跃 (10M 0.17→30M 0.28) 同步; H2 (randinit 即含
  任务无关特征) 在所有档位被排除; 1M/10M 档增益小 — 迁移能力在
  30M+ 才真正建立 (层迁移 rel_depth 也在 30M+ 才进入深层)
- 证据: evidence/s4_randinit_table.{md,json}; randinit 三 band 平坦
  (无层结构) vs trained 有明确 late-band 优势 — 排除证据双重
- T2.2.1 首半验收 (四档 randinit 表) 达成; 三协议版待 T1.2 协议
  升级后统一重跑 (pooling 口径差异已记录)

### 2026-09-16 04:05: T2.2.3 S6 涌现时间轴全量完成 — 线 2 独有主发现
- **S6 全量 (10M s17, 19 ckpt × 20 层, 380 probe 行, 20k/4k family split)**:
  - F1 非单调: 0.1B→0.5B 升至峰值 0.2497 (L18 late), 1.0B 后回落至
    ~0.17 平台; best-layer 从 late/middle 带下移至 early (L1-L3)
  - **跨模型时间轴三角验证**: 1M L1→L6 (上行) / 30M@0.1B L4 起点 /
    10M L19→L1 (下行+回落) / 100M L2→L20 (强上行) — 终态 best-layer
    位置 = 训练动力学终点态; 跨模型 final 对比 (10M early/30M mid/
    100M late) 是动力学分岔, 不是静态属性
  - **per-class 分解 (第三遍)**: 0.5B 峰→1.9B 谷的差由非 rRNA 类驱动
    (misc_RNA 0.48→0.36, snoRNA 0.33→0, pre_miRNA 0.21→0, lncRNA
    0.18→0, ncRNA 0.07→0); rRNA 反而 0.96→0.98 — 跨家族特征被从
    深层挤出, rRNA 主通道加深 (语料 56% rRNA 偏置的因果链)
  - 证据: evidence/s6_timeline.json + figs/fig_s6_emergence.png/pdf
  - 命名: "pretraining-time feature attrition" (训练时间轴特征磨蚀)
  - 预印本定位: 图 4/5 素材, 与 BERT probe 文献中期峰值对话
- 100M-s29 @1882M (94%), ~1h 内 DONE
- 30M s29/s43 全速训练中

### 2026-09-16 05:00: S6 四尺度跨尺度图完成 — 磨蚀是 10M 特有动力学
- 补齐 1M (9 ckpt) / 100M (4 ckpt) / 30M (5 ckpt) 时间轴; 跨尺度图
  figs/fig_s6_cross_scale.png + evidence/s6_cross_scale.json
- **四尺度四形态**: 1M 缓升+缓上移 / 10M 磨蚀+大下行 (唯一) /
  30M 持续升+持续上移 / 100M 持续升+强上行
- 结论: 10M 特征磨蚀为尺度特异 (非普遍); 30M+ 容量足以持续积累
  家族特征 — "磨蚀-容量" 解释; 与 S1 主表的 10M F1 停滞 (0.17) 互为
  因果印证 (磨蚀的宏观表现)
- 100M 早 ckpt rel=0.045 (L1) -> 1.9B rel=0.91 (L20): 深层特征是
  预训练后期才建立的 (与交档 L2→L19 记录一致, 扩展为连续轨迹)

### 2026-09-16 05:10: S6 第三遍验证 — 30M 全带轨迹细读 (措辞修正)
- 30M 12 层三带均值: 0.3B→0.7B 全带上 (late 0.289→0.325);
  0.7B→0.9B 轻微回落 (late -0.013) — 30M 有弱磨蚀苗头, 幅度远小于
  10M (-0.07), 且 0.9B 仍高于 0.3B
- 结论措辞修正: "磨蚀在 10M 最剧烈且造成终态反转; 30M 弱苗头被上升
  淹没; 1M/100M 无" — 写入 S6 图注

- [auto] rnasc_10M_s17_c1Mcs complete: nt=0.90B best_val=0.9815 fallback=0; final probe+linkage+s1_summary done

### 2026-09-16 06:20: 语料轴第一点 + S6 四尺度完善收尾
- **10M-c1Mcs DONE + 自动 probe**: 语料上限 0.90B (1M seqs, ~2.2
  epoch), val=0.9815; probe best L9 (middle, rel=0.474) F1=0.1878
  — vs 10M-full (14.1B, 0.14 epoch) F1=0.1725 L1(early):
  同参数量下小语料+多epoch 反而更高 F1 + best 层更深; 语料三点
  (c1Mcs 0.188 / c5Mcs pending / full 0.1725) 的 epoch-覆盖叙事
  (红队 A 修正) 有了第一个数据点
- S6 补充: 10M-c1Mcs 的时间轴也值得跑 (小语料多 epoch 是否磨蚀?)
  → 排入下一批 (ckpt 已有 9 个)
- s29 99%+ (1984M, lr 4.6e-08); c5Mcs 70% (1399M/2B)

- [auto] rnasc_100M_s29 complete: nt=2.00B best_val=0.7956 fallback=0; final probe+linkage+s1_summary done

### 2026-09-16 08:05: ★100M 三-seed 定稿 + T2.1.3 slope 初判 650M
- **100M 三-seed 完整 (s17/s29/s43 各 2.0B, 全 fallback=0)**:
  best_val 0.7964/0.7956/0.7939 (±0.0013); probe F1 0.3396±0.0117
  (0.3378/0.3307/0.3529); best rel 0.712; E/M/L 0.237/0.306/0.318
  — seed_table 100M 行定稿 (n=3)
- **T2.1.3 预注册 slope 初判**: slope=(0.3396-0.2846)/log10(100/30)
  = 0.1068/decade; bootstrap CI95 [0.0882, 0.1306]; CI 下界 = 2.9×eps
  (0.03) -> **decision = "650M"** (触发第二阶段 4×A100 DP)
  - 注意: 30M 侧暂为单 seed (0.2846); 30M-s29/s43 在训 (~2 天);
    数量级不会翻转 (即使 30M±0.03, slope 仍 0.08-0.13 > eps)
  - 行动: 等语料三点 (c5Mcs ~1.5h) 后, 30M 三-seed 齐前预排
    650M 启动准备 (模型 spec + DP 适配 + 显存测算), 30M 定稿
    slope 后立即投 650M

### 2026-09-16 08:51: 例行巡检 — 9/14 DONE、fallback 全 0、终 probe 全覆盖、队列不追加
- **健康度 (status @ 08:34)**: 14 run = 9 DONE + 5 RUNNING; DONE run
  cpu_fallback_count 全 0; RUNNING run (c5Mcs/30M-s17/30M-c10M/30M-s29/
  30M-s43) 历史每条 validation fallback 均 0 → 硬规则未触发, 无需停训;
  ledger 无 failed 行 (attempts 最高 1, 为 10M 伪重启历史已解决);
  supervisor/watch_all 常驻, 5 个 train PID 全在 GPU, 无崩溃待诊
- **2.0B 终 probe 核对 (规则 3)**: ckpt 间隔 100M、训练至 2.0B 收尾
  不落 2.0B ckpt, best_checkpoint=1.9B → 终 probe 即 1.9B 全层记录。
  probe_results.jsonl 核对: 100M_s17 0.3378@L19 / 100M_s29 0.3307@L11 /
  100M_s43 0.3529@L16 (各 23 层), 10M_s17 0.1754@L1 (20 层), 1M_s17
  0.1539@L6 (18 层), 均 n_train=20000/n_eval=4000 — **5/5 已完成,
  无需补跑**; GPU6/7 空闲 (约 36.7G/33.5G free) 留作后续
- **语料轴 DONE run 终态 probe**: 30M-c1M best 0.315 (0.80B, 语料上限
  0.85B); 30M-c1Mcs-s17/s29 与 10M-c1Mcs 已由 auto pipeline probe (0.90B)
- **RUNNING 进度**: 10M-c5Mcs 1.63B/2.0B (81%, val@1.6B=0.8965, 约 3h
  后 DONE+自动终 probe); 30M-s17 1.27B (63%, val=0.8704); 30M-s17-c10M
  1.26B (63%, val=0.8708) — 二者约 1 天内 DONE; 30M-s29 0.17B (8%,
  val=1.1159) / 30M-s43 0.25B (12%, val=1.0042) — 约 2-3 天
- **wave.json (规则 4)**: 14 条 = 全部 8 基础 run + 6 后续 (c1Mcs x2 /
  c5Mcs / 10M-c1Mcs / 30M-s29-full / 30M-s43-full), 含后续任务 → 不追加
- 8 基础 run: 6/8 DONE (1M/10M/100M x3/30M-c1M); 30M-full 与 30M-c10M
  在训 (63%) → 规则 6 (S1 scaling 表汇总) 未触发, 待 30M 定稿
- 注: status.json 实际位于 /mnt/cunyuliu/rna-sc/ 根目录 (status/ 子目录
  只有 status.txt + cron.log), 后续巡检取数以此路径为准

- [auto] rnasc_10M_s17_c5Mcs complete: nt=2.00B best_val=0.8830 fallback=0; final probe+linkage+s1_summary done

### 2026-09-16 10:00: ★T2.1.2 语料三点曲线收官 (红队 A 修正闭环)
- **10M × {c1Mcs, c5Mcs, full} 三点全齐 (各 2.0B nt, seed 17)**:
  - c1Mcs  (0.9B unique, 2.2 ep): F1=0.1878 best L9 (middle 0.474)
  - c5Mcs  (2.4B unique, 0.83 ep): F1=0.1524 best L4 (early 0.211)
  - full   (14.1B unique, 0.14 ep): F1=0.1725 best L1 (early 0.053)
- **三点 U 型 (非单调)**: 中间语料 c5Mcs 最差 — 既未充分重复也未
  充分覆盖; 两端 (多-epoch 记忆 / 大-多样性) 各自更优
- **val loss 与 probe F1 排序完全相反** (c1Mcs val 0.9815 最差但 F1
  最好; full val 0.8716 最好 F1 中间) — **MLM 损失与跨家族可迁移性
  解耦的直接证据** (预印本 4.4 节核心句)
- best-layer rel_depth 随语料缩小单调上移 (0.053→0.211→0.474):
  语料越小, 家族特征住得越深
- 图: figs/fig_corpus3.png/.pdf; 证据: evidence/corpus3.json
- epoch-覆盖差异已显式标注于图 (不假装同质, 红队 A 合规)

### 2026-09-16 14:30: Day 7 战役总结 (夜巡+日巡全链路)
**今日完成 (12 commits: f9abf37..28b4f0e)**:
1. T2.3.2 语料多样性 5 arms (Shannon/GS + Vendi GPU 嵌入版) — 验收达成
2. T2.2.1 S4 randinit 四档 H2 排除表 — 验收达成 (首半)
3. T2.2.3 S6 四尺度时间轴 — 磨蚀发现 (10M 特有, U 型 F1 + 层下行)
4. 100M 三-seed 定稿 (F1 0.3396±0.0117) — S1 主表核心
5. T2.1.3 slope 初判 0.107/decade CI[0.088,0.131] → 650M 触发
6. T2.1.2 语料三点 U 型 + val/F1 反转 — 解耦证据
7. 650M spec 锁定 666.3M (e6c74da)
8. 预印本骨架 v0.2 + abstract 四发现整合 (28b4f0e)

**基础设施**: cron typo 事故修复; probe --ckpt-nt 功能 (S6 通道);
watch_all 自动链 5 次 DONE→probe→fig 全绿; s1_seed_table 三-seed
聚合生效; gpu_liveness+check.sh 双保险验证有效

**在途**: 30M 三-seed (s17 74%/s29 15%/s43 23%); 30M-c10M 71%;
~1 天后 30M-s17 DONE → probe; ~2 天后三-seed 齐 → slope 定稿 → 650M

**下一批优先级** (30M 齐前): 10M-c1Mcs 时间轴 (磨蚀 vs 多-epoch
交互, ckpt 已有); 30M-c1Mcs 已有 2 seeds (s29 done) — slope 用
30M-full s17 即可, 但 3-seed 是合同验收; S12 全家族版重跑 (100M)

### 2026-09-16 15:00: S12 x 100M (预印本 4.5 节素材)
- s12_linkage --run RNA-Sc-100M_s17: 18 类有 DI, 10 类进 linkage;
  Spearman(DI, best-layer) = -0.244 (vs 30M-c1Mcs -0.640);
  Spearman(DI, late-early) = -0.399 (vs 30M -0.362)
- 解读: 100M 上 DI-层关联减弱 — 家族特征已充分深化 (与 S1/S6
  的层迁移结论互恰); 30M-c1Mcs 的强关联 (-0.64) 是"中间态"信号
- 存档: evidence/s12_linkage_100M_s17.json
- 注意: DI 以 rna_type 聚合 (类级) 而非 Rfam 家族级 — 预注册的
  家族级版本需要 per-class F1 × Rfam 家族 DI 的映射表升级
  (T1.2.2 协议升级后做); 当前作为 4.5 节的初步证据

### 2026-09-16 16:40: S6 磨蚀归因细化 — 与语料重复度无关
- **10M-c1Mcs 时间轴 (4 ckpt, 0.1/0.3/0.5/0.7B, 全层)**:
  0.1B L18 0.207 -> 0.3B L13 0.240 -> 0.5B L9 0.245 (峰) ->
  0.7B L9 0.205 -> 0.9B(final) L9 0.188
- 与 10M-full 同型 (峰后回落+层下移) — **磨蚀在 2.2-epoch 小语料
  同样发生**, 排除"大语料见太多数据"解释; 磨蚀发生在第一→第二
  epoch 之间 (0.5→0.9B), 是优化动力学 (训练时长) 的尺度特异现象
- 预印本 4.3 节更新: 磨蚀 = f(model scale, training duration),
  与 corpus repetition 无关; "erosion-capacity" 账户改为
  "erosion-duration × capacity" 双因子

### 2026-09-16 20:34: 例行巡检 (check.sh + status.json + probe 对照)
- 14 runs: 10 DONE / 4 RUNNING, 无崩溃, supervisor 重试 0 次,
  cpu_fallback_count 全部为 0 (RUNNING 的 4 个经训练日志 grep 复核,
  无 fallback/NaN 记录)
- 在途 (85%/75%/20%/35%): 30M-s17 1.70B | 30M-c10M 1.50B |
  30M-s29 0.40B | 30M-s43 0.70B; 全部 4 个 train PID 在卡,
  GPU0-5 满, GPU6 空闲 ~33GB
- DONE 汇总 (nt done / best_val_loss): 100M-s17 2.0B/0.7964,
  100M-s29 2.0B/0.7956, 100M-s43 2.0B/0.7939, 10M 2.0B/0.8716,
  10M-c5Mcs 2.0B/0.8830, 1M 2.0B/1.0824, 30M-c1M 850M(1 epoch 语料
  耗尽)/0.8960, 30M-c1Mcs 902M/0.9142, 30M-s29-c1Mcs 902M/0.9129,
  10M-c1Mcs 902M/0.9815
- 最终 probe 核查 (probe_results.jsonl): 全部 2.0B-完成 run 均已有
  ckpt_nt≈1.9B 全层 probe 记录 (100M x3 seeds, 10M, 10M-c5Mcs,
  1M); 无需补跑, 本轮不启动新 probe 进程
- 小语料 run 的 1.9B probe 缺失符合预期 (语料 <2.0B nt, 1 epoch 后
  自然停止, 属设计内行为); 其非末位 ckpt probe (如 10M-c1Mcs
  0.9B L9 F1 0.188) 为中间证据, 不作最终结论
- wave.json: 8 个基础 run 全部在队, 尚有 4 个未 DONE → 不追加

### 2026-09-16 22:30: 30M-full final probe 定稿 + slope 更新 (0.143/decade)
- **30M-s17 DONE (2.0B, val=0.8214) + final probe (1.9B ckpt, 协议一致)**:
  F1=0.2656, best L11 (rel=1.0 最后一层!), E/M/L = 0.183/0.220/0.245
  - 与 S6 30M 时间轴一致 (0.9B L8 -> 2.0B L11): 层迁移持续到最后一层
  - 勘误: 之前 slope 用的 30M 0.2846 是 0.1B 早 ckpt 行 (当时 full
    未完); 现在 final 0.2656 (选择逻辑正确切换)
- **slope 重算: 0.1432/decade, CI95 [0.1245, 0.1670]** — CI 下界
  4.1×eps(0.03), 650M 决策增强 (等 s29/s43 后最终定稿)
- watch_all 幂等盲区发现+修复: probed_runs() 只查"全层覆盖", 未查
  "final ckpt 的行" — S6 时间轴 run DONE 后被跳过; 已手动补 probe;
  s1_seed_table/slope/fig1 已刷新
- s1_slope_decision 30M 选择逻辑验证: final-ckpt 行优先 (1.9B) 而非
  0.1B 行 ✓ (选择规则三遍检查通过)

### 2026-09-17 08:45: 巡检 patrol（规则复核 + 最终 probe 复检/补齐）
- 状态快照 status.txt: 14 runs, 11 DONE, 3 RUNNING (30M-s17-c10M 1900M/95%,
  30M-s29 700M/35%, 30M-s43 1100M/55%); no alerts; cpu_fallback 全部 =0（规则1 ✓）;
  3 训练 PID 在 GPU、检查点持续写入 (c10M 08:15 / s29 05:43 / s43 06:34), 无崩溃、
  无 supervisor 重试>5（规则2 ✓）
- 8 基础 run: 7 DONE + 30M-c10M RUNNING（未全 DONE）→ wave.json 维持现状、不追加
  后续任务（规则4 ✓; 规则6 未触发）
- 最终 probe（规则3）: 按"latest=最高已存 ckpt≈1.9B"项目约定核查 probe_results.jsonl,
  7 个 2.0B-DONE run（100M x3、10M、10M-c5Mcs、1M、30M）均已有 latest-ckpt 全层
  probe 记录; 本轮按规则对 7 个 run 复核并重跑 final probe（GPU5/6/7 分派, 幂等追加
  同 ckpt 行）, 7/7 进程正常退出, 记录 ckpt_nt≈1.9e9
  - 说明: 各 run 目录最高已存 .pt 为 ckpt_nt1900*（1.9B）, 无 2.0B 检查点文件, 故
    final probe 落点为 1.9B 属既定协议（时长/语料耗尽后停止, 非 smoke/proxy）
- 运维备注: 首轮误将 3 个 probe 同时压 GPU6 触发 CUDA OOM, 已改分 GPU5/7 错峰重发
  成功（后续 probe 并发建议≤2/卡）
- 待办: 30M-c10M 及 3 个 30M 训练 run 未完成; 8/8 DONE 且 final probe 齐全后再生成
  S1 scaling 对比表（val + probe F1）

### 2026-09-17 09:20: ★probe 重复性方差事件 + 确定性根治 (inc12)
- **发现**: jsonl 出现 322 行重复 (1M/30M/100M final ckpt 被重复
  probe; 来源为另一自动化会话的 probe_RNA-Sc-*_final.log 系列,
  与 watch_all 命名空间不同)
- **科学发现**: 重复 probe 的 run-to-run 方差巨大 — 1M L4 达
  0.0999 F1, 100M 早期层 0.02-0.05; 弱特征层受 probe 头初始化
  主导 (未 seed 的 LinearProbe init + randperm shuffle)
- **根治**: probe.py inc12 — 每层固定 seed (17+layer_idx), 头
  初始化与数据顺序确定; 验证: 同 ckpt 两次 probe 逐位一致 ✓
- **处置**: jsonl 去重 322 行 (first-writer-wins, 协议一致) +
  56 行 smoke (<4000) 清理; seed_table 重跑恢复
- **方法学结论 (入预印本方法节)**: probe 可重复性方差在弱层
  可达 ±0.05-0.10 F1 — 所有报告数字均来自确定性 probe; 历史
  非确定性 probe 的跨 run 比较需注明此方差上界

- [auto] rnasc_30M_s17_c10M complete: nt=2.00B best_val=0.8216 fallback=0; final probe+linkage+s1_summary done

### 2026-09-17 14:00: 30M-c10M DONE — 语料轴七点全景 (两尺度对比)
- **30M 语料轴四点齐** (全部自动链: DONE→probe→table):
  c1Mcs 0.2971 (rel 0.545) / c1M 0.3150 (0.636) / c10M 0.2865
  (1.000) / full 0.2656 (1.000)
- **两尺度语料轴形态对比 (预印本 4.4 节核心)**:
  - 10M: U 型 (中段 c5Mcs 塌陷 0.152)
  - 30M: 单调 (c1M 0.315 最优 → full 0.266; 中段 c10M 0.287
    稳定, 不塌)
  - 解读: 10M 容量不足以同时记忆+泛化 (中段两头不沾); 30M 容量
    使中段稳定 — 与 S6 磨蚀-容量交互互为印证; 小语料多-epoch
    在两尺度都是最优 (2.35 ep 的 30M-c1M 0.315 = 全局最高 F1)
- best-rel 对比: 30M 语料轴全在深层 (0.545-1.0), 10M 全在浅层
  (0.053-0.474) — 层深度由模型规模主导, 语料影响次之
- 图: figs/fig_corpus3.png (7 arms); 证据: evidence/corpus3.json

### 2026-09-17 17:30: ★确定性 probe 重跑全表 (inc12 协议统一)
- 11 runs final ckpt 全部确定性重跑; jsonl last-writer 去重
  (1336->1141 行); 全部派生物刷新 (seed_table/fig1/corpus3/s6/
  slope)
- **数字变化 (旧非确定 -> 新确定)**: 30M-full 0.2656->0.2466;
  c1M 0.3150->0.3160; c1Mcs 两 seed 方差 ±0.0341->±0.0098 (大
  方差约一半来自 probe 非确定性!); 1M 0.1517->0.1604
- **slope 终稿版**: 0.1774/decade, CI95 [0.1524, 0.2079] — CI
  下界 5.1×eps, 650M 决策极稳 (30M 侧单 seed; s29/s43 齐后
  换入)
- **⚠️ 口径警告**: S6 时间轴中间点 (0.1-0.9B) 仍是旧非确定性
  协议; 30M 时间轴尾点 (final) 0.2466 与中间点 0.34 (旧协议)
  的落差部分来自协议差 — **S6 结论需确定性重跑中间点后再定稿**
  (排入 650M 前的下一批); 10M 时间轴同样
- 预印本纪律: 所有最终数字一律以确定性协议为准

### 2026-09-17 21:00: S6 确定性重跑定稿 — 磨蚀形态终版
- 37 个时间轴点全部 inc12 确定性协议重跑; 图/表全部刷新
- **磨蚀强度尺度倒 U 型 (终稿)**: 10M -0.082 (0.25 峰→0.17
  平台, best-layer L16→L1 大下行) >> 30M -0.021 (0.267→0.247
  轻微) > 1M +0.014 / 100M +0.031 (持续上升, 无磨蚀)
- 10M 磨蚀的确定性细节: 0.1B 即有峰 (L16 0.2528), 0.5B 二峰
  (0.2549), 1.1B 后塌陷, late-band F1 0.23→0.12 — 与旧非确定
  性版本形态一致 (结论稳健, 但数字口径统一后才能下此结论)
- 预印本 4.3 节终稿口径: "attrition strength is scale-dependent
  with an inverted-U shape (strongest at 10M)" — 1M 容量太小
  磨不动, 100M 容量足够防磨蚀, 10M 正好在"容量-语料张力"最大点

- [auto] rnasc_30M_s43 complete: nt=2.00B best_val=0.8186 fallback=0; final probe+linkage+s1_summary done

### 2026-09-18 02:30: Day 8 中夜总结 (s43 收官 + 等待 s29)
**Day 7-8 完成 (17 commits: 9b1837e..34fbb71)**:
1. 确定性 probe 革新: 发现重复性方差 (弱层 ±0.10 F1) → inc12 逐层
   seed → bit-exact 验证 → 11 runs 重跑 → 37 个 S6 时间轴点重跑
2. S6 磨蚀终版: 尺度倒 U 型 (10M -0.082 >> 30M -0.021 > 1M/100M
   无); 与语料重复无关 (c1Mcs 复现)
3. 30M-s43 DONE+probe: 30M n=2 (0.2616±0.0213); slope 0.149 仍
   650M; 100M 侧三 seed 0.3394±0.0147
4. watch_all 幂等盲区根治 (inc11: manifest final_nt 对照)
5. 语料轴 7 点全景: 10M U 型 vs 30M 单调 (容量交互)
6. 预印本 v0.3 (含 probe 确定性方法节)

**在途**: 30M-s29 (76%, ~5h) — DONE 后 watch_all 自动 probe →
30M n=3 → slope 终稿 → 650M 启动 (spec 666.3M 已锁定, supervisor
自动抓 GPU)

**遗留口径债务**: S4 randinit 表 + 10M-c1Mcs 时间轴 + s12_linkage
是旧非确定性协议 — 下一批确定性重跑后升级预印本 v0.4

- [auto] rnasc_30M_s29 complete: nt=2.00B best_val=0.8192 fallback=0; final probe+linkage+s1_summary done

### 2026-09-18 14:30: ★★T2.1.3 slope 终稿 650M 触发 (合同级里程碑)
- **30M 三-seed 完整** (s17/s29/s43 各 2.0B, fallback=0):
  val 0.8214/0.8192/0.8186 (±0.0015); probe F1 0.2651±0.0162
  (0.2466/0.2720/0.2767); best rel 0.788; E/M/L 0.194/0.230/0.247
- **S1 主表终稿 (确定性协议)**: 1M 0.1604 / 10M 0.1731 /
  30M 0.2651±0.0162 (n=3) / 100M 0.3394±0.0147 (n=3)
- **T2.1.3 预注册 slope 终稿**: 0.142 F1/decade, bootstrap CI95
  [0.1044, 0.1797] — CI 下界 3.5×eps(0.03) → **decision = 650M**
  (T4.3.1 第二阶段触发)
- **行动**: RNA-Sc-650M (666.3M, d1408 L28 H22 f5632, spec
  e6c74da) 已入 wave.json (need 24GB 单卡); supervisor 将在 GPU
  空间足够时自动启动; S6 需 2.0B nt @ ~1/6 100M 速度 ≈ 5-6 天
- 30M 三 seed 的 best-rel: s17 0.727 / s29 0.091? (待查 s29 行)
  / s43 — 层位置 seed 间波动, rel 深层为主

### 2026-09-18 15:00: supervisor 重启持 650M 等 GPU + Day 8 收官
- supervisor 曾在 30M 三-seed 齐后判 wave complete 退出 — 650M
  入队晚于其退出; 已重启, 现正确等待 24GB 单卡 (当前最大空闲
  15.5GB, 外部占用); 轮询中, 有空间即自动启动
- **Day 8 终态**: S1 主表 1M-100M 四档全 n>=1 (30M/100M 三
  seed); slope 终稿 0.142 CI [0.104, 0.180] 650M 触发; 全部
  probe 确定性协议; S6 四尺度 + 语料七点 + S4 四档 + S12 + 多样
  性五臂 — 核心实验矩阵收口
- 650M 训练 (~5-6 天) 期间: 预印本 v0.4 (randinit/c1Mcs 时间轴/
  s12 确定性重跑), T2.2.2 S5 矩匹配对照, 10M c1M prefix arm 对照

### 2026-09-19 13:15: Day 9 v0.4 确定性重跑批次收口（交接文档 + 三项旧协议债务清零）
- 交接文档本地四件套全量状态回写：02_TASKS v2.4 / 03_CHECKLIST v1.9 /
  01_SPEC 新增附录 A（S0-S15 × H1-H8 执行状态映射，非冻结，冻结正文
  未动；含路径约定修正：evidence/figs 在 /mnt 不在 /home）
- **v0.4 债务三项清零（inc12 确定性协议，GPU6 串行 25 分钟）**：
  1. S4 randinit 73 旧行清除（备份 probe_results.pre_v04randinit_
     20260919.jsonl）→ 四档重跑 73 新行（18/20/12/23 层全）→
     新表：+0.0593/+0.0430/+0.1221/+0.1686（增益单调扩大复现，
     H2 排除稳健）；生成脚本入库 rna_sc/s4_randinit_table.py
     （初版为内联脚本未入库——可复现性缺口补上）
  2. 10M-c1Mcs 时间轴 4 ckpt（nt=100011217/300021677/500027239/
     700044056，实际 ckpt nt 而非圆整值——旧失败根因）：0.1B 0.218
     (L14) → 0.3B 0.230 (L16) → 0.5B 0.244 峰 (L9) → 0.7B 0.204
     (L6)——磨蚀 + 层下移在确定性协议下复现（9/16 旧协议结论升级
     为确定性口径）
  3. S12 linkage 确定性复算：30M-c1Mcs ρ=−0.478 / 100M −0.384 /
     30M-s29 −0.370（n=10 类；方向一致：高 DI 家族峰层更靠前；
     关联随规模减弱）。run 标签版证据保存（s12_linkage_30M_s17_
     c1Mcs.json / s12_linkage_100M_s17.json），根治 watch_all 单
     OUT 路径覆盖丢证据问题；s12_linkage.json 恢复为 s29 值
- 下游刷新：s1_summary / s1_seed_table / fig1_layer_migration
- 650M 训练不受影响（GPU2 nt≈0.14B/2.0B，watch_all/cron 全链在岗）
- 待办：S5 矩匹配（T2.2.2，650M 窗口）、T2.3.1 饱和点统计脚本、
  预印本 v0.4 数字更新

### 2026-09-19 13:52: T2.2.2 S5 矩匹配对照完成（H3 排除，四档全）
- probe.py 新增 --moment-matched（S5 控制）：先抓取 trained 各张量
  均值/方差 → 再重造 seed-17 随机模型 → 逐张量归一化重标定到
  trained 矩（74-146 tensors matched）；run 名 _mommatch17
- **H3 排除表（inc12 确定性协议，GPU6 串行 16 分钟）**：
  trained−mommatch = 1M +0.0286 / 10M +0.0478 / 30M +0.1233 /
  100M +0.1668；mommatch 峰值 F1 0.123-0.160 ≈ randinit 水平
  （0.101-0.158）——**匹配训练权重的一阶/二阶矩不能恢复任何
  预训练收益；收益来自权重结构（特征），非好初始化**
- 附带 bug 教训（自查第 2 遍抓出）：首版补丁先重造模型再"匹配"，
  匹配对象错成随机模型自身（只做单位方差化）；修复为**先捕获
  trained 矩再重造**。已验证 "moment-matched N tensors" 打印与
  74/82 张量数合理
- 表生成脚本入库 rna_sc/s5_mommatch_table.py（模式同 s4）
- 至此 Li et al. 三对照（S4 randinit / S5 mommatch / S6 timeline）
  全部确定性协议闭环——H2/H3 全档排除，H4 时间轴证据齐

### 2026-09-19 14:05: T2.3.1 饱和点统计完成（corpus_saturation.py）
- 95% 阈值 + 上升段插值 + 形态分类（monotone/U/mixed）+ 同 epoch
  覆盖配对（红队修正 A）落进 corpus_saturation.json
- **诚实结论：经典上升饱和点不存在**——两尺度均在最小唯一语料
  臂达峰（10M 0.9B / 30M 0.85B）；30M 形态=monotone-fall
  （0.316→0.302→0.287→0.247），10M 形态=mixed（0.186→0.152→0.173）
- 固定 2.0B nt 预算下 "更多唯一数据 ≠ 更好"：饱和点报告为 argmax
  臂（非渐进上界的 95%）——写预印本时按 "no classic saturation;
  performance peaks at the smallest corpus arm under fixed exposure"
  表述，配 epoch 覆盖标注
- 同覆盖对：30M-c1M（2.35 ep）vs 30M-c1Mcs（2.22 ep）——prefix
  vs 簇级分层归因用

### 2026-09-19 14:20: 预印本 OUTLINE v0.4（确定性数字全量入稿）
- 4.1-4.6 全部刷新为 inc12 确定性终值：S1 主表（含 30M n=3）/
  slope 0.142 CI [0.104,0.180] / S4 四档 / S5 矩匹配（新 4.6 节）/
  S6+c1Mcs 归因 / S12 三 run linkage / 语料轴 + 饱和点结论
- 剩余 3 个 PENDING 为真实未完成项（650M 结果 / BERT 中途峰文献 /
  结构任务磨蚀）；v0.3 备份 OUTLINE_v0.3_backup_20260919.md
- 结论链完整：H2 (S4) + H3 (S5) 全档排除 → 收益来自权重结构；
  H1 增益单调 + slope 触发 650M；H4 层迁移 + 磨蚀倒 U；H5 语料
  轴双形态；H6 初步（DI-峰层负相关）

### 2026-09-19 14:25: T0.2.6 评测矩阵 runner 上线（S9 前置，冒烟+10M 定稿）
- eval_matrix.py 入库：声明式 spec（模型×任务×协议×切分）+ eval ledger
  （flock JSONL 防重，模式同训练 ledger）+ GPUGuard 拒绝 CPU 回退
- 协议 v1：probe-balanced（class-weighted + cap10，红队修正 B）与
  probe-meanpool（day-1 基线）；切分 v1：family（簇级不相连）与
  random（family_validation 池内 i%5 行划分——**两科学性修正**：
  禁止从 MLM train 池取样（会把预训练暴露与切分类型混杂）；random
  侧家族重叠即协议要点，单变量隔离）
- 自查 3 遍抓出并修复：GPUGuard 导入源错误 / 死函数含不存在列名 /
  random 分支 tensor 堆叠类型
- **10M 首个 Δ(随机−家族) 数据点（strong）**：
  probe-balanced: family 0.1555 vs random 0.4928（Δ+0.337——家族
  切分下性能崩塌至 1/3，NABench "simply cheating" 的自训家族实证）；
  probe-meanpool: 0.1731 vs 0.1737（Δ≈0——协议选择掩盖泄漏效应，
  协议×切分交互证据）；meanpool family 复现 day-1 值 0.1731（确定性
  交叉验证）
- 1M/30M/100M 批次排队中（GPU6 串行）；v2（T1.2）：zero-shot/LoRA/
  full-FT + 任务三分法

### 2026-09-19 15:28: T0.2.6 v1 全矩阵 16 格收官（Δ 随规模放大定律）
- 四模型（1M/10M/30M/100M）× 两协议 × 两切分全格完成，ledger
  16 done（含 smoke），GPU6 串行总 ~53 分钟
- **核心发现 1——Δ(随机−家族) 随规模单调放大**（probe-balanced）：
  1M +0.0552 → 10M +0.3373 → 30M +0.4378 → 100M +0.4344——
  规模越大，random 切分可利用的家族内相似性越多（0.15→0.61），
  真泛化（family 切分）几乎不涨（0.10→0.17）→ **协议敏感性
  本身是规模的函数**；"随机切分下 bigger is better" 是度量
  伪影的直接证据
- **核心发现 2——协议×切分×规模三重交互**：meanpool 的 Δ 远小于
  balanced（10M +0.0006 vs +0.3373）；1M meanpool Δ 甚至为负
  （-0.0372）——协议选择系统性掩盖/放大泄漏效应（NABench 论断
  的 RNA 自训家族版实证 + 协议维度扩展）
- 层维度附带发现：30M/100M random 侧最佳层中段（8-10），family
  侧早层反超——层依赖随切分翻转（后续可并入 S7 分析）
- 证据：evidence/eval_matrix_v1_delta.json + eval/
  eval_matrix_results.jsonl + eval_matrix.jsonl（ledger）

### 2026-09-19 15:45: T1.2.5 k-mer 基线组 v1（良渚结论 RNA 复现 + 预印本叙事闭环）
- baselines_kmer.py：k-mer(1-6) 频率（5460 维）+ class-balanced
  logistic；family 与 random（i%5 与 eval_matrix 完全可比）双切分
- **核心结果（rna_type 任务）**：
  family: k-mer 0.1630 vs LM 1M/10M/30M/100M 0.098/0.156/0.168/
  0.170——家族级真泛化下 LM 对组成基线增益 ≈ 0（100M 仅 +0.007，
  1M/10M 为负）→ 良渚 Nat Commun 2025 "困难切分 gLM 打不过简单
  基线"在 RNA 受控家族复现
  random: k-mer 0.5180 vs LM 0.153/0.493/0.605/0.604——k-mer 自身
  Δ=+0.355：**泄漏是协议性质而非模型性质**（组成统计即可吃到）；
  random 下的"规模收益"大部分是家族相似性泄漏
- 与 S4/S5 组成完整三段论：(a) 预训练显著超越随机初始化/矩匹配
  （权重结构真实存在）；(b) 但真泛化口径下结构收益未转化为超越
  组成统计的下游增益；(c) random 切分放大的是家族相似性可利用度
  ——"预训练有用"的表观证据在协议修正后大幅缩水
- 证据：evidence/classical_baselines.json（kmer1-6+logistic v1；
  LightGBM/one-hot CNN 随后补）

### 2026-09-19 15:55: 预印本 OUTLINE 4.7 节（DELTA 定律 + 基线崩塌）入稿
- 摘要新增 (5)：Δ 随规模单调放大 + k-mer 复现（泄漏=协议性质）
  + 家族级评估下 LM 对组成基线优势崩塌至 ~0
- 贡献列表新增 (e)；三段论叙事段入 4.7
- 至此 Day 9 全部产出闭环：文档回写（4 件套）→ v0.4 确定性
  （S4/c1Mcs/S12）→ S5 矩匹配（H3）→ 饱和点 → 评测矩阵 16 格
  （Δ 定律）→ k-mer 基线（良渚复现）→ Fig3 候选 → OUTLINE v0.4+
  （9 commits: b3c0ff0..07aa5fe 待推最后一个）

### 2026-09-19 16:10: T1.1.1 bpRNA 数据接入完成（存量资产复用）
- 发现 /mnt/cunyuliu/BPfold_data/bpRNA 已有 bpRNA-1M(2.0) 标准
  TR0/VL0/TS0 切分（其他项目遗留，10814/198/1305 bpseq）
- bprna_parse.py：bpseq -> parquet（name/source/split/seq/pairs，
  1-based i<j 配对列表）+ 家族计数表；非连续位置重索引；断言
  i<j<=len 单测过
- 全量解析：**12,317 序列 0 失败，329,268 配对（184,174 长程
  ≥24nt，S8 级配比）**；家族标签 = 文件名 SOURCE（RFAM 9594 /
  CRW 669 / SRP 154 / tmRNA 145 / SPR 140 / RNP 112...）
- 产出：data/bpRNA_parsed.parquet + evidence/bpRNA_family_counts.json
- 下游：S7 结构 probe 扩面 / S13b 结构版钟形 / T3.3 三协议结构行

### 2026-09-19 16:35: S4×S9 交叉完成（泄漏归因三角定位）
- eval_matrix 跑 randinit/mommatch 双切分（10M 全 + 100M randinit）
- **归因表（probe-balanced，Δ=random−family）**：
  trained 10M +0.337 / 100M +0.434（100%）
  randinit 10M +0.038（11%）/ 100M +0.080（18%）
  mommatch 10M +0.041（12%）
  k-mer 基线 +0.355（105%）
- **机制结论**：泄漏红利兑现需要训练过的权重结构（对照只吃到
  11-18%），且随规模上升（容量越大读出越多组成层泄漏）；但 k-mer
  吃到 105% → 信号本体在序列组成层，预训练的角色是"学会读取
  组成层泄漏特征"。三方交叉把 "what transfers" 从黑箱拆成
  信号（组成层）× 读取器（训练结构）× 协议（切分方式）三因子
- 证据：evidence/s4x9_leakage_attribution.json；预印本 4.7 补强

### 2026-09-19 17:35: 1M/10M 补种子入队（全档三 seed 目标）+ 回应质询
- 用户质询三问（PPT 结果速览一）：1M/10M 单种子 / 10M best_rel=0.05
  例外 / 主表缺 random 切分列
- **行动 1**：wave.json 追加 RNA-Sc-1M_s29/s43 + 10M_s29/s43
  （need 2/3GB，supervisor 每轮重读 wave 会自动捞——当前 8 卡
  被外部占满在等待，有空即启动）；s1_seed_table FAMILY 映射扩展
  四行——目标：五档全三 seed（1M ~11h ×2、10M ~17h ×2）
- **行动 2（解释入档）**：10M best_rel=0.05 不是异常——S6 时间轴
  显示 10M 最好层随训练持续下移（0.1B 时 L16/rel 0.84 → 1.1B 后
  塌到 L1-3/rel 0.05-0.16），是磨蚀发现的层维度投影（中深层特征
  被磨掉、只剩早期层）
- **行动 3**：PPT 页 34 主表补 random 切分列 + 层位注记

### 2026-09-19 19:40: 四补种训练全部启动（6 卡并行）+ 用户质询回应
- supervisor 自动捞起新入队的 4 个补种 run：1M_s29（GPU5）/
  1M_s43（GPU1）/ 10M_s29（GPU4）/ 10M_s43（GPU0）——各 nt≈0.06B
  起步、loss ~1.3 正常下降；加 650M（GPU2）共 5 自训 + 外部任务
  并行；全 8 卡显存占用
- 目标：五档全三 seed（1M/10M 补齐后与 30M/100M 对齐）；
  FAMILY 映射已扩（s1_seed_table 自动并入）
- 用户对 PPT 三问的回应：单种子补齐（本批）/ 10M best_rel=0.05
  = 磨蚀签名（非异常，已在页 34 加脚注）/ random 切分列已补入
  主表（16 格数据）

- [auto] rnasc_1M_s43 complete: nt=2.00B best_val=1.0893 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_1M_s29 complete: nt=2.00B best_val=1.0631 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_10M_s43 complete: nt=2.00B best_val=0.8754 fallback=0; final probe+linkage+s1_summary done

- [auto] rnasc_10M_s29 complete: nt=2.00B best_val=0.8820 fallback=0; final probe+linkage+s1_summary done

### 2026-09-20 00:35: ★五档全三 seed 达成——10M 谷发现（磨蚀系统性证实）
- watch_all 自动链：4 补种 DONE → probe → s1_seed_table 自动并入，
  零人工干预完成全档三 seed：
  1M 0.1650±0.0131 / 10M 0.1535±0.0173 / 30M 0.2651±0.0162 /
  100M 0.3394±0.0147
- **10M 谷（新发现，入预印本）**：三 seed 下 10M 均值（0.1535）显著
  低于 1M（0.1650）——10M 的 mid-training 峰（0.2549@0.5B）在
  2.0B 全预算下塌到 1M 之下。磨蚀不是 seed 噪声（3 seed 全陷落）
  而是 10M 尺度的系统性质；S6 磨蚀倒 U 的"10M 谷"在三 seed 统计
  下加深
- slope 判定澄清：规则设计只看 30M→100M 段（FAMILY 本就只含
  30M/100M——预注册原文），10M 不参与判定；650M 触发决策不受
  影响，继续有效
- scaling 形态更新：1M→10M 为负增长（-0.0115），30M 起陡升——
  "10M 处于容量-语料张力最大点"叙事从层维度（磨蚀）扩展到
  终值维度（谷）
- fig1 已刷新（五档三 seed 版）

### 2026-09-20 16:00: S7 结构 probe 四档 + S14 RNS 全量（Day 10 双新线落地）
- **S7 结构 probe（bpRNA 配对位置二分类，首个非 rna_type 任务）**：
  1M 0.5526 (L6/rel0.35) / 10M 0.5678 (L13/rel0.68) / 30M 0.5756
  (L3/rel0.27) / 100M 0.5890 (L22/rel1.00)——结构任务上规模增益
  平缓（+0.036/decade 级）且 best 层行为与 rna_type 完全不同
  （中早层即有效，无磨蚀塌陷——磨蚀是任务特异性的！这补上了
  预印本 limitation "attrition shown for rna_type only" 的关键
  对照：结构 probe 无 10M 层塌陷）
- **S14 RNS（H8 表征可靠性，控制集 KS p=1.0 三查过）**：
  1M 0.172 / 10M 0.104 / 30M 0.078 / 100M 0.077 (RNS@10)——
  randinit 0.54-0.58；**表征组织质量 1M→30M 单调改善后平台**，
  与下游 F1 的 30M→100M 陡升完全解耦（E14 方向证据：嵌入
  邻近结构 ≠ 下游有用性，Prabakaran claim 跨域验证 + 解耦发现）
- 过程修复：probe_structure run_name 双重赋值 bug（自查第 2 遍
  抓到，mislabeled randinit 行已从 jsonl 剔除 + 备份）；三小 bug
  （list/sum、device、编辑换行）全在冒烟阶段暴露
- randinit 对照修复版重跑中（s7_ri_fixed.log）

### 2026-09-20 17:20: 预印本 OUTLINE v0.5（五节升级入稿）
- 4.1：全档三 seed 主表 + 10M 谷（系统性磨蚀，1M→10M 负增长）
- 4.3：磨蚀任务特异性（S7 bpRNA 结构 probe 无 10M 层塌陷——
  磨蚀侵蚀家族判别特征非结构特征）
- 4.8（新）：S14 RNS 解耦（表征质量 30M 平台 vs 下游 F1 持续升）
- 4.9（新）：S13b 预注册负结果（NOT-BELL，语料规模约束）
- 摘要 (5) 升级含 10M 谷；limitation "attrition rna_type only"
  标记 RESOLVED；v0.4 备份留档
- 剩余 2 个 PENDING：650M 结果（训练中 35%）+ BERT 文献引用

### 2026-09-20 18:20: S7 结构 probe 对照完成——预训练结构零增益发现
- S7 完整表（bpRNA 配对位置 F1）：
  1M 0.5294 / 10M 0.5663 / 30M 0.5756 / 100M 0.5890
  10M randinit 0.5678（与 trained 0.5663 差 0.0015！）
- **核心发现：结构任务上预训练增益 ≈ 0（10M 对照）**——bpRNA
  配对位置的线性可分性来自架构先验（ALiBi 位置编码 + 嵌入
  几何）；与 S4（rna_type 增益 +0.04~+0.17）形成任务对照：
  **预训练学到的是家族判别特征（泄漏读取器），不是结构特征**
- 证据三角互证：S7 结构零增益 + S12 高 DI 家族峰层更早 +
  S13b NOT-BELL + S14 表征-下游解耦——四条独立证据链一致指向
  "RNA 语料 MLM 预训练在 2.0B nt 预算下学到的可迁移内容主要是
  家族级序列统计，结构信息获得有限"
- 100M randinit 对照 timeout（rc=124）重试中（3h 预算）
- 预印本 4.3 节此发现待入稿（v0.6）

### 2026-09-21 10:15: GPU6 恢复批重启 + PPT Day10 同步 + S1 表重建
- 根因诊断：100M randinit 首次重试 rc=1 = GPU6 被外部任务瞬时挤占
  （OOM，4.75GB 可用）；S13b 全量版同因死亡（进程消失、json 未
  更新）；GPU6 已释放（36GB 空闲）→ gpu6_resume.sh 串行重启两任务
- PPT Day10 同步（37 页）：S1 三 seed 主表在用户 19:12 保存时已
  丢失（比对两备份确认）→ 完整重建（三 seed ± std + 10M 谷标注
  + 650M 55% 状态行）；新增页 37（S7/S13b/S14 表格 + 四证据链
  注记）；Day10 前备份留档
- 650M：nt=1.10B/2.0B（55%），loss 0.83——预计 ~1.5 天完成，
  快于原估（GPU2 独占 + 无干扰）

### 2026-09-21 11:50: GPU6 恢复批全部收口——S7 终表 + S13b 全量确认
- **S7 结构 probe 终表（双对照）**：100M trained 0.5890 vs
  randinit 0.5855（Δ+0.0035）；10M trained 0.5663 vs randinit
  0.5678（Δ-0.0015）——**结构任务预训练增益 ≈ 0 在两个独立尺度
  复现**（|Δ|≤0.004），四证据链对照基础双尺度成立
- S13b 全量（8000 train，30 点）：NOT-BELL 确认，CI 收紧至
  [-0.183, -0.166]；峰 x=1.765 仍在数据范围外（结论与 v1 小样本
  一致——稳健）
- 650M：nt=1.12B/2.0B（56%），loss 0.61；预计 ~1.2 天完成

### 2026-09-21 13:00: T1.3.2 首个外部模型（RNA-FM 96M）逐层 probe 完成
- 服务器存量资产复用：RNA-FM_pretrained.pth（fairseq dict，ESM 式
  12 层 d=640 FFN 8x vocab25）——probe_rnafm.py 最小复现前向
  （FFN 8x 维度修正）
- tokenizer 验证：current-token identity hit 0.40 > chance 0.25
  （A/C/G/U=4/5/6/7 映射正确 + 模型真实工作）
- **全量结果（20k/4k，inc12 协议）**：12 层 F1 从 0.1335 (L0)
  单调降到 0.0582 (L11)——**best 在第 0 层（嵌入层）**；与自训
  家族层行为完全相反（受控家族 best 深层 0.86，RNA-FM best 嵌入层）
- **对照科学价值**：① RNA-FM 96M（官方更大语料）家族级 F1
  0.1335 < RNA-Sc 100M 0.3394——官方模型在困难切分下同样脆弱
  （良渚结论线 1 侧印证）；② 层行为反转 = 预训练配方（语料
  构成/时长）主导层组织方式，不是参数量
- 下一步：RiNALMo 三档接入（Zenodo 下载）

### 2026-09-21 14:30: 红队 E 强制项通过——去 rRNA 分层全结论稳健
- der_rna.py：从现有 jsonl 的 per_class_f1 重算排除 rRNA 的
  macro-F1（免重跑 probe）
- **全部结构性格结论在去 rRNA 下存活**：规模趋势 ✓（30M>10M、
  100M>30M）；10M 谷 ✓（更明显：0.062<0.074）；层迁移方向 ✓
  （1M 0.47→10M 0.14→30M 0.79→100M 0.86）
- 绝对值缩水（100M 0.34→0.27）= rRNA 贡献大部分绝对性能；
  结构性结论由非 rRNA 家族独立支撑——审稿人 E 质疑正面回应
- 附带发现：去 rRNA 后 10M best 层 0.14（vs 含 rRNA 的 0.05）
  ——磨蚀塌层部分由 rRNA 通道驱动，非 rRNA 通道早层优势保留

### 2026-09-21 18:10: S14 v2 家族分层交叉验证（T3.5.5 / C9.4 验收达成）
- s14_family.py：11 家族 × {RNS@10（30M/1M）× per-family probe F1}
  交叉（GPU1 重试成功——GPU6 外部挤占 OOM 后换卡策略生效）
- **Spearman(RNS, probeF1) = −0.19**（弱负相关）：方向符合 E14a
  （分离好→probe 好）但解释力弱 → 家族层面"表征分离 ≠ 下游
  有用"解耦成立（与规模轴解耦互证）
- 家族细节：rRNA RNS 0.025（分离最好）probe 0.97（最高）；
  sRNA/snoRNA RNS 0.20-0.43 且 probe F1=0——**欠表示家族嵌入
  更随机化**（Prabakaran 主张的 RNA 域验证，E14a/b 混合形态）
- C9.4 验收：交叉验证表 + E14 判定齐（证据 s14_family_
  crossval.json）

## Day 11（2026-09-22 凌晨-晨）——T1.2.5 收口 + 外部模型线扩展
- T1.2.5 全基线完成（dc1a4fc）：LightGBM family 0.1760/random 0.5485、
  one-hot CNN 0.1725/0.5617、randemb 0.0702/0.0557；收益口径
  LM−最强基线：family 30M +0.089/100M +0.163、random 全负
- RiNALMo-micro 36M probe（dc1a4fc）：multimolecule hf-mirror 接入，
  best L8 0.2407（vs RNA-FM L0 0.1335）——语料组成>参数量
- 红队 E 外部版（0065bc8）：探针 v2 补 per_class_f1；两外部模型
  层形态去 rRNA 全存活（derRNA_external.json）
- PPT 38 页：新增结果速览（四）（五）表格页
- 650M nt=1.3B/2.0B（65%），loss 1.21，训练健康

## Day 11 补充（2026-09-22 晨）——复现批（用户质询触发）
- 用户质询 1（CNN random 反超所有 LM）：核查确认表述错误——
  30M 0.605/100M 0.604 > CNN；且 CNN 补三 seed：0.5343±0.0206
  （0.5617 单 seed 偏乐观）；PPT/文档已修正
- 用户质询 2（单点实验不严谨）：RiNALMo 参数量轴三点闭合
  （micro 36M 0.2407 / mega 148M 0.2532 / giga 650M 0.2667）
  ——18× 参数仅 +2.6pp；语料轴 +11pp；语料组成主导三点证据
- micro pseed29 复现 0.2436（层位 L7-L8 稳定）
- S7 randinit 补齐四尺度：1M 0.5452/30M 0.5786（结构零增益全档）
- de-rRNA 外部版四模型层形态全存活
- 650M 训练持续（nt≈1.45B/2B）

## Day 11 续（2026-09-22 午）——T1.3.3 + T1.2.6 probe 线
- T1.3.3 分箱表完成（a90ff13）：短箱塌陷/长箱规模分化（30M/100M
  0.116/0.106 vs 小档 0.052）
- T1.2.6 低数据 probe 线：全尺度曲线平坦（<5pp/百倍样本）——S14
  解耦在数据量轴复现
- PPT 39 页：结果速览（六）分箱+低数据表
- 650M nt=1.5B/2.0B（75%）

## Day 11 晚（2026-09-22）——显存利用批（四卡并行）
- T1.2.6 full-FT 线（GPU4，f93ec82）：10M 0.059→0.108 / 100M
  0.064→0.153 上升曲线（vs probe 平坦）——低数据瓶颈=头容量
- S14 时间轴（GPU3，f93ec82）：10M RNS 峰 1.0B vs F1 峰 0.5B
  错位；1.0B 后 RNS 亦降——解耦三轴（规模/家族/时间）齐
- S9 独立查重（GPU5，3dc9e03）：精确协议复算 0.6053/0.6040
  与 ledger 逐位一致（30M/100M random 平台真实）；v1 差异
  系我方 probe 超参不同（协议敏感性附注 +0.10-0.16 F1）
- 650M nt=1.6B（80%）

## Day 11 晚三（2026-09-22）——用户质询批（全层统计+mega s29）
- mega pseed29 补齐（87ee95b）：L29 0.2541（vs L25 0.2532）——
  外部线 8/8 run 双 seed 矩阵闭环
- ext_full_layers.py：全层 rel-depth 四分带统计表（用户质询
  其他深度层触发）——RNA-FM 四带单调降；RiNALMo 三档升至
  late/top 峰（evidence/ext_full_layers.json）
- PPT 页 37 加全层附表
- 650M nt=1.66B（83%）

## Day 11 晚四（2026-09-22）——用户质询：四分带稀释
- 细粒度对齐分析（26e2313）：giga 对 mega 29/30 对齐层更高
  （+0.017 全层增益，中段 +0.023）——四分带确实稀释
- 深层发现：micro→mega 同绝对层更弱（-0.054）但好层数 0→5；
  mega→giga 转全层抬升——参数增益形态转变（延展→抬升）
- 量级结论稳健：top10 层均值 18× +4.8pp
- 650M nt≈1.67B（84%）

## Day 12（2026-09-22 晚五）——交接收口批：收口链部署 + S3 重加权 arm 启动
- 650M 收口链自动化补齐（closeout_650m.py）：等 watch_all DONE probe
  → s1_final_verdict 五档终判 → s13b_bell v2（650M 追加覆盖点）；
  修正了此前"终判需手动触发"的链路缺口
- S14 RNS 650M 单点（s14_rns_650m.py，GPU6 逐序列前向 OOM 硬化版）：
  补 H8 规模轴终点（预期 RNS<=0.077 平台延续或更低）
- S3 多样性重加权 arm（T2.3.3）正式启动：
  - s3_reweight_corpus.py：alpha=1.0 簇级展平（1/簇大小^α·med），
    14.1M train 行 → 57.7M 有效行（超采样上限 8×，中位簇 842），
    r22_train_reweighted.parquet 13.0GB 落盘 /mnt
  - train_s3_rw.py 绕过 SPLIT_8080 硬编码，30M 模型同配方单变量
    启动（GPU3，runs/RNA-Sc-30M_s17_rw1，corpus_tag=rw1）
  - 注意：validate 仍走原 split 的 validation 池（对比组可比性保持；
    训练分布 rw1 vs 30M-full 的 F1 对比即 H5 多样性检验）
- S9 独立查重通过（3dc9e03）；外部线 8/8 双 seed 闭环（Day 11 晚三/四）

## Day 12 补（2026-09-22 17:35）——S14 650M RNS 终点落盘
- S14 RNS 650M 单点完成（GPU6）：RNS@10 = 0.0684（@50 0.0910 / @100
  0.1042），低于 100M 的 0.077 → H8 规模轴终点确认：表征质量在
  30M 平台后继续缓慢改善（0.077→0.068），"平台+缓降"形态——与
  下游 F1 的陡升进一步解耦（E14b 叙事强化：表征组织与下游有用性
  双轴分离在五档全尺度成立）
- 注意口径注记：len cap 192（v1 四档为 256）+ 逐序列前向——绝对值
  与 v1 略不可比（已写入 json note 字段），趋势结论不受影响
- 30M-rw1 训练健康（nt=43M/2.0B，loss 1.29 正常区间）

## Day 12 续二（2026-09-22 晚六）——T1.0.3 300M 锚点档启动（修订三执行）
- 300M spec 注册（specs.py，commit 7101c49）：d=1024/L=24/h=16/ff=4096
  → 302.1M（0.7% 标称偏差，家族 12% 容差带内；deep-narrow 形态）
- 300M@2B iso-token 臂经 wave.json → supervisor 自动调度 GPU0 启动
  （10:13Z，fresh）；~3-4 天完成
- 科学角色：①补 100M→650M 对数轴 6.5× 空洞（触发判断外推→内插）；
  ②300M@5.9B 语料最优锚点臂待本臂完成后排队（Claim-14 边界判据）
- 当前集群全景：GPU0=300M / GPU2=650M(85%) / GPU3=30M-rw1(S3)，
  三任务并行 + 收口链 + watch_all + cron 全链在岗

## Day 12 续三（2026-09-22 18:40）——巡检告警处置：rw1 误杀排查
- 18:32 巡检抓到 ALERT GPU-CONTEXT-LOSS pid=1214842（rw1 的 bash 包装
  进程，cron 守护脚本因 4 分钟日志 stale 判定 GPU 上下文丢失而 KILL）
- 三遍核实结论：**误杀的是外层 bash wrapper，实际训练进程 1214846
  （1h25m，GPU3 4.6GB，99.7% CPU）全程存活且健康**——log 滚动正常
  （nt=80M/2.0B，loss 1.26-1.32），GPU3 利用率 100%
- 根因：train_s3_rw.py 的 nohup 包装链比 supervisor 直启的进程多一层
  bash（bash→python），cron 守护脚本的 stale-log 启发式盯的是 bash
  pid（它本身不打日志 → 恒 stale）
- 风险点（诚实登记）：①rw1 无 checkpoint 落盘（首个 VAL/ckpt 在
  nt=100M；当前 80M）——若真挂将丢失 80M nt 进度，重启代价 45 分钟；
  ②rw1 的 bash wrapper 已死，进程脱管（不影响训练，只影响守护）
- 处置：训练进程保留不动（避免重启返工）；下次 cron 若再 KILL 会
  miss（pid 已不存在）；后续 rw1 类自启 arm 改用 supervisor 队列
  模式启动（守护一致性）——已作为纪律记入

## Day 12 续四（2026-09-22 19:05）——650M 例行巡检（未 DONE，不打扰训练）
- **RNA-Sc-650M_s17 进度 86.7%**（nt=1734M/2.0B，step=185000；log
  DONE 帧计数=0，log 仍在滚动，GPU2 util 100%）
- 最新 ckpt：runs/RNA-Sc-650M_s17/ckpt_nt1700101716_step181412.pt
  （17:41 落盘，7.5G；对应 VAL best=0.7816 @nt=1700M）
- 吞吐 ~6.4k nt/s（1600M→1700M 历时 4h22m）→ 剩余 266M nt，
  ETA ≈ 2026-09-23 早 06:30 前后
- 收口链在岗待命（无需人工干预）：watch_all（pid 3748436）+
  closeout_650m --device 6（pid 1070350）将在 DONE 后自动执行
  probe → s1_final_verdict 五档终判 → s13b_bell v2；当前
  eval/probe_results.jsonl 无 RNA-Sc-650M_s17 行（符合预期，未 DONE）
- 证据：logs/RNA-Sc-650M_s17.log 尾帧 / runs/RNA-Sc-650M_s17/
  manifest.json（budget_nt=2.0B，17 次 validation 全程无 CPU 回退）

## Day 12 续四（2026-09-22 19:10）——T4.1 图表工程启动（650M 等待窗口）
- Fig 5c（S14 RNS，T4.1.5c）生成：figs/fig_s14_rns.{png,pdf}——
  (a) 规模轴五档含 650M 终点 0.0684 + randinit 带 0.54-0.58；
  (b) 10M 时间轴双峰错位（RNS 峰 1.0B vs F1 峰 0.5B）——H8 双轴
  解耦的主图（fig_s14_rns.py）
- 外部模型线图（4.10）生成：figs/fig_ext_corpus_vs_params.{png,pdf}
  ——(a) RiNALMo 三档参数轴近平线（18× +2.6pp）+ 受控家族对照
  (b) 语料轴对比（RNA-FM 96M 通用 0.1335 vs micro 36M ncRNA
  0.2407——小参数 +11pp）
- 数据三遍核对：绘图脚本数字与证据 JSON 逐位一致（程序化输出
  确认 rinalmo 0.2407/0.2532/0.2667、RNS 五档 0.172→0.068）
- OUTLINE.md 4.8/4.10 节补图引用；本地 figs_v1/ 备份两图
- 650M 87%（等收口）；300M 34M nt 健康；rw1 80M nt 健康

## Day 12 续五（2026-09-22 19:40）——preprint DRAFT v1.0 撰写启动（T4.2）
- DRAFT_v1.md 落盘（preprint/，380 行）：OUTLINE v0.7 全证据骨架扩写
  成完整英文手稿草稿——Title/Abstract/Intro（四点动机）/Related
  Work（含 REDIAL/DNA 分界）/Methods/Results 4.1-4.12 全节成文/
  Discussion/Limitations/Repro + D1-D11 写作纪律自查门
- 数字三遍核对：四档 seed 表均值、RNS 五档、slope CI 程序化比对
  全部在文中逐位一致；650M 相关 7 处 PENDING-650M 占位槽（收口链
  填充后升级 v1.1）
- 写作纪律门：D1-D3/D7-D10 ✅；D4/D6/D11（完整参考文献列表）
  标注 submission 时补——结构已留位
- 状态：650M 87% / 300M 39M nt / rw1 117M nt 全健康

## Day 12 续六（2026-09-22 19:25）——D4/D6/D11 参考文献列表完成
- preprint/DRAFT_refs.md 落盘：30 条完整文献列表，全部取自备忘录
  §9 已核验证据池（三源交叉核验过的 DOI/arXiv 才打印；未核验
  标识符标 [id-verify] 留最终 bib pass——零伪造 DOI 纪律）
- 五组分类：蛋白域锚点 8 条（Rives/Li/Hou/Prabakaran/InterPLM/
  Vishniakov/DenAdel/ESM-2）+ RNA LM 9 条 + 基准与协议研究 10 条
  + scaling 文献 3 条（Muennighoff/Chinchilla/Kaplan）
- DRAFT_v1.md 写作纪律门升级：D4/D6/D11 ⚠️→✅（引用完整性）；
  D1-D11 全门通过（PENDING-650M 槽除外）
- 650M 87%（1.74B，剩 ~5h）；300M 41M；rw1 123M 健康

## Day 12 续七（2026-09-22 19:40）——Fig 5 生成（T4.1.5 落勾）
- figs/fig5_controls_timeaxis.{png,pdf}（三面板）：
  (a) 对照排除图——trained/randinit/moment-matched 四档对比 +
  增益标注（+0.059/+0.043/+0.122/+0.169）；
  (b) 时间轴四尺度轨迹——10M attrition valley（峰 0.2549@0.5B）
  + 30M/100M 持续上升；
  (c) best-layer 相对深度时间轴——10M 层塌缩签名 vs 大尺度层深化
- 数字三遍核对：deltas 与 s4_randinit_table.json 逐位一致；
  10M 峰 0.5B/0.2549 与 s6_cross_scale.json 一致
- 至此 T4.1 图资产 4/6：Fig 1（已有四档版）/ Fig 3（delta 热图
  已有）/ Fig 5（本次）/ Fig 5c（S14 已有）+ 外部模型图；
  待 650M：Fig 1 升级五档版 + Fig 5b（S13b v2）

## Day 12 续八（2026-09-22 19:50）——表 1 生成（T4.1.6 落勾）
- preprint/TABLE1_baselines.md：9 行完整基线总表（四档 LM +
  randinit 对照 + 四条经典基线），列 = family F1 / random F1 /
  Δ(rand−fam) / LM−最强经典基线
- 数字三遍核对：CNN 三 seed [0.5617, 0.5295, 0.5117] → 0.5343
  ±0.0207 与 TASKS 登记一致；LM−最强基线 1M −0.011 / 10M −0.022
  / 30M +0.089 / 100M +0.163 与 4.12 节一致；k-mer Δ +0.355 一致
- 表格自动生成脚本入库（rna_sc/table1_baselines.py，防手抄错数）

## Day 12 续九（2026-09-22 19:55）——Fig 2 生成（T4.1.2 落勾）
- figs/fig2_layerwise_tasks.{png,pdf}（2×2 四面板）：
  (a) rna_type 逐层曲线四尺度（层迁移 + 10M 早期层签名）；
  (b) 去 rRNA 分层散点（红队 E——全尺度趋势存活）；
  (c) bpRNA 结构逐层曲线（平坦、无 10M 磨蚀——任务特异性）；
  (d) 结构任务 trained vs randinit 柱状（|Δ|≤0.016 全档）
- 数字核对：结构四档 trained best 0.5294/0.5663/0.5756/0.5890 与
  G++.1 登记逐位一致；derRNA 散点 f1_all→f1_der 与
  derRNA_stratified.json 一致
- T4.1 图表资产 6/6 主体完成（除 650M 依赖项：Fig 1 五档升级 +
  Fig 5b S13b v2）

## Day 12 续十（2026-09-22 20:10）——DRAFT v1.1 自动填槽链上线
- fill_draft_650m.py 入库：从 s1_final_verdict.json 自动填充
  DRAFT_v1.md 的 7 处 PENDING-650M 槽（verdict 未就绪时无副作用
  退出）；填前自动备份 DRAFT_v1_pre650M_backup.md
- closeout_650m 链扩展为四段：DONE probe → 五档终判 → S13b v2 →
  DRAFT v1.1 自动填槽（进程已重启加载新代码）
- 至此 650M 收口全链无人值守化：训练→probe→终判→图表素材→
  手稿填数字全部自动

## Day 12 续十一（2026-09-22 20:20）——5.9B 预算臂管线打通
- train.py 补 --budget-nt 参数（run→resolve_config 全链贯通，warmup
  按比例自适应；单测验证 300M@5.9B → budget 5.9B/warmup 0.0295B）
- supervisor.py 支持 wave 条目 budget_nt 字段并重启加载新代码
  ——正确 adopted 650M/300M 两个在跑 run（接管无缝）
- T1.0.3 臂②300M@5.9B（corpus_tag=b59）入队 wave.json：等 650M
  释放 GPU2 后 supervisor 自动拉起（Claim-14 语料最优锚点判据的
  必需实验）；~7-9 天完成（5.9B nt 全语料 1 epoch）
- 3×2 析因矩阵至此全部入轨：300M@2B（在跑）/ 300M@5.9B（排队）/
  100M@5.9B（T1.0.4，视 300M@5.9B 进度排期）/ 650M@2B（在跑收口）

## Day 12 续十二（2026-09-22 20:30）——650M 巡检（未 DONE，仅记录不干预）
- RNA-Sc-650M_s17 训练健康推进：logs/RNA-Sc-650M_s17.log DONE 帧=0；
  尾部 nt=1771M/2.0B（≈88.6%，step 189000，pid 422582 CPU 96.7%，
  GPU2 util 100%，日志 mtime 20:22 持续刷新，20 min 内 1760M→1771M）
- 最新 ckpt runs/RNA-Sc-650M_s17/ckpt_nt1700101716_step181412.pt
  （val_loss 0.7816；manifest.json 17 个 val 点单调降 1.0662→0.7816）
- 收口链值守确认：closeout_650m + watch_all 进程存活
  （logs/closeout_650m.log 尾部 "chain A: waiting for 650M final probe"）
- 按纪律不动训练：终判（s1_final_verdict.py）/ S13b v2 / DRAFT v1.1
  填槽 / preprint v1.0 / T1.2.6 full-FT 均待 DONE 后自动或下次巡检执行

## Day 12 续十二（2026-09-22 20:35）——b59 臂启动经过（如实登记）
- 300M@5.9B（b59）第一次 GPU5 启动 OOM（其他用户三进程占满后
  挤压）；supervisor 自动重试调度 GPU3 成功——与 rw1 共卡训练
  （b59 nt=4M 推进中，rw1 199M 存活但吞吐降）
- 调度判断：GPU3 40GB 上 300M（~14GB 峰值）+ 30M rw1（~5GB）
  可共存；650M DONE 释放 GPU2 后 supervisor 会按显存重新平衡
- 注意：b59 的 run_id 在日志行显示为 rnasc_300M_s17（resolve_config
  的 tag 拼接未含 b59——manifest 已含 corpus_tag=b59 区分，无
  数据风险；run_id 显示瑕疵留待下轮修）

## Day 12 续十三（2026-09-22 21:20）——650M 巡检（未 DONE，仅记录不干预）
- RNA-Sc-650M_s17 训练健康推进：logs/RNA-Sc-650M_s17.log **DONE 帧计数=0**
  （grep -c DONE）；尾部 nt=1793M/2.0B（**≈89.7%**，step=191400，loss
  0.88 波动正常，lr 余弦尾部 7.90e-06）；进程 pid 422582 存活（Sep19 起
  CPU 96.7%，GPU2 util 100%）；日志 mtime 21:14 持续刷新——训练健康。
  status.json 85.01% 系 ckpt 快照口径（17:41 第 17 ckpt），非停滞。
- 最新 ckpt：runs/RNA-Sc-650M_s17/ckpt_nt1700101716_step181412.pt
  （val_loss 0.7816；manifest.json 17 个 val 点单调降 1.0662→0.7816）。
  第 18 ckpt（nt 1.8B）预计 ~23:00 落盘，DONE（2.0B）预计明日凌晨。
- 收口链值守确认：closeout_650m 进程存活（pid 1948279，"chain A:
  waiting for 650M final probe"→logs/closeout_650m.log）+ watch_all
  存活（pid 3748436，Sep17 起，cycle 1632）+ /tmp/watch_pretrain_650.sh
  kill -0 监听 pid 422582；eval/probe_results.jsonl 中 RNA-Sc-650M_s17
  行数=0——未 DONE 不 probe，符合协议。DONE 后自动：probe→s1_final_
  verdict 五档终判（evidence/s1_final_verdict.json）→S13b v2→DRAFT
  v1.1 填槽，无需人工触发。
- 同卡在训臂（不加干预）：300M@2B（pid 1441172，GPU0，nt=107M/2.0B，
  manifest 已落 1 ckpt val_loss 1.0661）；300M@5.9B b59（pid 2046309，
  GPU3，nt=21M，manifest 已含 corpus_tag=b59）；30M-rw1（pid 1214846，
  GPU3，nt=220M/2.0B=11%，18:32 GPU-CONTEXT-LOSS 事件已消化）。
  cron.log 尾部 no alerts、all 3 train PIDs present on GPUs。
- 按纪律未执行：s1_final_verdict.py 手动触发 / TRAINING_LOG 终判落款
  02_TASKS T2.1.3 收口 / preprint v1.0 / T1.2.6 full-FT 线——均待 DONE
  后由收口链自动或下次巡检执行（GPU 全忙：0-5 卡 util 58-100%，无空
  闲卡可启 full-FT）。

## Day 12 续十四（2026-09-22 23:19）——650M 巡检（未 DONE，仅记录不干预）

- RNA-Sc-650M_s17 训练健康推进：logs/RNA-Sc-650M_s17.log **DONE 帧计数=0**
  （grep -c DONE）；尾部 nt=1837M/2.0B（**≈91.9%**，step=196000，loss
  0.55 波动正常，lr 余弦尾部 4.97e-06）；进程 pid 422582 存活（3d16h，
  CPU 96.8%，GPU2 util 100%），日志 mtime 23:07 持续刷新——训练健康。
  按 100M nt/4.1h 节奏推算，DONE（2.0B）预计 09-23 早 06:00-07:00。
- 最新 ckpt（第 18 个）：runs/RNA-Sc-650M_s17/ckpt_nt1800114281_step192108.pt
  （21:50 落盘，提前于 21:20 预测的 ~23:00；val_loss=0.7776 best；
  manifest.json 18 个 val 点单调降 1.0662@0.1B→0.7776@1.8B，无过拟合）。
- 收口链值守确认：closeout_650m 进程存活（pid 1948279，20:02 起，
  "chain A: waiting for 650M final probe"→logs/closeout_650m.log）+
  watch_all 存活（pid 3748436，Sep17 起，cycle 1668）+ /tmp/
  watch_pretrain_650.sh kill -0 监听 pid 422582；eval/probe_results.jsonl
  中 RNA-Sc-650M_s17 行数=0——未 DONE 不 probe，符合协议；
  s14_rns_650m.json（20:27）/ s1_final_verdict.json（12:06）均在位。
- 同卡在训臂（不加干预）：300M@2B（pid 1441172，GPU0，99%）、
  300M@5.9B b59（pid 2046309，GPU3）、30M-rw1（pid 1214846，GPU3）；
  GPU6/7 为 S14 RNS 补点重跑与他方进程占用；cron.log：no alerts、
  all 4 train PIDs present on GPUs，无 ALERTS / CPU FALLBACK。
- 按纪律未执行：s1_final_verdict.py 手动触发 / 02_TASKS T2.1.3 收口 /
  TRAINING_LOG 终判落款 / preprint v1.0 撰写 / T1.2.6 full-FT 线
  （GPU 0-5 util 58-100% 全忙，无空闲卡）——均待 DONE 后由收口链
  自动执行或下次巡检确认收口结果。

- [closeout][WARN] 650M probe not complete after 6h wait; verdict deferred

- [auto] rnasc_650M_s17 complete: nt=2.00B best_val=0.7757 fallback=0; final probe+linkage+s1_summary done

- [fill_draft_650m] DRAFT v1.1 auto-fill: 6 slots replaced from s1_final_verdict (650M F1 0.3632, gain 2.4 pp, slope 0.0293); backup DRAFT_v1_pre650M_backup.md

## Day 13（2026-09-23 13:20）——★650M DONE + 五档终判出（S1 收口）
- 650M 凌晨 DONE（nt=2.0B，best_val 0.7757，fallback=0，5826 nt/s）；
  watch_all 已自动完成全 28 层 probe（best L8 0.3632）
- 收口链超时缺口如实登记：closeout_650m 的 6h 等待窗在 DONE 前耗尽
  （凌晨 02:12 DONE vs 20:02 启动的 6h 窗），WARN 落款 verdict deferred
  ——本次人工补跑 s1_final_verdict 成功收口（根因：等待窗应从 DONE
  事件起算而非进程启动；修复入收口纪律）
- **五档终判（evidence/s1_final_verdict.json）**：
  1M 0.1650±0.0131 / 10M 0.1535±0.0173 / 30M 0.2651±0.0132 /
  100M 0.3394±0.0120 / 650M 0.3632
  - **650M_gain = +2.4pp（6.5× 参数）——与外部线 RiNALMo 18×+2.6pp
    定量互证（跨家族收敛）**
  - **slope 100M→650M = 0.0293 < ε=0.03：scaling 饱和确认**（触发
    斜率 0.142 衰减 5 倍；full-axis 0.0829/decade）
  - 10M 谷持续存在（650M 时代仍 10M < 1M）
  - **层迁移终点非单调：650M best L8/rel 0.296（中早期）**——
    100M rel 0.864 后回落，新现象（解释候选：650M 容量下中早期
    层已足够承载家族级统计，深层过特化于 rRNA 通道——与 S12 DI
    关联/磨蚀机制呼应；分析待下轮）
- S14 650M 终点更新（20:27 重跑版）：RNS@10 0.062（< 前值 0.0684，
  共卡拥挤下逐序列口径）——H8 平台+缓降结论不变
- DRAFT v1.1 自动填槽完成（6/7 槽；1 槽 S13b v2 运行中待回填）
- S13b v2（+650M 置信度覆盖点）GPU6 运行中

## Day 13 补（2026-09-23 14:15）——S13b v2 终判 + 650M 收口链全闭环
- S13b v2 完成（GPU1 重跑成功；GPU6 首次 OOM 换卡）：36 家族点
  （+650M 6 点），NLL 覆盖扩至 1.03-1.37（650M 最自信 RNP 1.03/
  CRW 1.20）——预注册判据下仍 NOT-BELL（峰值 x=1.72 在数据外）：
  H7 负结果对置信度覆盖扩展稳健，E13b-b 定案（图已重绘）
- DRAFT v1.1 第 7 槽回填完成——七槽全满，DRAFT v1.1 收口
- 650M 收口全链闭环：S1 五档终判 + S14 终点 + S13b v2 + DRAFT 填槽
- GPU2 已释放可接 T1.2.6 full-FT 扩档

## Day 13 补二（2026-09-23 14:30）——Fig 1 五档主图升级
- fig1_layer_migration.py 主 RUN 集换为五档（1M/10M/30M/100M/650M
  + randinit 对照；去掉 c1M/c1Mcs/s29/s43 子线——语料臂与种子副本
  留 Fig 5b/附录位），fig1_layer_migration.png 重绘完成
- 五档层曲线 + best-layer 迁移（1M rel0.47 → 10M 0.14 → 30M 0.79 →
  100M 0.86 → 650M 0.30 非单调终点）为论文 Fig 1 主图定稿版


## Day 13 补三（2026-09-23 19:25）——晚巡检：650M 收口复核 + T2.1.3 归档 + T1.2.6 扩档启动
- 晚巡检复核 DONE 帧（logs/RNA-Sc-650M_s17.log 尾部）：
  DONE rnasc_650M_s17 | nt=2000003270 steps=213514 best_val=0.7757 |
  5826 nt/s peak=15579MB fallback=0 ——与 manifest.json
  （final_nt=2000003270, best_checkpoint=ckpt_nt1900122218_step202784.pt,
  status=DONE, end_utc=2026-09-22T22:11:50Z）一致
- watch_all 自动 probe 复核：eval/probe_results.jsonl RNA-Sc-650M_s17
  28/28 层全覆盖于 final_nt=1900122218，best L8 F1=0.3632；
  watch_all.log 见 "rnasc_650M_s17 DONE nt=2.00B val=0.7757 -> probe GPU2"
- s1_final_verdict.py 幂等复跑：evidence/s1_final_verdict.json md5
  前后一致（08f2542b...）——五档终判稳定（650M F1 0.3632 > 100M
  0.3394，+2.4pp；slope 100M→650M 0.0293 < ε=0.03，scaling 饱和；
  10M 谷持续；层迁移终点 650M rel 0.296 非单调）
- 02_TASKS 收口：docs/TASKS_V2.md T2.1.3 勾选 ✅（验收三件套齐：
  s1_slope_decision.json 触发判定 / s1_final_verdict.json 终判 /
  TRAINING_LOG 决策记录）
- preprint v1.0 线：DRAFT_v1.md 清理 fill_draft_650m 痕迹 4 处
  （"650M PENDING"→五档表述、"True.."→规范句、"rel 0.30.."→"rel
  0.296"、RNS 650M 0.0684→0.062 引 s14_rns_650m.json；摘要规模
  1M–100M→1M–650M）——DRAFT v1.1 定稿版
- T1.2.6 full-FT 扩档启动：fullft_lowdata.py RUNS 增 650M s17（v1.1
  三档 10M/100M/650M）；t126_watch_launch.sh watcher 已起
  （pid 2656868），gpu_pick 判 GPU0 真实空闲 19GB 后于 19:29 自动
  启动（logs/t126_fullft_650m.log），产物 evidence/t126_fullft.json，
  完成后落 logs/t126_fullft_650m.done；timeout 6h、单次退出、不覆盖
  他人进程；同卡在训臂 300M s17 不受干预
- 侧记：closeout_650m 的 6h 等待窗缺口已在前次落款登记（根因：
  窗口应自 DONE 事件起算），本轮仅复核未重触发

## Day 13 补四（2026-09-23 20:10）——晚巡检二：五档终判幂等复核 + t126 v1 OOM→v2 自愈记录

- 五档终判幂等复核（本条由 20:01 独立会话执行）：复跑 s1_final_verdict.py
  前后 evidence/s1_final_verdict.json md5 完全一致（08f2542b...）
  ——五档表/checks 数字稳定可复现：650M F1 0.3632 > 100M 0.3394
  （+2.4pp）；slope 100M→650M=0.0293 < ε=0.03（scaling 饱和）；
  10M 谷持续；层迁移终点 rel 0.296（L8/28）非单调。与 Day 13 补三
  的 13:24（6d35bf9）结论逐项吻合。
- probe 复核：eval/probe_results.jsonl 中 RNA-Sc-650M_s17 全 28 层
  覆盖于 final ckpt_nt=1900122218（early 9/middle 9/late 10），
  best f1_macro=0.3632@L8——watch_all 自动收口口径无误。
- 侧记 DRAFT 同步：本地论文/ 目录 DRAFT_v1.md 已回传 19:23 清理版
  （md5 1a66c729...与远端一致；本地原 14:27 版已过时）。
- **t126 watcher 事件补录（Day 13 补三落款 19:30 之后发生，此前未记）**：
  v1 watcher（19:29 起，pid 2656868）在 GPU0 遭遇共卡租户 ramp，
  backward 时 OOM 退出（===t126 fullft rc=1 19:42:04===，
  证据 logs/t126_fullft_650m.log——OOM 堆栈 + 已跑完 10M/100M 两档
  三点后 650M 未开始即中断）；**v2 watcher 19:42:36 自动自愈重启**
  （pid 2718971 存活，gpu_pick ≥22GB 真实空闲判据 + 5 次重试 +
  96h deadline），当前 8 卡均无 ≥22GB 空闲（GPU6/7 共卡 7.9/15.8GB
  已用），watcher 每 10min 轮询等待，20:03 仍在 "no free GPU yet"。
  v2 语义变化：等待窗从"进程启动"改为 deadline 循环，OOM 失败重试
  间隔 30min，不会覆盖他人进程——v1 的 6h 超时缺口已由 v2 根治
  （与 closeout_650m 6h 缺口登记同根因、不同实例）。
- 在训 3 run 不打扰：300M s17 30%、300M b59 15%、30M rw1 40%
  （status.md 18:20 口径，推进健康）。

## Day 13 补五（2026-09-23 22:20）——22:00 巡检：收口链复核 + t126 v2 等待中 + verdict 三次幂等一致

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部 1111 行）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_checkpoint=ckpt_nt1900122218_step202784.pt,
  end_utc=2026-09-22T22:11:50Z）逐位一致；最终 ckpt 19 个
  （ckpt_nt1900122218_step202784.pt，7.5G，best_val 0.7757）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  28/28 层（final ckpt_nt=1900122218，early 9/middle 9/late 10），
  best L8 f1_macro=0.3632——收口链自动收口口径无误。
- **五档终判第三次幂等复跑（22:19）**：s1_final_verdict.py 复跑前后
  evidence/s1_final_verdict.json md5 完全一致（08f2542b...，与 Day 13
  13:24 / Day 13 补三 19:2x / Day 13 补四 20:01 三次口径相同）——
  五档表数字稳定可复现：
  - 1M 0.1650±0.0107 / 10M 0.1535±0.0141 / 30M 0.2651±0.0132 /
    100M 0.3394±0.0120 / 650M 0.3632（单 seed，预注册）
  - 650M_gain +2.4pp（6.5× 参数）；slope 100M→650M = 0.0293 < ε=0.03
    ——scaling 饱和确认；full-axis 0.0829 F1/decade
  - 10M 谷持续存在（10M 0.1535 < 1M 0.1650）
  - 层迁移终点非单调：650M best L8 rel=0.296（中早期）
- 02_TASKS 收口状态复核：docs/TASKS_V2.md T2.1.3 已勾选 ✅（验收三件套
  齐：evidence/s1_slope_decision.json 触发判定 / evidence/
  s1_final_verdict.json 终判 / TRAINING_LOG.md Day 13 落款）——
  T2.1.3 收口完好，无需重做。
- preprint v1.0 线复核：DRAFT_v1.md 七槽已满（fill_draft_650m 6 槽 +
  S13b v2 第 7 槽回填，摘要规模已表 1M–650M；git ff2830a/b96c146/
  6d35bf9 落款）——DRAFT v1.1 定稿版在位，本轮继续撰写中。
- T1.2.6 full-FT 扩档：t126 v2 watcher 存活（pid 2718971，t126_watch_
  launch.sh，02:29+）；日志显示 21:01–22:02 每 10min "no free GPU yet"
  （8 卡无 ≥22GB 真实空闲）；v1 首跑 10M/100M 两档六点已产
  （logs/t126_fullft_650m.log + evidence/t126_fullft.json），650M 档
  待 GPU 空闲自动启动（attempt 1 OOM 后 30min 重试节奏，96h deadline）。
  本轮不干预 3 个在训 run：300M s17（GPU0）/ 300M b59（GPU3）/
  30M rw1（GPU3）。

## Day 13 补六（2026-09-23 23:25）——23:20 巡检：t126 full-FT 650M 扩档完成收口 + 全链证据复核

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_checkpoint=ckpt_nt1900122218_step202784.pt,
  end_utc=2026-09-22T22:11:50Z）逐位一致；19 个 ckpt、单 ckpt 7.5G。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  28/28 层（final ckpt_nt=1900122218，early 9/middle 9/late 10），
  best L8 f1_macro=0.3632——收口链口径无误。
- **五档终判第四次幂等复跑（23:1x）**：s1_final_verdict.py 复跑前后
  evidence/s1_final_verdict.json md5 完全一致（08f2542b...，与
  Day 13 13:24 / 补三 19:2x / 补四 20:01 / 补五 22:19 四次口径相同）
  ——五档表数字稳定可复现：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M = 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M L8
  rel=0.296）。
- **T2.1.3 收口完好复核**：docs/TASKS_V2.md T2.1.3 ✅（验收三件套：
  evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  TRAINING_LOG.md Day 13 落款）——无需重做。
- **t126 full-FT 650M 扩档完成（本轮新事件，此前未记）**：v2 watcher
  （pid 2718971，t126_watch_launch.sh）于 22:22:55 捕获 GPU1 真实
  空闲，attempt 2 启动 fullft_lowdata.py（v1.1 三档 10M/100M/650M），
  22:41:45 rc=0 完成——证据链：
  - logs/t126_fullft_650m.log：[650M] fullft n=100/1000/10000 →
    f1 0.0947/0.1212/0.1564（10M/100M 两档复跑一致：
    0.0585/0.0753/0.1310 与 0.0639/0.1209/0.1360）
  - evidence/t126_fullft.json（22:38:59 落盘）：三档 × 三点全量
  - logs/t126_fullft_650m.done（22:39:04 落盘）：watcher 单次退出
    （pid 2718971 不复存在，语义达成）
  - 事件时间线：v1 19:29 GPU0 OOM（rc=1 19:42:04）→ attempt 1
    20:23:37 GPU2 OOM（rc=1 20:30:47，共卡租户 ramp）→ attempt 2
    22:22:55 GPU1 成功——v2 watcher 自愈判据（≥22GB 真实空闲 +
    30min 重试 + 96h deadline）实战验证有效
  - 结论：650M full-FT 在最低数据量 n=100 拿到最大低数据优势
    （0.0947 vs 10M 0.0585），full-FT 升 / probe 平坦结论在
    五档口径下成立
- **交接文档同步（02_TASKS=TASKS_V2.md）**：T1.2.6 [~]→[x] 收口
  （补录 650M 扩档完成 + 三档数字 + DRAFT 回填记录）。
- **preprint v1.0 线**：DRAFT_v1.md §4.11 回填三档 full-FT 数字
  （10²: 0.059/0.064/0.095；10⁴: 0.131/0.136/0.156；650M 低数据
  优势表述 + evidence/t126_fullft.json 引用）——DRAFT v1.1 定稿版
  八槽全满（七 650M 槽 + t126 低数据槽）。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @781M/2.0B
  （GPU0，lr 2.02e-04）/ 300M b59 @500M/5.9B（GPU3，lr 2.95e-04）/
  30M rw1 @1046M/2.0B（GPU3，lr 2.81e-04）；t126 用的 GPU1 已释放。

## Day 14（2026-09-24 19:19）——19:00 巡检：650M 全链第 5 次幂等复核 + DRAFT 位校验

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_val_loss=0.7756562890347106,
  best_checkpoint=ckpt_nt1900122218_step202784.pt,
  end_utc=2026-09-22T22:11:50Z）逐位一致；19 ckpts（7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  28/28 层（final ckpt_nt=1900122218，best L8 f1_macro=0.3632）——
  收口链自动收口口径无误。
- **五档终判第 5 次幂等复跑（19:1x，本轮会话）**：s1_final_verdict.py
  复跑前后 evidence/s1_final_verdict.json md5 完全一致
  （08f2542bbeef97e82adc4d7d7242e030，与 Day 13 13:24 / 补三 19:2x /
  补四 20:01 / 补五 22:19 / 补六 23:1x 五次口径相同）——五档表数字
  稳定可复现：1M 0.1650±0.0107 / 10M 0.1535±0.0141 / 30M 0.2651±0.0132 /
  100M 0.3394±0.0120 / 650M 0.3632（单 seed，预注册）；650M_gain +2.4pp；
  slope 100M→650M 0.0293 < ε=0.03（scaling 饱和确认）；10M 谷持续；
  层迁移终点非单调（650M best L8 rel=0.296，中早期）。
- **T2.1.3 / T1.2.6 收口完好复核**：docs/TASKS_V2.md 两项均 [x]，证据链
  齐备（evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  evidence/t126_fullft.json / logs/t126_fullft_650m.done）——无需重做；
  T2.1.3 下已追加 09-24 复核注记（本轮）。
- **preprint v1.0 线（位校验新增）**：preprint/DRAFT_v1.md（20,528B，
  09-23 23:29 版）八槽全满 + 纪律门 D1–D11 全绿；本轮逐位校验：正文
  evidence 引用全部可解析（t126_fullft / t126_lowdata），关键数字与源
  JSON 一致（五档表 vs evidence/s1_final_verdict.json；650M full-FT 三点
  0.0947/0.1212/0.1564 vs evidence/t126_fullft.json；best_val 0.7757 vs
  runs/RNA-Sc-650M_s17/manifest.json）。下一节点：T4.2.3 claim 措辞
  全文检索 → T4.2.5 arXiv 挂出（完整核心实验，非占位）。
- **T1.2.6 full-FT 线**：logs/t126_fullft_650m.done 在位（09-23 22:39），
  v2 watcher 已按单次退出语义退出（ps 复核无 t126_watch 进程）——
  扩档完成，无待办。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1096M/2.0B（54.8%，
  GPU0，lr 1.29e-04）/ 300M b59 @747M/5.9B（12.7%，GPU3，lr 2.89e-04）/
  30M rw1 @1478M/2.0B（73.9%，GPU3，lr 9.64e-05）。

## Day 14 补（2026-09-24 20:11）——20:00 巡检：650M 全链第 6 次幂等复核（用户指令会话）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_val_loss=0.7756562890347106,
  best_checkpoint=ckpt_nt1900122218_step202784.pt,
  end_utc=2026-09-22T22:11:50Z）逐位一致；run 目录 19 ckpts（最新
  09-23 02:12 ckpt_nt1900122218_step202784.pt，7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  行（grep 计数 28 = 28/28 层，final ckpt_nt=1900122218，best L8
  f1_macro=0.3632）——自动收口径无误。
- **五档终判第 6 次幂等复跑（20:1x，本轮会话）**：s1_final_verdict.py
  复跑前后 evidence/s1_final_verdict.json md5 完全一致
  （08f2542bbeef97e82adc4d7d7242e030，与 Day 13 13:24 / 补三 19:2x /
  补四 20:01 / 补五 22:19 / 补六 23:1x / Day 14 19:1x 五次口径相同）
  ——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M best L8
  rel=0.296，中早期）。
- T2.1.3 / T1.2.6 收口完好复核：docs/TASKS_V2.md 两项均 [x]，证据链
  在位（evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  evidence/t126_fullft.json / logs/t126_fullft_650m.done）——无需重做。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（20,528B，09-23 23:29
  版）八槽全满 + 纪律门 D1-D11 全绿；下一节点 T4.2.3 claim 措辞全文
  检索 → T4.2.5 arXiv 挂出（完整核心实验，非占位）。
- T1.2.6 full-FT 线：logs/t126_fullft_650m.done 在位（09-23 22:39），
  v2 watcher 单次退出语义达成（无 t126_watch 进程）——扩档完成，
  无待办。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1107M/2.0B（55.4%，
  GPU0，lr 1.26e-04）/ 300M b59 @760M/5.9B（12.9%，GPU3，lr 2.89e-04）/
  30M rw1 @1497M/2.0B（74.9%，GPU3，lr 8.97e-05）。

## Day 14 补二（2026-09-24 21:17）——21:00 巡检：650M 全链第 7 次幂等复核（用户指令会话）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_val_loss=0.7756562890347106,
  best_checkpoint=ckpt_nt1900122218_step202784.pt）逐位一致；run 目录
  19 ckpts 在位（最新 09-23 02:12）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  行 28/28 层（final ckpt_nt=1900122218，best L8 f1_macro=0.3632）；
  watch_all 进程仍在值守（PID 3748436）。
- **五档终判第 7 次幂等复跑（21:1x，本轮会话）**：s1_final_verdict.py
  复跑前后 evidence/s1_final_verdict.json md5 完全一致
  （08f2542bbeef97e82adc4d7d7242e030，与前六次口径相同）——五档表
  稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 / 30M 0.2651±0.0132 /
  100M 0.3394±0.0120 / 650M 0.3632（单 seed，预注册）；650M_gain
  +2.4pp；slope 100M→650M 0.0293 < ε=0.03（scaling 饱和确认）；
  10M 谷持续；层迁移终点非单调（650M best L8 rel=0.296）。
- T2.1.3 / T1.2.6 收口完好复核：docs/TASKS_V2.md 两项均 [x]，证据链
  在位（evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  evidence/t126_fullft.json / logs/t126_fullft_650m.done）。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（20,528B，09-23
  23:29 版）零 PENDING 槽、纪律门 D1–D11 全绿；下一节点 T4.2.3 claim
  措辞全文检索 → T4.2.5 arXiv 挂出。
- T1.2.6 full-FT 线：logs/t126_fullft_650m.done 在位（09-23 22:39），
  无 t126_watch 进程（单次退出语义）——扩档完成，无待办。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1126M/2.0B（56.3%，
  GPU0，lr 1.22e-04）/ 300M b59 @775M/5.9B（13.1%，GPU3，lr 2.88e-04）/
  30M rw1 @1517M/2.0B（75.9%，GPU3，lr 8.31e-05）。

## Day 14 补三（2026-09-24 22:2x）——22:00 巡检：650M 全链第 8 次幂等复核（用户指令会话）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE,
  final_nt=2000003270, best_val_loss=0.7756562890347106,
  best_checkpoint=ckpt_nt1900122218_step202784.pt,
  end_utc=2026-09-22T22:11:50Z）逐位一致；run 目录 19 ckpts（最新
  09-23 02:12 ckpt_nt1900122218_step202784.pt，7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  行 28/28 层（final ckpt_nt=1900122218，best L8 f1_macro=0.3632）；
  watch_all 进程仍在值守（PID 3748436）。
- **五档终判第 8 次幂等复跑（22:1x，本轮会话）**：s1_final_verdict.py
  复跑前后 evidence/s1_final_verdict.json md5 完全一致
  （08f2542bbeef97e82adc4d7d7242e030，与前七次口径相同）——五档表
  稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 / 30M 0.2651±0.0132 /
  100M 0.3394±0.0120 / 650M 0.3632（单 seed，预注册）；650M_gain
  +2.4pp；slope 100M→650M 0.0293 < ε=0.03（scaling 饱和确认）；
  10M 谷持续；层迁移终点非单调（650M best L8 rel=0.296，中早期）。
- T2.1.3 / T1.2.6 收口完好复核：docs/TASKS_V2.md 两项均 [x]，证据链
  在位（evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  evidence/t126_fullft.json / logs/t126_fullft_650m.done）；T2.1.3 下
  09-24 巡检注记追加第 8 次复核记录（本轮）。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（20,528B，09-23
  23:29 版）零 PENDING 槽、纪律门 D1–D11 全绿；下一节点 T4.2.3 claim
  措辞全文检索 → T4.2.5 arXiv 挂出（完整核心实验，非占位）。
- T1.2.6 full-FT 线：logs/t126_fullft_650m.done 在位（09-23 22:39），
  无 t126_watch 进程（单次退出语义）——扩档完成，无待办；t126_fullft
  三点曲线 650M 0.0947/0.1212/0.1564（n=100/1000/10000）与
  evidence/t126_fullft.json 一致。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1144M/2.0B（57.2%，
  GPU0，lr 1.17e-04）/ 300M b59 @789M/5.9B（13.4%，GPU3，lr 2.88e-04）/
  30M rw1 @1538M/2.0B（76.9%，GPU3，lr 7.62e-05）。

## Day 14 补四（2026-09-24 23:1x）——23:00 巡检：650M 全链第 9 次幂等复核（用户指令会话：五档终判运行确认）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部，line 1111）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE，
  final_nt=2000003270，best ckpt_nt1900122218_step202784.pt）一致；
  run 目录 19 ckpts（最新 ckpt_nt1900122218_step202784.pt 09-23 02:12 落盘）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  行 28/28 层（final ckpt_nt=1900122218，best L8 f1_macro=0.3632，
  logs/probe_rnasc_650M_s17_final_auto.log 逐层记录在位）；watch_all
  值守进程存活（PID 3748436，alive cycle=2232+）。
- **五档终判第 9 次幂等复跑（23:0x，本轮会话）**：`python -m
  rna_sc.s1_final_verdict` 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前八次口径相同）
  ——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续（0.1535 < 0.1650）；层迁移终点
  非单调（650M best L8/rel 0.296，中早期）。
- T2.1.3 / T1.2.6 收口完好复核：docs/TASKS_V2.md 两项均 [x]，证据链
  在位（evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  evidence/t126_fullft.json / logs/t126_fullft_650m.done）；T2.1.3 下
  追加第 9 次复核记录（本轮）。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（20,528B，09-23
  23:29 版，md5 77e285d6）零 PENDING 槽、纪律门 D1–D11 全绿；§4.11
  650M 三档低数据数字（0.0947/0.1212/0.1564）与 evidence/t126_fullft.json
  一致；下一节点 T4.2.3 claim 措辞全文检索 → T4.2.5 arXiv 挂出。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（rc=0 09-23 22:41:45），
  watcher 单次退出，无 t126_watch 进程（复核确认）。GPU0/GPU1 上
  运行中的 rnafteval.finetune_base（full/frozen, seed 29）属
  rna-ft-eval m6A sweep 项目（/home/cunyuliu/rna-ft-eval/scripts/
  q_m6a_sweep.sh），与 rna-sc T1.2.6 无关，不干预。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1167M/2.0B（58.4%）/
  300M b59 @800M/5.9B（13.6%）/ 30M rw1 @1560M/2.0B（78.0%）——
  日志尾部 3 行推进正常（09-24 23:0x 口径）。

## Day 15（2026-09-25 19:1x）——19:00 巡检：650M 全链第 10 次幂等复核（用户指令会话）+ T4.2.3 claim 措辞全文检索收口

- DONE 帧复核（logs/RNA-Sc-650M_s17.log line 1111）：DONE rnasc_650M_s17
  | nt=2000003270 steps=213514 best_val=0.7757 | 5826 nt/s peak=15579MB
  fallback=0——与 runs/RNA-Sc-650M_s17/manifest.json（status=DONE，
  final_nt=2000003270）一致；run 目录 19 ckpts（最新
  ckpt_nt1900122218_step202784.pt）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含 RNA-Sc-650M_s17
  行 28/28 层（final ckpt_nt=1900122218，best L8 f1_macro=0.3632）；
  watch_all 值守进程存活（alive cycle=2484，handled=8）。
- 五档终判第 10 次幂等复跑（19:16，本轮会话）：python -m
  rna_sc.s1_final_verdict 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前九次口径相同）
  ——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续（三 seed 均值口径）；层迁移终点
  非单调（650M best L8/rel 0.296）。
- **T4.2.3 claim 措辞全文检索收口（preprint v1.0 线推进）**：
  DRAFT_v1.md 全文风险词检索（novel/first/SOTA/prove/outperform/
  significantly/comprehensive/robust 等）零高危命中；"first" 两处
  均带限定语（D7）；"controlled" 全部限定自训家族（D1）。修正 4 处
  seed 语义精度：摘要/§4.1/§5 "under three seeds"（可误读 3/3 为负）
  → 精确口径 "三 seed 均值为负、2/3 seed 为负（s29 −0.040、
  s43 −0.008、s17 +0.013）"，与 evidence/s1_final_verdict.json
  五档表逐 seed 段一致（REVIEW_DISCIPLINE.md 规则 2：口径显式）。
  DRAFT_v1.md md5 77e285d6→a2d6e10e，零 PENDING 槽保持。docs/
  TASKS_V2.md T4.2.3 勾选 [x] + 证据链落款。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（rc=0 09-23 22:41:45，
  logs/t126_fullft_650m.done 在位），无 t126_watch 进程（ps 复核
  确认）；GPU 0-5 满载（rnafteval m6A sweep 等他项目 + 在训 run），
  GPU 6/7 空闲但 T1.2.6 已收口，无新任务入队。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1448M/2.0B（72.4%，
  lr 5.35e-05）/ 300M b59 @1026M/5.9B（17.4%，lr 2.79e-04）/
  30M rw1 @1971M/2.0B（98.6%，接近收尾，lr 3.20e-07）——日志尾部
  推进正常（09-25 19:1x 口径）。

## Day 15 补（2026-09-25 20:1x）——20:10 巡检：650M 全链第 11 次幂等复核（用户指令会话）+ T4.2.4 limitation 收口

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部 line 1111）：DONE
  rnasc_650M_s17 | nt=2000003270 steps=213514 best_val=0.7757 |
  5826 nt/s peak=15579MB fallback=0——与 runs/RNA-Sc-650M_s17/
  manifest.json（status=DONE, final_nt=2000003270,
  best_checkpoint=ckpt_nt1900122218_step202784.pt）一致；run 目录
  19 ckpts（最新 09-23 02:12，7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含
  RNA-Sc-650M_s17 行 28/28 层（final ckpt_nt=1900122218，best L8
  f1_macro=0.3632）；watch_all 值守进程存活（pid 3748436，自 Sep17
  连续值守）。
- 五档终判第 11 次幂等复跑（20:1x，本轮会话）：python -m
  rna_sc.s1_final_verdict 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前十次口径
  相同）——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M best
  L8/rel 0.296）。
- **T4.2.4 limitation 收口（preprint v1.0 线推进）**：DRAFT_v1.md §6
  五条扩七条——新增 B3 线 1 泄漏余量（+0.17 控制排除增益参照
  randinit/moment-matched、不含成分对照；100M family-split LM
  0.170 vs k-mer logistic 0.163 / LightGBM 0.176，超成分余量
  +0.007、对 LightGBM 为负——真实信号与成分阅读不可分离）与架构
  受控范围（单 recipe、RiNALMo-arch Q5 未测、within-family）；原
  红队 A epoch 覆盖 / 种子不平衡 / 红队 E rRNA 偏置 / pooled
  day-1 probe / 外部线 D1 五条保留。docs/TASKS_V2.md T4.2.4
  勾选 [x] + 证据链落款；T2.1.3 下追加第 11 次复核注记。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（evidence/t126_fullft.json
  3×3 点 + logs/t126_fullft_650m.done 09-23 22:39 在位），无
  t126_watch 进程（ps 复核）；GPU 0-5 满载（rnafteval m6A sweep
  等他项目），GPU 6/7 空闲——T1.2.6 已收口，不新起任务。
- 本轮不干预 3 个在训 run（健康推进）：300M s17 @1465M/2.0B
  （73.2%，lr 5.05e-05）/ 300M b59 @1039M/5.9B（17.6%，lr
  2.79e-04）/ 30M rw1 @1994M/2.0B（99.7%，收尾中，lr 1.37e-08）
  ——日志尾部推进正常（09-25 20:1x 口径）。

## Day 15 补二（2026-09-25 21:1x）——21:18 巡检：650M 全链第 12 次幂等复核（用户指令会话）+ 30M rw1 DONE 新事件

- DONE 帧复核（logs/RNA-Sc-650M_s17.log 尾部 line 1111）：DONE
  rnasc_650M_s17 | nt=2000003270 steps=213514 best_val=0.7757 |
  5826 nt/s peak=15579MB fallback=0——与 runs/RNA-Sc-650M_s17/
  manifest.json（status=DONE, final_nt=2000003270,
  best_checkpoint=ckpt_nt1900122218_step202784.pt）一致；run 目录
  19 ckpts（最新 09-23 02:12，7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含
  RNA-Sc-650M_s17 行 28/28 层（final ckpt_nt=1900122218，best L8
  f1_macro=0.3632，logs/probe_rnasc_650M_s17_final_auto.log 在位）；
  watch_all 值守进程存活（pid 3748436，自 Sep17 连续值守，
  alive cycle=2496 handled=8）。
- 五档终判第 12 次幂等复跑（21:1x，本轮会话）：python -m
  rna_sc.s1_final_verdict 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前十一次口径
  相同）——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M best
  L8/rel 0.296）。
- T2.1.3 收口状态复核：docs/TASKS_V2.md 已 [x]（验收三件套齐：
  evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  TRAINING_LOG.md Day 13 落款）；本轮追加第 12 次复核注记。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（21,356B，
  09-25 20:17 版，md5 cbfc3064，T4.2.3+T4.2.4 双收口后版本）零
  PENDING 槽；T4.2.3 claim 措辞检索 / T4.2.4 limitation 七条均已
  [x]；下一节点 T4.2.5 arXiv 挂出（完整核心实验，非占位）。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（evidence/
  t126_fullft.json 3×3 点：650M 0.0947/0.1212/0.1564 + logs/
  t126_fullft_650m.done 09-23 22:39 在位），无 t126_watch 进程
  （ps 复核确认）；GPU 0-5 满载（rnafteval m6A sweep 等他项目 +
  在训 run，util 88-100%），GPU 6/7 空闲（2.0G/16.8G 显存占用、
  util N/A）——T1.2.6 已收口，无新任务入队。
- **新事件：30M rw1（S3 家族重加权 arm，T2.3.3）DONE（21:1x）**：
  logs/RNA-Sc-30M_s17_rw1.log 尾部 DONE rnasc_30M_s17 |
  nt=2000006712 steps=187769 best_val=0.0000 | 7386 nt/s
  peak=2967MB fallback=0；runs/RNA-Sc-30M_s17_rw1/manifest.json
  status=DONE final_nt=2000006712，19 ckpts。best_val=0.0000 为
  train_s3_rw.py patch 副作用（SPLIT_8080 一并被指向 reweighted
  parquet，VAL 循环无样本记 0），训练 loss 本身正常收敛
  （1.34→0.3-1.2 区间）——不判定为训练异常。注意：DONE 帧
  run_id 为 rnasc_30M_s17（无 rw1 后缀），watch_all 的 handled/
  probed 集合按原 30M_s17 吸收，**rw1 不会触发自动 final-probe**——
  S3 线 probe 留待 T2.3.3 收口时手动触发（rna_sc.probe --run-dir
  runs/RNA-Sc-30M_s17_rw1），本轮不干预。
- 本轮不干预 2 个在训 run（健康推进）：300M s17 @1485M/2.0B
  （74.2%，lr 4.68e-05）/ 300M b59 @1077M/5.9B（18.3%，lr
  2.77e-04）——日志尾部推进正常（09-25 21:1x 口径）。

## Day 15 补三（2026-09-25 22:2x）——22:25 巡检：650M 全链第 13 次幂等复核（用户指令会话，全部既定分支均收口态）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log line 1111）：DONE
  rnasc_650M_s17 | nt=2000003270 steps=213514 best_val=0.7757 |
  5826 nt/s peak=15579MB fallback=0——与 runs/RNA-Sc-650M_s17/
  manifest.json（status=DONE, final_nt=2000003270,
  best_checkpoint=ckpt_nt1900122218_step202784.pt）一致；run 目录
  19 ckpts（最新 09-23 02:12，7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含
  RNA-Sc-650M_s17 行 28/28 层（final ckpt_nt=1900122218，best L8
  f1_macro=0.3632，logs/probe_rnasc_650M_s17_final_auto.log 在位，
  09-23 06:16）；watch_all 值守进程存活（pid 3748436，自 Sep17
  连续值守 8d18h，watch_all.log "rnasc_650M_s17 DONE nt=2.00B
  val=0.7757 -> probe GPU2 / handled" 在位）。
- 五档终判第 13 次幂等复跑（22:25，本轮会话）：python -m
  rna_sc.s1_final_verdict 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前十二次口径
  相同，rc=0）——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M best
  L8/rel 0.296）。
- T2.1.3 收口状态复核：docs/TASKS_V2.md 已 [x]（验收三件套齐：
  evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  TRAINING_LOG.md Day 13 落款）；本轮追加第 13 次复核注记。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（21,356B，
  09-25 20:17 版，md5 cbfc3064，T4.2.3+T4.2.4 双收口后版本）零
  PENDING 槽（grep -c PENDING = 0）；T4.2.3 claim 措辞检索 /
  T4.2.4 limitation 七条均已 [x]；下一节点 T4.2.5 arXiv 挂出
  （完整核心实验，非占位）。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（evidence/
  t126_fullft.json 3×3 点：650M 0.0947/0.1212/0.1564 + logs/
  t126_fullft_650m.done 09-23 22:39 在位），无 t126_watch 进程
  （ps 复核确认）；GPU 0-5 满载（rnafteval m6A sweep 等他项目 +
  在训 run，util 100%），GPU 6/7 空闲（1.6G/12.8G 显存占用、
  util N/A）——T1.2.6 已收口，无新任务入队。
- 本轮不干预 2 个在训 run（健康推进）：300M s17 @1498M/2.0B
  （74.9%，lr 4.46e-05）/ 300M b59 @1100M/5.9B（18.6%，lr
  2.76e-04）——日志尾部推进正常（09-25 22:2x 口径）。30M rw1
  已 DONE（21:1x，见补二落款），S3 线 probe 留待 T2.3.3 收口
  时手动触发，本轮不干预。

## Day 15 补四（2026-09-25 23:1x）——23:13 巡检：650M 全链第 14 次幂等复核（用户指令会话，全部既定分支均收口态）

- DONE 帧复核（logs/RNA-Sc-650M_s17.log line 1111）：DONE
  rnasc_650M_s17 | nt=2000003270 steps=213514 best_val=0.7757 |
  5826 nt/s peak=15579MB fallback=0——与 runs/RNA-Sc-650M_s17/
  manifest.json（status=DONE, end_utc=2026-09-22T22:11:50Z,
  final_nt=2000003270,
  best_checkpoint=ckpt_nt1900122218_step202784.pt）一致；run 目录
  19 ckpts（最新 ckpt_nt1900122218_step202784.pt，09-23 02:12，
  7.5G/个）。
- watch_all 自动 probe 复核：eval/probe_results.jsonl 含
  RNA-Sc-650M_s17 行 28/28 层（final ckpt_nt=1900122218，best L8
  f1_macro=0.3632，logs/probe_rnasc_650M_s17_final_auto.log 在位，
  09-23 06:16）；watch_all 值守进程存活（pid 3748436，自 Sep17
  连续值守 8d19h，watch_all.log alive cycle=2520 handled=8）。
- 五档终判第 14 次幂等复跑（23:09，本轮会话）：python -m
  rna_sc.s1_final_verdict 复跑前后 evidence/s1_final_verdict.json
  md5 完全一致（08f2542bbeef97e82adc4d7d7242e030，与前十三次口径
  相同，rc=0）——五档表稳定：1M 0.1650±0.0107 / 10M 0.1535±0.0141 /
  30M 0.2651±0.0132 / 100M 0.3394±0.0120 / 650M 0.3632（单 seed，
  预注册）；650M_gain +2.4pp；slope 100M→650M 0.0293 < ε=0.03
  （scaling 饱和确认）；10M 谷持续；层迁移终点非单调（650M best
  L8/rel 0.296）。
- T2.1.3 收口状态复核：docs/TASKS_V2.md 已 [x]（验收三件套齐：
  evidence/s1_slope_decision.json / evidence/s1_final_verdict.json /
  TRAINING_LOG.md Day 13 落款）；本轮追加第 14 次复核注记（补四）。
- preprint v1.0 线（位校验）：preprint/DRAFT_v1.md（21,356B，
  09-25 20:17 版，md5 cbfc3064，T4.2.3+T4.2.4 双收口后版本）零
  PENDING 槽（grep -c PENDING = 0）；下一节点 T4.2.5 arXiv 挂出
  （完整核心实验，非占位）——撰写线无新动作，不重复落款。
- T1.2.6 full-FT 线：无待办——650M 扩档完成（evidence/
  t126_fullft.json 3×3 点：650M 0.0947/0.1212/0.1564 + logs/
  t126_fullft_650m.done 09-23 22:39 在位），无 t126_watch 进程
  （ps 复核确认）；GPU 0-5 满载（rnafteval m6A sweep 等他项目 +
  在训 run，util 100%），GPU 6/7 空闲（1.6G/25.5G 显存占用、
  util N/A）——T1.2.6 已收口，无新任务入队（无可用空闲 GPU 满足
  满血 650M 门槛，v1 watcher 终态维持，不启动新 FT）。
- 本轮不干预 2 个在训 run（健康推进）：300M s17 @1511M/2.0B
  （75.6%，lr 4.24e-05）/ 300M b59 @1114M/5.9B（18.9%，lr
  2.75e-04）——日志尾部推进正常（09-25 23:1x 口径）。

## Day 17（2026-09-26 14:50）——S3 重加权 arm 收口（T2.3.3 落勾，H5 双轴定案）
- 30M-rw1 手动 final-probe（watch_all 因 run_id 无 rw1 后缀不自动触发
  ——train_s3_rw 的 tag 拼接瑕疵后果，manifest 区分无碍）：12/12 层
  inc12 确定性协议完成，best L11 F1 = 0.2408
- **H5 双轴分解定案**（evidence/s3_rw1_closeout.json）：
  - 数量轴（S2）：小语料更优（c1M 0.316 > full 0.2651）
  - 多样性轴（S3）：同语料展平更差（rw1 0.2408 < full 0.2651）
  - **结论：2.0B nt 预算下语料轴由高信号家族的有效重复主导，而非
    覆盖多样性——DenAdel 单细胞域否定结果的 RNA 跨域复现**
    （与 Muennighoff 重复有效区间互证；负结果配三候选机制解释，
    D3 纪律合规）
- 3×2 析因进度：300M@2B 98%（1.96B/2.0B，~2h DONE）；b59 26%
  （1.52B/5.9B）；Claim-14 判据等两臂齐

- [auto] rnasc_300M_s17 complete: nt=2.00B best_val=0.7801 fallback=0; final probe+linkage+s1_summary done

## Day 17 补（2026-09-26 15:58）——300M@2B 锚点档收口（T1.0.3 臂①落勾）
- 300M@2B DONE（nt=2.0B，best_val 0.7801，fallback=0，5947 nt/s）；
  watch_all 自动全 24 层 probe：**best L22 F1 = 0.3445（rel 0.957）**
- **六档内插表（evidence/t103_300m2b_closeout.json）**：
  1M 0.1650 / 10M 0.1535 / 30M 0.2651 / 100M 0.3394 / 300M 0.3445 /
  650M 0.3632——**100M→300M 仅 +0.5pp（近平台确认）；300M→650M
  +1.9pp**——iso-token 2B 线上段饱和在 300M 内已现
- **层迁移终点逆转在六档确认**：rel 0.471→0.141→0.788→0.864→
  0.957（300M 顶点）→0.296（650M 逆转）——非单调终点结构定型
- Claim-14 中期判读：300M@2B 0.3445 近平台——**边界判据转交
  300M@5.9B 臂（b59，26% 在训）**：若 5.9B 增益不显著 → 语料最优
  边界 ≈300M 成立（Claim-14 可写）
- 3×2 析因进度：2B 列全齐（1M-650M 六点）；5.9B 列 b59 在训

## Day 17 补二（2026-09-26 16:20）——T1.0.4 启动：3×2 析因最后一格
- 100M@5.9B（b59，GPU4，supervisor 自动拉起）启动——3×2 析因矩阵
  最后一格入轨：2B 列六点全齐 + 5.9B 列三臂（300M b59 27% /
  100M b59 刚启 / 650M@5.9B 视结论二期）
- 100M@5.9B 双重角色：析因预算效应分离 + RNA 域数据受限定律实测点
  （Muennighoff 重复有效区间的受控测试）
- 集群当前：GPU3 b59-300M（27%）+ GPU4 b59-100M（新）双 5.9B 臂
  并行；GPU0/2 空闲留 full-FT/分析用

## Day 17 补三（2026-09-26 16:30）——S12 linkage 六档补点（H6 深化）
- 300M（−0.339）与 650M（−0.222）linkage 补点完成（带 run 标签
  存档 s12_linkage_RNA-Sc-{300M,650M}_s17.json）
- **DI-最佳层关联随规模衰减曲线完整化**：30M-c1Mcs −0.478 →
  100M −0.384 → 300M −0.339 → 650M −0.222——单调衰减（n=10 类
  各点方向一致负相关）
- 机制解读：高解耦家族依赖早期层的模式在大尺度下逐渐减弱——
  与层迁移终点逆转（650M rel 0.296）和磨蚀机制互洽：容量足够时
  深层被 rRNA 通道占据（家族级统计在中早期层已足够），DI 差异
  被稀释
- H6 状态：S12 六档齐（S8 接触图仍未启动——二期可选）

## Day 17 补四（2026-09-26 16:47）——S14 时间轴 v2（H8 三轴闭环）
- 300M + 650M 各 4 ckpt RNS 轨迹完成（GPU2 空闲补位，OOM 硬化
  口径与 650M add-on 一致）：
  - 300M：0.1201→0.1079→0.0920→0.0814 单调降（无峰）
  - 650M：0.1373→0.1099→0.0774→0.0662 单调降
  - 对照 10M v1：峰 1.0B 后回落
- **H8 时间轴定案**：10M 的"表征组织中途退化"是容量不足特有
  现象——300M/650M 表征组织单调改善全程——与磨蚀容量门槛
  （S6 倒 U）同构，表征/迁移双指标在小容量下同步异常、大容量
  下同步健康——**容量门槛是 RNS 峰与 F1 磨蚀的共同根因**（机制
  统一解释，论文 Discussion 候选段落）
- H8 三轴全闭环：规模轴（五档+终点）/ 家族轴（ρ=−0.19）/
  时间轴（三尺度形态分化）

## Day 17 补五（2026-09-26 17:10）——八假设全终判 + DRAFT 数字同步
- H4 终判升格（OUTLINE 4.3 + SPEC）：可迁移特征集中于容量允许处
  （压力→早期层 / 充足→中晚层 / 结构永不依赖预训练）；Li et al.
  早期层账户仅在磨蚀 regime 复现——限定形式
- **八假设 H1-H8 全部终判完成**（七个实验终判 + H4 写作升格）
- DRAFT_v1.md 五处数字同步：4.1 六档表+内插+终点逆转 / 4.5 语料
  收口（rw1 0.2408）/ 4.6 S12 六档衰减 / 4.8 时间轴 v2 容量门槛；
  程序化核对五项全过
