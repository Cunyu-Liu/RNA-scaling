# X-upload-main 执行报告

- 日期：2026-11-26
- 总结：**主臂三档终值权重 PASS；SPLIT_8080 仍阻塞，不能等价重建；配置适配已落地但未伪造数据完成状态。**
- 备份根全程只读；未修改 `code_git`、交接文档或论文稿；未触碰 `/root/rnaft`，未执行 kill、未干预其他课题进程。

## 1. 主臂终值权重

三枚 ckpt 均由各自 manifest 的最大 `nt` 确认。远端 `/root/rna-sc/runs` 原始文件的 SHA-256 与本地只读备份逐文件一致，随后只读加载原件、删除 `opt`，保留 `model/cfg/nt/step/...`，原子写入本项目 weights 目录。

| run | ckpt | nt / step | 张量数 | 远端剥离后字节 | 远端 SHA-256 | 验收 |
|---|---|---|---:|---:|---|---|
| RNA-Sc-30M_s17 | ckpt_nt1900121822_step202784.pt | 1900121822 / 202784 | 101 | 132860263 | `21b9e8594c46648610a9221019e3f0b1b846b7c652966111cb3e09100e8f7037` | PASS |
| RNA-Sc-100M_s17 | ckpt_nt1900122218_step202784.pt | 1900122218 / 202784 | 189 | 366586871 | `7e73e31317b7a4eac601356942bff4dd885729556f5255b9c079b61749d3bb45` | PASS |
| RNA-Sc-650M_s17 | ckpt_nt1900122218_step202784.pt | 1900122218 / 202784 | 229 | 2665204775 | `0631ccb128900f84eb02fb0c4396ae1de5b2330d1ea003465f4134098e63512d` | PASS |

逐位比对结论：三档模型键顺序均完全一致，所有模型张量均通过 `torch.equal`，`RNAMLMEncoder.load_state_dict(strict=True)` 全部通过，`optimizer_present=false`。三份上传 manifest 与备份 SHA-256 也分别一致。

本地 torch 2.8.0 与远端 torch 2.14.1 写出的容器文件 SHA-256 不同；这是序列化容器差异，**不是张量差异**。两者哈希均保留在 `weight_source_strip_sha256.tsv`、`remote_strip_verification.json` 和 `weight_verification.json`，不以容器哈希不同替代或掩盖逐张量验收。

### CUDA 前向

启动前 RTX 5090 已用 14,638 MiB、空闲 17,473 MiB。三档依次串行运行，显式 `cuda:0`、BF16、无梯度；模型和 logits 均在 CUDA，logits 全部有限，无 CPU fallback。

| run | logits | dtype | 峰值分配 MiB | 峰值保留 MiB |
|---|---|---|---:|---:|
| 30M | `[2,128,7]` | bfloat16 | 230.54 | 236.00 |
| 100M | `[2,128,7]` | bfloat16 | 559.86 | 612.00 |
| 650M | `[2,128,7]` | bfloat16 | 3906.26 | 4076.00 |

远端权重：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights/{RNA-Sc-30M_s17,RNA-Sc-100M_s17,RNA-Sc-650M_s17}/`。

## 2. SPLIT_8080 判定

按要求只读执行 `find /root/rna-sc /root/rnaft_restore /teams/HoulabData_1788502323/liucunyu -name '*8080*'`，最终 `find_exit=0`，共 76 个匹配路径，`release22_split_8080.parquet` 精确命中为 0。完整清单见 `find8080_paths.txt`，汇总见 `find8080_summary.json`。首次查找触及工具时限后，以不限时任务重跑并自然完成；此处仅采用最终完整结果。

`release22_cluster_split.parquet` 的实测结果为 3,357,201 行，schema 只有 `cluster_id, split`；SHA-256 为 `c25e7337393ddce39859192be2a1eb6b031371cad6925962ebfe74f99142e1c1`。cluster 级 split 计数为：train 3,022,118、family_validation 227,978、family_test 45,281、validation 30,780、test 31,044。

旧 `split8080_deep_verify.json` 记录的目标文件为 29,012,227 行、3,357,201 簇，必须含 `split_membership/canonical_sequence/rna_type`。cluster 表缺少全部三列，且没有序列和 RNA 类型信息，无法从每簇一行恢复每序列一行，故**不能等价重建**，未生成伪替代 parquet 或重建脚本。

影响面：P2.5 的 family_validation/family_test 输入、P2.7 的 family_validation random 协议输入均仍阻塞。在原始切分表或信息等价来源到位前，不应启动这两项目正式测评，也不能以 cluster 表替换协议。

## 3. 配置适配

未修改备份或远端 `code_git/rna_sc/config.py`（SHA-256 `e1fef7c37cd1ec2d79f95c872a773859bd517a6a3914e981f7d0557bc10295e6`）。新增：

- `/home/cunyuliu/rna-sc-p2/sitecustomize.py`，SHA-256 `fa0c4b800f2a20f14a21ca57502c7423742dbeb8c1bee0e08db9418e7ee4e4cb`；
- `/home/cunyuliu/rna-sc-p2/p2_python.sh`，SHA-256 `5eeeff61cefb07dd816f6f78a51e51ba3a97adb6952e2b58f21f8ddabed7fa1e`。

使用 `p2_python.sh` 或设置 `PYTHONPATH=/home/cunyuliu/rna-sc-p2` 后，`SPLIT_8080` 解析为 `/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/release22_split_8080.parquet`；也可用 `RNA_SC_SPLIT_8080` 显式覆盖。`config_adaptation.json` 状态为 `ADAPTED_TARGET_MISSING`，明确记录目标文件尚不存在。

## 4. 异常与降级

- 任务描述给出的 `/teams/.../venv/bin/python` 实际不存在；按 setup 报告和实测使用 `/home/cunyuliu/rna-sc-p2/venv/bin/python`，torch `2.14.1+cu132`，CUDA 可用。
- 首轮本地到远端 rsync 因速度过慢在 300 秒工具时限处中止，未作为完成证据。改用远端已存在且与备份源 SHA-256 相同的原始 ckpt 就地剥离；最终三档均独立通过源哈希、张量、strict load、远端文件哈希和 CUDA 验收。
- 本地剥离脚本首次因本机缺 pyarrow 无法导入包而失败；改为直接加载 `model.py` 后完成。该失败不产生正式结果。
- SPLIT_8080 按合同降级为明确阻塞，未缩水协议、未运行 smoke 冒充正式测评。

## 5. 证据路径

远端汇总：`/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/upload_main/`。

本地汇总：`补证_P2_20261125/results/upload_main/`，含本报告、剥离/哈希清单、逐张量验证、三档 GPU JSON、SPLIT_8080 评估、配置适配、执行脚本及 manifest。
