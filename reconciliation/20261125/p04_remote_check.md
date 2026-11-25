# P0.4 远端只读核查

- 主机：`root@px2-jcy.matpool.com:29375`
- 远端时间戳：`2026-11-25T16:58:35+08:00`
- 连接：SSH 成功；全部命令均为只读查询。
- 边界：未写入、未启动或停止任何任务，未修改任何文件，未触碰 `/root/rnaft`。

## 执行命令

```bash
date -Is
nvidia-smi
ls -la /root/rna-sc/runs/
df -h /home /teams/HoulabData_1788502323/liucunyu 2>/dev/null
ls -la /teams/HoulabData_1788502323/liucunyu/ 2>/dev/null
ls -la /home/ 2>/dev/null
free -g
nproc
```

## GPU 实况

- GPU 数量：1；型号：`NVIDIA GeForce RTX 5090`。
- 总显存：`32607 MiB`；已用：`5403 MiB`；按总量减已用量计算，未占用约 `27204 MiB`。
- 瞬时 GPU 利用率：`44%`；功耗：`227W / 575W`；温度：`50C`。
- 驱动：`595.84`；`nvidia-smi` 报告 CUDA Version：`13.2`。
- 进程：PID `3533551`，`codonflow` 环境 Python，`812 MiB`；PID `3542400`，`/home/cunyuliu/llr_env` Python，`4576 MiB`。
- 裁决：未见 RNA-Sc GPU 进程，但卡并非空闲，仍有其他项目计算负载。可作为 P2 探针复测候选，执行前仍需重新查询并协调余量；本次未启动复测。

## 存储与内存

- `/home` 位于 `overlay`：总量 `300G`，已用 `292G`，可用 `8.2G`，使用率 `98%`，挂载点 `/`。
- `/teams/HoulabData_1788502323/liucunyu` 位于 `fx`：总量 `7.9T`，已用 `7.1T`，可用 `823G`，使用率 `90%`，挂载点 `/teams/HoulabData_1788502323`。
- 内存：`free -g` 报告总量 `60 GiB`、已用 `11 GiB`、可用 `48 GiB`；Swap 为 `0 GiB`。
- CPU：`nproc = 16`。
- 落点裁决：`/home/cunyuliu` 已存在，可放代码与小文件，但系统盘余量紧张；备份权重、数据及输出应放 `/teams/HoulabData_1788502323/liucunyu/` 下的新任务专属目录。该目录当前有 `823G` 可用，适合大文件；本报告未创建目录。

## 目录实况

远端 `/root/rna-sc/runs/` 仅有以下 7 个目录：

```text
RNA-Sc-100M_s17
RNA-Sc-100M_s17_b59
RNA-Sc-10M_s17
RNA-Sc-1M_s17
RNA-Sc-300M_s17
RNA-Sc-30M_s17
RNA-Sc-650M_s17
```

未见 `marscorpus`、`rnacentral` 或 `rfamcap` 目录。这只是远端当前目录实况，不替代本地权威备份的权重核查。

`/teams/HoulabData_1788502323/liucunyu/` 可正常列出，团队盘已有多个其他项目目录；未见名称明确为 `rna-sc` 的顶层目录。`/home/` 可正常列出，其中 `/home/cunyuliu` 存在。其他项目目录与本任务无关，未进入、未修改。

## P2 低成本补证勘察结论

- 可复测资源：单张 RTX 5090 约有 `27.2 GB` 名义未占用显存，但瞬时利用率为 `44%`，不是独占空闲卡。
- 推荐布局：代码/环境的小文件落 `/home/cunyuliu`；权重、数据和探针输出落团队盘任务专属目录。
- 主要限制：系统盘仅剩 `8.2G`；不得在 `/home` 复制大权重或批量输出。
- 本次仅勘察，未验证探针代码依赖、未加载权重、未估算具体任务显存峰值，也未执行任何训练或测评。
