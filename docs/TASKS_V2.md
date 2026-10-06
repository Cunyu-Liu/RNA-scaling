# RNA-LM 迁移学习机理研究：任务分解（TASKS V2 · 事无巨细版）

> 版本：3.26（2026-10-06【★Day 26 收口 + 交接核查日】：①30M_b59 DONE（nt=5.90B/best_val 0.7928）→ closeout 自动链收口（probe 12 层 best L10 0.1942 + randinit 0.1245@L6）——**3×2 析因第三点：30M 档预算效应 −5.24pp（0.1942 vs 2B 0.2466）**，翻转链 −5.24/−2.74/+3.76 单调成立，交叉点 100M↔300M 之间（cafec9d/5d7c791）；②**S7 结构预算矩阵 4×2 全落**（s7_structure_budget_matrix.json）：结构通道预算效应单调 +0.09/+0.85/+1.87pp——与 family 通道符号翻转形成双通道对照（family=小尺度过训故事 / structure=尺度门控欠训故事；100M 格 c93cd1d，650M 最后一格在训）；③S7 b59 randinit 对照三档全收（0.586/0.5868/0.5899）——学习增量 −0.9/+1.1/+2.7pp 尺度放大，300M 双臂逐位一致（同机同路径自校验）+ 30M/100M 差~1pp = 探测噪声地板免费标定（5d29c91/65ad95e）；④**预注册三通道裁决落地（p5rns_b59_verdict.json）**：finite-channel 强形式证伪——RNS 收紧（100M 0.083→0.052/300M 0.067→0.043）+ P5 non-rRNA +0.11/+0.29/+0.36 nats/token 尺度放大，仅 family-Delta 守恒 → §5 结论改写"30M 三重平台是 family 通道现象"（c93cd1d）；⑤P5 v1 协议伪迹被 randinit 对照捕获并废弃（v2 MLM 同掩码位协议）；30M_b59 mommatch 0.1258 ≈ randinit 0.1208 对照三件套对齐；S7 650M watchdog 部署（cron */30，28 层完整性门 + 重试 + lock 自清，a1eb634）；在训：650M_b59 72%（~2-3 天，唯一剩余臂——收口后 family 第 4 点 + S7 最后一格 + P2 干预臂判定全自动）；交接批：DRAFT 同步本地镜像（91de84d7）、PPT slide 53 新增 + 4 页 stale 修正（四遍验证）、本地 01/02/03 文档回写）
> 版本：3.25（2026-10-04 晚【★Claim-14 证伪落证五件套】：①300M_b59 DONE（nt=5.90B/best_val 0.7503）→ closeout 自动链收口（probe 24 层 best L22 0.3821 + randinit 24 行）；**3×2 析因第二点：300M 档预算效应 +3.76pp（0.3821 vs 2B 0.3445）——与 100M 档 −2.74pp 符号翻转**，且 0.3821 > 650M@2B 0.3632 全线新最优；②**Claim-14 预注册检验判 FAIL**（判据“增益<1.0pp→边界≈300M”，实测 +3.76pp ≫ bar → boundary_holds=false 入 evidence/factorial_verdict.json）——语料最优规模 >300M、2.0B iso-token 对大尺度欠训，表述改写为 Chinchilla 式 compute-optimal 交互（每档尺度各有最优预算：100M≈2B / 300M≥5.9B / 650M 预期更高）；③DRAFT §4.1 预算段重写 + 结构预测段标注（4931b41 零 PENDING）；④fig6 v2 两点预算轴（红绿箭头+650M 参照线+证伪角标，bb7c7fa，像素级四元素核验）+ PPT slide 51（几何三查 0 问题）；⑤TRAINING_LOG Day 25 双盘（ce422d4）；在训：30M_b59 95%（凌晨自动链收口第三点）/ 650M 56%）
> 版本：3.24（2026-10-03 晚【★H5 多尺度链符号翻转定论】：10M_rw1 DONE（nt=2.0B，31556 nt/s）→ closeout 自动 probe L14 0.1746——**重加权效应 10M +0.15pp / 30M −0.58pp / 100M −4.29pp 跨尺度符号翻转**（容量门控的先验效用：容量受限时压平 rRNA 先验微正，容量充足后家族频率本身是可学习信号，压平即损失）；best_val=0.0000 判因闭环（语料 parquet 全 train split → validate 流空 0/0——协议性伪迹，三证训练健康）；h5_rw_multiscale.py + verdict 入库（04e82a5）；PPT slide 50；300M_b59 89% 在途）
> 版本：3.23（2026-10-03 04:0x【10M_rw1 第三死迁移 + DRAFT §4.1 回填】：①10M_rw1 16:15 第三次静默死亡（无栈/run 目录空）→ 死因判定 GPU6 cgroup 5.1GB 宿主内存份额 → **迁移 GPU3 重启**（PID 1552168，2.1k nt/s 共卡限速，2B 需 ~11 天——决策：H5 链 30M/100M 已齐，10M 列 camera-ready 前补齐项不返工）；②DRAFT §4.1 主表回填 100M@5.9B 预算轴段落（d99a65a，−2.74pp + 层位下移 + randinit 完整 + in flight 声明——主表/§4.8 双入口；零 PENDING 保持）；③300M_b59 82.8%（~1 天收口）30M 64.4% 650M 40.7%）
> 版本：3.22（2026-10-03 01:0x【★3×2 析因第一点收口】：100M@5.9B DONE（nt=5.9B/best_val 0.7626/fallback=0）——closeout_b59 自动链首战成功（probe 23 层 0.2989@L16 + randinit 46 行 0.1577 全自动）；**预算效应 −2.74pp（vs 2B 0.3263）——过训负效应**：2.0B 已在/超过 100M 档 compute-optimal 点，RNA 语料重复训练不兑现（Muennighoff 假说域边界实测）；与 S2 饱和点/30M 现象同族——iso-token 2B 主线预算选择接近最优；层位 L21→L16 前移（磨蚀同型）；DRAFT §4.8 Q19/Q20 同步（210bab5）+ SPEC S14 五轴版 + PPT slide 48）
> 版本：3.21（2026-10-02 18:0x【Q19 RNS 协议对照五问 + 分箱新发现】：①Q1 协议差异诚实定位（k∈{10,50,100} vs 论文 k=1000——池规模 4500 约束；无 100 次欠采样——方差缺口登记 T3.5.8）；②Q2 家族层 Spearman −0.19 已有 + T3.5.7（RNS vs 前向共变 COV 连续相关）补缺；③Q3 分箱结构测评落地（s14_bin_eval.py + 诊断 s14_bin_diag.py）——**高 RNS 箱 pair-F1 +18%/long-range +29.3%，与蛋白论文 −40%/−60% 方向相反**，长度混杂已排除（Spearman(len,RNS)=+0.19）→ 机制两候选（组成通道翻转 / RNA 域 RNS 标记"长而常见"非"难"）；家族轴不翻转——"RNS 预测方向取决于混杂轴"方法学警示；④Q4 六档 RNS-参数量表整理；⑤Q5 灵感四条（行动项 A：eval_matrix 加 RNS 协变量列 T1.2.7；行动项 B：Discussion 协议建议段——embedding 交付同时交付 RNS 分布））
> 版本：3.20（2026-10-02 00:5x【Q10-Q18 交接收口 + b59 析因收口链部署日】：①watch_all 重大 bug 修复（inc12-suffix：b59/rw1 臂 DONE 帧 run_id 无后缀→5.9B 臂训完不会被自动 probe——已改为按日志文件名 key，22 个 DONE run 验证全对，值守进程已带补丁重启）；②closeout_b59.py + factorial_verdict.py 部署（4 个 5.9B 臂 DONE→自动 probe+randinit 对照→3×2 析因终判表 + Claim-14 检验，evidence/factorial_verdict.json）；③10M_rw1 死任务重启（supervisor 曾用普通 train 误启被杀 rc=-9，改 train_s3_rw 手动 GPU6 真版重启）；④100M_rw1 补 probe：best 0.2834@L21（< full 0.3394——重加权负效应 100M 档复现，H5 双轴多尺度链）；⑤在跑 4×5.9B 臂进度 10-02 00:4x：100M 85.9%/300M 71.5%/30M 49.3%/650M 30.7%；Q10-Q18（结构涌现三测度/读出通道/Partner-Oracle/位置对探针/外部模型全套/NB 电池组/简单基线/归因修正）详见问题与答案.md）
> 版本：3.19（2026-10-01【Q16-Q17 收口日】：外部模型结构探针全量——RNA-FM 0.587@L0 深层崩塌/RiNALMo micro 0.653>mega 0.607<giga 0.728@L32 U 型深层陡升/NB 0.615@L30/自训 650M 0.6255；语料>参数（650M 同参数 +0.10）+可证伪预测（5.9B vs Rfam 富集臂）；NB 电池组四臂终值（MLI/注意力头层位架构对比/saliency 诚实负）；figs_v1 六图 300M 全更新；六档结构 randinit 齐（Δ≈0 全档）；"线性读出饱和 300M vs 前向耦合 650M 增长"分叉入档）
> 版本：3.18（2026-09-28~30【Q10-Q14 结构涌现深挖】：共变敏感性测试（650M COV +0.096 超 100M 4.7 倍，randinit≈0——结构知识 100% 预训练来源）；读出头 v1-v5 五轮（线性 0.61→交互头 0.64 墙→Partner-Oracle 0.998→位置对探针 AUC 0.93+→DP 求解器 pair-F1 0.17-0.20）；无模型对级基线 0.922（组成捷径支配，净增量 +0.03@650M/RNA-FM 负）；finetune 收敛检查（墙 ~0.64 同位）；"知识在、求解器缺"定论；DRAFT §4.4 多轮 commit）
> 版本：3.17（2026-09-26 20:1x 晚【650M 巡检日】：用户指令会话核验——DONE 帧（log line 1111，nt=2000003270/best_val=0.7757）/manifest/probe 28/28 层三口径一致；五档终判第 16 次幂等复跑 md5 不变（08f2542b，toktokenbench env）；preprint v1.0（DRAFT_v1.md 09-26 17:03 版，零 PENDING）与 T1.2.6（t126_fullft_650m.done）双线复核在位无需启动；8 卡全忙（300M_b59 27.1% + 100M_b59 在训），不打扰）
> 版本：3.16（2026-09-24 晚【T2.1.3 终验收口日】：五档终判第 9 次幂等复跑 md5 不变（08f2542b，用户指令会话核验）——650M DONE 帧（log line 1111）/manifest/probe 28/28 层三口径一致；T1.2.6 650M 扩档完成 [~]→[x]（t126_fullft.json 三档三点齐 + .done 落盘）；DRAFT v1.1 七槽回填完毕、§4.11 低数据三档入文，preprint 线推进至 T4.2.3 措辞检索 → T4.2.5 arXiv；在训 3 run 不打扰）
> 版本：3.15（2026-09-22 晚五【交接日】：Day 12 收口批——①closeout_650m 自动收口链部署（DONE→probe→五档终判→S13b v2，修复终判手动触发缺口）；②T2.3.3 S3 家族重加权 arm 正式启动（alpha=1.0 簇级展平，14.1M→57.7M 有效行，30M-rw1 GPU3 训练中）；③S14 650M RNS 单点补 H8 终点（OOM 硬化版 GPU6）；④代码 push GitHub 33daa68）
> 版本：3.14（2026-09-22 晚四：用户质询"四分带稀释趋势"→细粒度对齐分析（26e2313）——giga 29/30 对齐层高于 mega（+0.017 全层性增益）；更深发现：参数增益形态从"深度延展"（micro→mega 同层更弱但好层 0→5）转为"全层抬升"（mega→giga）；≥0.24 层数 0→5→18；量级结论稳健（top10 均值 18× +4.8pp）；650M 84%）
> 版本：3.13（2026-09-22 晚三：用户质询批①全层统计表②mega s29 缺口——ext_full_layers.py 四分带全层统计入档（87ee95b）+ mega p29 L29 0.2541 补齐→外部线 8/8 双 seed 矩阵闭环（144 行）；PPT 页 37 加附表；650M 83%）
> 版本：3.12（2026-09-22 晚二：外部线种子复现全闭环（15e951b）——RNA-FM p29 L2 0.1325/RiNALMo-giga p29 L30 0.2644：全部外部结论双 seed 稳定（层位相邻、F1≤0.3pp）；外部账本 114 行 7 run；650M 83%）
> 版本：3.11（2026-09-22 午后：显存利用批——T1.2.6 full-FT 线完成（f93ec82：full-FT 上升 vs probe 平坦→低数据瓶颈=头容量）；T3.5.6 S14 时间轴（RNS 峰 1.0B vs F1 峰 0.5B 错位+双降——解耦三轴齐）；S9 独立重算在跑（SPEC 待办）；650M 80%）
> 版本：3.10（2026-09-22 午：T1.3.3 length_bin 落勾 + T1.2.6 probe 线完成（a90ff13）——短序列箱全尺度塌陷、512+ 长箱规模分化（30M/100M 0.11 vs 小档 0.05）、低数据曲线全尺度平坦（S14 解耦再证）；650M 75%）
> 版本：3.9（2026-09-22 晨三：**复现批收口（7689c62）**——RiNALMo 参数量轴三点闭合（36M/148M/650M：18× 参数仅 +2.6pp，对数平线）；语料组成主导三点证据链 + 层迁移定律跨架构成立；de-rRNA 外部版四模型全存活；CNN 三 seed 0.5343±0.021；S7 四尺度 randinit 全档——用户质询"单点不严谨"全部补证完成）
> 版本：3.8（2026-09-22 晨二：**复现批（c1f18f2，用户质询"单点实验不严谨"触发）**——CNN 三 seed 0.5343±0.0206、RiNALMo mega 148M 补档（4× 参数仅 +1.3pp）、micro pseed29 层位稳定、S7 randinit 补齐至四尺度全档（结构零增益 |Δ|≤0.016 全档）；"random 全负"错误表述废弃（30M/100M 高于 CNN）；giga 650M 在途）
> 版本：3.7（2026-09-22 晨：红队 E 外部版通过（0065bc8）——RNA-FM L0 最优/RiNALMo 中后段单峰去 rRNA 后层形态全存活；探针 v2 补 per_class_f1（账本 24 行）；PPT 38 页（36/37 新增基线全表+外部模型对比表，页码自洽）；650M 65%）
> 版本：3.6（2026-09-22 凌晨：T1.2.5 全基线收口（dc1a4fc）——LightGBM/CNN/randemb 补齐，收益口径终表 family 30M +0.089/100M +0.163、random 全负；RiNALMo-micro 36M 外部 probe 完成——best L8 0.2407，语料组成>参数量、层行为近受控家族；650M 65%）
> 版本：3.5（2026-09-21 晚：S14 v2 家族交叉（T3.5.5/C9.4 落勾，bdaef5c）——ρ=−0.19 家族层面解耦 + 欠表示家族嵌入随机化（Prabakaran RNA 验证）；红队 E 通过（20ac90a/9a5520d）；650M 62%）
> 版本：3.4（2026-09-21 午二：红队 E 强制项通过（20ac90a）——去 rRNA 分层下规模趋势/10M 谷/层迁移全部稳健（结构性结论由非 rRNA 家族独立支撑）；650M 62%）
> 版本：3.3（2026-09-21 午：T1.3.2 RNA-FM 96M 完成（e65b005）——官方模型 best 层在嵌入层（与受控家族深层反转）+ 家族级 0.1335 < 自训 100M 0.3394（线 1 脆弱性印证）；层组织=配方主导）
> 版本：3.2（2026-09-21：S7 终表双尺度对照——结构零增益复现（100M randinit 0.5855 ≈ trained 0.5890）；S13b 全量确认 NOT-BELL（CI 收紧）；GPU6 恢复批收口（d6067cc）；PPT 37 页 Day10 同步 + S1 三 seed 表重建；650M 56%）
> 版本：3.1（2026-09-20 晚：S7 结构对照——**预训练结构零增益**（10M randinit 0.5678 ≈ trained 0.5663）+ 四证据链汇聚（家族统计迁移/结构未学到）；S13b NOT-BELL 预注册负结果（1bc1c18）；预印本 v0.5→v0.6（b98567b/638c8e4）：三 seed 主表 + 10M 谷 + 磨蚀任务特异性 + S14 解耦 + S13b 负结果入稿）
> 版本：3.0（2026-09-20 Day 10：★五档全三 seed 达成 + 10M 谷发现（8e81b11）；S7 bpRNA 结构 probe 四档（f920431）——磨蚀任务特异性（结构任务无层塌陷）；S14 RNS 规模轴完成（H8 首证据：表征质量 30M 平台与下游 F1 解耦）；650M nt≈0.7B/2B）
> 版本：2.9（2026-09-19 晚二：T2.2.3 磨蚀层位口径澄清（10M best_rel=0.05=磨蚀签名，用户质询触发）+ T1.2.4 random 主表数值入档；1M/10M 补种四 run 已由 supervisor 自动启动（6 卡并行，26fc359）——五档全三 seed 目标执行中）
> 版本：2.8（2026-09-19 晚：T1.1.1 bpRNA 接入 ✓（b960e6e，12,317 seq/329,268 配对/存量资产复用）；S4×S9 泄漏归因三角 ✓（4e2ed4d——对照只吃到 11-18% 红利、k-mer 105%、信号在组成层）；预印本 4.7 归因段入稿（ab74141））
> 版本：2.7（2026-09-19 傍晚：T1.2.4 Δ 汇总表 v1 + T1.2.5 k-mer 基线 v1 落勾（07aa5fe）——家族切分 LM 增益≈0（良渚复现）+ 泄漏=协议性质；T0.2.6 全 16 格 + Δ 随规模放大定律 + Fig3 候选；预印本三段论（S4/S5 权重结构存在 → 真泛化收益≈组成基线 → random 切分收益是泄漏）闭环）
> 版本：2.6（2026-09-19 下午二：T0.2.6 评测 runner v1 完成落勾（deb8eae）——10M Δ(随机−家族) 首个强证据：balanced 0.1555/0.4928 vs meanpool Δ≈0（协议×切分交互）；1M/30M/100M 批次 GPU6 排队）
> 版本：2.5（2026-09-19 下午：T2.2.2 S5 矩匹配四档完成——H3 全档排除（+0.0286/+0.0478/+0.1233/+0.1668，mommatch≈randinit）；Li et al. 三对照 S4/S5/S6 全部 inc12 确定性闭环（b948061））
> 版本：2.4（2026-09-19 v0.4 确定性重跑收口：S4 randinit 四档重跑（+0.0593/+0.0430/+0.1221/+0.1686）+ s4_randinit_table.py 入库；10M-c1Mcs 时间轴 4 ckpt 重跑（峰 0.5B 0.244→0.7B 0.204，磨蚀复现）；S12 linkage 三 run 复算（−0.478/−0.384/−0.370）+ run 标签版保存；jsonl 旧行清除备份 probe_results.pre_v04randinit_20260919.jsonl；650M nt=0.14B+ 持续训练）
> 版本：2.3（2026-09-18 状态回写：T2.1/T2.1.3 收口含 650M 触发（slope 0.142 CI[0.104,0.180]）；T2.2.1 首半/T2.2.3 四尺度定稿/T2.3.2 多样性/T3.2.1 cmscan 完成标记 + 证据路径；probe 确定性协议 inc12（弱层 run-to-run ±0.10 F1 方差发现→逐层 seed 根治）+ jsonl 两轮去重入册；仓库 Cunyu-Liu/RNA-scaling f9abf37..ededb4c 22 commits；650M 666.3M 训练已启动）
> 版本 2.2（2026-09-16 修订二【逻辑自洽审查修补】：T3.4 重定位为 fitness 分支（依赖 T1.1.6 二期可选）+ 新增 T3.4b 结构版钟形（H7 主检验，主支柱）；对应 SPEC v1.6 假设空间 6→8）
> 依据：01_SPEC v1.1 + DECISIONS_V1.1_20260915（Q1-Q9 修订）+ 本次模型/任务复查
> 用法：本文件是**唯一执行清单**。每项有 ID、验收物、依赖、状态框 [ ]。
> 状态图例：[ ] 未开始 · [~] 进行中 · [x] 完成（附证据路径）· [!] 受阻/变更

