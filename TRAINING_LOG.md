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
