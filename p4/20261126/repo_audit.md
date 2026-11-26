# X-repo-audit：GitHub 仓库发布完整性审计

- 日期：2026-11-26
- 仓库：<https://github.com/Cunyu-Liu/RNA-scaling>（默认分支 `main`）
- 工作副本：`/tmp/rna-scaling-push`
- 审计基线：`d136200cb071caa83bdc112a8e2861b5a9248a85`
- 最终提交：`c185b67a2d37617ee4e7b73dd0bb49002606739d`
- 补传 commit：`c185b67`（`audit: restore paper figure targets and sync P4 gate (2026-11-26)`）

## 1. 最终交付清单逐项审计

| 项 | 交付要求 | 基线审计结果 | 最终状态与补传 |
|---|---|---|---|
| ① | 重写 DRAFT：`paper/v2_20261126/` | 在位：`DRAFT_v2_20261125.md` 及 14 个 Markdown 分节、14 个数字 CSV。 | **在位**；DRAFT、全部分节与本地权威源逐字节一致，无需补传。 |
| ② | 六图脚本 + PDF：`figures/` | 12/12 在位，6 个脚本均通过 AST 解析，6 个 PDF 均有 `%PDF-` 文件头；但 DRAFT 的 6 个 PNG 相对链接目标缺失。 | **已补齐**：从本地 `figs_v6/` 补传 6 个原始 PNG 至 `paper/figs_v6/`，保持 DRAFT 和分节源不变；图链 6/6 可解析。补传于 `c185b67`。 |
| ③ | 对账表：`reconciliation/20261125/` | 43 个文件在位，覆盖主表、差值表、种子/语料对账、基线表、远端核查、未完成注册表、黑名单检查及重生成脚本。 | **在位**；43/43 与本地 `对账_P0_20261125/` 逐字节一致，无需补传。 |
| ④ | 链式摘要：`paper/chain_summary_onepage.md` | 在位。 | **在位**；与本地 `论文重写_P1_20261125/chain_summary_onepage.md` 逐字节一致，无需补传。 |
| ⑤ | 数字溯源：`provenance/` + `paper/v2_20261126/sections/*_numbers.csv` | `provenance/` 14 个 CSV；论文分节目录 14 个 `_numbers.csv`，均非空。 | **在位**；分节数字 CSV 与本地权威源逐字节一致，无需补传。 |
| ⑥ | P2 预注册 + 脚本 + 汇总证据：`p2/20261126/` | 共 149 个文件：7 个预注册文件、39 个脚本、101 个轻量证据文件，另有 P2 汇总与 split 终裁 2 个报告。 | **在位**；本地可对应的预注册、汇总与终裁均逐字节一致，无需补传。预注册存在不表示未运行实验已完成。 |
| ⑦ | P3 预注册 + 准备：`p3/` | 共 18 个文件：`prereg/` 3 个、`prep/` 15 个，含训练准备代码、配置、报告与启动说明。 | **在位**；3 个预注册与本地源逐字节一致，无需补传。仍仅为 PREP_COMPLETE，不宣称正式训练已启动或完成。 |
| ⑧ | P4 断言器 + 门报告：`p4/20261126/` | 断言器、逐条结果、覆盖率报告均在位；`final_gate_report.md` 缺少本地终版末尾 4 行图链修复/PASS 附录。 | **已同步**：用本地 `发布_P4_20261126/final_gate_report.md` 更新仓库报告，其他 3 个文件保持不变。补传于 `c185b67`。 |
| ⑨ | `REPRODUCE.md` + `LICENSE` + `repo_manifest.md` | 三者均在仓库根；GitHub License API 返回 `MIT LICENSE`。 | **在位**；`repo_manifest.md` 与本地发布清单逐字节一致，无需补传。 |

## 2. 补传内容

补传提交 `c185b67a2d37617ee4e7b73dd0bb49002606739d` 共变更 7 个文件：

- 新增 `paper/figs_v6/fig1_q1q2_transfer_controls.png`；
- 新增 `paper/figs_v6/fig2_q3_dualworld.png`；
- 新增 `paper/figs_v6/fig3_q4.png`；
- 新增 `paper/figs_v6/fig4_q5_readout_chain.png`；
- 新增 `paper/figs_v6/fig5_q6_supply.png`；
- 新增 `paper/figs_v6/fig6_crosscut.png`；
- 更新 `p4/20261126/final_gate_report.md`，仅加入本地终版已有的 4 行附录。

未修改 DRAFT、分节源、任何实验数字、交接文档或只读备份。

## 3. 关键验证

- 基线同步：执行 HTTP/1.1 `fetch origin main` 后 `reset --hard origin/main`，HEAD 确认为 `d136200cb071caa83bdc112a8e2861b5a9248a85`。
- 来源一致性：DRAFT、链式摘要、28 个分节文件、六图脚本/PDF/PNG、43 个对账文件、P4 文件、发布清单及可对应的 P2/P3 预注册与终裁，共 **109/109 项逐字节一致**。
- 图链：从 `paper/v2_20261126/DRAFT_v2_20261125.md` 所在目录解析，Fig.1–6 **6/6 目标存在且与本地 PNG 逐字节一致**。
- 大小门禁：最终仓库 565 个跟踪文件，最大单文件 675,124 bytes；**超过 5 MB 的文件为 0**。
- 权重/数据门禁：跟踪文件中 `.pt/.pth/.ckpt/.parquet/.fasta/.fa/.fna/.npz/.npy/.jsonl` **命中 0**；权重与数据仍按 `repo_manifest.md` 声明保留在备份/团队远端。
- 推送：前两次 HTTP/1.1 推送分别发生接收超时和 443 连接超时，第三次成功，`d136200..c185b67 main -> main`。
- 远端复核：`git ls-remote origin refs/heads/main` 返回 `c185b67a2d37617ee4e7b73dd0bb49002606739d`，与本地 HEAD 完全一致；工作区干净且与 `origin/main` 无分叉。

## 4. 阻塞项

**无。** 九项最终交付清单均已齐备，草稿图链与 P4 终版报告缺口已补传并完成远端核验。