---

## T0 立项与基建（第 0-1 月）——状态：基本完成

### T0.1 导师确认与文档治理
- [x] 00-03 文档体系交接（4 份全读，2026-09-13）
- [x] Q1-Q9 九问修订确认 + DECISIONS_V1.1 归档（/home/cunyuliu/rna-sc/DECISIONS_V1.1_20260915.md）
- [ ] T0.1.1 split 口径勘误待导师拍板：文档写"8/1/1"，实测 TokBench 为
      train 48.7% / family_val 25.9% / family_test 24.4% / val 0.57% / test 0.38%
      ——S0 "held-out 10%" 用 val+test（约 1%）承担，family_* 留给家族级评测
      【验收：导师邮件/会议纪要一句确认，写入 SPEC 勘误节】
- [ ] T0.1.2 两层级发布/投稿渠道等 6 待决项随下一次汇报收口

### T0.2 基建（复用 TokBench）——已验收项
- [x] A3：release22_split_8080 深验证 PASS（29,012,227 行 / 3,357,201 簇 /
      簇泄漏 0 / 序列泄漏 0；证据 evidence/split8080_deep_verify.json）
- [x] A4：全局家族索引（cluster_pure=true；data/release22_cluster_split.parquet）
- [x] A5：ledger 上线（claim 防重 + flock 锁 + upsert 恢复；三事故后实战修复）
- [x] A6：冒烟 ALL PASS（mask 确定性/参数 ±12%/前反向/loss 下降/零 CPU 回退）
- [x] 基建代码：model/config/data/train/ledger/status/supervisor/smoke/
      family_table/probe/subsample（GitHub Cunyu-Liu/RNA-scaling，~20 commits）
- [~] T0.2.5 外部数据集家族分配表 join（stage-2：等 T1.1 数据落地后做，
      用 canonical hash + Infernal 双路对齐 cluster_id_8080）
- [x] T0.2.6 评测侧统一 runner：eval_matrix.py（模型×任务×协议×切分的
      声明式 spec + eval ledger 化（flock JSONL 防重），防漏测/重测）
      【v1 完成含冒烟（2026-09-19，commit deb8eae）】：协议 v1 =
      probe-balanced（类平衡，红队 B）+ probe-meanpool（day-1 基线）；
      切分 v1 = family + random（held-out 池 i%5 行划分）；**10M 首个
      Δ(随机−家族)：balanced 0.1555 vs 0.4928（家族切分崩塌至 1/3）；
      meanpool Δ≈0——协议×切分交互证据**；1M/30M/100M 批次 GPU6 排队；
      v2（T1.2）加 zero-shot/LoRA/full-FT + 任务三分法
      【验收达成：单模型冒烟 ✓ + ledger 记录 ✓；证据：eval/
      eval_matrix_results.jsonl + eval_matrix.jsonl】

