# X-P3-launch-prep：P3.1 多种子训练启动准备报告

日期：2026-11-26  
状态：**PREP_COMPLETE / NOT_AUTHORIZED / NOT_STARTED / DATA_NOT_READY**。四个正式 run 均未启动，未写正式训练账本；所有训练相关执行均为明确标记的小步数或合成数据 smoke。

**2026-11-26 留存及 iso-budget 追加修订**：每 run 仅保留 0.5B/1.0B/1.5B/1,900,122,218nt 四个 checkpoint，最后一点为 final；新 run 与 s17 历史对照逐 nt 严格一致。详见 `retention_amendment.md`。修订解除原全量权重存储阻塞，但不解除数据或启动授权门禁。

## 1. 交付位置

- 本报告：`补证_P2_20261125/results/p3_1_prep/report.md`
- 启动手册：`补证_P2_20261125/results/p3_1_prep/LAUNCH_MANUAL.md`
- 可执行配置与脚本：`补证_P2_20261125/results/p3_1_prep/code/`
- 干跑证据：`补证_P2_20261125/results/p3_1_prep/evidence/`
- 两机执行副本：`/home/cunyuliu/rna-sc-p2/p3_1/`
- 未来正式权重：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights_p3/`
- 未来 supervisor 日志：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/p3_1/`

未修改只读备份、原始 `code_git` 或交接文档。

## 2. 冻结配方与 checkpoint 规则

备份及两机执行副本的 `train.py/config.py/data.py/specs.py` SHA256 均与预注册逐项一致。

| 项 | 300M | 650M |
|---|---:|---:|
| 实测/冻结参数量 | 302,098,432 | 666,279,680 |
| d_model / layers / heads / d_ff | 1024 / 24 / 16 / 4096 | 1408 / 28 / 22 / 5632 |
| context / effective valid nt per step | 1024 / 16,384 | 1024 / 16,384 |
| 终点 | 1,900,122,218 cumulative valid nt，与 s17 逐 nt 一致 | 同左 |
| optimizer | AdamW, betas=(0.9,0.95), wd=0.1 | 同左 |
| LR / schedule | 3e-4；10M nt warmup，保持 s17 的名义 2B cosine 轨迹，在 1,900,122,218nt 精确停止 | 同左 |
| precision / clip / dropout | BF16 / 1.0 / 0.0 | 同左 |
| validation | `validation`，每 100M nt，masked-target NLL 累计至 4M nt | 同左 |
| Early Stop / CPU fallback | 关闭 / 禁止 | 关闭 / 禁止 |

数据流保持 parquet 行序、长序列非重叠 1024-nt chunk、15% MLM 的 80/10/10 规则和 `CRC32(canonical sequence) XOR seed`。适配 runner 在模型构建前设置 training seed，满足预注册的初始化控制；原 `build_model` 是在构建后才设种子，此差异已显式记录，未改原文件。

配置中的 `ckpt_nt` 与 `val_interval_nt` 都为 100M；修订后的适配 runner 仍每 100M nt validation、在 budget final 强制补做并记录完整收敛时间轴，但仅在跨过 0.5B/1.0B/1.5B/1,900,122,218nt 时保存 model+optimizer checkpoint。final 必留，DONE 前强制检查四个目标齐全、final checkpoint 的 `nt==final_nt` 且 ZIP/CRC 完整。新 run probe 使用最大留存 `ckpt_nt`，与既有 s17 的 1,900,122,218nt 逐 nt 一致。`budget_nt=max_final_nt=1,900,122,218`，另以 `schedule_budget_nt=2,000,000,000` 保持 s17 的原 LR 轨迹，不足或 overshoot 均拒绝；DONE 只能是 `stop_reason=budget`、`early_stop_patience=None`、`cpu_fallback_count=0`。

## 3. 独立工程适配

`code/p3_train.py` 调用冻结源码，但修复了不能安全用于长跑的原 resume 工程问题：

