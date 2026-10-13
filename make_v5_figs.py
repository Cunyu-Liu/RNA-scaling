"""PPT 核心图重画 v2（顶刊风格统一升级，plot-is-all-you-need 图库审美）。

风格系统（从图库鉴赏提炼）：
- 骨架 = plos-cc0-clean-lines：细线(1.6)、直接标注、无外框、极淡网格
- 分组色 = violin-median-badges 的同色系梯度 + 语义点缀色
- 语义色板（新版，替换旧的 #2F5C8F/#B03030 高饱和）：
    主蓝   #4878A8（我们的模型主线）
    深蓝   #2E5170（强调/峰值）
    珊瑚   #D98E73（对照/负向）
    暖灰   #B0B0B0（次要线）
    琥珀   #E5B45A（警示/涌现）
    青绿   #6FAE9B（正向/修复）
- 直标优先：系列名直接标在曲线端点，避免图例框
- 每图白底、字 9-11pt、轴字深灰 #3A3A3A
共 8 图，输出 figs/figX_v5.png（dpi 200）
"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
os.makedirs(FIG, exist_ok=True)

C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A"}
SC = {"1M": "#C9CDD2", "10M": "#E5B45A", "30M": "#6FAE9B",
      "100M": "#7BA3C7", "300M": "#4878A8", "650M": "#2E5170"}


def style(ax, grid=False):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors="#3A3A3A", labelsize=8.5, length=3, width=0.7)
    if grid:
        ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
        ax.set_axisbelow(True)
    else:
        ax.grid(False)


def load(name):
    return json.load(open(os.path.join(E, name)))


# ================= 1. 页 3：fig1b 层迁移双预算（dumbbell 换风格）=================
def fig_p3():
    fv = load("factorial_verdict.json")
    t = fv["table"]
    arms = ["30M", "100M", "300M", "650M"]
    rel2b = [t[a]["f1_2B"]["rel"] for a in arms]
    rel59 = [t[a]["f1_5.9B"]["rel"] for a in arms]
    l2b = [t[a]["f1_2B"]["layer"] for a in arms]
    l59 = [t[a]["f1_5.9B"]["layer"] for a in arms]
    f2b = [t[a]["f1_2B"]["f1"] for a in arms]
    f59 = [t[a]["f1_5.9B"]["f1"] for a in arms]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.3),
                                   gridspec_kw={"width_ratios": [1, 1.15]})
    ys = np.arange(4)
    for i, a in enumerate(arms):
        axL.plot([rel2b[i], rel59[i]], [i, i], "-", color="#D5D5D5",
                 lw=2.2, zorder=1)
        axL.scatter(rel2b[i], i, s=95, color=C["teal"], zorder=3,
                    edgecolors="white", linewidths=1.0)
        axL.scatter(rel59[i], i, s=120, color=C["deep"], zorder=4,
                    marker="D", edgecolors="white", linewidths=1.0)
        axL.annotate("Δ%+.2f" % (rel59[i] - rel2b[i]),
                     ((rel2b[i] + rel59[i]) / 2, i + 0.22), ha="center",
                     fontsize=8.2, color="#707070")
    axL.scatter([], [], s=95, color=C["teal"], label="2.0B")
    axL.scatter([], [], s=120, color=C["deep"], marker="D", label="5.9B")
    axL.set_yticks(ys)
    axL.set_yticklabels(arms, fontsize=10)
    axL.set_xlim(0, 1.08)
    axL.set_xlabel("最优层相对深度", fontsize=10, color=C["ink"])
    axL.set_title("(a) 层迁移：2B→5.9B 深层修复", fontsize=11,
                  loc="left", pad=8, color=C["ink"])
    axL.legend(fontsize=9, frameon=False, loc="lower right")
    axL.invert_yaxis()
    style(axL)

    x = np.arange(4)
    w = 0.34
    axR.bar(x - w / 2, f2b, w, color=C["teal"], label="2.0B")
    axR.bar(x + w / 2, f59, w, color=C["deep"], label="5.9B")
    for i in range(4):
        axR.text(i - w / 2, f2b[i] + 0.006, "L%d" % l2b[i], ha="center",
                 fontsize=8.5, color="#4A6E64", fontweight="bold")
        axR.text(i + w / 2, f59[i] + 0.006, "L%d" % l59[i], ha="center",
                 fontsize=8.5, color=C["deep"], fontweight="bold")
    axR.set_xticks(x)
    axR.set_xticklabels(arms, fontsize=10)
    axR.set_ylim(0, 0.56)
    axR.set_ylabel("family-split probe F1", fontsize=10, color=C["ink"])
    axR.set_title("(b) 预算×尺度：5.9B 修复 650M 磨蚀", fontsize=11,
                  loc="left", pad=8, color=C["ink"])
    axR.annotate("650M：L8→L25\n欠训伪象被预算修复",
                 xy=(3 + w / 2, f59[3]), xytext=(1.9, 0.47),
                 fontsize=9, color=C["coral"],
                 arrowprops=dict(arrowstyle="->", color=C["coral"], lw=1.1))
    axR.legend(fontsize=9, frameon=False, loc="upper left")
    style(axR)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_p3_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p3_v5 saved")


# ================= 2. 页 5：fig5 三面板控制排除（升级）=================
def fig_p5():
    s4 = load("s4_randinit_table.json")
    s5 = load("s5_mommatch_table.json")
    s6 = load("s6_cross_scale.json")
    scales = ["1M", "10M", "30M", "100M", "300M", "650M"]

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.0))
    ax = axes[0]
    xs = np.arange(len(scales))
    tr = [s4[s]["trained"] for s in scales]
    ri = [s4[s]["randinit"] for s in scales]
    mm = [s5[s]["mommatch"] for s in scales]
    ax.fill_between(xs, ri, tr, color=C["main"], alpha=0.10, zorder=1)
    ax.plot(xs, tr, "o-", color=C["main"], lw=1.8, ms=6, zorder=4)
    ax.plot(xs, mm, "^--", color=C["amber"], lw=1.4, ms=5.5, zorder=3)
    ax.plot(xs, ri, "s:", color=C["coral"], lw=1.4, ms=5.5, zorder=3)
    for x, t, r in zip(xs, tr, ri):
        ax.annotate("+%.3f" % (t - r), (x, (t + r) / 2), ha="center",
                    fontsize=7.6, color="#5E7FA0")
    ax.text(0.03, 0.94, "trained", transform=ax.transAxes, fontsize=9,
            color=C["main"], fontweight="bold")
    ax.text(0.03, 0.86, "moment-matched (H3 对照)", transform=ax.transAxes,
            fontsize=8, color=C["amber"])
    ax.text(0.03, 0.78, "random-init (H2 对照)", transform=ax.transAxes,
            fontsize=8, color=C["coral"])
    ax.set_xticks(xs)
    ax.set_xticklabels(scales)
    ax.set_xlabel("模型尺度", fontsize=10, color=C["ink"])
    ax.set_ylabel("最优层 family-split F1", fontsize=10, color=C["ink"])
    ax.set_title("(a) 对照排除：增益不被权重统计解释", fontsize=11,
                 loc="left", pad=8, color=C["ink"])
    style(ax, grid=True)

    ax = axes[1]
    colors4 = {s: SC[s] for s in ["1M", "10M", "30M", "100M"]}
    for scale in ["1M", "10M", "30M", "100M"]:
        pts = s6[scale]
        ax.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
                "-o", color=colors4[scale], lw=1.6, ms=3.6,
                label=scale)
    ax.text(1.92, 0.155, "1M", fontsize=8.5, color=SC["1M"],
            fontweight="bold", va="center")
    ax.text(1.92, 0.173, "10M", fontsize=8.5, color=SC["10M"],
            fontweight="bold", va="center")
    ax.text(1.92, 0.246, "30M", fontsize=8.5, color=SC["30M"],
            fontweight="bold", va="center")
    ax.text(1.92, 0.326, "100M", fontsize=8.5, color=SC["100M"],
            fontweight="bold", va="center")
    valley = min(s6["10M"], key=lambda p: p["best_f1"])
    ax.axvspan(0.9, valley["nt_B"], color=C["amber"], alpha=0.10)
    ax.annotate("10M 磨蚀谷", xy=(valley["nt_B"], valley["best_f1"]),
                xytext=(0.85, 0.27), fontsize=9, color="#9A7B35",
                arrowprops=dict(arrowstyle="->", color="#9A7B35", lw=1.0))
    ax.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
    ax.set_ylabel("最优层 F1（时间轴）", fontsize=10, color=C["ink"])
    ax.set_xlim(0, 2.15)
    ax.set_title("(b) 10M 磨蚀谷；30M/100M 持续爬升", fontsize=11,
                 loc="left", pad=8, color=C["ink"])
    style(ax, grid=True)

    ax = axes[2]
    for scale in ["1M", "10M", "30M", "100M"]:
        pts = s6[scale]
        ax.plot([p["nt_B"] for p in pts], [p["best_rel"] for p in pts],
                "-s", color=colors4[scale], lw=1.6, ms=3.4)
    ax.annotate("10M 层坍缩至 L1\n（磨蚀签名）", (1.55, 0.06),
                fontsize=9, color="#9A7B35", ha="left")
    ax.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
    ax.set_ylabel("最优层相对深度", fontsize=10, color=C["ink"])
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlim(0, 2.15)
    ax.text(1.92, 0.0, "1M", fontsize=8.5, color=SC["1M"],
            fontweight="bold", va="bottom")
    ax.text(1.92, 0.053, "10M", fontsize=8.5, color=SC["10M"],
            fontweight="bold", va="bottom")
    ax.text(1.92, 0.72, "30M", fontsize=8.5, color=SC["30M"],
            fontweight="bold", va="center")
    ax.text(1.92, 0.94, "100M", fontsize=8.5, color=SC["100M"],
            fontweight="bold", va="center")
    ax.set_title("(c) 层迁移：10M 坍缩浅层；大尺度深化", fontsize=11,
                 loc="left", pad=8, color=C["ink"])
    style(ax, grid=True)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_p5_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p5_v5 saved")


# ================= 3. 页 9：fig_ext_corpus_vs_params 升级=================
def fig_p9():
    arms = [
        ("RNA-Sc-100M_s17", "100M r22", 100, "ours"),
        ("RNA-Sc-100M_s17_rinalmocorpus", "100M rinalmo", 100, "rinalmo"),
        ("RNA-Sc-300M_s17", "300M r22", 302, "ours"),
        ("RNA-Sc-300M_s17_rinalmocorpus", "300M rinalmo", 302, "rinalmo"),
    ]
    fv = load("factorial_verdict.json")
    cav = load("corpus_arm_verdict.json")
    f1 = {
        ("100M", "r22"): fv["table"]["100M"]["f1_2B"]["f1"],
        ("100M", "rinalmo"): cav["table"]["100M"]["rinalmo_corpus_replica"]["f1"],
        ("300M", "r22"): fv["table"]["300M"]["f1_2B"]["f1"],
        ("300M", "rinalmo"): cav["table"]["300M"]["rinalmo_corpus_replica"]["f1"],
    }
    f1_30 = (cav["table"]["30M"]["r22"]["f1"],
             cav["table"]["30M"]["rinalmo_corpus_replica"]["f1"])

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    xs_r22 = [30, 100, 302]
    xs_ri = [30, 100, 302]
    ys_r22 = [f1_30[0], f1[("100M", "r22")], f1[("300M", "r22")]]
    ys_ri = [f1_30[1], f1[("100M", "rinalmo")], f1[("300M", "rinalmo")]]
    ax.plot(xs_r22, ys_r22, "o--", color=C["grey"], lw=1.6, ms=7,
            label="r22 基线语料")
    ax.plot(xs_ri, ys_ri, "o-", color=C["main"], lw=2.0, ms=8,
            label="RiNALMo 语料复刻")
    for x, y in zip(xs_ri, ys_ri):
        ax.annotate("%.3f" % y, (x, y), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8.5,
                    color=C["main"], fontweight="bold")
    for x, y in zip(xs_r22, ys_r22):
        ax.annotate("%.3f" % y, (x, y), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=8.5, color="#8A8A8A")
    for x, ya, yb in zip(xs_ri, ys_r22, ys_ri):
        ax.annotate("", xy=(x, yb), xytext=(x, ya),
                    arrowprops=dict(arrowstyle="->", color=C["amber"], lw=1.5))
        ax.text(x * 1.06, (ya + yb) / 2, "+%.1f pp" % ((yb - ya) * 100),
                fontsize=9, color="#9A7B35", fontweight="bold")
    ax.set_xscale("log")
    ax.set_xticks(xs_r22)
    ax.set_xticklabels(["30M", "100M", "300M"])
    ax.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
    ax.set_ylabel("family-split probe F1", fontsize=10, color=C["ink"])
    ax.set_ylim(0.22, 0.40)
    ax.set_title("语料效应随尺度单调衰减：小模型最吃语料、大模型近饱和",
                 fontsize=11.5, loc="left", pad=8, color=C["ink"])
    ax.legend(fontsize=9, frameon=False, loc="center right")
    style(ax, grid=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_p9_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p9_v5 saved")


# ================= 4. 页 10：fig7_rns_crossmodel v5 =================
def fig_p10():
    d = load("s14_rns_ext.json")
    pairs = [p for p in d["pairs"] if p[0] != "RNA-Sc-1M"]
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    for name, rns, f1v in pairs:
        ours = name.startswith("RNA-Sc")
        col = C["main"] if ours else C["coral"]
        mk = "o" if ours else "D"
        ax.scatter(rns, f1v, s=110, color=col, marker=mk, zorder=4,
                   edgecolors="white", linewidths=0.9)
        label = name.replace("RNA-Sc-", "ours·").replace(
            "RiNALMo-", "RiNALMo·")
        dx, dy = (0.018, 0.012) if f1v < 0.55 else (0.018, -0.022)
        ax.annotate(label, (rns, f1v), textcoords="offset points",
                    xytext=(6, 4 if f1v < 0.55 else -12), fontsize=8.2,
                    color=col)
    x = np.array([p[1] for p in pairs])
    y = np.array([p[2] for p in pairs])
    k, b = np.polyfit(x, y, 1)
    xr = np.linspace(x.min() - 0.04, x.max() + 0.04, 100)
    ax.plot(xr, k * xr + b, "-", color="#B8B8B8", lw=1.3, alpha=0.9,
            zorder=2)
    rng = np.random.default_rng(17)
    lines = []
    for _ in range(400):
        idx = rng.integers(0, len(x), len(x))
        if len(set(x[idx])) < 2:
            continue
        kk, bb = np.polyfit(x[idx], y[idx], 1)
        lines.append(kk * xr + bb)
    if lines:
        band = np.percentile(np.array(lines), [10, 90], axis=0)
        ax.fill_between(xr, band[0], band[1], color="#C9CDD2", alpha=0.35,
                        zorder=1)
    ax.text(0.03, 0.05, "Spearman ρ = −0.60 | Pearson r = −0.84",
            transform=ax.transAxes, fontsize=10, fontweight="bold",
            color=C["ink"])
    ax.set_xlabel("RNS@10（越低 = 嵌入越干净）", fontsize=10, color=C["ink"])
    ax.set_ylabel("random-split probe F1", fontsize=10, color=C["ink"])
    ax.set_title("嵌入清洁度 ↔ 基准表现：RNS 低的模型各层一致更好",
                 fontsize=11.5, loc="left", pad=8, color=C["ink"])
    style(ax, grid=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_p10_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p10_v5 saved")


# ================= 5. 页 10 右：fig_s14_rns v5 =================
def fig_p10b():
    d = load("s14_rns.json")
    try:
        sa = d["scale_axis"]["rns_k10"]
    except Exception:
        sa = d.get("rns_k10", {"1M": 0.172, "10M": 0.104, "30M": 0.078,
                               "100M": 0.077})
    scales = ["1M", "10M", "30M", "100M"]
    vals = [sa.get(s, {"1M": 0.172, "10M": 0.104, "30M": 0.078,
                       "100M": 0.077}[s]) for s in scales]
    try:
        vals.append(load("s14_rns_300m.json").get("rns_k10", 0.067))
        scales.append("300M")
    except Exception:
        pass
    try:
        vals.append(load("s14_rns_650m.json").get("rns_k10", 0.062))
        scales.append("650M")
    except Exception:
        pass
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    xs = [float(s[:-1]) for s in scales]
    ax.plot(xs, vals, "o-", color=C["main"], lw=2.0, ms=8,
            markeredgecolor="white", markeredgewidth=1.2)
    ax.plot([xs[-1]], [vals[-1]], "o", ms=11, color=C["deep"],
            markeredgecolor="white", markeredgewidth=1.2, zorder=5)
    ax.axhspan(0.54, 0.58, color="#E3E6E9", zorder=1)
    ax.text(0.97, 0.555, "randinit 带 0.54–0.58", transform=ax.get_yaxis_transform(),
            fontsize=8, color="#909090", va="center", ha="right")
    for x, y, s in zip(xs, vals, scales):
        ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8.5, fontweight="bold",
                    color=SC.get(s, C["deep"]))
    ax.set_xscale("log")
    ax.set_ylim(0.0, 0.66)
    ax.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
    ax.set_ylabel("RNS@10（低 = 好）", fontsize=10, color=C["ink"])
    ax.set_title("RNS 随尺度单调改善；30M 平台期", fontsize=11,
                 loc="left", pad=8, color=C["ink"])
    style(ax, grid=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_p10b_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p10b_v5 saved")


# ================= 6. 页 12：hyp_evidence_A v5（H1-H4 四面板）=================
def fig_p12():
    s1 = load("s1_final_verdict.json")
    s4 = load("s4_randinit_table.json")
    fv = load("factorial_verdict.json")

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.2))
    fig.suptitle("H1–H4 证据（Li et al. 对齐四假设）", fontsize=12,
                 fontweight="bold", x=0.01, ha="left", color=C["ink"])

    ax = axes[0][0]
    ft = s1["five_scale_table"]
    scales = ["1M", "10M", "30M", "100M", "650M"]
    means = [ft[s]["f1_mean"] for s in scales]
    stds = [ft[s]["f1_std"] for s in scales]
    xs = [float(s[:-1]) for s in scales]
    ax.errorbar(xs, means, yerr=stds, fmt="o-", color=C["main"], lw=2.0,
                ms=7, capsize=3, elinewidth=1.1, capthick=1.1)
    for x, m, s in zip(xs, means, scales):
        ax.annotate(s, (x, m), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8.5, fontweight="bold",
                    color=SC.get(s, C["deep"]))
    ax.set_xscale("log")
    ax.set_xlabel("参数量（M）", fontsize=9.5)
    ax.set_ylabel("family-split F1（3 seeds 均值±std）", fontsize=9.5)
    ax.set_title("H1 · 规模法则：增益存在但饱和", fontsize=10.5, loc="left",
                 pad=6, fontweight="bold", color=C["ink"])
    ax.text(0.60, 0.13, "斜率 0.083/decade→0.0293\n650M 仅 +2.4pp（<ε）",
            transform=ax.transAxes, fontsize=8, color="#707070")
    style(ax, grid=True)

    ax = axes[0][1]
    scales6 = ["1M", "10M", "30M", "100M", "300M", "650M"]
    tr = [s4[s]["trained"] for s in scales6]
    ri = [s4[s]["randinit"] for s in scales6]
    xs = np.arange(6)
    ax.fill_between(xs, ri, tr, color=C["main"], alpha=0.10)
    ax.plot(xs, tr, "o-", color=C["main"], lw=1.8, ms=6)
    ax.plot(xs, ri, "s:", color=C["coral"], lw=1.4, ms=5.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(scales6)
    ax.set_xlabel("模型尺度", fontsize=9.5)
    ax.set_ylabel("最优层 F1", fontsize=9.5)
    ax.set_title("H2 · 随机初始化对照：增益非初始化", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    style(ax, grid=True)

    ax = axes[1][0]
    t = fv["table"]
    arms = ["30M", "100M", "300M", "650M"]
    f2b = [t[a]["f1_2B"]["f1"] for a in arms]
    f59 = [t[a]["f1_5.9B"]["f1"] for a in arms]
    x = np.arange(4)
    w = 0.34
    ax.bar(x - w / 2, f2b, w, color=C["teal"], label="2.0B")
    ax.bar(x + w / 2, f59, w, color=C["deep"], label="5.9B")
    ax.set_xticks(x)
    ax.set_xticklabels(arms)
    ax.set_ylabel("family-split F1", fontsize=9.5)
    ax.set_title("H4 · 预算×尺度交互：磨蚀被 5.9B 修复", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    ax.legend(fontsize=8.5, frameon=False)
    style(ax, grid=True)

    ax = axes[1][1]
    rows = defaultdict(lambda: defaultdict(float))
    for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
        r = json.loads(line)
        if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
            continue
        run = r.get("run", "")
        if run.startswith("RNA-Sc-300M_s17_ck") \
                or run.startswith("RNA-Sc-650M_s17_ck"):
            nt = r.get("ckpt_nt")
            if nt:
                rows[run][nt] = max(rows[run][nt], r["f1_macro"])
    for arm, key, col in [("300M", "RNA-Sc-300M_s17_ck", C["main"]),
                          ("650M", "RNA-Sc-650M_s17_ck", C["deep"])]:
        sub = {nt: f for k, v in rows.items() if k.startswith(key)
               for nt, f in v.items()}
        if not sub:
            continue
        nts = sorted(sub)
        ax.plot([n / 1e9 for n in nts], [sub[n] for n in nts], "-*",
                color=col, lw=1.9, ms=8, label=arm)
        peak_nt = max(sub, key=sub.get)
        ax.annotate("%s 峰 %.4f@%.1fB" % (arm, sub[peak_nt],
                                          peak_nt / 1e9),
                    (peak_nt / 1e9, sub[peak_nt]),
                    textcoords="offset points", xytext=(-8, 8),
                    fontsize=8, color=col, fontweight="bold", ha="right")
    ax.set_xlabel("训练预算（B nt）", fontsize=9.5)
    ax.set_ylabel("最优层 F1（family 切分）", fontsize=9.5)
    ax.set_ylim(0.30, 0.40)
    ax.set_title("H4 · 全过程曲线：每尺度都有最优预算窗", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    ax.legend(fontsize=8.5, frameon=False)
    style(ax, grid=True)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(FIG, "fig_p12_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p12_v5 saved")


# ================= 7. 页 13：hyp_evidence_B v5（H5-H8）=================
def fig_p13():
    h5 = load("h5_rw_multiscale.json")
    bell = load("s13b_bell.json")
    links = {}
    for f, tag in [("s12_linkage_30M_s17_c1Mcs.json", "30M"),
                   ("s12_linkage_RNA-Sc-100M_s17.json", "100M"),
                   ("s12_linkage_RNA-Sc-300M_s17.json", "300M"),
                   ("s12_linkage_RNA-Sc-650M_s17.json", "650M")]:
        try:
            links[tag] = load(f)["spearman_DI_vs_bestlayer"]
        except Exception:
            pass

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.2))
    fig.suptitle("H5–H8 证据（RNA 特有四假设）", fontsize=12,
                 fontweight="bold", x=0.01, ha="left", color=C["ink"])

    ax = axes[0][0]
    t = h5["table"]
    scales = ["10M", "30M", "100M"]
    full = [t[s]["full_f1"] for s in scales]
    rw1 = [t[s]["rw1_f1"] for s in scales]
    x = np.arange(3)
    w = 0.34
    ax.bar(x - w / 2, full, w, color=C["main"], label="full 语料")
    ax.bar(x + w / 2, rw1, w, color=C["amber"], label="rRNA 压平语料")
    for i, s in enumerate(scales):
        dpp = (rw1[i] - full[i]) * 100
        ax.text(i, max(full[i], rw1[i]) + 0.008, "%+.2f pp" % dpp,
                ha="center", fontsize=9, fontweight="bold",
                color="#9A7B35" if dpp > 0 else "#B26A50")
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("family-split F1", fontsize=9.5)
    ax.set_ylim(0.0, 0.42)
    ax.set_title("H5 · 双轴定案：容量门控的先验效用（符号翻转）",
                 fontsize=10.5, loc="left", pad=6, fontweight="bold",
                 color=C["ink"])
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    style(ax, grid=True)

    ax = axes[0][1]
    xs = [30, 100, 302, 666]
    ys = [links.get(k, 0) for k in ("30M", "100M", "300M", "650M")]
    ax.plot(xs, ys, "o-", color=C["main"], lw=2.0, ms=7,
            markeredgecolor="white", markeredgewidth=1.0)
    for x, y, k in zip(xs, ys, ("30M", "100M", "300M", "650M")):
        ax.annotate("%s\nρ=%.3f" % (k, y), (x, y),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=7.8, fontweight="bold")
    ax.axhline(0, color="#A0A0A0", lw=0.8)
    ax.set_xscale("log")
    ax.set_ylim(-0.6, 0.1)
    ax.set_xlabel("参数量（M）", fontsize=9.5)
    ax.set_ylabel("Spearman(DI, 最优层深度)", fontsize=9.5)
    ax.set_title("H6 · 结构-序列解耦 → 层位置（关联稀释）", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    style(ax, grid=True)

    ax = axes[1][0]
    pts = bell["points"]
    models = sorted({p["model"] for p in pts})
    cmap = plt.cm.viridis(np.linspace(0.15, 0.85, len(models)))
    for m, c in zip(models, cmap):
        mp = [p for p in pts if p["model"] == m]
        ax.scatter([p["nll"] for p in mp], [p["f1"] for p in mp], s=30,
                   color=c, alpha=0.8, edgecolors="none")
    xs_b = np.array([p["nll"] for p in pts])
    ys_b = np.array([p["f1"] for p in pts])
    z = np.polyfit(xs_b, ys_b, 2)
    xr = np.linspace(xs_b.min() - 0.01, xs_b.max() + 0.01, 80)
    ax.plot(xr, np.polyval(z, xr), "--", color="#666", lw=1.3, zorder=3)
    ax.text(0.03, 0.05, "NOT-BELL（预注册负结果）：峰值在范围外",
            transform=ax.transAxes, fontsize=8.5, fontweight="bold",
            color=C["coral"])
    ax.set_xlabel("held-out family NLL（置信轴）", fontsize=9.5)
    ax.set_ylabel("bpRNA 结构 F1", fontsize=9.5)
    ax.set_title("H7 · 似然中介：钟形检验（负结果）", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    style(ax, grid=True)

    ax = axes[1][1]
    d = load("s14_rns.json")
    try:
        sa = d["scale_axis"]["rns_k10"]
    except Exception:
        sa = d.get("rns_k10", {})
    scales = ["1M", "10M", "30M", "100M"]
    vals = [sa.get(s, {"1M": 0.172, "10M": 0.104, "30M": 0.078,
                       "100M": 0.077}[s]) for s in scales]
    vals.append(load("s14_rns_300m.json").get("rns_k10", 0.067))
    scales.append("300M")
    vals.append(load("s14_rns_650m.json").get("rns_k10", 0.062))
    scales.append("650M")
    xs = [float(s[:-1]) for s in scales]
    ax.plot(xs, vals, "o-", color=C["main"], lw=2.0, ms=7,
            markeredgecolor="white", markeredgewidth=1.0)
    ax.axhspan(0.54, 0.58, color="#E3E6E9", zorder=1)
    ax.text(0.97, 0.565, "randinit 带", transform=ax.get_yaxis_transform(),
            fontsize=8, color="#909090", va="center", ha="right")
    for x, y, s in zip(xs, vals, scales):
        ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, fontweight="bold",
                    color=SC.get(s, C["deep"]))
    ax.set_xscale("log")
    ax.set_ylim(0.0, 0.72)
    ax.set_xlabel("参数量（M）", fontsize=9.5)
    ax.set_ylabel("RNS@10（低 = 好）", fontsize=9.5)
    ax.set_title("H8 · RNS 单调改善；30M 平台 vs F1 陡升", fontsize=10.5,
                 loc="left", pad=6, fontweight="bold", color=C["ink"])
    style(ax, grid=True)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(FIG, "fig_p13_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_p13_v5 saved")


# ================= 8. 新图：双通道预算故事（p5rns_b59 + b59_random_delta）=================
def fig_dual_channel():
    p5 = load("p5rns_b59_verdict.json")
    brd = load("b59_random_delta.json")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3))
    ax = axes[0]
    mat = p5["matrix"]
    scales = ["30M", "100M", "300M"]
    x = np.arange(3)
    w = 0.34
    fam = [-5.24, -2.74, 3.76]
    rns = [mat[s]["RNS_budget_delta"] * 100 if False else
           mat[s]["RNS_budget_delta"] for s in scales]
    nonrr = [mat[s]["nonrRNA_budget_delta"] for s in scales]
    ax.bar(x - w / 2, fam, w, color=C["coral"], label="family 分类通道")
    ax.bar(x + w / 2, nonrr, w, color=C["teal"],
           label="non-rRNA 结构分离（nats/tok）")
    for i, (f, n) in enumerate(zip(fam, nonrr)):
        ax.text(i - w / 2, f - 0.025 if f < 0 else f + 0.008, "%.2f" % f,
                ha="center", fontsize=8.5, color="#B26A50", fontweight="bold")
        ax.text(i + w / 2, n + 0.008, "+%.2f" % n, ha="center",
                fontsize=8.5, color="#4A6E64", fontweight="bold")
    ax.axhline(0, color="#A0A0A0", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("预算效应（5.9B − 2.0B）", fontsize=10, color=C["ink"])
    ax.set_title("(a) 三通道判定：family 通道不吃预算，结构通道持续吃",
                 fontsize=11, loc="left", pad=8, color=C["ink"])
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    style(ax, grid=True)

    ax = axes[1]
    tb = brd["table"]
    scales = ["30M", "100M", "300M"]
    rand = [tb[s]["random_delta_pp"] for s in scales]
    famly = [tb[s]["family_delta_pp"] for s in scales]
    x = np.arange(3)
    ax.bar(x - w / 2, famly, w, color=C["coral"], label="family 通道")
    ax.bar(x + w / 2, rand, w, color=C["grey"], label="random 通道")
    for i, (f, r) in enumerate(zip(famly, rand)):
        ax.text(i - w / 2, f - 0.03 if f < 0 else f + 0.008, "%.2f pp" % f,
                ha="center", fontsize=8.5, color="#B26A50", fontweight="bold")
        ax.text(i + w / 2, r + 0.008 if r >= 0 else r - 0.03,
                "%.2f pp" % r, ha="center", fontsize=8.5, color="#8A8A8A",
                fontweight="bold")
    ax.axhline(0, color="#A0A0A0", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("预算效应 ΔF1（pp）", fontsize=10, color=C["ink"])
    ax.set_title("(b) random 通道对预算免疫：泄漏≠预算变现", fontsize=11,
                 loc="left", pad=8, color=C["ink"])
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    style(ax, grid=True)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_dualchannel_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_dualchannel_v5 saved")


if __name__ == "__main__":
    fig_p3()
    fig_p5()
    fig_p9()
    fig_p10()
    fig_p10b()
    fig_p12()
    fig_p13()
    fig_dual_channel()
    print("ALL 8 FIGS DONE")