### T0.3 文献精读上岗（与 T0.2 并行）
- [~] 必读四篇 + REDIAL/Papazoglou（Q9 两篇新参考文已精读归档）
- [ ] T0.3.1 RiNALMo 评测章节复现（A7 验收）：bpRNA 家族级切分二分类，
      复现其 F1 ±0.02 内【验收：单测脚本 + 复现报告入 evidence/】
- [ ] T0.3.2 RNA-FM 评测设置精读笔记（结构 probe 部分，作 S8 对照口径）
- [ ] T0.3.3 Li et al. ICML 2024 实验细节节精读（370 实验因子组合——
      开题前已列"必精读"，至今未完成，阻塞 S4/S5 对照设计的最终冻结）

### T0.4 服务器运维（贯穿）
- [x] 服务器 cron 每 2h + 本地巡检每日 2 次（CPU 回退硬规则/崩溃诊断/
      队列接力/记录推送全自动）
- [x] TRAINING_LOG.md 逐日记录（事故-决策-吞吐-结论四段式）
- [x] 8 起调度/数据事故根治（详见 TRAINING_LOG 事故节）

---

## T1 评测基建与线 1（现成模型，第 1-2 月）——关键路径

### T1.0 模型补全（本次复查结论，2026-09-16）

已核查 2025-09 至 2026-09 新发布，评测名单更新：

| 模型 | 状态 | 动作 |
|---|---|---|
| RiNALMo 33M/148M/651M | 已在册 | 主力（Zenodo 全公开）|
| RNA-FM 26M/96M | 已在册 | 第二同源系列 |
| RIBOSPAN 1.61B/10K ctx | 已在监控清单 M4（arXiv 2608.22849，2026-08-24） | **必须入线 1**（自称最强 encoder-only，缺它重蹈 RNAscope 覆辙）|
| BiRNA-BERT 117M | **新增**（Commun Biol 2025-11，自适应双 token 化，开源） | 线 1 补入——正好是"tokenization 变量"的活样本 |
| ChaRNABERT | 复查发现（可学习字符 token 化系列） | 线 1 可选——与 BiRNA-BERT 二选一（tokenization 轴不堆两个）|
| ERNIE-RNA 86M | 已在册 | 结构增强预训练代表 |
| HydraRNA | 已在册（Genome Biol 2025-11） | 观察（hybrid 架构，附录级）|
| Moirain（生成式 DPO，arXiv 2605.23961） | 新见 | **不入线 1**——条件生成模型，与判别式协议矩阵不匹配 |
| GoForth / Designing-RNAs（设计向 LM） | 新见 | 不入线 1（设计任务不在任务三分法内）|

- [x] T1.0.1 RIBOSPAN + BiRNA-BERT（或 ChaRNABERT）写入 SPEC 5 节模型矩阵（2026-09-20 补执行：SPEC §5 + PPT 页 12 同步写入；页 30 复查1 决议与页 12 表格此前的缺口已闭合）
- [~] T1.0.3 300M 锚点档（2026-09-20 修订三决议，用户拍板）：
      ① 300M@2B（S1 家族第 5 档，单种子；对数轴空洞 6.5×→2.2×，100M→650M 触发判断由外推变内插）；
      ② 300M@5.9B（语料最优锚点——5.9B÷20 ≈ 295M 恰为 R22 语料的 Chinchilla 边界）；
      ③ **论文级 claim（用户指示必写，登记 SPEC §1.2 Claim-14）**：若实测证明"R22 语料能喂饱的最大模型 ≈300M"，则正文定量论证"当前超过该边界的 RNA LM（RiNALMo-giga 651M、RiboSpan 1.61B 等）的参数量超出 RNA 语料可支撑的最优规模"——300M@5.9B vs 300M@2B 的预算增益不显著即为边界成立的实测判据
      【验收：SPEC §4/§5/§8 增补 + 权重落盘 /mnt/cunyuliu/models/，含 SHA256】
      **执行进展（2026-09-22 晚六）**：spec 注册完成（specs.py，7101c49）
      ——d=1024/L=24/h=16/ff=4096 → 302.1M（0.7% 标称偏差，家族
      deep-narrow 形态，12% 容差带内）；**臂① 300M@2B 收口完成
      （2026-09-26 Day 17，8597410）**：DONE（best_val 0.7801，
      fallback=0）→ watch_all 自动 24 层 probe：**best L22 F1=0.3445
      （rel 0.957）**——六档内插表：1M 0.1650 / 10M 0.1535 / 30M
      0.2651 / 100M 0.3394 / 300M 0.3445 / 650M 0.3632——**100M→300M
      仅 +0.5pp（近平台），300M→650M +1.9pp**；层迁移终点逆转六档
      确认（rel 峰 0.957@300M → 0.296@650M）；**臂② 300M@5.9B
      在训（b59，26%，~4 天）**：--budget-nt 管线（a652012）；
      Claim-14 判据转交 b59——若 5.9B 增益不显著 → 语料最优边界
      ≈300M 成立
      【证据：evidence/t103_300m2b_closeout.json + rna_sc/train.py
      --budget-nt（a652012）+ wave.json b59 条目 +
      logs/RNA-Sc-300M_s17.log DONE 帧】
- [~] T1.0.4 5.9B 预算臂群（原 T1.0.2 重编号，2026-09-20 修订二决议）：3×2 析因（100M/300M/650M × 2B/5.9B）预算效应可分离——100M@5.9B 兼作 RNA 域数据受限定律实测点；后追加 30M@5.9B（H30 因果干预臂）
      【验收：SPEC 增补 + 权重落盘 /mnt/cunyuliu/models/，含 SHA256】
      **执行状态（2026-10-06 交接核查）**：**4 臂中 3 臂 DONE 并全部
      自动收口**——①100M_b59 DONE 10-03（−2.74pp 过训）；②300M_b59
      DONE 10-04（+3.76pp 欠训补偿，0.3821>650M@2B 0.3632 全线新最优，
      Claim-14 证伪）；③30M_b59 DONE 10-05（−5.24pp 最深过训，翻转链
      −5.24/−2.74/+3.76 单调）；④650M_b59 72% 在训（GPU0，~2-3 天，
      唯一剩余臂）。**附产品全落**：S7 结构预算矩阵 4×2×2（trained/
      randinit，evidence/s7_structure_budget_matrix.json——结构通道
      +0.09/+0.85/+1.87pp 单调 vs family 通道符号翻转的双通道对照）；
      p5rns 三通道裁决（finite-channel 强形式证伪，RNS/P5 尺度放大
      移动）；30M_b59 mommatch 对照（0.1258≈randinit 0.1208）；S7 650M
      watchdog（monitoring/s7_650m_watchdog.sh，cron */30，28 层完整
      性门 + 失败重试 + lock 自清）——650M 收口动作全自动覆盖（family
      probe + randinit + mommatch + S7 最后一格 + factorial_verdict 第
      4 行）
      【证据：evidence/factorial_verdict.json（3/4 行）+ s7_structure_
      budget_matrix.json + p5rns_b59_verdict.json + h5_rw_multiscale.json
      + logs/RNA-Sc-650M_s17_b59.log + rna_sc/closeout_b59.py（mommatch
      补丁版）+ monitoring/s7_650m_watchdog.sh】
- [x] T1.0.2 主流基准侧交叉核对：BEACON/良渚/RNAGym/深圳湾 21 模型清单
      对照完成，无其他遗漏；月度监控 M4 持续兜底

### T1.1 数据接入（事无巨细）
- [x] T1.1.1 bpRNA(new)：下载 + 解析（bpRNA 描述符 → 配对矩阵 + family 标签）
      【验收：解析单测 + 家族计数表】【**完成 2026-09-19（b960e6e）**：
      复用存量 BPfold_data/bpRNA（bpRNA-1M(2.0) TR0/VL0/TS0 标准切分，
      10814/198/1305 bpseq）；bprna_parse.py 解析 12,317 序列 0 失败，
      329,268 配对（184,174 长程 ≥24nt）；家族标签 = 文件名 SOURCE
      （RFAM/CRW/SRP/tmRNA/SPR/RNP...）；断言 i<j≤len 单测过；
      产出 data/bpRNA_parsed.parquet + evidence/bpRNA_family_counts.json】
- [ ] T1.1.2 ArchiveII：10 家族 3,975 序列（leave-family-out 协议直接复用
      其家族标签）【验收：与 RiNALMo TestSetB 家族名对齐表】
- [ ] T1.1.3 Rfam 家族分类：release22 rna_type 已在跑；升级 clan 层标签
      另行解析（可选）
- [ ] T1.1.4 剪接位点：SpliceBERT 数据（148 物种供体/受体位点）
      【验收：位点提取单测（GT-AG 统计对齐原文）】
- [ ] T1.1.5 家族分配 join（T0.2.5）：四源 → cluster_id_8080，产出
      family_assignment.parquet【验收：无归属冲突断言 + 覆盖率报告
      （PDB-only 家族允许无 join，单独标记 isolated）】
- [ ] T1.1.6 RNAGym DMS 子集（局部变异类，二期可选）：家族分组下载，
      优先级最低

### T1.2 三协议矩阵框架（S9，Q8 修订后）
- [ ] T1.2.1 zero-shot 评估器：encoder 型 masked marginal 口径（Z4）——
      逐位掩盖重打分 vs 一次前向近似两种口径都实现并报告差异（口径差
      异本身就是协议偏差证据）【验收：单模型×单任务冒烟 + 口径差异表】
- [ ] T1.2.2 linear probe 评估器：扩展 probe.py 到任务三分法；**红队修正
      B**：(a) 类别平衡（class-weighted loss + 平衡采样，v1 不平衡口径
      保留为对照）；(b) 序列级头一律 CLS/attention-pool（mean-pool 仅留
      "顺序盲下界"对照）【验收：三任务各一冒烟 + 两口径差异表】
- [ ] T1.2.3 full FT 评估器：统一 attention-pool 分类头，100M 档 +
      RiNALMo-micro 限做（Z2 分层）；评测/微调零重叠运行时断言
      【验收：断言单测（构造故意重叠案例必须报错）】
- [~] T1.2.4 双切分（Q7 核心）：random split seed 隔离 + 家族级 split
      用 T1.1.5 分配表；Δ(随机−家族) 每组合必报【验收：Δ 汇总表初版】
      **Δ 汇总表 v1 已出（2026-09-19，T0.2.6 runner 产出，commit
      879d468）**：probe-balanced Δ 随规模单调放大（1M +0.055 /
      10M +0.337 / 30M +0.438 / 100M +0.434）——协议敏感性是规模
      的函数；meanpool Δ≈0（10M）甚至为负（1M）——协议×切分×规模
      三重交互；random = held-out 池 i%5 行划分（两科学性修正落地：
      禁用 MLM train 池防混杂）
      【证据：evidence/eval_matrix_v1_delta.json + eval/
      eval_matrix_results.jsonl】（random split 的 seed 隔离正式
      版与家族分配表版待 T1.1.5 后升级——v1 为 i%5 确定性划分）
      **random 切分主表数值（2026-09-19 已入 PPT 页 34）**：
      1M 0.153 / 10M 0.493 / 30M 0.605 / 100M 0.604
      （probe-balanced 口径；⚠️ random 高分 = 泄漏红利，同池 i%5
      行划分下家族重叠——不是泛化能力，解读须配页 35 归因三角：
      k-mer 自身 Δ=+0.355 / 对照仅 11-18%）