- 原逻辑加载 checkpoint 的 `nt` 后又从头重放并增加计数，可能直接错误结束；适配版重放只定位数据，不增加 `nt` 或 optimizer step。
- 保留历史 validation/checkpoint manifest，记录 resume event；checkpoint 和 manifest 采用临时文件原子替换。
- 只从 manifest 已登记且通过 ZIP/CRC 检查的最近 checkpoint 恢复。
- 没有有效 checkpoint 时保留旧 manifest 副本，再以同一冻结种子重启。
- val loss 平台期只报警，不停止；预注册 1,900,122,218nt iso-token 终点优先，不设训练步数上限。

## 4. 数据就绪门禁

`code/data_gate.py` 在两机均按预期拒绝当前启动，证据为 `evidence/server*/data_gate_expected_block.json`：最终 parquet、deep receipt、representative receipt、probe receipt 和 `COMPLETE` 阶段均不存在。重建日志最后仍为 `WAIT_SOURCE_DOWNLOAD`。

放行必须同时满足：

- 最终文件实际 SHA256 与全表验证 receipt 绑定；原文件 SHA 仅作信息项，不替代内容等价。
- 29,012,227 行及五 split 精确计数：14,130,321 / 164,280 / 108,979 / 7,525,752 / 7,082,895。
- representative 与旧 cluster 表双向零差异、cluster→split 全表一致、无簇或精确序列跨 split。
- 566,077 条 rfamcap train oracle 全字段精确匹配，原 schema 与物理行数核对通过。
- family_validation 前 20,000 和 family_test 前 4,000 的 probe 流计数 smoke 通过，管线阶段为 `COMPLETE`。

由于真实数据尚未发布，本轮只完成合成 parquet 的数据流 shape/非重叠计数/同种子确定性/异种子 mask smoke，未声称真实数据流或内容验收通过。

## 5. GPU 编排与实测

- 服务器1：300M-s29 → 650M-s29。
- 服务器2：300M-s43 → 650M-s43。
- 同机严格串行；300M/650M 启动分别要求至少 16,000/28,000MiB 当前可用显存。OOM 不降 batch、不改数学配方、不清理其他进程。

全尺寸 `16×1024` 输入、真实 BF16 forward/backward、grad clip 和 AdamW step 结果：

| 服务器 / run | 参数 | peak allocated | peak reserved | checkpoint | 结果 |
|---|---:|---:|---:|---:|---|
| 服务器1 / 300M-s29 | 302,098,432 | 5,830MiB | 5,866MiB | 3.376GiB | PASS |
| 服务器2 / 300M-s43 | 302,098,432 | 5,780MiB | 5,820MiB | 3.376GiB | PASS |
| 服务器2 / 650M-s43 | 666,279,680 | 12,726MiB | 13,458MiB | 7.447GiB | PASS |

服务器1的 650M-s29 smoke 在其他任务占显存时于 AdamW step OOM，未通过；未改 batch、未使用 allocator workaround、未触碰其他进程，证据保存在 `evidence/server1/RNA-Sc-650M_s29_oom.json`。650M 的模型构建和全尺寸训练步已在服务器2真实 CUDA 验证，服务器1正式运行仍由 28,000MiB 可用显存门禁保护。所有成功 smoke 的 `cpu_fallback_count=0`。

两台恢复 smoke 均 PASS：1M 合成数据连续训练与 16,384nt 中断恢复均到 32,768nt、32 steps，validation 为 `[16384,32768]`，最终模型所有张量 `torch.equal`，无非预算停止或 CPU fallback。证据为 `evidence/server*/resume.json`。

## 6. 阻塞项

1. **未获正式启动授权**：未授权调用 `launch_server.sh` 已实测以退出码 2 拒绝。
2. **数据未就绪**：目标 parquet 未发布，完整内容等价验收未完成。
3. **原共享存储阻塞已由留存裁决解除，启动当日复查仍保留**：原 19 个 checkpoint/run 需约 411.27GiB；现四 run 仅四点留存合计约 **86.5838GiB**。重建空间、安全余量和实测盘余量见 `retention_amendment.md`。脚本不会静默删除或改点。
4. **启动当日资源未放行**：05:35 服务器1约 19,489MiB、服务器2约 9,891MiB 显存被占用；每次正式 run 前都会重新检查，当前状态不代表未来启动时状态。

因此，本任务交付的是经过干跑验证的启动准备，不是在飞训练，更不是完成的 P3.1 多种子实验。
