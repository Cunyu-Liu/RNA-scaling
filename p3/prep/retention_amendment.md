# X-P3-retention：P3.1 四点留存与严格 iso-budget 修订

日期：2026-11-26  
状态：**AMENDMENT_VERIFIED / STORAGE_BLOCKER_RESOLVED / NOT_AUTHORIZED / NOT_STARTED / DATA_NOT_READY**。

本任务只修订运营留存、精确停止预算与验证工程，不启动正式训练。四个正式 run 均未启动；数据内容等价门禁与正式启动授权仍未解除。

## 1. 最终裁决：与 s17 逐 nt 一致

原适配 runner 在每 100M nt validation 后都保存 model+optimizer checkpoint，19 个/run 时四个 run 合计约 411.27GiB，无法给数据重建和临时文件留下安全边际。首次留存修订曾把 final 设为名义 2.0B；主代理随后追加裁决，**该 2.0B final 口径已作废**，因为既有 s17 用于对照的实际终值是 **1,900,122,218nt**。

现执行协议为：

- 新 run 主停止终点固定为 **1,900,122,218 cumulative valid nt**，与 s17 两档历史 checkpoint 逐 nt 一致。
- `budget_nt=max_final_nt=1900122218`，不再允许 final overshoot；不足或超过均拒绝验收。
- 每 run 只保留名义 **0.5B / 1.0B / 1.5B / 1,900,122,218nt** 四个 checkpoint，最后一点为 final，不是额外第五份。
- DONE 前强制核对四个目标齐全、最后 checkpoint 的 `nt==final_nt==1900122218`，并通过 ZIP/CRC 完整性检查。
- validation 每 100M nt 记录，并在 budget final 强制补做；完整收敛时间轴保留在 manifest。optimizer 状态随四点保存，恢复使用最近有效点。
- 新 run probe 使用同一 final，与 s17 历史对照严格 iso-budget；不得改用 2.0B、best-val、中间点或 5.9B/b59 checkpoint。

### 停止预算与 LR schedule 预算分离

冻结源码的 `budget_nt` 同时控制 warmup 比例和 cosine schedule。直接把该字段改为 1.900122218B 会把 warmup 从 10,000,000 隐式缩为 9,500,611nt，并改变 s17 所处学习率轨迹，因此本任务没有采用这种不具可比性的实现。

配置现显式区分：

- `budget_nt=1900122218`：训练停止、final 验收和第四留存点。
- `schedule_budget_nt=2000000000`：保持 s17 原 **10M warmup + 名义 2B cosine** 轨迹。

runner 仅在 `base_train.lr_at` 所读取的冻结配置中使用 schedule budget；停止与 final 判断使用 iso-budget。manifest 同时记录 `iso_budget_nt` 和 `schedule_budget_nt`，禁止把二者混写。

## 2. 修改位置

本地权威副本：

- `results/p3_1_prep/code/p3_train.py`：精确停止、四点触发、双预算分离、final 强校验和恢复策略一致性检查。
- `results/p3_1_prep/code/configs/RNA-Sc-{300M,650M}_s{29,43}.json`：统一 `budget_nt=max_final_nt=1900122218`、`schedule_budget_nt=2000000000`、`retain_ckpt_nt=[500000000,1000000000,1500000000,1900122218]`。
- `results/p3_1_prep/code/preflight.py`：证据显式记录 iso/schedule 两种预算及四点。
- `results/p3_1_prep/code/supervisor.py`：完成验收核对四点/final，平台期日志继续到实际 iso-budget。
- `results/p3_1_prep/code/smoke_retention.py`：验证精确 final、19 次 validation、四点及双预算。
- `results/p3_1_prep/code/smoke_resume.py`：覆盖两点合成留存、断点恢复和 final 文件检查。
- `results/p3_1_prep/SHA256SUMS`、`report.md`、`LAUNCH_MANUAL.md` 与 `prereg/P3_1_multiseed.md` 同步更新。

两机执行副本均已同步到 `/home/cunyuliu/rna-sc-p2/p3_1/`，预注册参考副本为同目录 `P3_1_multiseed.md`。单 run 磁盘门槛保持 300M **25,000MiB**、650M **45,000MiB**。脚本不静默删除旧权重，也不允许用不同留存策略的 manifest 恢复。

## 3. 最终干跑与恢复证据

| 检查 | 服务器1 | 服务器2 | 证据 |
|---|---|---|---|
| 四配置解析、冻结配方、10M warmup、2B schedule | PASS | PASS | `evidence/server*/RNA-Sc-*_config.json` |
| 精确 iso-budget、19 次 validation、四点触发 | PASS | PASS | `evidence/server*/retention_triggers.json` |
| final 必留、重复触发抑制、非法策略拒绝 | PASS | PASS | 同上 |
| 合成 CUDA 中断恢复 | PASS | PASS | `evidence/server*/resume.json` |

两机触发点 JSON 一致：目标为 `[500000000,1000000000,1500000000,1900122218]`，合成可变 valid-nt batch 模拟的实际点为 `[500039680,1000079360,1500119040,1900122218]`；validation 首尾 `[100007936,1900122218]`，共 **19 次**，checkpoint 恰为 **4 个**，`exact_iso_budget=true`、`final_is_retained=true`。

恢复 smoke 使用 1M 模型和合成 parquet，连续与 16,384nt 中断恢复均达到 **32,768nt / 32 steps**，最终模型 `model_tensor_mismatches=[]`，`stop_reason=budget`，`cpu_fallback_count=0`。

验证过程中曾拦截两类错误并已修正后重跑：名义 2.0B 的 final 不再符合追加裁决；直接缩短冻结 `budget_nt` 会隐式缩放 warmup。以上 PASS 均来自最终的“精确 1,900,122,218nt 停止 + 原 2B schedule”实现，失败中间态不记为通过证据。

## 4. 权重与共享盘安全边际

留存份数不变，因此实测权重核算不变：300M 单份 **3,625,432,769B**，650M 单份 **7,995,654,245B**。

| 项目 | 计算 | 永久占用 |
|---|---:|---:|
| 300M 两个 run | 3,625,432,769 × 4 × 2 | **27.0115790GiB** |
| 650M 两个 run | 7,995,654,245 × 4 × 2 | **59.5722664GiB** |
| 四 run 合计 | 16 份 checkpoint | **92,968,696,112B = 86.5838454GiB** |

双机同时原子写按 300M+650M 各一份临时文件预留 **10.8229807GiB**。最终实测最差共享盘余量为服务器2的 **397.6836GiB**（2026-11-26 06:11 +08:00）；以 200GiB 后续重建规划上限计算：

\[
397.6835938 - 200 - 86.5838454 - 10.8229807
= \mathbf{100.2767677\ GiB}.
\]

因此，在该包络下，后续重建中间产物、四点永久权重和双机临时写之和小于当前最差盘余量，安全边际约 **100.28GiB**。200GiB 是规划上限而非全量重建的实测峰值；正式启动前必须重测 `df`，若重建超额、其他写入降低余量或需要额外 probe 缓存，必须重新核算，不能把该余量视为无条件可消费空间。

## 5. 结论与仍存阻塞

- 原全量权重存储阻塞已解除；新 run 与 s17 的停止/probe 终点已统一为 **1,900,122,218nt**，同时保留 s17 原学习率轨迹。
- 代码、预注册、两机副本、哈希清单和最终干跑证据一致。
- **数据仍未就绪，正式训练仍未授权、未启动。** 本报告不表示 P3.1 在飞或完成。