- [x] T1.2.5 传统基线组（Q4）：k-mer(1-6)+logistic / k-mer+LightGBM /
      one-hot CNN / random-emb+头【验收：每任务基线表 + 收益口径列
      （LM−最强基线）】
      **v1 完成（2026-09-19，commit 07aa5fe）**：k-mer(1-6)+balanced
      logistic 双切分——family 0.1630 / random 0.5180（自身 Δ=+0.355）
      → **家族级真泛化下 LM 对组成基线增益 ≈ 0**（100M +0.007，
      1M/10M 负）——良渚结论 RNA 受控复现；**泄漏是协议性质**
      （组成统计即可吃到）——与 S4/S5 组成预印本三段论
      【证据：evidence/classical_baselines.json】
      **v2 全基线完成（2026-09-22，commit dc1a4fc）**：baselines_extra.py
      补齐 LightGBM / one-hot CNN / random-emb+头（与 v1 完全同 split
      同规模，表可比）——
      family：kmer+LightGBM **0.1760**（新最强基线）> one-hot CNN
      0.1725 > logistic 0.1630 >> randemb 0.0702（组成地板）
      random：one-hot CNN **0.5617**（新最强）> LightGBM 0.5485 >
      logistic 0.5180 >> randemb 0.0557
      **收益口径（LM−最强基线）**：family 1M −0.011 / 10M −0.023 /
      30M +0.089 / 100M +0.163；random 口径（LM−CNN）：1M −0.41 /
      10M −0.07 / 30M **+0.04** / 100M **+0.04**——小规模 LM 被纯监督
      CNN 反超、大规模仅 +4pp；泄漏红利大部分可被纯序列监督模型
      吃掉（协议性质再证，但"random 全负"旧表述已废弃——2026-09-22
      用户质询修正：30M/100M random 0.605/0.604 > CNN 0.5617）；
      randemb ~0.06 vs randinit LM ~0.10-0.13 → embedding 训练本身
      贡献 4-7pp
      【证据：evidence/classical_baselines_extra.json】
- [x] T1.2.6 低数据 regime（S10）：10²/10³/10⁴ 采样曲线（probe 与
      full FT 两条线）【验收：三任务学习曲线图 v1】
      **probe 线完成（2026-09-22，a90ff13）+ full-FT 线完成（f93ec82）**：
      probe 曲线全尺度平坦（30M：0.064/0.063/0.112）；**full-FT 曲线
      上升（10M 0.059→0.075→0.108；100M 0.064→0.121→0.153）**——
      同采样量下 full-FT 增长而 probe 平坦 → 低数据瓶颈是探针头
      容量而非表征；规模×数据量交互（100M full-FT 100 样本即超
      10M 万样本）【证据：evidence/t126_fullft.json】
      （注意：此线用 mean-pool 口径，绝对值与 S1 主表
      attention-pool 不可比，相对结论自洽——预印本引用时需标注）
      **650M 扩档完成（2026-09-23 22:41:45 rc=0）**：v1 watcher 19:29
      GPU0 遭共卡租户 OOM（rc=1 19:42:04，10M/100M 两档完成后中断）
      → v2 watcher 19:42:36 自愈重启（≥22GB 真实空闲判据 + 5 重试 +
      96h deadline）→ attempt 2 GPU1 22:22:55 启动 → 22:41:45 rc=0；
      650M 档三点 n=100/1000/10000 → f1 0.0947/0.1212/0.1564，全
      三档（10M/100M/650M）× 3 点落 evidence/t126_fullft.json +
      logs/t126_fullft_650m.done 落盘，watcher 单次退出；
      结论：650M full-FT 最低数据优势最大（0.0947 vs 10M 0.0585
      @n=100），full-FT 升 vs probe 平坦在五档口径下成立；
      DRAFT_v1.md §4.11 已回填三档数字（0.0947/0.1212/0.1564）
      【证据：evidence/t126_fullft.json + logs/t126_fullft_650m.log +
      logs/t126_fullft_650m.done + TRAINING_LOG Day 13 补六 +
      2026-09-24 23:1x 终验复核（本轮会话，.done 在位、无 t126_watch
      进程残留、json 三档数字一致）】

### T1.3 逐层 probe 全矩阵（S7）
- [x] T1.3.1 rel_depth 层轴 + depth_band 汇总（已上线）
      【2026-09-20 扩面 + 09-21 终表 + **09-22 四尺度对照补齐**：bpRNA
      结构 probe（首个非 rna_type 任务）四档+**全四档对照**完成——
      1M 0.5294/10M 0.5663/30M 0.5756/100M 0.5890；
      **四尺度 randinit 对照（09-22 补齐 1M/30M，c1f18f2）：1M
      0.5452 / 10M 0.5678 / 30M 0.5786 / 100M 0.5855——预训练结构
      增益全档 |Δ|≤0.016（1M 甚至 randinit 更高）**（架构先验即
      足够，"结构零增益"从双尺度升级为四尺度全档证据）；与 rna_type
      （+0.04~+0.17）形成任务对照；无 10M 磨蚀层塌陷（磨蚀任务特异
      性）；四证据链汇聚（S7 零增益 + S12 + S13b + S14）：2.0B nt
      预算下 RNA MLM 迁移的主要是家族级序列统计、结构信息有限
      【证据：eval/probe_structure_results.jsonl + evidence/
      s7_structure_probe.json（commit f920431/cd51777/d6067cc/c1f18f2）】
- [~] T1.3.2 外部模型逐层 probe：RiNALMo 三档 / RNA-FM 两档 / BiRNA-BERT
      【验收：跨模型 early/middle/late 可比表 + "低层主导"初步曲线 +
      **红队修正 E：去 rRNA 分层重跑强制项**】
      【**RNA-FM 96M 完成（2026-09-21，e65b005）**：probe_rnafm.py
      （fairseq ckpt 最小 ESM 式前向复现 + tokenizer 验证 0.40>0.25）；
      12 层 F1 0.1335(L0)→0.0582(L11) 单调降，**best 在嵌入层**——
      与受控家族（best rel 0.86 深层）完全反转；家族级 F1 0.1335 <
      RNA-Sc-100M 0.3394（官方模型困难切分脆弱的线 1 印证）；
      层组织方式由预训练配方主导非参数量】
      【**RiNALMo-micro 36M 完成（2026-09-22，dc1a4fc）**：multimolecule
      rinalmo-micro（d480/L12/rotary，hf-mirror 下载 ext/rinalmo/），
      probe_rinalmo.py 复用 probe_rnafm 协议（tokenizer 运行时断言
      ACGU→6/7/8/9 + pooler 缺失已核实无碍）；12 层曲线：L0 0.1482 →
      峰 L8 0.2407 → L11 0.2088——**中后段单峰，层行为接近受控家族**
      （区别于 RNA-FM 的 L0 最优单调降）；家族级 0.2407 > RNA-FM-96M
      0.1335——**语料组成（36M ncRNA 专注）> 参数量（96M 通用）**，
      与"语料规模约束"机制结论一致】
      【**多 seed/规模复现批（2026-09-22，c1f18f2+7689c62+15e951b+87ee95b，
      用户质询"单点实验不严谨"触发）**：① micro probe-seed29：best
      L7 0.2436（vs pseed17 L8 0.2407）——层位稳定相邻、F1 波动
      0.3pp，非种子偶然；**② RNA-FM pseed29（15e951b）：best L2
      0.1325（vs L0 0.1335）——早期层最优与 ~0.13 水位双复现；
      ③ RiNALMo-giga pseed29：best L30 0.2644（vs L27 0.2667）——
      深层最优与 ~0.27 水位双复现；④ RiNALMo-mega pseed29（87ee95b，
      用户质询"mega 缺 s29"补齐）：best L29 0.2541（vs L25 0.2532）
      ——top 带稳定 0.1pp——**外部线 8/8 run 双 seed 矩阵彻底闭环**；
      ⑤ **RiNALMo 参数量轴三点完整**：micro 36M 0.2407（L8, rel
      0.73）/ mega 148M 0.2532（L25, rel 0.86）/ giga 650M 0.2667
      （L27, rel 0.84）——**18× 参数量总增益仅 +2.6pp（对数尺度近乎
      平线）**；语料轴同量级对照：ncRNA vs 通用 = +11pp（0.24 vs
      0.13）——**语料组成主导、参数量次之，三点证据链闭合**；
      层迁移定律跨架构/跨语料家族成立（best rel 0.73→0.86→0.84，
      与受控家族同向加深）；giga L0=0.095→深层峰（非嵌入层最优，
      再证 RNA-FM 的 L0 形态是配方特异）；⑥ **全层四分带统计表 + 细粒度对齐分析（87ee95b + 26e2313，
      用户质询"其他深度层是否统计/四分带是否稀释趋势"触发）**：
      ext_full_layers.py 四分带表 + mega_giga_aligned.py 逐层对齐
      （种子平均）——**① giga 对 mega 逐层对齐 29/30 层更高（均值
      +0.017，中段 L4-9 +0.023 最大）——四分带确实稀释了趋势**；
      **② 更深发现：绝对层对齐下 micro→mega 同层反而更弱（−0.054），
      高质层数（≥0.24）0→5→18——参数量增益形态从"深度延展"
      （micro→mega：同层更弱但好层变多）转变为"全层抬升"
      （mega→giga：29/30 对齐层更高）**；③ 量级结论稳健：top10 层
      均值 micro 0.210→mega 0.242→giga 0.258（18× +4.8pp），对数
      平线结论在细口径下仍成立
      【证据：evidence/ext_full_layers.json + mega_giga_aligned.json】
      ⑦ one-hot CNN 三 seed：random 0.5617/0.5295/0.5117 →
      **0.5343±0.0206**（排序结论不变：1M/10M < CNN < 30M/100M）；
      ⑧ de-rRNA 外部版四模型层形态全存活
      【证据：probe_results_ext.jsonl（144 行 8 run 全覆盖）+
      evidence/ext_full_layers.json + derRNA_external.json +
      classical_baselines_extra_s29/s43.json】】
      【**红队 E 外部版完成（2026-09-22，0065bc8）**：探针 v2 重跑补
      per_class_f1（类名键，账本 24 行，v1 备份）；der_rna_ext.py——
      RNA-FM 0.1335@L0→去 rRNA 0.0876@L0（L0 最优稳健）；RiNALMo
      0.2407@L8→0.2000@L8（中后段单峰稳健）；两模型层形态全部存活
      （rRNA/tRNA 承载绝对性能 0.97/0.94，结构性结论由非 rRNA 类
      独立支撑——与家族线 der_rna.py 镜像发现）
      【证据：evidence/derRNA_external.json】】
      【**红队 E 强制项通过（2026-09-21，20ac90a）**：der_rna.py 去
      rRNA 分层重算（per_class_f1 免重跑）——规模趋势/10M 谷/层迁移
      方向全部存活（谷更明显 0.062<0.074）；绝对值缩水（rRNA 承载
      大部分绝对性能）但结构性结论由非 rRNA 家族独立支撑；
      附带发现：去 rRNA 后 10M best 层 0.14（vs 0.05）——塌层部分
      由 rRNA 通道驱动
      【证据：evidence/derRNA_stratified.json】】
