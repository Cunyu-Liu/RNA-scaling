# P3.1 多种子训练启动手册

状态：**PREP_READY / NOT_AUTHORIZED / NOT_STARTED**。本手册不构成启动授权。正式训练前必须由主代理在 P2 收口后显式授权，并解决数据、共享存储和启动当日显存门禁。

## 远端位置

- 两机代码：`/home/cunyuliu/rna-sc-p2/p3_1/`
- 正式权重：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights_p3/`
- 日志与状态：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/p3_1/`
- 服务器1 Python：`/home/cunyuliu/rna-sc-p2/venv/bin/python`
- 服务器2 Python：`/home/cunyuliu/rna-sc-p2/venv-core/bin/python`

队列固定为：

- 服务器1：`RNA-Sc-300M_s29` → `RNA-Sc-650M_s29`
- 服务器2：`RNA-Sc-300M_s43` → `RNA-Sc-650M_s43`

每台同一时刻只训练一个 run，不自动运行 probe，不启动或清理任何其他课题进程。

## 启动前硬性检查

1. 主代理明确确认保留“饱和稳健”目标，并显式授权这四个新训练和 GPU 预算。
2. `release22_split_8080.parquet` 重建管线必须到 `COMPLETE`；数据 gate 必须全过。文件存在或 SHA 单独匹配均不够。
3. **2026-11-26 留存及 iso-budget 追加修订**：每 run 只保存 0.5B/1.0B/1.5B/1,900,122,218nt 四个 checkpoint，最后一点为 final，与 s17 逐 nt 一致；validation 和完整 manifest 仍每 100M nt 记录，并在 budget final 强制补做。四 run 权重实测估算合计 **86.5838GiB**，双机并发原子写另预留 10.8230GiB。不得由执行脚本静默删除旧 checkpoint 或改变本留存协议；启动时仍须复查共享盘余量。
4. 启动当日复查其他课题占用。脚本要求 300M 至少 16,000MiB 可用、650M 至少 28,000MiB 可用；不足即停止，不缩 batch、不抢占。
5. CUDA 不可用、源码指纹不符、磁盘不足、数据验收缺失或 OOM 均停止留证。

可手动执行只读门禁（不会训练）：

```bash
cd /home/cunyuliu/rna-sc-p2/p3_1
/home/cunyuliu/rna-sc-p2/venv/bin/python data_gate.py \
  --output /teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/p3_1/manual_data_gate.json
```

服务器2将 Python 换成 `venv-core/bin/python`。

## 正式启动仪式（仅在主代理下令后执行）

服务器1：

```bash
cd /home/cunyuliu/rna-sc-p2/p3_1
bash launch_server.sh server1 --authorized-p3-1
```

服务器2：

```bash
cd /home/cunyuliu/rna-sc-p2/p3_1
bash launch_server.sh server2 --authorized-p3-1
```

缺少第二个参数时脚本以退出码 2 拒绝。`nohup` supervisor PID 写入 `logs/p3_1/server{1,2}.pid`。

## 监控与恢复

```bash
tail -f /teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/p3_1/server1.nohup.log
cat /teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/p3_1/server1_status.json
```

服务器2将文件名中的 `server1` 换成 `server2`。每个 run 另有独立日志、数据 gate 和 preflight JSON。

- 非 OOM 异常最多自动尝试 20 次，从最近的 manifest 登记且通过 ZIP/CRC 完整检查的 checkpoint 恢复。
- 恢复时数据重放不增加 `nt` 或 optimizer step，历史 validation/checkpoint manifest 保留。
- 没有有效 checkpoint 时归档旧 manifest，并以同一冻结种子从头重启，不覆盖旧 manifest。
- val loss 连续不改善只打印 `VAL_PLATEAU_OBSERVED`，**绝不 Early Stop**。预注册终点优先：只有 `final_nt == 1,900,122,218`、`stop_reason=budget`、`cpu_fallback_count=0` 才验收为 DONE；不足或 overshoot 均拒绝。
- OOM 标记 `BLOCKED_OOM_NO_BATCH_RESIZE` 并停止；CUDA 丢失也停止，不转 CPU。

## 完成后边界

supervisor 的 `QUEUE_DONE` 只表示该机的两个训练 run 完成，不表示多种子饱和结论完成。后续仍须按预注册对最大留存 `ckpt_nt`（1,900,122,218nt final）做全层 probe，并一次性计算三种子配对斜率与 CI；新 run 与既有 s17 严格 iso-budget。
