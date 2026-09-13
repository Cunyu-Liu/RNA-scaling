# RNA-Sc 训练记录（TRAINING LOG）

> 项目：RNA-LM 迁移学习机理研究（SPEC v1.1，S0-S12）
> 服务器：A100 集群（bms-18937653-012），用户 cunyuliu
> 代码：/home/cunyuliu/rna-sc（git 管理），数据/runs：/mnt/cunyuliu/rna-sc
> 环境：conda toktokenbench（torch 2.6.0+cu124）

## 2026-09-13（Day 0：交接 + 基建 + wave1 启动）

### 交接完成项
- 00-03 全部交接文档通读（备忘录/SPEC/TASKS/CHECKLIST）；
- TokBench 资产定位：~/tokenizer-benchmark（代码）+ /mnt/cunyuliu/tokenizer-benchmark（数据）；
- 切分资产深验证（验收 A3+B1，证据 /mnt/cunyuliu/rna-sc/evidence/split8080_deep_verify.json）：
  29,012,227 行 / 3,357,201 簇 / **簇级泄漏 0 / 序列级泄漏 0 → PASS**；
  split: train 14.13M(48.7%) / family_validation 7.53M(25.9%) / family_test 7.08M(24.4%) / validation 164k / test 109k；
  字母表纯净 ACGU；长度 10-583,414 nt。
  ⚠️ 文档中的"8/1/1 比例"与实际不符——TokBench 的真实设计是家族级大 held-out（50%），S0 的
  "held-out 10%"目标用 validation(0.6%)+test(0.4%)=1% 或 family_validation 承担，待导师确认口径。

### 基建（T0.2）
- /home/cunyuliu/rna-sc 项目骨架：ALiBi MLM encoder（SDPA 显存安全版）/ frozen config /
  split 流式 MLM 数据管线（nt 口径 exposure）/ 训练 runner（manifest 纪律）/ ledger（Z5）/
  status 监控 / smoke 测试 / supervisor 调度器；
- 复用 TokBench：nt 口径预算、GPUGuard 模式、manifest+ledger 纪律、验证集选择纪律。

### 冒烟测试（验收 A6）— ALL PASS
- mask 确定性 ✓ / 15% 比例 ✓ / 四档参数量 ±12% ✓ / 前向反向 ✓ / 真实 split 批处理 ✓ /
  loss 1.956→1.465(30步) ✓ / cpu_fallback_count=0 ✓

### 事故与决策记录（重要）
1. **架构修订**：SPEC 表格的宽扁架构（如 1M=4层/d256）实际参数 3.15M（超目标 3 倍）。
   修订为深窄形态：1M=18层/d64(0.89M)、10M=20层/d192(8.86M)、30M=12层/d480(33.2M,
   +10.7% 在 12% 容差内，保留 RiNALMo-micro 对齐优势)、100M=23层/d576(91.6M)。
   理由：等参数量是 scaling 归因的前提（Li et al. 惯例是架构由参数目标反推）。
2. **wave1 OOM 事故**：启动时 nvidia-smi 显示 GPU6/7 各 ~2GB 已用（>38GB 空闲），但 GPU6/7
   实际是 5.1GB 物理卡且其他用户进程随后涌入 → 3 个 run OOM。证据：logs/*.log 的
   torch.OutOfMemoryError 堆栈。
   **修复**：① GPU 选择改用 torch.cuda.mem_get_info（分配器真实值）；② batch_nt 32768→16384；
   ③ supervisor：崩溃自动 --resume-from 最新 ckpt 重启（≤5 次）；④ supervisor 按真实空闲显存
   动态选 GPU，不设其他 gate（遵守"有显存就能用"规则）。
3. **重复启动事故**：supervisor 初版未跳过 ledger 中 running 且 pid 存活的行，重复启动 10M
   （同 out-dir 双写）。已杀重复进程、修复 supervisor（adopt 存活 run、跳过活跃 run）。

### 当前运行（wave1，全部 2.0B nt 预算，bf16，LR 3e-4×档位系数，warmup 0.5% cosine）
| run | model | GPU | pid | 启动 (UTC) |
|---|---|---|---|---|
| rnasc_30M_s17 | RNA-Sc-30M 主 scaling 轴 | 1 | 2660615 | 09:40 |
| rnasc_10M_s17 | RNA-Sc-10M 主 scaling 轴 | 1 | 2630869 | 09:32 (wave1 原始进程) |
| rnasc_30M_s17c1M | 30M×1M 语料（S2 数据量轴） | 2 | 2660624 | 09:40 |
| rnasc_1M_s17 | RNA-Sc-1M 主 scaling 轴 | 7 | 2660631 | 09:40 |

早期 loss 轨迹：10M 1.32→1.26@22M nt；30M 1.35@2M；1M 1.31@4M；30M-c1M 1.28@4M。
（MLM 4 字母表随机基线 ln4≈1.386；loss 已低于随机 → 学习发生）

### 训练预算与 ETA（按冒烟吞吐 ~3-4k nt/s 估）
- 1M/10M/30M 单 run 2.0B nt ≈ 6-8 天/卡；
- supervisor 挂机自动续；100M 主档（3 种子 17/29/43）与 30M-c10M 排队进入 wave.json
  （显存满足即自动启动）。

### 下一步（Day 1+）
- [ ] 观察 24h：首个 100M nt checkpoint + val loss 落盘；
- [ ] 把 100M s17/s29/s43 与 30M-c10M 加入 wave.json；
- [ ] 全局家族分配表（T0.2.2，cluster_id 为键）；
- [ ] S5 权重统计重采样对照、S4 随机初始化对照（评测侧）；
- [ ] 逐层 probe 协议（T1.3 起步：CLSPool/attention pooling，禁 mean-pool）；
- [ ] GitHub 仓库初始化 + 推送。