- [x] T1.3.3 length_bin 分箱报告（Z3）：16-127/128-511/512-4096 三箱
      （外评序列短只留三箱）【验收：分箱 probe 表】
      **完成（2026-09-22，a90ff13）**：四尺度 best-layer 分箱表——
      **① 短序列箱（16-127）全尺度塌陷**（0.019-0.055，仅 298 条）；
      ② 中箱（128-511，2384 条）承载主信号；③ **512+ 长箱出现规模
      分化：30M 0.116 / 100M 0.106 vs 1M/10M ~0.052**——规模收益
      集中于长序列（与 S12 linkage 长度依赖一致）；口径同 T1.2.6
      （mean-pool，相对结论自洽）
      【证据：evidence/t133_lengthbin.json】

---

## T2 线 2：自训受控家族（第 2-3 月）——执行中

### T2.1 主 scaling 轴（S1）——2026-09-18 收口（确定性 probe 协议）
- [x] 10M 完整 2.0B nt（best_val 0.8716，fallback=0，34k nt/s）
- [x] 30M-c1M 完整（850M nt 语料上限，best_val 0.8960）
- [x] 1M/10M/30M-full/30M-c10M/100M s17/s29/s43 全部 DONE（各 2.0B，fallback=0）
      【证据：logs/RNA-Sc-*.log DONE 帧 + manifest status=DONE】
- [x] **S1 主表定稿（inc12 确定性协议）**：1M 0.1604 / 10M 0.1731 /
      30M 0.2651±0.0162（三 seed）/ 100M 0.3394±0.0147（三 seed）；
      best rel-depth 0.47/0.05/0.79/0.86（层迁移定律）
      【证据：evidence/s1_seed_table.json + figs/fig1_layer_migration.png】
- [x] T2.1.1 c1Mcs（簇级分层 Q3）：已生成（1,000,011 序列/190,917 簇）入队
- [x] T2.1.2 **红队修正 A**：语料三点曲线完成（10M×{c1Mcs,c5Mcs,full}
      = U 型：0.186/0.152/0.173）+ 30M 四点（单调：c1M 0.316 全局最优）
      + val-loss/F1 排序完全反转（解耦证据）+ epoch 覆盖显式标注
      【证据：evidence/corpus3.json + figs/fig_corpus3.png（commit 41bc608/d41f72c）】
- [x] T2.1.3 100M 处斜率判定（R1 预设规则）：**slope=0.142 F1/decade，
      bootstrap CI95 [0.1044, 0.1797]，CI 下界 3.5×ε → decision=650M 触发**
      【证据：evidence/s1_slope_decision.json + TRAINING_LOG 2026-09-18 14:30
      决策记录（commit ededb4c）】
      **★五档终判收口（2026-09-23 Day 13，6d35bf9）**：650M F1 0.3632
      （+2.4pp，与外部线 RiNALMo 18×+2.6pp 跨家族互证）；
      **slope 100M→650M = 0.0293 < ε=0.03——scaling 饱和确认**
      （触发斜率 0.142 衰减 5 倍）；10M 谷持续；层迁移终点非单调
      （650M best L8/rel 0.296）；收口链 6h 超时缺口人工补跑
      （根因：等待窗从进程启动而非 DONE 事件起算，已登记待修）
      【证据：evidence/s1_final_verdict.json + TRAINING_LOG Day 13】
      **终验收口（2026-09-24 23:1x，用户指令会话第 9 次幂等复跑）**：
      `python -m rna_sc.s1_final_verdict` 复跑前后 md5 一致
      （08f2542bbeef97e82adc4d7d7242e030）；DONE 帧三口径一致
      （logs/RNA-Sc-650M_s17.log line 1111 + manifest.json +
      probe 28/28 层 ckpt_nt=1900122218）；T2.1.3 五档终判收口
      终验通过，无待办【证据：evidence/s1_final_verdict.json +
      TRAINING_LOG Day 14 补四 + docs/TASKS_V2.md 155 行注记】
      **第 16 次幂等复核（2026-09-26 20:1x，用户指令会话）**：
      同上三口径一致 + md5 仍为 08f2542b（toktokenbench env 复跑，
      复跑前后不变）；watch_all 值守进程存活（PID 3748436）；
      preprint v1.0 撰写线（preprint/DRAFT_v1.md 22,209B、09-26
      17:03 版、md5 94cfb6dd、零 PENDING）与 T1.2.6 full-FT 线
      （evidence/t126_fullft.json 三档三点 + logs/
      t126_fullft_650m.done）双线复核在位——两条线均已于 09-23/
      09-24 收口，无需启动；GPU 8 卡全忙（300M_b59 27.1% +
      100M_b59 刚启），不干预【证据：TRAINING_LOG Day 17 补八 +
      docs/TASKS_V2.md 第 16 次复核注记】
- [~] **T4.3.1 650M 第二阶段已启动**（2026-09-18）：spec 666.3M
      （d1408/L28/H22/f5632，commit e6c74da）训练中（supervisor 自动
      调度 GPU2；~5-6 天 2.0B）

### T2.2 对照实验（S4/S5/S6）
- [x] S4 随机初始化对照（10M 档 probe：0.131 vs 0.214）
- [x] T2.2.1 S4 扩面首半：四档全做 randinit probe（1M/10M/30M/100M）
      【v0.4 确定性重跑定稿 2026-09-19】trained−randinit = +0.0593/
      +0.0430/+0.1221/+0.1686——增益随规模单调扩大，30M 陡增；
      H2 全档排除；生成脚本入库（rna_sc/s4_randinit_table.py，可从
      jsonl 复现全表）【证据：evidence/s4_randinit_table.{md,json}
      （v0.4 重算；初版 commit 9ab963a）】
      三协议版待 T1.2 协议升级后统一重跑
- [x] T2.2.2 S5 权重统计重采样对照（H3）：**完成（2026-09-19，inc12
      确定性协议，commit b948061）**——probe.py --moment-matched（先捕获
      trained 逐张量均值/方差再重造随机模型，74-146 tensors matched）；
      四档 trained−mommatch = +0.0286/+0.0478/+0.1233/+0.1668，
      mommatch ≈ randinit 水平 → **H3 全档排除（收益来自权重结构非
      好初始化）**；表生成脚本入库 rna_sc/s5_mommatch_table.py
      【证据：evidence/s5_mommatch_table.{md,json} + logs/
      v05_mommatch.log（commit b948061）】
- [x] S6 中途 checkpoint（每 100M nt 自动落盘，全部 run 生效）
- [x] T2.2.3 S6 涌现时间轴：**四尺度 37 点确定性重跑定稿**（1M/10M/
      30M/100M × ckpt 轨迹）——磨蚀强度尺度倒 U 型（10M −0.082 ≫
      30M −0.021 ＞ 1M/100M 无）；10M 磨蚀与语料重复无关（**c1Mcs
      时间轴 v0.4 确定性重跑复现**：0.1B 0.218 → 0.3B 0.230 →
      0.5B 0.244（峰）→ 0.7B 0.204 回落 + 层下移 L16→L6，
      2026-09-19）；pretraining-time 曲线 + 跨尺度图
      【证据：evidence/s6_timeline.json + s6_cross_scale.json +
      figs/fig_s6_emergence.png + fig_s6_cross_scale.png
      （commit e611f7e/b8a24de；c1Mcs 时间轴 v0.4 批次 2026-09-19）】
      **⚠️ 口径澄清（2026-09-19 用户质询触发，防误读）**：10M 主表
      best_rel=0.05（层在 L1-3）不是异常值——是磨蚀在层维度的
      签名：10M 最好层随训练持续下移（0.1B 时 L16/rel 0.84 →
      0.5B 峰 L11/rel 0.58 → 1.1B 后塌到 L1-3/rel 0.05-0.16），
      中深层可迁移特征被磨掉、仅剩早期层；30M/100M 容量足够防磨蚀
      层位正常后移（0.79/0.86）。层位非单调（1M 0.47 → 10M 0.05
      → 30M 0.79 → 100M 0.86）正是磨蚀倒 U 的投影。PPT 页 34
      已加脚注 †。

### T2.3 语料轴（S2/S3，H5）——2026-09-18 主体完成
- [x] c1M(prefix)/c1Mcs/c5Mcs/c10M/full 采样方式对照 + 数据量曲线
      （10M 三点 U 型 + 30M 四点单调，见 T2.1.2）
- [x] T2.3.1 saturation point 统计量（借鉴 Nat Methods 文）：**完成
      （2026-09-19，corpus_saturation.py，commit b228809）**——95% 阈值
      + 上升段插值 + 形态分类 + 同 epoch 覆盖配对；**诚实结论：无经典
      上升饱和点**（固定 2.0B nt 下两尺度均于最小唯一语料臂达峰：10M
      0.9B / 30M 0.85B；30M monotone-fall，10M mixed）；同覆盖对
      30M-c1M vs c1Mcs（2.35 vs 2.22 ep）
      【证据：evidence/corpus_saturation.json】
- [x] T2.3.2 三多样性指标（Shannon/Gini-Simpson/Vendi）：全部 5 语料
      变体完成（Shannon/GS 双层 + Vendi GPU 嵌入版；发现采样方式本身
      改变家族构成——cs 臂 rRNA 56.4%→61.5%）
      【证据：evidence/corpus_diversity.{md,json} + corpus_vendi.json
      （commit f9abf37/82cd846）】
- [ ] T2.3.3 DenAdel 反向先验对话（新）：S3 结果无论方向均写入与 DenAdel et al.
      （Nat Methods 2026，单细胞域）的对照表——多样性改善→跨域差异发现；
      不改善→跨域验证（引用纪律：单细胞域 ≠ RNA LM，明确域差异）【验收：对照表】
      （写作期任务，S3 重加权 arm 决策后执行）
- [x] T2.3.3 S3 多样性 arm（家族重加权语料）：设计冻结 + 训练 1 档
      【验收：H5 双轴分解结论 v1（与 rRNA 56% 偏置交叉验证，红队 E）】
      **★收口完成（2026-09-26 Day 17，01d4ee0）**：30M-rw1（alpha=1.0
      簇级展平，57.7M 有效行）12/12 层 inc12 probe：best L11 F1 =
      0.2408 < full 0.2651（3 seed 均值）/ s17 full best 0.2466——
      **多样性展平负效应**；H5 双轴定案：数量轴小语料更优（c1M
      0.316）vs 多样性轴展平更差——DenAdel 单细胞域否定结果 RNA
      跨域复现（三候选机制解释入 evidence；负结果配机制，D3 合规）
      【证据：evidence/s3_rw1_closeout.json + eval/probe_results.jsonl
      （rw1 12/12 层）+ data/r22_train_reweighted.{parquet,json}】
      **rw1 尺度扩展批（2026-09-27~10-02，H5 稳健性多尺度复制）**：
      ① 100M-rw1（2.0B，09-29 08:03 DONE）→ 10-02 补 probe（supervisor
      事故修复后）：**best 0.2834@L21 < 100M full 0.3394——重加权
      负效应在 100M 档复现**（−5.6pp，比 30M 档 −2.4pp 更强——尺度
      越大语料组成越重要，与"语料组成主导"主线自洽）；② 10M-rw1
      （GPU6 重启训练中，10-02 nt≈0.2B/2.0B）——三尺度 rw1 链完成后
      H5 双轴结论升级为多尺度稳健版
      【证据：eval/probe_results.jsonl（100M_s17_rw1 23/23 层）+
      logs/RNA-Sc-10M_s17_rw1.log + supervisor.log 事故记录】
