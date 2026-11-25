# X-sanity300 执行报告

- 日期：2026-11-26
- 总结：**300M 主臂权重上传与 CUDA 验收 PASS；X-P23 正式 batch=16 复跑完成，但旧锚点逐位验收 FAIL；协议同一性及同硬件原函数交叉验证 PASS；外部 COV 可信度升级冻结。**
- 未修改 P2_3 旧结果、交接文档或论文稿；未触碰 `/root/rnaft`，未 kill 或干预其他进程；全程无 CPU fallback。

## 1. 主臂终值权重

只读备份与服务器原始文件均为 `ckpt_nt1900122218_step202784.pt`，SHA-256 同为 `4f761014594fd937e357170a089c37ce79e68e23220432d9b7a6cd5085f66166`。备份 manifest 与服务器原件哈希也一致（`6465fa4b74a3b34892188586841e60900100570768a6687a0825a71200e0cfb1`），最大留存 `nt` 为 1900122218。

按 upload_main 流程只读加载原件、删除 `opt`、原子写入：

`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights/RNA-Sc-300M_s17/ckpt_nt1900122218_step202784.pt`

剥离后 1,208,467,879 字节，SHA-256 `465ca31b2c520c2aa5168a7d57f660c6191d4198ce5811489e7db7ee7edfc443`；197 个模型张量，键顺序及所有张量与原件逐位一致，`optimizer_present=false`。

独立 CUDA 冒烟通过：strict load、`cuda:0`、BF16、logits `[2,128,7]` 且全部有限；峰值分配 1768.95 MiB、保留 1806 MiB，无 CPU fallback。

## 2. X-P23 正式协议复跑

直接导入哈希锁定的 `/home/cunyuliu/rna-sc-p2/p2_3/run_p2_3_cov.py`（SHA-256 `693c5b8f…e007b`）。包装器仅改变输出目录，并将 sanity 分支原硬编码 b59 `nt=5800296014` 的 ckpt 加载断言替换为主臂 `nt=1900122218, step=202784`；冻结条件、干预、batch=16、BF16 读出和 pooled 汇总均调用原函数。

100 条抽样序列、1640 conditions、COV/CTRL 各 4920 mutations，condition batch=16，无 OOM 降批量。

| 臂 | COV | CTRL | COV−CTRL | old_drop |
|---|---:|---:|---:|---:|
| 主臂 trained | 0.04957731208609388 | 0.0026793007557787906 | **0.04689801133031509** | -0.015332180466989151 |
| 同架构 randinit17 | -0.0005501234744925324 | -0.0004714661467123807 | **-0.00007865732778015170** | — |

`trained − randinit17 = 0.046976668658095244`。两臂 condition ID 与顺序完全一致，逐 condition JSONL 可逐位重算汇总。

## 3. 旧锚点逐位比对

旧锚点 `COV−CTRL=0.04693655029252882`，本次为 `0.04689801133031509`，差值 **-0.00003853896221372999**；旧/新 hex 分别为 `0x1.8081148fca82bp-5` / `0x1.8030421d2810bp-5`，不逐位一致。

- COV：差 -0.000029813550781535025。
- CTRL：差 +0.000008725411432196264。
- old_drop：差 +0.0000040942830117837725。
- mutation 数均为 4920，一致。

因此预注册的 bitwise sanity 验收为 **FAIL**，不能把外部 COV 表可信度升级为已通过。

## 4. 协议差异排查

### 数据与条件

bpRNA 备份和远端 SHA-256 均为 `20d4ed56fa4f1d6e485cb48fe7b0b4d11bfe0fda2049904622dcc35874d15c51`。独立调用备份原 `run_cov300.py` 的抽样与 `build_conditions`，与 P2_3 冻结条件逐字段比较：100 条序列及顺序、pair 打乱/截断、CTRL k 位置、mask、互补定义、1640 个完整 condition payload 全部一致。

### condition batch

旧权威脚本每个 condition 单独前向；X-P23 预注册脚本 batch=16。补做 batch=1 诊断后：

| 项目 | batch=1 主臂 | 与旧锚点差 |
|---|---:|---:|
| COV | 0.049601403558164184 | -0.0000057220787112316485 |
| CTRL | 0.002685495074290041 | +0.000014919729943446789 |
| COV−CTRL | **0.04691590848387414** | **-0.00002064180865467974** |
| old_drop | -0.015350524670604382 | -0.000014249920603446806 |

直接调用备份原 `run_cov300.py::evaluate_model`（仅改数据/权重路径与 `cuda:0`）得到完全相同结果；原函数与迁移脚本 batch=1 的 COV、CTRL、COV−CTRL、old_drop 全部逐位一致。这证明在当前硬件与批量下迁移计算等价，也说明 batch 会影响 BF16 数值，但 batch 差异不足以使旧锚点逐位复现。

本次环境为 RTX 5090、torch 2.14.1+cu132；旧脚本指定 `cuda:6`，项目备份来自 A100，旧锚点完整精确数值环境未随 JSON 固化。残差与跨硬件/软件数值环境一致，但没有旧环境可复跑，**不将其宣称为已唯一证明的原因**。服务器2实测也为 RTX 5090，未提供 A100 复现路径。

## 5. 异常与降级

- 首次 trained 启动在正式前向前因原脚本 b59 `nt` 断言停止；未生成正式结果。随后仅适配主臂 ckpt 加载/断言并重跑。
- 正式 sanity 按原脚本以 exit 3 报告锚点不一致；该退出是预期验收信号，原始 JSON/JSONL 已完整保存，不作为运行中断删除。
- **降级结论：协议同一性 PASS、同硬件原函数交叉验证 PASS；旧锚点 bitwise FAIL；外部 COV 主张及表可信度升级保持 FROZEN。** 不改写 P2_3 外部 COV 数字或旧 manifest。

## 6. 证据

远端：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/sanity300/`；日志：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs/sanity300/`。

本地：`补证_P2_20261125/results/sanity300/`，含原始逐 condition JSONL、CSV/JSON 汇总、权重与 CUDA 验收、协议诊断、执行脚本、manifest 和 SHA-256 清单。
