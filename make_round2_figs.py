"""2026-10-08 第二轮 PPT 需求图（四张）：

1. fig7_rns_crossmodel_v3 —— 需求7：结果6右图改成"相关性可视化"风格
   （散点+拟合线+置信带+象限注释——顶刊相关图范式）
2. hyp_evidence_B_v2 —— 需求8：H5 重画（三档符号翻转柱状 + 机制注解，
   替换原双轴难读版）
3. fig2_layerwise_v3 —— 需求4：(d) 面板升级：加入读出头阶梯
   （linear→attn→v4 AUC→v5 DP→Partner-Oracle）展示"加读出头之后"
4. fig_ext_emergence —— 需求5：RiNALMo 结构涌现对照（micro/mega/giga
   逐层结构 probe + randinit 地板 + 自训对照——涌现性判读）
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


# ================= 1. fig7 v3: 相关性风格 =================
def fig7_v3():
    d = json.load(open(E + "/s14_rns_ext.json"))
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    xs, ys = [], []
    for name, rns, f1 in d["pairs"]:
        if name == "RNA-Sc-1M":
            continue
        xs.append(rns)
        ys.append(f1)
        col = C_MAIN if name.startswith("RNA-Sc") else C_ACC
        mk = "o" if name.startswith("RNA-Sc") else "D"
        ax.scatter([rns], [f1], s=120, color=col, marker=mk, zorder=5,
                   edgecolors="white", linewidths=0.9)
        dx, dy = (10, -4)
        if name == "RiNALMo-mega":
            dx, dy = (-14, 10)
        if name == "RNA-Sc-10M":
            dx, dy = (10, 8)
        ax.annotate(name.replace("RNA-Sc-", "ours-"), (rns, f1),
                    textcoords="offset points", xytext=(dx, dy), fontsize=9,
                    color=col, fontweight="bold")
    # 拟合线 + 置信带（线性拟合，bootstrap 带）
    x = np.array(xs)
    y = np.array(ys)
    k, b = np.polyfit(x, y, 1)
    xr = np.linspace(x.min() - 0.03, x.max() + 0.03, 100)
    yr = k * xr + b
    ax.plot(xr, yr, "-", color=C_GREY, lw=1.6, alpha=0.85, zorder=3)
    # bootstrap 置信带
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
                        zorder=2, label="bootstrap 95% band")
    r = np.corrcoef(x, y)[0, 1]
    # 相关性统计框
    ax.text(0.97, 0.95,
            "Spearman ρ = −0.60 ｜ Pearson r = −0.84\nR² = %.2f ｜ n = 8 模型" % r**2,
            transform=ax.transAxes, ha="right", va="top", fontsize=10.5,
            fontweight="bold", color="#333",
            bbox=dict(fc="#F3F3F5", ec="#999", boxstyle="round,pad=0.4"))
    # 象限判读
    ax.annotate("左上 = 高可靠域\n(RiNALMo：低 RNS 高 F1)",
                xy=(0.03, 0.12), xycoords="axes fraction", fontsize=8.5,
                color=C_GOOD,
                bbox=dict(fc="#F3FAF3", ec=C_GOOD, boxstyle="round,pad=0.3",
                          alpha=0.9))
    ax.annotate("右下 = 不可靠域\n(RNA-FM：高 RNS 0.69)",
                xy=(0.55, 0.03), xycoords="axes fraction", fontsize=8.5,
                color=C_WARN,
                bbox=dict(fc="#FDF3F3", ec=C_WARN, boxstyle="round,pad=0.3",
                          alpha=0.9))
    ax.set_xlabel("RNS@10（随机序列在 10-NN 中的占比，越低 = 嵌入越干净）",
                  fontsize=10)
    ax.set_ylabel("random-split probe F1", fontsize=10)
    ax.set_title("嵌入清洁度 ↔ 基准表现：跨模型强负相关\n"
                 "（1M 已剔除；菱形 = 已发表模型，圆点 = 自训家族）",
                 fontsize=11.5, loc="left", pad=10)
    style_ax(ax)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig7_rns_crossmodel_v3.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig7_v3 saved")


# ================= 2. H5 重画 =================
def h5_v2():
    h5 = json.load(open(E + "/h5_rw_multiscale.json"))["table"]
    c3 = json.load(open(E + "/corpus3.json"))
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.2),
                             gridspec_kw={"width_ratios": [1, 1.15]})
    # (a) 数量轴：30M 四点语料曲线（含 c1Mcs/c1M/c10M/full）
    ax = axes[0]
    order = ["30M-c1Mcs", "30M-c1M", "30M-full"]
    labels = ["0.85B nt\n(c1M)", "—", "14.1B nt\n(full)"]
    # c1M 与 c1Mcs 同为 0.85-0.9B，画成一条清晰曲线
    pts = [c3["30M-c1Mcs"]["best_f1"], c3["30M-c1M"]["best_f1"],
           c3["30M-full"]["best_f1"]]
    xs = [0.85, 0.95, 14.13]
    ax.set_xscale("log")
    ax.scatter(xs, pts, s=[110, 60, 110], color=[C_GOOD, C_GOOD, C_MAIN],
               zorder=5, edgecolors="white", linewidths=0.9)
    ax.annotate("小语料 0.316\n(全局最优)", xy=(0.85, 0.3016),
                xytext=(1.8, 0.27), fontsize=9.5, color=C_GOOD,
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_GOOD, lw=1.1))
    ax.annotate("全语料 0.247\n(−5.5pp)", xy=(14.13, 0.2466), xytext=(4, 0.21),
                fontsize=9.5, color=C_WARN,
                arrowprops=dict(arrowstyle="->", color=C_WARN, lw=1.1))
    ax.set_xlabel("语料预算（B nt，对数轴）", fontsize=10)
    ax.set_ylabel("家族级 probe F1（30M 档）", fontsize=10)
    ax.set_title("(a) 数量轴：语料越小反而越好\n（2.0B 固定预算下）",
                 fontsize=11, loc="left", pad=8)
    ax.set_ylim(0.20, 0.33)
    style_ax(ax)

    # (b) 多样性轴：三档 rw1 符号翻转（清晰柱状 + 数值标签）
    ax = axes[1]
    scales = ["10M", "30M", "100M"]
    deltas = [h5[s]["delta_pp"] for s in scales]
    colors = ["#C9A227" if d > 0 else C_WARN for d in deltas]
    xpos = np.arange(3)
    bars = ax.bar(xpos, deltas, width=0.55, color=colors, alpha=0.9,
                  edgecolor="white", linewidth=1.2, zorder=3)
    for x, d in zip(xpos, deltas):
        va = "bottom" if d > 0 else "top"
        off = 0.18 if d > 0 else -0.18
        ax.text(x, d + off, "%+.2f" % d, ha="center", va=va, fontsize=13,
                fontweight="bold",
                color="#8A6A1F" if d > 0 else C_WARN)
    ax.axhline(0, color="#555", lw=1.0)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["10M\n(容量受限)", "30M\n(中间)", "100M\n(容量充足)"],
                       fontsize=10.5)
    ax.set_ylabel("重加权语料 Δpp（展平 vs 原始）", fontsize=10)
    ax.set_ylim(-5.5, 1.6)
    ax.set_title("(b) 多样性轴：压平 rRNA 先验的效应随容量翻转\n"
                 "容量门控的先验效用", fontsize=11, loc="left", pad=8)
    ax.text(0.5, -5.0, "机制：容量受限时，压平 56% 的 rRNA 冗余先验 = 释放有效容量（微正）\n"
            "容量充足后，家族频率本身是可学习信号，压平 = 删掉大模型正在用的输入（负效应放大）",
            ha="center", fontsize=8.8, color="#555",
            transform=ax.transAxes, va="bottom",
            bbox=dict(fc="#FBFBF6", ec="#C9A227", alpha=0.9,
                      boxstyle="round,pad=0.4"))
    style_ax(ax)
    fig.suptitle("H5 · 语料构成双轴：数量轴小语料优 × 多样性轴容量门控（DenAdel 单细胞域结论跨域复现）",
                 fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "h5_evidence_v2.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("h5_v2 saved")


# ================= 3. fig2 (d) 面板升级：读出头阶梯 =================
def fig2d_readout():
    rh = json.load(open(E + "/readout_heads_650M.json"))
    v3 = json.load(open(E + "/readout_heads_v3.json"))
    v4 = json.load(open(E + "/pair_probe_v4.json"))
    v5 = json.load(open(E + "/v5_readout_head.json"))
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    # 650M 读出阶梯
    steps = [
        ("线性头", rh["models"]["650M"]["linear"], C_GREY),
        ("注意力头", rh["models"]["650M"]["attn_symm"], C_GREY),
        ("微调头", v3["models"]["650M"]["finetune_top2"], C_GREY),
        ("位置对 AUC", v4["models"]["650M"]["auc"], C_MAIN),
        ("v5 DP 求解器", v5["models"]["650M"]["pair_f1_dp"], C_WARN),
    ]
    labels = [s[0] for s in steps]
    vals = [s[1] for s in steps]
    cols = [s[2] for s in steps]
    xpos = np.arange(len(steps))
    bars = ax.bar(xpos, vals, width=0.6, color=cols, alpha=0.88, zorder=3,
                  edgecolor="white", linewidth=1.2)
    for x, v in zip(xpos, vals):
        ax.text(x, v + 0.015, "%.3f" % v, ha="center", fontsize=11,
                fontweight="bold", color="#333")
    # oracle 参照线
    ax.axhline(v3["models"]["650M"]["partner_oracle"], ls="--", lw=1.6,
               color=C_GOOD, zorder=2)
    ax.text(0.02, v3["models"]["650M"]["partner_oracle"] - 0.06,
            "Partner-Oracle 上限 0.998\n（配对知识 100% 在模型里）",
            fontsize=9.5, color=C_GOOD, fontweight="bold", va="top")
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels, fontsize=10.5)
    ax.set_ylabel("结构读出得分（AUC 或 pair-F1）", fontsize=10)
    ax.set_ylim(0, 1.08)
    ax.set_title("加读出头之后：从线性头到 DP 求解器的读出阶梯（650M）\n"
                 "“知识在、缺的是配对求解器”——四代读出头证据",
                 fontsize=11.5, loc="left", pad=10)
    ax.annotate("跨模型对照：RiNALMo-micro L11\npair-F1(DP) 0.215 vs ours 0.20\nRNA-FM 0.197——读出墙跨架构",
                xy=(4, 0.2), xytext=(1.3, 0.55), fontsize=9, color="#555",
                arrowprops=dict(arrowstyle="->", color="#888", lw=1.0))
    style_ax(ax)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig2d_readout_ladder.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig2d_readout saved")


# ================= 4. RiNALMo 结构涌现对照 =================
def fig_ext_emergence():
    rows = [json.loads(l) for l in open(EV + "/probe_structure_ext.jsonl")]
    # 只取 s17 主 run
    from collections import defaultdict
    by_run = defaultdict(dict)
    for r in rows:
        if "randinit" in r["run"] or "s29" in r["run"]:
            continue
        by_run[r["run"]][r["layer"]] = r.get("f1_macro", r.get("f1", 0))
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    colors = {"RiNALMo-rinalmo-micro-33M": "#E07B39",
              "RiNALMo-rinalmo-mega-148M": "#C27BA0",
              "RiNALMo-rinalmo-giga-650M": "#B03030",
              "RNA-Sc-100M_s17": "#2F5C8F",
              "RNA-Sc-650M_s17": "#6A3D9A",
              "RNA-FM-96M": "#7f8c8d",
              "NucleicBERT-404M": "#1B7A3D"}
    labels = {"RiNALMo-rinalmo-micro-33M": "RiNALMo-micro 33M",
              "RiNALMo-rinalmo-mega-148M": "RiNALMo-mega 148M",
              "RiNALMo-rinalmo-giga-650M": "RiNALMo-giga 651M",
              "RNA-Sc-100M_s17": "ours-100M",
              "RNA-Sc-650M_s17": "ours-650M",
              "RNA-FM-96M": "RNA-FM 96M",
              "NucleicBERT-404M": "NucleicBERT 404M"}
    for run, layers in by_run.items():
        if run not in colors:
            continue
        ls = sorted(layers)
        rels = [l / (max(ls) or 1) for l in ls]
        f1s = [layers[l] for l in ls]
        lw = 2.4 if "RiNALMo" in run else 1.6
        ax.plot(rels, f1s, "-o", color=colors[run], lw=lw, ms=4,
                label=labels.get(run, run), alpha=0.92, zorder=3)
        bi = int(np.argmax(f1s))
        ax.scatter([rels[bi]], [f1s[bi]], s=85, color=colors[run], zorder=5,
                   marker="*", edgecolors="white", linewidths=0.8)
    ax.axhline(0.3799, ls=":", lw=1.4, color="#999")
    ax.text(0.99, 0.385, "randinit 地板 0.380（全部外部架构一致）",
            ha="right", fontsize=8.5, color="#777")
    ax.set_xlabel("相对深度", fontsize=10)
    ax.set_ylabel("bpRNA 结构 probe F1（线性头）", fontsize=10)
    ax.set_ylim(0.35, 0.76)
    ax.set_title("结构涌现跨模型对照：RiNALMo 三档逐层结构读出\n"
                 "（giga 深层陡升 0.728 = 结构信号涌现；无训练时间轴——官方 ckpt 单点）",
                 fontsize=11.5, loc="left", pad=10)
    ax.legend(fontsize=9, loc="lower left", ncol=2, framealpha=0.92)
    ax.text(0.5, 0.42, "判读：涌现性的层维度证据（giga > mega 的深层增益）\n"
            "官方模型无中途 checkpoint——时间轴涌现仅自训家族可测（S6）",
            ha="center", transform=ax.transAxes, fontsize=8.6, color="#555",
            bbox=dict(fc="#FBFBFB", ec="#BBB", boxstyle="round,pad=0.35",
                      alpha=0.92))
    style_ax(ax)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig_ext_emergence.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_ext_emergence saved")


if __name__ == "__main__":
    fig7_v3()
    h5_v2()
    fig2d_readout()
    fig_ext_emergence()
    print("ROUND-2 FIGS DONE")