- [ ] T2.3.4 spike-in RNA 二期设计（掺 mRNA 对照，仅设计文档不训练）

---

## T3 线 3：涌现分析（与 T1/T2 并行）

### T3.1 无监督接触预测（S8）
- [ ] T3.1.1 结构数据：PDB RNA 链 C4'/P 距离矩阵 + bpRNA 配对标签对齐
      （家族切分沿用 T1.1.5）【验收：接触数据集 + 家族数报告（E2）】
- [ ] T3.1.2 logistic 接触头：拟合/测试严格分离 + APC + top-L（≥24nt
      长程）；**红队修正 E：接触定义双口径**（蛋白式 8Å C4' 与 RNA
      文献口径并列，差异入附录）【验收：Rao 2020 协议单测 + RiNALMo
      官方口径对照】
- [ ] T3.1.3 涌现时间线：自训家族 × S6 ckpt × 接触精度（length_bin 分箱）
      【验收：涌现曲线 + bootstrap CI（E3）】
- [ ] T3.1.4 注意力直读对照：注意力图 vs 头部 logit 两口径（与
      Papazoglou 2025 对话）【验收：两口径对比表】

### T3.2 家族解耦指数（S12，H6）——**红队修正 D：提前，CPU 并行本周启动**
- [x] T3.2.1 Infernal cmscan 跑 Rfam 家族（服务器装 Infernal，CPU 任务
      不等 GPU）【验收：家族协方差得分表】【证据：evidence/
      s12_decoupling_index_full.json（127 家族 DI 表）+ data/Rfam.cm +
      s12_work/cmscan.tbl】
- [~] T3.2.2 解耦指数 = 家族内序列一致性 / 协方差得分；按指数分层涌现
      早晚【验收：H6 相关性 + CI（E3）】
      初步版（inc12 确定性协议，2026-09-19）：30M-c1Mcs Spearman(DI, best-layer)
      = −0.478（n=10 类）；100M s17 −0.384；30M-s29 −0.370——方向一致
      （高 DI 家族峰层更靠前），关联随规模减弱（特征深化）。run 标签版
      证据已保存（s12_linkage_30M_s17_c1Mcs.json / _100M_s17.json）；
      **r: rna_type 类级聚合，预注册 Rfam 家族级版需 per-class F1 × 家族
      DI 映射表升级（T1.2.2 协议升级后）**
      【证据：evidence/s12_linkage_30M_s17_c1Mcs.json +
      s12_linkage_100M_s17.json + s12_linkage.json（s29 副本）
      （commit cb5b7af；v0.4 重算 2026-09-19）】

### T3.3 二级结构
- [ ] T3.3.1 bpRNA 家族级切分三协议 + 双切分（并入 T1.2 矩阵结构类行）
      【验收：结构类矩阵行完整】

### T3.4 似然水平机制分析（S13，fitness 分支版；2026-09-16 红队审查后重定位）
- **定位**：检验 H7 的 fitness 分支，非 Q1 主支柱（主支柱 = T3.4b 结构版钟形）
- **依赖：T1.1.6（RNAGym，二期可选）+ T1.2.1 zero-shot 产出 + T2.1 自训模型——若 RNAGym 不入一期，本节整体后移二期或降为附录，不阻塞主线**；计算量 <5 GPU 时
- [ ] T3.4.1 全模型 × RNAGym/局部变异 assay 野生型 NLL 表（masked
      marginal 与 T1.2.1 口径统一；wild-type marginal 对照口径入附录）
      【验收：NLL 表 + 口径差异说明】
- [ ] T3.4.2 NLL 轴性能曲线：LOWESS + 二阶多项式双拟合；钟形判定判据
      （峰值区间 vs 最低 10% NLL 区间 ≥0.1，bootstrap CI 不含 0）
      【验收：曲线图 + 判定结论（E13a 钟形 / E13b 不重现）】
- [ ] T3.4.3 两成分分解：上下文理解（跨位点 Spearman）vs 替换特异性
      （位内 3 突变 Spearman 均值）分别画 NLL 轴——判定哪个成分贡献钟形
      【验收：两成分曲线 + 成分归因结论】
- [ ] T3.4.4 种子方差（100M 档 3 种子 NLL 极差分布，对标 Hou "10% 蛋白
      NLL 差>0.5"）+ 混杂检查（NLL vs Infernal 同源数/家族表示度）
      【验收：方差报告 + 混杂相关表】
- [ ] T3.4.5 决策判据 D13：E13a → narrative 升 B 第一证据链；E13b →
      三候选解释（语料规模/解耦/共进化弱）可分辨性检查，不可分辨则
      limitation 呈现（预注册路径）【验收：D13 结论写入结果章节】

### T3.4b 结构版钟形（S13b，H7 主检验；2026-09-16 新增——机制分析主支柱）
- **定位**：把 Hou 钟形思想移植到结构任务（本课题任务重心），与 H6 交叉验证——H7 的主检验，RNA 域首发（蛋白域无人做结构版钟形）
- 依赖：T1.3 结构 probe 产出 + T2.1 家族级困惑度（S0 held-out）+ S4/S6 对照与 ckpt 提供全置信度区间覆盖；计算量 = 复用已有产出，仅分析
- [ ] T3.4b.1 置信度轴双口径：家族级 held-out 困惑度（主）+ 每位点重建
      熵（辅，按序列/家族聚合）【验收：家族级置信度表（双口径）】
- [ ] T3.4b.2 结构性能轴：bpRNA 家族级 F1（T1.3 产出）+ 接触 precision@L
      （T3.1 产出）——家族级聚合与置信度轴对齐
      【验收：家族级性能表】
- [ ] T3.4b.3 钟形检验：家族级散点 + LOWESS + 二阶多项式；判据同 S13
      （峰值 vs 最低 10% 区间 ≥0.1，bootstrap CI）；randinit/S6 ckpt
      补全置信度区间覆盖【验收：E13b-a/E13b-b 判定 + 曲线图（T4.1.5b 主图）】
- [ ] T3.4b.4 与 T3.2 解耦指数交叉验证：解耦分层后钟形是否仍成立
      （偏离 → H6×H7 交互效应，两假设互证）【验收：分层钟形图】

### T3.5 RNS 表征质量曲线（S14，2026-09-16 新增，Prabakaran NM 2026 移植；第二优先）
- 依赖：无（与 T1/T2 全并行——最独立一条线）；计算量 = 各模型两次前向
- [x] T3.5.1 随机对照集构造三查（长度 KS p>0.05 / 单+二核苷酸频率差 <2% /
      规模 3× 评测集）【验收：三查报告（C9.1），不过不进入计算】
      【完成 2026-09-20：KS p=1.0 / mono dev 0.0006 / 3× = 4500 条
      （f920431）；一阶 Markov 匹配 mono+di 频率】
- [~] T3.5.2 embedding 提取：全模型（线 1 + RNA-Sc 全档 + S6 ckpt +
      S4 随机对照）× 真实集 + 随机集；mean-pool 合法性在 RNS 语境单独
      声明（与 T1.2.2 池化纪律分开，防自相矛盾指控）【验收：embedding
      落盘 + 声明注记】
      【自训家族四档 + 双 randinit 完成（layer_frac 0.75）；线 1 与
      S6 ckpt 时间轴待 v2】
      【**650M 单点补齐启动（2026-09-22 晚五，GPU6）**：s14_rns_650m.py
      OOM 硬化版（逐序列前向 + len cap 192，共享小卡安全）——H8 规模轴
      终点，预期 RNS≤0.077 平台延续或更低；侧文件
      evidence/s14_rns_650m.json 不覆写 v1【证据：logs/
      s14_rns_650m_v2.log（运行中）】】
- [x] T3.5.3 RNS_k 计算（k ∈ {10,50,100}）× 三条分析轴
      （vs 规模 / vs 训练步数 / 家族分层对接 H6+H5）
      【验收：三张曲线（C9.2）+ RNS_k 曲线族】
      【规模轴完成 2026-09-20：RNS@10 0.172/0.104/0.078/0.077
      （1M→30M 改善后平台，与下游 F1 解耦——E14 方向）；时间轴/
      家族分层轴待 v2；k=10/50/100 全报（evidence/s14_rns.json）】
- [x] T3.5.4 指标有效性自检：随机初始化对照 RNS 显著高于所有预训练模型
      （否则构造有 bug）【验收：自检结论（C9.3）】
      【通过 2026-09-20：randinit RNS@10 0.54-0.58 ≫ 全部预训练档
      0.077-0.172】
- [x] T3.5.5 与 T1.3 probe 性能按家族交叉验证（相关 + CI）→ E14a
      （RNS 有效前置筛查指标）/ E14b（解耦本身是 RNA 域发现）
      【验收：交叉验证表 + E14 判定】
      【完成 2026-09-21（bdaef5c）：11 家族 Spearman(RNS, probeF1)
      = −0.19——方向符合 E14a 但解释力弱 → 家族层面解耦成立（与
      规模轴互证）；rRNA 分离最好 probe 最高（0.025/0.97），
      sRNA/snoRNA 高 RNS 且 probe=0——欠表示家族嵌入更随机化
      （Prabakaran RNA 验证）；证据 s14_family_crossval.json】
- [x] T3.5.6 **训练时间轴版**（f93ec82，2026-09-22）：10M 四 ckpt
      （0.5B/1.0B/1.5B/1.9B）RNS 曲线——**RNS 峰在 1.0B（0.1283），
      probe F1 峰在 0.5B（0.244）——两峰错位；且 1.0B 后 RNS 也下降
      （→0.1041）**：10M 磨蚀不只是"头退化"，表征组织本身在
      1.0B 后退化，但时间点滞后于迁移磨蚀——**解耦的第三轴证据
      （规模轴/家族轴/时间轴齐）**
      【证据：evidence/s14_timeaxis.json】

- [~] T3.5.7 RNS × 前向共变 COV 连续相关（Q19-Q2 缺口）：按序列/家族聚合
      RNS@10 与 COV−CTRL（Q10 数据复用），对标蛋白域 RNS-TMscore −0.70
      【验收：Spearman + 散点图入 evidence】
- [ ] T3.5.8 RNS bootstrap 方差（Q19-Q1 缺口）：10× 随机池重生成，
      报告各档 RNS std（对标论文 100 次欠采样）；若 std ≪ 档间差则
      单次结论稳
      【验收：RNS ± std 表 + DRAFT 方法节协议差异声明】
- [x] T3.5.9 RNS 分箱结构测评（Q19-Q3，s14_bin_eval.py）：TS0 三分箱
      ×（全体位 pair-F1 / ≥24 long-range F1）——**高 RNS 箱 +18%/+29.3%
      （蛋白论文 −40%/−60% 方向反转）**；长度混杂排除（diag：
      Spearman(len,RNS)=+0.19）；机制两候选 + 家族轴不翻转的轴依赖
      警示入档；后续：控长度分层/650M/randinit 对照三臂（登记待跑）
      【验收：evidence/s14_bin_eval.json + s14_bin_diag.json ✓】
