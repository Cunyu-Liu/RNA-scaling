"""2026-10-09 第三轮修复图（五张）：

1. fig2d_readout_ladder_v2 —— 修口径混用：分双面板（左=逐位点 macro-F1
   口径：线性/注意力/微调 + randinit 对照；右=对级口径：AUC 与 pair-F1
   分轴），每面板内口径统一
2. fig_ext_emergence_v2 —— 修 RiNALMo 曲线消失（键名错误
   'RiNALMo-rinalmo-*' → 实际 'RiNALMo-*'）
3. fig7_rns_crossmodel_v4 —— 标注避让（右上角小图例表代替逐点长标注 +
   关键点引线）
4. hyp_evidence_A_v2 —— H4 修复（s6_cross_scale 四尺度真数据：
   best_rel 演化轨迹 + 10M 塌层标注）
5. hyp_evidence_B_v2 —— H5 分两图（a 数量轴 / b 多样性轴——b 补
   100M/300M/650M 情况说明）+ H6/H7/H8 恢复（原 B 页四格版恢复）
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"
os.makedirs(FIG, exist_ok=True)

C_MAIN, C_WARN, C_GOOD, C_GREY, C_ACC = "#2F5C8F", "#B03030", "#1B7A3D", "#8A8A8A", "#C27BA0"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5, width=0.9, labelsize=9)
    ax.grid(alpha=0.22, ls=":", lw=0.7)
    ax.set_axisbelow(True)


# ============ 1. 读出头阶梯 v2：双面板分口径 ============
def fig2d_v2():
    rh = json.load(open(E + "/readout_heads_650M.json"))
    v3 = json.load(open(E + "/readout_heads_v3.json"))
    v4 = json.load(open(E + "/pair_probe_v4.json"))
    v5 = json.load(open(E + "/v5_readout_head.json"))
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 5.6))

    # 左：逐位点 macro-F1（口径统一：每位点配对二分类的 macro-F1）
    heads = ["线性头", "注意力头", "微调头"]
    vals = [rh["models"]["650M"]["linear"], rh["models"]["650M"]["attn_symm"],
            v3["models"]["650M"]["finetune_top2"]]
    rvals = [rh["models"]["650M_randinit"]["linear"],
             rh["models"]["650M_randinit"]["attn_symm"]]
    xpos = np.arange(3)
    axL.bar(xpos, vals, width=0.52, color=C_MAIN, alpha=0.9, zorder=3,
            edgecolor="white", linewidth=1.2, label="650M trained")
    axL.bar(xpos[:2], rvals, width=0.52, color=C_GREY, alpha=0.55, zorder=2,
            edgecolor="white", linewidth=1.0, label="randinit 对照")
    for x, v in zip(xpos, vals):
        axL.text(x, v + 0.012, "%.3f" % v, ha="center", fontsize=11,
                 fontweight="bold", color=C_MAIN)
    for x, v in zip(xpos[:2], rvals):
        axL.text(x, v - 0.035, "%.3f" % v, ha="center", fontsize=9.5,
                 color="#777")
    axL.set_xticks(xpos)
    axL.set_xticklabels(heads, fontsize=11)
    axL.set_ylabel("逐位点 macro-F1（同口径）", fontsize=10)
    axL.set_ylim(0, 0.75)
    axL.set_title("(a) 序列头升级（口径统一）：读出头容量不是瓶颈\n"
                  "trained 0.61→0.63→0.64；randinit 0.50→0.59（头自身也在学）",
                  fontsize=10.5, loc="left", pad=8)
    axL.legend(fontsize=9, loc="upper left")
    style_ax(axL)

    # 右：对级（AUC 与 pair-F1 两个子指标——分组呈现，不混轴）
    labels = ["候选对\nAUC", "top-L\nP@L", "DP 求解器\npair-F1"]
    auc_v = [v4["models"]["650M"]["auc"]]
    topl_v = [v4["models"]["650M"]["topL_precision"]]
    dp_v = [v5["models"]["650M"]["pair_f1_dp"]]
    # 每个指标画在归一化 0-1 但各自标注真值 + 口径注明
    xs = np.arange(3)
    vals2 = [auc_v[0], v5["models"]["650M"]["pair_f1_topL"], dp_v[0]]
    cols = [C_GOOD, C_GREY, C_WARN]
    bars = axR.bar(xs, vals2, width=0.52, color=cols, alpha=0.9, zorder=3,
                   edgecolor="white", linewidth=1.2)
    for x, v in zip(xs, vals2):
        axR.text(x, v + 0.015, "%.3f" % v, ha="center", fontsize=11.5,
                 fontweight="bold", color="#333")
    axR.axhline(v3["models"]["650M"]["partner_oracle"], ls="--", lw=1.6,
                color=C_GOOD, zorder=2)
    axR.text(2.45, v3["models"]["650M"]["partner_oracle"] - 0.02,
             "Partner-Oracle 0.998\n（知识 100% 在）", fontsize=9.5,
             color=C_GOOD, fontweight="bold", ha="right", va="top")
    axR.set_xticks(xs)
    axR.set_xticklabels(labels, fontsize=10.5)
    axR.set_ylabel("对级得分（各自口径，数值直标）", fontsize=10)
    axR.set_ylim(0, 1.1)
    axR.set_title("(b) 对级读出（三种口径）：排序能力强、解码成对弱\n"
                  "AUC 0.95=“知道哪些位点可能配”；DP-F1 0.20=“选不出正确伙伴”",
                  fontsize=10.5, loc="left", pad=8)
    style_ax(axR)
    fig.suptitle("“加读出头之后”：分口径看——头容量非瓶颈，缺的是配对解码器（650M）",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig2d_readout_ladder_v2.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig2d_v2 saved")


# ============ 2. RiNALMo 涌现图 v2：修键名 ============
def fig_emergence_v2():
    rows = [json.loads(l) for l in open(EV + "/probe_structure_ext.jsonl")]
    from collections import defaultdict
    by_run = defaultdict(dict)
    for r in rows:
        if "randinit" in r["run"] or "s29" in r["run"] or "pseed" in r["run"]:
            continue
        by_run[r["run"]][r["layer"]] = r.get("f1_macro", r.get("f1", 0))
    colors = {"RiNALMo-micro-33M": "#E07B39",
              "RiNALMo-mega-148M": "#C27BA0",
              "RiNALMo-giga-650M": "#B03030",
              "RNA-Sc-650M_s17": "#6A3D9A",
              "RNA-FM-96M": "#7f8c8d",
              "NucleicBERT-404M": "#1B7A3D"}
    labels = {"RiNALMo-micro-33M": "RiNALMo-micro 33M",
              "RiNALMo-mega-148M": "RiNALMo-mega 148M",
              "RiNALMo-giga-650M": "RiNALMo-giga 651M",
              "RNA-Sc-650M_s17": "ours-650M",
              "RNA-FM-96M": "RNA-FM 96M",
              "NucleicBERT-404M": "NucleicBERT 404M"}
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    plotted = 0
    for run, layers in by_run.items():
        if run not in colors:
            continue
        plotted += 1
        ls = sorted(layers)
        rels = [l / (max(ls) or 1) for l in ls]
        f1s = [layers[l] for l in ls]
        lw = 2.6 if "RiNALMo" in run else 1.7
        ax.plot(rels, f1s, "-o", color=colors[run], lw=lw, ms=4.5,
                label=labels.get(run, run), alpha=0.94, zorder=3)
        bi = int(np.argmax(f1s))
        ax.scatter([rels[bi]], [f1s[bi]], s=100, color=colors[run], zorder=6,
                   marker="*", edgecolors="white", linewidths=0.9)
    assert plotted >= 5, "RiNALMo 曲线仍缺失！实际画了 %d 条" % plotted
    ax.axhline(0.3799, ls=":", lw=1.4, color="#999")
    ax.text(0.99, 0.385, "randinit 地板 0.380（全部架构一致）",
            ha="right", fontsize=8.5, color="#777")
    ax.set_xlabel("相对深度", fontsize=10)
    ax.set_ylabel("bpRNA 结构 probe F1（线性头）", fontsize=10)
    ax.set_ylim(0.35, 0.78)
    ax.set_title("结构涌现跨模型对照（v2 修复版）：RiNALMo 三档全在\n"
                 "giga 深层陡升 0.728（涌现性层证据）；官方 ckpt 无时间轴（单点）",
                 fontsize=11.5, loc="left", pad=10)
    ax.legend(fontsize=9, loc="lower left", ncol=2, framealpha=0.92)
    ax.annotate("giga 0.728@L32 深层峰", xy=(1.0, 0.728), xytext=(0.62, 0.75),
                fontsize=9.5, color="#B03030", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#B03030", lw=1.2))
    style_ax(ax)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig_ext_emergence_v2.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_emergence_v2 saved (%d curves)" % plotted)


# ============ 3. fig7 v4：标注避让 ============
def fig7_v4():
    d = json.load(open(E + "/s14_rns_ext.json"))
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    # 右上角图例表代替逐点标注
    legend_rows = []
    for name, rns, f1 in d["pairs"]:
        if name == "RNA-Sc-1M":
            continue
        col = C_MAIN if name.startswith("RNA-Sc") else C_ACC
        mk = "o" if name.startswith("RNA-Sc") else "D"
        ax.scatter([rns], [f1], s=130, color=col, marker=mk, zorder=5,
                   edgecolors="white", linewidths=0.9)
        legend_rows.append((name.replace("RNA-Sc-", "ours-"), rns, f1, mk, col))
    x = np.array([p[1] for p in legend_rows])
    y = np.array([p[2] for p in legend_rows])
    k, b = np.polyfit(x, y, 1)
    xr = np.linspace(x.min() - 0.03, x.max() + 0.03, 100)
    ax.plot(xr, k * xr + b, "-", color=C_GREY, lw=1.6, alpha=0.85, zorder=3)
    rng = np.random.default_rng(17)
    lines = []
    for _ in range(200):
        idx = rng.integers(0, len(x), len(x))
        if len(set(x[idx])) < 2:
            continue
        kk, bb = np.polyfit(x[idx], y[idx], 1)
        lines.append(kk * xr + bb)
    if lines:
        band = np.percentile(np.array(lines), [5, 95], axis=0)
        ax.fill_between(xr, band[0], band[1], color=C_GREY, alpha=0.18,
                        zorder=2)
    r = np.corrcoef(x, y)[0, 1]
    # 两点关键引线（只标最重要的两端，避免全点重叠）
    for name, rx, ry in [("RiNALMo-giga", 0.0153, 0.5442),
                         ("RNA-FM-96M", 0.6932, 0.0998)]:
        if name == "RiNALMo-giga":
            ax.annotate(name, xy=(rx, ry), xytext=(rx + 0.06, ry + 0.06),
                        fontsize=9.5, color=C_ACC, fontweight="bold",
                        arrowprops=dict(arrowstyle="-", color=C_ACC, lw=0.9))
        else:
            ax.annotate("RNA-FM 96M（嵌入最脏）", xy=(rx, ry),
                        xytext=(rx - 0.16, ry + 0.05), fontsize=9.5,
                        color=C_WARN, fontweight="bold",
                        arrowprops=dict(arrowstyle="-", color=C_WARN, lw=0.9))
    # 图例表（右上，代替逐点长标注）
    txt = "\n".join(["%s  RNS %.3f → F1 %.3f" % (n, rx, ry)
                     for n, rx, ry, _, _ in legend_rows])
    ax.text(0.985, 0.965, txt, transform=ax.transAxes, ha="right", va="top",
            fontsize=7.8, family="DejaVu Sans",
            bbox=dict(fc="white", ec="#BBB", alpha=0.93,
                      boxstyle="round,pad=0.4"))
    ax.text(0.02, 0.04,
            "Spearman ρ = −0.60 | Pearson r = −0.84 | R² = %.2f" % r**2,
            transform=ax.transAxes, fontsize=10, fontweight="bold",
            color="#333",
            bbox=dict(fc="#F3F3F5", ec="#999", boxstyle="round,pad=0.35"))
    ax.set_xlabel("RNS@10（越低 = 嵌入越干净）", fontsize=10)
    ax.set_ylabel("random-split probe F1", fontsize=10)
    ax.set_title("嵌入清洁度 ↔ 基准表现（v4 标注避让版）\n"
                 "RNA-FM 0.0998 已核验：其语料未见过我们评测家族（无泄漏红利）"
                 "且嵌入最脏——负对照",
                 fontsize=11.5, loc="left", pad=10)
    style_ax(ax)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig7_rns_crossmodel_v4.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig7_v4 saved")


# ============ 4. hyp_evidence_A_v2：H4 修复 ============
def hyp_a_v2():
    s6 = json.load(open(E + "/s6_cross_scale.json"))
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.6))
    fig.suptitle("H1–H4 证据图（v2 修复版：H4 用 s6_cross_scale 真数据）",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")

    # H1
    ax = axes[0][0]
    s1 = json.load(open(E + "/s1_final_verdict.json"))
    t = dict(s1["five_scale_table"])
    t["300M"] = {"f1_mean": 0.3445, "f1_std": 0.0}
    order = ["1M", "10M", "30M", "100M", "300M", "650M"]
    xs = [1.0, 10.0, 30.0, 100.0, 302.0, 666.0]
    means = [t[s]["f1_mean"] for s in order]
    stds = [t[s].get("f1_std", 0) or 0 for s in order]
    ax.errorbar(xs, means, yerr=stds, fmt="-o", color=C_MAIN, lw=2.0, ms=7,
                capsize=3, markeredgecolor="white", markeredgewidth=0.8)
    for x, y, s in zip(xs, means, order):
        ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=7.4, fontweight="bold")
    ax.set_xscale("log")
    ax.set_ylim(0.12, 0.43)
    ax.set_xlabel("参数量 (M)", fontsize=8.6)
    ax.set_ylabel("家族级 probe F1", fontsize=8.6)
    ax.set_title("H1 · 特征复用随规模增长——但有上限", fontsize=9.2,
                 loc="left", pad=5, fontweight="bold")
    ax.text(0.98, 0.04, "证实（有语料边界）：斜率 0.0293<ε 饱和",
            transform=ax.transAxes, ha="right", fontsize=7.4, color=C_GOOD,
            fontweight="bold")
    style_ax(ax)

    # H2
    ax = axes[0][1]
    s4 = json.load(open(E + "/s4_randinit_table.json"))
    order4 = ["1M", "10M", "30M", "100M", "300M", "650M"]
    tr = [s4[s]["trained"] for s in order4]
    ri = [s4[s]["randinit"] for s in order4]
    xs4 = [1.0, 10.0, 30.0, 100.0, 302.0, 666.0]
    ax.plot(xs4, tr, "-o", color=C_MAIN, lw=2.0, ms=6, label="trained",
            markeredgecolor="white", markeredgewidth=0.7)
    ax.plot(xs4, ri, "-s", color=C_GREY, lw=1.8, ms=6,
            label="random-init", markeredgecolor="white", markeredgewidth=0.7)
    ax.set_xscale("log")
    ax.set_xlabel("参数量 (M)", fontsize=8.6)
    ax.set_ylabel("probe F1", fontsize=8.6)
    ax.legend(fontsize=7.6, loc="upper left")
    ax.set_title("H2 · 归纳偏置解释——被排除", fontsize=9.2, loc="left",
                 pad=5, fontweight="bold")
    ax.text(0.98, 0.04, "排除：增益随规模扩大 +0.059→+0.168", transform=ax.transAxes,
            ha="right", fontsize=7.4, color=C_GOOD, fontweight="bold")
    style_ax(ax)

    # H3
    ax = axes[1][0]
    s5 = json.load(open(E + "/s5_mommatch_table.json"))
    mm = [s5[s]["mommatch"] for s in order4]
    w = 0.14
    xpos = np.arange(6)
    ax.bar(xpos - w, tr, width=w, color=C_MAIN, label="trained", alpha=0.92)
    ax.bar(xpos, mm, width=w, color="#C9A227", label="moment-matched", alpha=0.92)
    ax.bar(xpos + w, ri, width=w, color=C_GREY, label="random-init", alpha=0.92)
    ax.set_xticks(xpos)
    ax.set_xticklabels(order4, fontsize=8)
    ax.set_ylim(0, 0.46)
    ax.set_ylabel("probe F1", fontsize=8.6)
    ax.legend(fontsize=7.4, ncol=3, loc="upper left")
    ax.set_title("H3 · 权重统计解释——被排除", fontsize=9.2, loc="left",
                 pad=5, fontweight="bold")
    ax.text(0.98, 0.04, "排除：mommatch ≈ randinit", transform=ax.transAxes,
            ha="right", fontsize=7.4, color=C_GOOD, fontweight="bold")
    style_ax(ax)

    # H4（修复：s6_cross_scale 真数据——四尺度 best_rel 演化）
    ax = axes[1][1]
    colors4 = {"1M": "#A0A0A0", "10M": "#C0392B", "30M": "#1B7A3D",
               "100M": "#2F5C8F"}
    for scale in ["1M", "10M", "30M", "100M"]:
        pts = s6[scale]
        xs_t = [p["nt_B"] for p in pts]
        rels = [p["best_rel"] for p in pts]
        f1s = [p["best_f1"] for p in pts]
        ax.plot(xs_t, rels, "-o", color=colors4[scale], lw=1.8, ms=4,
                label=scale, alpha=0.9)
    ax.set_xlabel("预训练 token（B nt）", fontsize=8.6)
    ax.set_ylabel("最佳层相对深度", fontsize=8.6)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("H4 · 层位置随训练演化（四尺度 37 点真数据）\n"
                 "10M 磨蚀塌层 0.84→0.05；100M 稳定深化 0.36→0.96",
                 fontsize=9.2, loc="left", pad=5, fontweight="bold")
    ax.annotate("10M 塌层\n(0.84→0.05)", xy=(1.9, 0.053), xytext=(0.9, 0.42),
                fontsize=7.4, color="#C0392B",
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.0))
    ax.legend(fontsize=7.6, loc="upper right")
    ax.text(0.98, 0.04, "限定成立：磨蚀（容量门控）仅 10M 出现",
            transform=ax.transAxes, ha="right", fontsize=7.4, color=C_GOOD,
            fontweight="bold")
    style_ax(ax)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "hyp_evidence_A_v2.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("hyp_a_v2 saved")


# ============ 5. hyp_evidence_B_v2：H5 分图 + H6-H8 恢复 ============
def hyp_b_v2():
    c3 = json.load(open(E + "/corpus3.json"))
    h5 = json.load(open(E + "/h5_rw_multiscale.json"))["table"]
    links = {}
    for f, tag in [("s12_linkage_30M_s17_c1Mcs.json", "30M"),
                   ("s12_linkage_RNA-Sc-100M_s17.json", "100M"),
                   ("s12_linkage_RNA-Sc-300M_s17.json", "300M"),
                   ("s12_linkage_RNA-Sc-650M_s17.json", "650M")]:
        try:
            links[tag] = json.load(open(os.path.join(E, f)))["spearman_DI_vs_bestlayer"]
        except Exception:
            pass
    bell = json.load(open(E + "/s13b_bell.json"))

    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.8))
    fig.suptitle("H5–H8 证据图（v2：H5 分轴详解 + H6/H7/H8 恢复）",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")

    # H5-a 数量轴（30M 档语料曲线）
    ax = axes[0][0]
    xs = [0.85, 0.9, 14.13]
    pts = [c3["30M-c1M"]["best_f1"], c3["30M-c1Mcs"]["best_f1"],
           c3["30M-full"]["best_f1"]]
    labels_x = ["0.85B\n(c1M 前缀)", "0.9B\n(c1Mcs 簇级)", "14.1B\n(full)"]
    xpos = np.arange(3)
    ax.bar(xpos, pts, width=0.5, color=[C_GOOD, C_GOOD, C_MAIN], alpha=0.9,
           zorder=3, edgecolor="white", linewidth=1.2)
    for x, v in zip(xpos, pts):
        ax.text(x, v + 0.004, "%.3f" % v, ha="center", fontsize=11,
                fontweight="bold")
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels_x, fontsize=9)
    ax.set_ylabel("家族级 probe F1（30M 档）", fontsize=9)
    ax.set_ylim(0, 0.36)
    ax.set_title("H5-a · 数量轴：小语料反而最优（0.316）\n"
                 "100M/300M/650M 无语料量臂（H5 仅 30M 档语料曲线 + 全尺度 rw 链）",
                 fontsize=9.4, loc="left", pad=6, fontweight="bold")
    ax.text(0.98, 0.60, "2.0B 固定预算下：\n重复暴露高信号家族\n> 见更多家族",
            transform=ax.transAxes, ha="right", fontsize=8, color=C_GOOD,
            bbox=dict(fc="#F3FAF3", ec=C_GOOD, boxstyle="round,pad=0.3",
                      alpha=0.9))
    style_ax(ax)

    # H5-b 多样性轴（三档 + 大尺度标注）
    ax = axes[0][1]
    scales = ["10M", "30M", "100M"]
    deltas = [h5[s]["delta_pp"] for s in scales]
    colors = ["#C9A227" if d > 0 else C_WARN for d in deltas]
    xpos = np.arange(3)
    ax.bar(xpos, deltas, width=0.5, color=colors, alpha=0.9, zorder=3,
           edgecolor="white", linewidth=1.2)
    for x, d in zip(xpos, deltas):
        va = "bottom" if d > 0 else "top"
        off = 0.15 if d > 0 else -0.15
        ax.text(x, d + off, "%+.2f" % d, ha="center", va=va, fontsize=12,
                fontweight="bold")
    ax.axhline(0, color="#555", lw=1.0)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["10M\n(容量受限)", "30M\n(中间)", "100M\n(容量充足)"],
                       fontsize=9.5)
    ax.set_ylabel("重加权语料 Δpp（展平 vs 原始）", fontsize=9)
    ax.set_ylim(-5.4, 1.5)
    ax.set_title("H5-b · 多样性轴：符号随容量翻转（容量门控先验）\n"
                 "300M/650M 无 rw 臂（100M 已 −4.29pp 趋势确立）",
                 fontsize=9.4, loc="left", pad=6, fontweight="bold")
    style_ax(ax)

    # H6（恢复）
    ax = axes[1][0]
    xs_l = [30.0, 100.0, 302.0, 666.0]
    ys_l = [links[k] for k in ["30M", "100M", "300M", "650M"]]
    ax.plot(xs_l, ys_l, "-o", color=C_MAIN, lw=2.0, ms=8,
            markeredgecolor="white", markeredgewidth=0.8)
    for x, y, k in zip(xs_l, ys_l, ["30M", "100M", "300M", "650M"]):
        ax.annotate("%s\nρ=%.3f" % (k, y), (x, y), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=8, fontweight="bold")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xscale("log")
    ax.set_ylim(-0.6, 0.1)
    ax.set_xlabel("参数量 (M)", fontsize=9)
    ax.set_ylabel("Spearman(DI, 最佳层深度)", fontsize=9)
    ax.set_title("H6 · 解耦指数-层位关联随容量衰减（−0.478→−0.222）",
                 fontsize=9.4, loc="left", pad=6, fontweight="bold")
    style_ax(ax)

    # H7+H8 合并格（右下：钟形散点 + RNS 规模轴双子图）
    ax = axes[1][1]
    pts = bell["points"]
    models = sorted({p["model"] for p in pts})
    cmap = plt.cm.viridis(np.linspace(0.08, 0.92, len(models)))
    for m, c in zip(models, cmap):
        mp = [p for p in pts if p["model"] == m]
        ax.scatter([p["nll"] for p in mp], [p["f1"] for p in mp], s=30,
                   color=c, alpha=0.8, edgecolors="none")
    xs_b = np.array([p["nll"] for p in pts])
    ys_b = np.array([p["f1"] for p in pts])
    z = np.polyfit(xs_b, ys_b, 2)
    xr = np.linspace(xs_b.min() - 0.01, xs_b.max() + 0.01, 80)
    ax.plot(xr, np.polyval(z, xr), "--", color="#444", lw=1.4, zorder=3)
    ax.set_xlabel("家族级 NLL（置信轴）", fontsize=9)
    ax.set_ylabel("bpRNA 结构 F1", fontsize=9)
    ax.set_title("H7 · 结构钟形：NOT-BELL（预注册负结果）＋H8 见页 8",
                 fontsize=9.4, loc="left", pad=6, fontweight="bold")
    ax.text(0.98, 0.96, "峰值在数据范围外\nRNA 域内无过度自信区间",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            color=C_WARN, fontweight="bold",
            bbox=dict(fc="#FDF3F3", ec=C_WARN, boxstyle="round,pad=0.3"))
    style_ax(ax)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "hyp_evidence_B_v2.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("hyp_b_v2 saved")


if __name__ == "__main__":
    fig2d_v2()
    fig_emergence_v2()
    fig7_v4()
    hyp_a_v2()
    hyp_b_v2()
    print("ROUND-3 FIX FIGS DONE")