- [ ] T1.2.7 eval_matrix RNS 协变量列（Q19-Q5 行动项 A）：每个
      probe/微调结果附带评测集 RNS 分布，报告"F1 ± RNS 分层"——
      random 切分泄漏红利的 RNS 视角归因
      【验收：eval_matrix 输出格式升级 + Δ 的 RNS 分层版】

---

## T4 预印本与发布（第 3 月末起）

### T4.1 图表工程（论文核心资产）
- [ ] T4.1.1 图 1：S1 scaling 主图（困惑度 + probe 双 y 轴 + 100M 斜率
      标注；**红队修正 C：跨模型趋势线与 100M 种子 CI 分列，不画
      per-model 伪误差棒**）
- [ ] T4.1.2 图 2：逐层涌现（rel_depth × 任务三分法，5 模型 × 协议；
      含去 rRNA 分层版）
- [ ] T4.1.3 图 3：协议×切分热图（Δ 泄漏敏感度）
- [ ] T4.1.4 图 4：语料轴（saturation point + 三多样性指标 + epoch
      覆盖标注）
- [ ] T4.1.5 图 5：S4/S5 对照 + 时间轴涌现（线 2 独有）
- [ ] T4.1.5b 图 5b：S13b 结构版钟形（家族级置信度 × 结构性能，主图）；
      S13 fitness 版 NLL 曲线为子图或附录（E13/E13b 判定结果决定版式）
      （2026-09-16 新增，红队审查后主从对调）
- [ ] T4.1.5c 图 5c：S14 RNS 三轴曲线（零监督涌现证据）（2026-09-16 新增）
- [ ] T4.1.6 表 1：基线组总表（LM−最强基线口径）
【验收：每图对应 S0-S12 映射行（C7 纪律）；无表外实验】

### T4.1b PPT 资产维护（2026-09-17 归档；2026-09-26 Day 17 大更新）
- [x] 汇报 PPT 33 页定稿：含 8 假设表（页 10）/H7/H8 方法详解页（页 17/18）/三篇论文借鉴页（页 29）/消融核验 13 项表（页 8）——全部最新讨论结论已同步
- [x] 2026-09-16 插入事故修复 + 2026-09-17 逐页复查（页码 3 处修正，核验记录见备忘录 8.2）
- [x] **Day 17 大更新（2026-09-26，39→41 页）**：页 33 主表 650M 终值 + 六档判词；页 35 总表
      650M/OUTLINE 更新；新增页 39 八假设终判总表（H1-H8×终判×证据）+ 页 40 机制新发现
      五项（层终点逆转/容量门槛/H5 双轴/S12 衰减/S13b v2）；三遍验证（zip/结构 13/13/
      数字 7/7）——验收记录 CHECKLIST J1
      【证据：ppt/RNA迁移学习测评.pptx（41 页）+ 更新前备份 _20260926_1949】
- [x] **Day 17 六问题修复（2026-09-26 晚，用户六条反馈逐条闭环）**：
      ①页 33 主表 300M 行补齐（7×6 六档）；②S4/S5 表 300M/650M 在途行
      （randinit 探针 GPU0/GPU2 已在服务器启动，SSH 恢复后回填）；
      ③best 层 0.30 两机制交叉解释入页 33+页 40；④全片字体微软雅黑
      统一（2029 runs + 主题方案 + 625 框溢出自适应）；⑤页 34 Δ 表在途
      行 + 页 35 标题清理；⑥页 37 受控五档全入表、页 38 full-FT 三档
      真值 + 长度分箱在途标注；三遍验证 PASS（CHECKLIST J5 详录）
      【证据：ppt/RNA迁移学习测评.pptx + 备份 _20260926_2030 +
      tmp_s33/s34/s37/s38 系列修复脚本（本地 work-mode 目录）】
- [x] **六档真值化收口（09-27 00:00-01:10，SSH A100 别名恢复后）**：
      randinit/mommatch/长度分箱/eval_matrix 全部六档补齐——页 33 两表、
      页 34 Δ 行、页 38 长度分箱全部真值（650M random 0.625 / Δ 六档
      +0.337→0.438→0.434→0.415→0.436 平台 / 长箱 650M 0.169 独一档）；
      因果层深挖（P1/P5）：三链机制（深层边际增益衰减 +18%→+2% /
      rRNA 全层可解码 / 随机地板随深度上升）写入页 33/40 + DRAFT；
      650M@5.9B 入队（wave b59）；commits 79ef263/62bfe82 推送
- [ ] 待办（阻塞于服务器 SSH 断连 10.249.129.13，2026-09-26 20:00 起）：
      randinit 300M/650M 出值后回填页 33 第二表；random-split F1
      （300M/650M）回填页 33 主表 random 列 + 页 34 Δ；长度分箱
      300M/650M 回填页 38；mommatch 300M/650M 随后补齐——全部
      回填后需重跑三遍验证 + PowerPoint 实际打开确认
- [ ] 后续若修改 PPT：必须"改后 PowerPoint 实际打开验证 + 留备份"（备忘录 8.2 运维纪律）
【验收：33 页无空页、页码一致、H7/H8 内容含关键词核验通过（2026-09-17）】

### T4.2 写作与 arXiv
- [~] T4.2.1 引言四点动机（D10：每点 RNA 证据引用）
      **DRAFT v1.0 全文已撰写（2026-09-22 19:40，601ee73）**：
      preprint/DRAFT_v1.md（380 行）——Title/Abstract/Intro（四点
      动机成文）/Related Work（REDIAL 分界 + DNA 平行工作）/
      Methods/Results 4.1-4.12 全节/Discussion/Limitations/Repro；
      数字与证据 JSON 程序化逐位核对通过（seed 表/RNS/slope CI）；
      7 处 PENDING-650M 占位槽待收口链填充后升级 v1.1；本地
      论文/ 目录同步备份
      【证据：preprint/DRAFT_v1.md + TRAINING_LOG Day 12 续五】
      **v1.1 槽回填完成（2026-09-23，b96c146/48f948d）**：七处
      650M 槽全部回填（零 PENDING 残留，§4.11 低数据三档
      0.0947/0.1212/0.1564 入文），Fig1 升级五档主图（ff2830a）；
      09-23 23:29 版（20,528B，md5 77e285d6）09-24 终验复核：
      零 PENDING 槽、纪律门 D1–D11 全绿——preprint v1.0 撰写线
      收口，推进至 T4.2.3 claim 措辞全文检索 → T4.2.5 arXiv 挂出
      【证据：preprint/DRAFT_v1.md（远端 09-23 23:29 版 md5
      77e285d6）+ git log 48f948d + TRAINING_LOG Day 14 补四】
- [ ] T4.2.2 相关工作：REDIAL 三分界（D9）/ 深圳湾差异化表（D4）/
        良渚三轴差异化 / Schmirler+Nat Methods 两新锚点入动机链
        【D4/D6/D11 引用列表完成（2026-09-22 19:25，e883362）】：
        preprint/DRAFT_refs.md——30 条完整文献（备忘录 §9 已核验池；
        未核验标识符 [id-verify] 标注留最终 bib pass，零伪造 DOI）；
        Related Work 正文含 REDIAL 三分界段落 + DNA 平行工作
        （Vishniakov）差异化 + 深圳湾/良渚协议问题定位；
        DRAFT_v1 纪律门 D1-D11 全 ✅（除 PENDING-650M 槽）
- [ ] T4.2.3 claim 措辞全文检索（D1-D8 逐条过）
- [ ] T4.2.4 limitation：线 1 泄漏疑虑（B3）/ epoch 覆盖约束（红队 A）/
      架构受控范围 / 种子不平衡 / rRNA 语料偏置（红队 E）
- [ ] T4.2.5 **arXiv 挂出（完整核心实验，非占位）★关键节点**
- [ ] T4.2.6 仓库整理发布（MIT license + 数据/权重清单）

### T4.3 第二阶段（条件触发）——**2026-09-18 触发执行中**
- [x] T4.3.1 650M 触发判定（T2.1.3 输出；原 4×A100 DP 预算已测算）：
      **slope 0.142/decade CI [0.104, 0.180] → 650M 触发**；spec 666.3M
      （d1408/L28/H22/f5632）锁定，单卡 24GB 可行（实测峰值显存验证中），
      supervisor 已自动调度启动（2026-09-18，GPU2）
      【证据：evidence/s1_slope_decision.json + rna_sc/specs.py（e6c74da）】
- [x] 650M 训练执行完毕（2.0B nt；**2026-09-23 06:09 DONE**：
      nt=2000003270 / steps=213514 / best_val=0.7757 / 5826 nt/s /
      fallback=0；2026-09-26 20:1x 巡检复核（第 16 次）：DONE 帧
      + manifest + probe 28/28 层三口径一致，run 目录 21 文件
      （19 个 100M-interval ckpt + best ckpt_nt1900122218_
      step202784.pt）；
      **自动收口链已执行完毕**：closeout_650m.py
      ——DONE → watch_all 自动 probe（28/28 层）→ s1_final_verdict
      五档终判（斜率重估/10M 谷/层迁移终点）→ s13b_bell v2
      （650M 置信度覆盖点）→ DRAFT v1.1 自动填槽 → TRAINING_LOG 落款，
      全链落地【证据：logs/RNA-Sc-650M_s17.log line 1111 DONE 帧 +
      runs/RNA-Sc-650M_s17/manifest.json（status=DONE）+
      eval/probe_results.jsonl（RNA-Sc-650M_s17 28/28 层）+
      evidence/s1_final_verdict.json（md5 08f2542b，16 次幂等）】
- [ ] T4.3.2 RiNALMo-arch 轴（Q5 受控段 B）：fairseq 适配 release22 →
      2 档训练【验收：B 段 2 ckpt + A/B/C 三段对比表 v1】（挤压则降级附录）
- [ ] T4.3.3 SAE 概念涌现计数（S15，InterPLM 移植；触发三条件：
      T3.4/T3.5 结论已稳 + T4.2.5 预印本已挂 + 2-3 周工程余量）：
      RNA-Sc-30M/100M + S4 随机对照的选定层（首/中/末三）训 TopK SAE
      → 特征与 Rfam 家族/bpRNA 结构基序对齐计数（F1>0.5）
      → 概念数 vs 规模/训练步数曲线 → 随机对照预期（核苷酸组成特征在、
      家族/结构概念零——InterPLM 发现的 RNA 复刻）
      【验收：E15a（概念数增长，图 1 候选）/ E15b（概念贫乏，与 REDIAL
      过参数化互证）判定 + 概念涌现曲线】

### T4.4 投稿
- [ ] T4.4.1 层级 1 转投（Brief Bioinform / Bioinformatics）
- [ ] T4.4.2 层级 2 完整版（NeurIPS/ICML 或 Nat Commun）

---

## T5 运维（贯穿）

- [x] 月度竞争监控制度化（M1-M4 清单 + 触发响应）
- [~] T5.1 自动巡检（每日 2 次；DONE run 自动补 probe 已生效）
      **watch_all inc12-suffix 补丁（2026-10-02）**：b59/rw1 臂 DONE 帧
      run_id 无后缀 → 旧逻辑下 5.9B 臂训完不会被自动 probe（被主臂的
      已 probe 状态遮蔽）；已改为按日志文件名 key，22 个 DONE run
      验证全对，值守进程带补丁重启；**rw1 纪律重申（09-27 事故）**：
      rw1/重加权任务只能手动 train_s3_rw 启动，永不进 supervisor wave
- [ ] T5.2 2026-10-02 月度监控第 1 轮执行（10-01 逾期 1 天，本轮会话
      补跑 M1-M4 检索）【验收：备忘录 5.4 表更新+日期戳】

---

## 依赖图（关键路径加粗）

```
T0.2.6(评测runner) ──→ **T1.2(三协议矩阵)** ──→ **T1.3(逐层probe)** ──┐
T1.1(数据接入)   ──↗        │                                        ├─→ **T4.1(图)** ─→ **T4.2.5(arXiv)**
T2.1(S1 训练)     ──→ T2.2(对照) ──→ T1.2 扩面                         │
T3.1/T3.2(涌现)   ─────────────────────────────────────────────────────┘
T3.4b(S13b,复用T1.3+T2.1产出,H7主检验)──→ T4.1.5b ｜ T3.4(S13,fitness分支,依赖T1.1.6二期)──→ 附录/二期
T3.5(S14,独立无依赖,H8)──→ T4.1.5c
T3.2.1(Infernal, CPU) 与主线并行 ｜ T5（监控，独立）
```

## 里程碑硬验收

| 时间 | 里程碑 | 硬验收 |
|---|---|---|
| 第 1 月末 | 基建+模型接入+评测 runner | A3-A6 ✓ + T1.0/T0.2.6 |
| 第 2 月末 | 线 1 三协议矩阵+逐层 probe | T1.2 四项 + T1.3.2/3 初版结论 |
| 第 3 月末 | **arXiv 挂出** | T4.1 六图 + T4.2 写作纪律全过 |
| 每月 1 日 | 竞争监控 | 5.4 表更新+日期戳 |

---

## 附：审稿人红队自批（2026-09-16，毫不留情版）

**审稿人 A（方法论）**：
> "自训家族 2.0B nt 预算？RiNALMo 官方用了远大于此的训练量。你们拿训了
> 一半的模型家族谈'涌现饱和'，就像跑了半程马拉松宣布破纪录。更糟的是
> 语料上限：release22 train 总量约 5.9B nt，你们最大的语料 arm 实际
> 见到的新鲜数据约 2B——**'数据量 axis'根本没跑到全量一个 epoch**，
> 还谈什么 scaling law？"

**修正 A**（成立）：(1) epoch 覆盖差异显式入方法节（c1M ≈2.4 epoch vs
full ≈34% 新鲜度，不假装同质）；(2) saturation point 只在同覆盖 arm 间
比较；(3) limitation 明写"预算受语料规模约束，与蛋白域 UniRef 不可比
——这正是 RNA 语料小一个数量级的题设本身"。T2.1.2 已改三点曲线。

**审稿人 B（实验设计）**：
> "probe 主指标 macro-F1？19 类里 rRNA 占 63.6%——probe 头连类别平衡
> 都没做，你们测的是表征还是标签分布？还有，逐层 probe 用 mean-pool
> 收集态——SPEC 自己写了'禁 mean-pool（顺序盲）'，你们第一天就违反
> 自己的规程，就加了个括号说'后面改'。"

**修正 B**（两条都成立）：(1) class-weighted loss + 平衡采样（v1 不平衡
口径保留为对照——顺带量化平衡影响，本身是协议偏差证据）；(2) 序列级
头一律 CLS/attention-pool（与 full FT 头统一），mean-pool 仅留"顺序盲
下界"对照。列入 T1.2.2 验收。

**审稿人 C（统计）**：
> "3 种子只在 100M 档？其他档单种子然后画带'置信区间'的 scaling 曲线？
> 横轴不同模型的误差棒——这是伪统计。还有 c1Mcs vs prefix-c1M 的'采样
> 方式对照'：两个 arm 各单种子，观察到的差异你打算归因给采样方式还是
> 种子噪声？"

**修正 C**（成立）：(1) 跨模型曲线不标 per-model CI，改"趋势线 + 100M
种子 CI"分列；(2) 采样对照 arm 补第 2 种子（c1Mcs-s29 入队）；(3) 单
种子档差异说明进 limitation。T4.1.1 验收已含。

**审稿人 D（定位）**：
> "'独有贡献'清单我逐条核过：深圳湾做了 21 模型零样本；良渚做了统一
> 微调+困难切分；你们把别人的协议拼起来加一个自训家族就叫'机理研究'？
> S12 解耦指数是唯一真正新的东西，它排在 T3.2——排期最晚、无备份。
> 主菜的工期给了配菜的三个对照。"

**修正 D**（部分成立——核心贡献排期风险真实）：(1) S12 提前：Infernal
cmscan 是 CPU 任务，与 GPU 训练完全并行，本周启动；(2) 三协议矩阵的
"新"收缩为"协议×切分×规模的交互归因"（写作层面防 D2 违规）；(3) 良
渚差异化写入相关工作（他们：统一微调×困难切分；我们：规模/层/语料三轴）。

**审稿人 E（生物）**：
> "接触图 ≥24nt、C4'/P 阈值——这是蛋白 8Å 的换算还是 RNA 文献口径？
> PDB RNA 条目才 7k，family-level 切分后每家族剩几条？统计功效何在。
> 另外 rRNA 占语料 56%，你们所有涌现结论会不会只是'rRNA 结构规律性'
> 的另一种说法？"

**修正 E**（成立）：(1) 接触定义双口径并报（差异入附录）；(2) 家族 n
报告 + 家族数下限预警（E2 强化）；(3) **所有涌现/probe 分析强制加"去
rRNA"分层重跑**（T1.3.2 验收增加）；语料端 rRNA 偏置与 T2.3.3 家族
重加权 arm 交叉验证。

**总修正跟踪表**（全部已并入上文对应任务项）：

| 红队项 | 修正 | 落点 |
|---|---|---|
| A 预算/语料 | epoch 覆盖显式化 + 同覆盖比较 | T2.1.2 / T2.3.1 |
| B probe 平衡 | class-weighted + attention-pool 头 | T1.2.2 |
| C 伪统计 | CI 语义修正 + 对照补种子 | T4.1.1 + c1Mcs-s29 |
| D 排期 | S12 提前（CPU 并行本周启动） | T3.2.1 |
| E rRNA 偏置 | 去 rRNA 分层强制 + 接触双口径 | T1.3.2 / T3.1.2 |

---

## 附二：交接反思与改进方案（2026-10-06 Day 27，执行人自查）

> 触发：用户四点质询（叙事证据强度 / PPT 数据核对 / 项目问题反思 / 论文主线逻辑）。本节按「问题 → 现状证据 → 改进动作」三段式自查，动作项并入上文任务编号。

### R-A 叙事链证据强度自查（每一幕能否被实验现象强证明）

| 幕 | 主张 | 证据等级 | 判定 |
|---|---|---|---|
| Act I | 六档 scaling + 10M 谷 + 650M 饱和 | 预注册+六档+三 seed（30M/100M）+斜率规则预注册触发 | ✅ 强 |
| Act II | H2/H3 排除（非初始化/非权重统计） | 六档 randinit/mommatch 双对照，b59 臂补齐三件套 | ✅ 强 |
| Act III | 磨蚀/层迁移/结构零增益 | 四尺度 37 点 + de-rRNA 干预（P1）+ 三测度体系 | ✅ 强（P2 650M@5.9B 在训收口中） |
| Act IV | 泄漏三角 + RNS 解耦 | 干预级（S4×S9 三角）+ 五轴 RNS + 三通道裁决 | ✅ 强 |
| Act V | 语料主导 + 预算×尺度交互 | 析因 3/4 点落 + 符号翻转单调 + S7 双通道 + 三通道裁决 | ✅ 强（650M 决定性单元格在训） |
| H7 钟形 | NOT-BELL 负结果 | 预注册判据 + v2 36 点 + 机制解释（语料域内无过度自信区间） | ✅ 按负结果纪律呈现 |

**遗留弱点（诚实登记）**：① 650M@5.9B 决定性单元格在训（~2-3 天）——Act V 完整性依赖它；② +0.10 语料 vs 架构归因仍是"首要嫌疑"级（正交判据 Rfam 富集臂未训）；③ 10M_rw1 +0.15pp < 种子 std，已按"中性偏正"诚实定级。

### R-B 主线逻辑与科学故事（已修复）

DRAFT v1.0 已采用五幕式侦探叙事（Introduction 1.x 段：Act I 现象 → Act II 排除平凡解释 → Act III 机制 → Act IV 真伪分离 → Act V 语料操纵），每幕绑定假设编号与证据链。**本次核查确认**：问题与结果之间的衔接通过"预注册可证伪预测"（P1-P5）与"符号翻转单调链"（−5.24/−2.74/+3.76）两个骨架承接——每一幕的推进都有前一幕的现象作为必要前提（例：Act V 的 Chinchilla 交互直接源于 Act I 的 slope 饱和与 Act III 的磨蚀层下移两个现象的交叉）。

### R-C 本次交接执行的修正

1. **PPT stale 数据清理**：slide 45/48/51/52 四页仍写 10-02~10-04 的旧在训状态（300M_b59 79% 等），已全部更新为 10-06 实测状态；新增 slide 53（Day 26 收口页：析因第三点 + S7 预算矩阵 + 三通道裁决，23 项数字与 evidence JSON 逐位核对）——三遍程序化验证 + 第四遍数字复核全过，备份 `.bak_day26_1420`。
2. **本地镜像滞后修复**：本地 论文/DRAFT_v1.md 停在 10-04 版，服务器已到 10-06 版（91de84d7）——已 scp 同步；refs/id_verify_log 一并同步。
3. **服务器 docs/TASKS_V2.md 停在 3.25 前版本**（v3.25 版本头之后无 Day 26 记录）——本日随 TRAINING_LOG Day 27 一并回写（服务器侧执行）。

### R-D 改进动作清单（并入任务编号）

| # | 动作 | 任务号 | 状态 |
|---|---|---|---|
| D-1 | 650M_b59 收口后 24h 内：family 第 4 点 + S7 最后一格 + factorial_verdict 终表 + fig6 升级三点/四点版 | T1.0.4 尾 | ⏳ 自动链在岗 |
| D-2 | P2 干预臂判定（650M@5.9B 深层边际增益是否恢复——假说 M 链①的干预级检验） | 假说 M | ⏳ 收口后 |
| D-3 | Rfam 富集语料臂（+0.10 归因的正交判据，预注册）——GPU 空窗期最高优先级新训 | T4.3.4（新增） | ⏳ 排队 |
| D-4 | fig6 v3（三点预算轴 + 单调翻转曲线）+ Fig 8 候选（S7 双通道对照图） | T4.1 | ⏳ 收口后 |
| D-5 | DRAFT Abstract 更新（预算轴三档 + 三通道裁决两句，当前 Abstract 停在 650M@2B 时代） | T4.2.1 | ⏳ 本周 |
| D-6 | arXiv 挂出前最终红队（D1-D11 重跑 + 数字逐位核对 + [id-verify] 已关闭确认） | T4.2.5 前置 | ⏳ 收口后 |

---

*执行人每日对照本清单勾选并推送；任何 [!] 变更需在 TRAINING_LOG 记录原因。*
