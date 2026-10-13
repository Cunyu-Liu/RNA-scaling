"""批次 2：需求轮 6 的 5 张近图统一到 v5 色板（内容不变，视觉升级）。

图（与 make_v5_figs.py 同一风格系统）：
  fig_dumbbell_v5  页 4（图 B 复测覆盖 + 图 A 四尺度哑铃）
  fig_cov_v5       页 6（COV 双面板：六尺度曲线 + 涌现三判据）
  fig_h4_v5        页 12（H4 全过程曲线 + 双预算最优层）
  fig_gapbridge_v5 页 8（三策略 × 两模型 + 缺口定位）
  fig_s8pair_v5    页 7（热图 + 条形图新配色版，横向并列）
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

C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A", "line": "#D5D5D5"}
SC = {"1M": "#C9CDD2", "10M": "#E5B45A", "30M": "#6FAE9B",
      "100M": "#7BA3C7", "300M": "#4878A8", "650M": "#2E5170"}


def style(ax, grid=False):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors=C["ink"], labelsize=8.5, length=3, width=0.7)
    if grid:
        ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
        ax.set_axisbelow(True)


def load(name):
    return json.load(open(os.path.join(E, name)))


# ================= 页 4：dumbbell v5 =================
def fig_dumbbell_v5():
    fv = load("factorial_verdict.json")
    t = fv["table"]
    cav = load("corpus_arm_verdict.json")
    f59 = {"300M": 0.3826, "650M": 0.4464}
    f59d = {"300M": 0.013, "650M": 0.012}

    arms = ["30M", "100M", "300M", "650M"]
    f2b = [t[a]["f1_2B"]["f1"] for a in arms]
    l2b = [t[a]["f1_2B"]["layer"] for a in arms]
    l59 = [t[a]["f1_5.9B"]["layer"] for a in arms]
    deltas = [-5.24, -2.74, 3.76, 8.32]
    corpus = {a: cav["table"][a]["delta_pp"] for a in
              ("30M", "100M", "300M")}

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.2),
                                   gridspec_kw={"width_ratios": [1, 1.1]})

    ys = np.arange(4)
    for i, a in enumerate(arms):
        xa, xb = f2b[i], f2b[i] + deltas[i] / 100
        axA.plot([xa, xb], [i, i], "-", color=C["line"], lw=2.4, zorder=1)
        axA.scatter(xa, i, s=95, color=C["teal"], zorder=3,
                    edgecolors="white", linewidths=1.0)
        axA.scatter(xb, i, s=115, color=C["deep"], marker="D", zorder=4,
                    edgecolors="white", linewidths=1.0)
        axA.annotate("%+.2f pp" % deltas[i],
                     ((xa + xb) / 2, i + 0.18), ha="center", fontsize=8.6,
                     color="#5A7A96" if deltas[i] > 0 else "#B08878")
    axA.scatter([], [], s=95, color=C["teal"], label="2.0B")
    axA.scatter([], [], s=115, color=C["deep"], marker="D", label="5.9B")
    axA.set_yticks(ys)
    axA.set_yticklabels(arms, fontsize=10)
    axA.invert_yaxis()
    axA.set_xlabel("family-split probe F1", fontsize=10, color=C["ink"])
    axA.set_title("(a) 预算×尺度哑铃：2B → 5.9B（3-seed 复测覆盖）",
                  fontsize=11, loc="left", pad=8, color=C["ink"])
    axA.legend(fontsize=9, frameon=False, loc="lower left")
    style(axA)

    x = np.arange(4)
    w = 0.34
    axB.bar(x - w / 2, f2b, w, color=C["teal"], label="2.0B")
    bars59 = [f2b[0] + deltas[0] / 100, f2b[1] + deltas[1] / 100,
              f59["300M"], f59["650M"]]
    axB.bar(x + w / 2, bars59, w, color=C["deep"], label="5.9B（复测）")
    for i in range(4):
        axB.text(i - w / 2, f2b[i] + 0.006, "L%d" % l2b[i], ha="center",
                 fontsize=8.5, color="#4A6E64", fontweight="bold")
        axB.text(i + w / 2, bars59[i] + 0.006, "L%d" % l59[i], ha="center",
                 fontsize=8.5, color=C["deep"], fontweight="bold")
    axB.set_xticks(x)
    axB.set_xticklabels(arms, fontsize=10)
    axB.set_ylabel("family-split probe F1", fontsize=10, color=C["ink"])
    axB.set_ylim(0, 0.56)
    axB.annotate("650M：5.9B 复测 0.4464（+8.32pp）",
                 xy=(3 + w / 2, bars59[3]), xytext=(1.35, 0.51),
                 fontsize=9.2, color=C["coral"],
                 arrowprops=dict(arrowstyle="->", color=C["coral"], lw=1.1))
    axB.set_title("(b) 5.9B 复测覆盖：650M 增益为真（3-seed）",
                  fontsize=11, loc="left", pad=8, color=C["ink"])
    axB.legend(fontsize=9, frameon=False, loc="upper left")
    style(axB)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_dumbbell_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_dumbbell_v5 saved")


# ================= 页 6：COV v5 =================
def fig_cov_v5():
    cov = load("covariation_test.json")
    cov650 = load("covariation_test_650M.json")
    scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
    vals = {}
    for s in scales:
        if s in cov:
            vals[s] = cov[s]["cov_minus_ctrl"]
        else:
            vals[s] = cov650["650M"]["cov_minus_ctrl"]
    ri = cov650["650M_randinit17"]["cov_minus_ctrl"]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.2),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    xs = [float(s[:-1]) for s in scales]
    ys = [vals[s] for s in scales]
    axL.plot(xs, ys, "o-", color=C["main"], lw=2.0, ms=8,
             markeredgecolor="white", markeredgewidth=1.2)
    axL.fill_between(xs, 0, ys, color=C["main"], alpha=0.08)
    axL.scatter([xs[4]], [ys[4]], s=140, color=C["amber"], zorder=5,
                edgecolors="white", linewidths=1.4)
    axL.annotate("300M 新补\n+0.047", (xs[4], ys[4]),
                 textcoords="offset points", xytext=(0, 16), ha="center",
                 fontsize=9, color="#9A7B35", fontweight="bold")
    axL.scatter([xs[5]], [ys[5]], s=120, color=C["deep"], zorder=5,
                edgecolors="white", linewidths=1.2)
    axL.annotate("650M +0.096", (xs[5], ys[5]), textcoords="offset points",
                 xytext=(-12, 10), ha="right", fontsize=9, color=C["deep"],
                 fontweight="bold")
    for x, y, s in zip(xs, ys, scales):
        axL.annotate(s, (x, y), textcoords="offset points",
                     xytext=(0, -15), ha="center", fontsize=8.2,
                     color=SC.get(s, C["ink"]))
    axL.axhline(ri, ls=":", lw=1.1, color=C["coral"])
    axL.text(0.98, 0.004, "randinit 基线 ≈ 0", fontsize=8, color=C["coral"],
             ha="right", va="bottom", transform=axL.get_yaxis_transform())
    axL.set_xscale("log")
    axL.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
    axL.set_ylabel("前向 COV − CTRL", fontsize=10, color=C["ink"])
    axL.set_title("(a) 前向共变：六尺度单调链（300M 补全）", fontsize=11,
                  loc="left", pad=8, color=C["ink"])
    style(axL, grid=True)

    axR.set_xlim(0, 1)
    axR.set_ylim(0, 1)
    axR.axis("off")
    rows = [
        ("判据 1 · 零基线", "randinit 对照 ≈ 0（4e-05）\n前向信号全部来自训练", C["teal"]),
        ("判据 2 · 效率反升", "大尺度段每参数增益反升\n（0.047→0.096 斜率超线性）", C["main"]),
        ("判据 3 · 撞穿读出墙", "前向 0.096 = 线性读出的 4 倍\n知识存了但线性读不出", C["deep"]),
    ]
    y = 0.92
    for title, body, col in rows:
        axR.text(0.02, y, title, fontsize=10.5, fontweight="bold", color=col,
                 transform=axR.transAxes, va="top")
        axR.text(0.05, y - 0.075, body, fontsize=9, color="#4A4A4A",
                 transform=axR.transAxes, va="top", linespacing=1.55)
        y -= 0.31
    axR.text(0.02, 0.03, "涌现的是知识存储，不是可读出性", fontsize=9.5,
             fontweight="bold", color=C["ink"], transform=axR.transAxes)
    axR.set_title("(b) 为什么 +0.096 构成涌现（三判据）", fontsize=11,
                  loc="left", pad=8, color=C["ink"])

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_cov_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_cov_v5 saved")


# ================= 页 12：H4 v5 =================
def fig_h4_v5():
    s6 = load("s6_cross_scale.json")
    fv = load("factorial_verdict.json")

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

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.8, 4.4))

    for arm in ["1M", "10M", "30M", "100M"]:
        pts = s6[arm]
        axL.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
                 color=SC[arm], lw=1.7, marker="o", ms=3.5, label=arm)
    for arm, key, col in [("300M", "RNA-Sc-300M_s17_ck", C["main"]),
                          ("650M", "RNA-Sc-650M_s17_ck", C["deep"])]:
        sub = {nt: f for k, v in rows.items() if k.startswith(key)
               for nt, f in v.items()}
        if not sub:
            continue
        nts = sorted(sub)
        axL.plot([n / 1e9 for n in nts], [sub[n] for n in nts],
                 color=col, lw=2.2, marker="*", ms=9,
                 label=arm + "（新）")
        peak = max(sub, key=sub.get)
        axL.annotate("%s 峰 %.4f" % (arm, sub[peak]),
                     (peak / 1e9, sub[peak]),
                     textcoords="offset points", xytext=(-4, 8),
                     fontsize=8, color=col, fontweight="bold", ha="right")
    axL.axvline(0.35, color="#9A7B35", ls=":", lw=1.0)
    axL.text(0.37, 0.12, "10M 磨蚀谷窗口", fontsize=8, color="#9A7B35",
             rotation=90, va="bottom")
    axL.set_xlabel("训练预算（B nt）", fontsize=10, color=C["ink"])
    axL.set_ylabel("最优层 F1（family 切分）", fontsize=10, color=C["ink"])
    axL.set_ylim(0.10, 0.42)
    axL.set_title("H4 涌现时间线：六尺度全过程（650M 5 点补全）",
                  fontsize=11, loc="left", pad=8, color=C["ink"])
    axL.legend(fontsize=8.2, frameon=False, loc="lower right", ncol=2)
    style(axL, grid=True)

    t = fv["table"]
    arms = ["30M", "100M", "300M", "650M"]
    rel2b = [t[a]["f1_2B"]["rel"] for a in arms]
    rel59 = [t[a]["f1_5.9B"]["rel"] for a in arms]
    x = range(4)
    w = 0.38
    axR.bar([i - w / 2 for i in x], rel2b, w, color=C["teal"],
            label="2.0B 最优层深度")
    axR.bar([i + w / 2 for i in x], rel59, w, color=C["deep"],
            label="5.9B 最优层深度")
    for i in range(4):
        axR.text(i - w / 2, rel2b[i] + 0.02, "L%d" % t[arms[i]]["f1_2B"]["layer"],
                 ha="center", fontsize=9.5, color="#4A6E64", fontweight="bold")
        axR.text(i + w / 2, rel59[i] + 0.02, "L%d" % t[arms[i]]["f1_5.9B"]["layer"],
                 ha="center", fontsize=9.5, color=C["deep"], fontweight="bold")
    axR.set_xticks(list(x))
    axR.set_xticklabels(arms, fontsize=10)
    axR.set_ylim(0, 1.12)
    axR.set_ylabel("最优层相对深度", fontsize=10, color=C["ink"])
    axR.set_title("H4 链②：5.9B 修复 650M 磨蚀（L8→L25）", fontsize=11,
                  loc="left", pad=8, color=C["ink"])
    axR.legend(fontsize=9.5, frameon=False, loc="upper left")
    style(axR)
    axR.annotate("磨蚀被预算修复", xy=(3 + w / 2, rel59[3]), xytext=(1.9, 0.55),
                 fontsize=9.5, color=C["coral"],
                 arrowprops=dict(arrowstyle="->", color=C["coral"], lw=1.1))

    fig.suptitle("H4 磨蚀/容量门控：全过程曲线 + 双预算证据", fontsize=12,
                 y=1.0, color=C["ink"])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_h4_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_h4_v5 saved")


# ================= 页 8：gapbridge v5 =================
def fig_gapbridge_v5():
    d = load("gapbridge_decoder_v2.json")
    m = d["models"]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.2),
                                   gridspec_kw={"width_ratios": [1.2, 1]})

    labels = ["A: top-L 贪心\n（S8 基线）", "B: +非交叉 DP\n（top-2L 约束）",
              "C: B + 环长≥3\n（结构先验）"]
    x = np.arange(3)
    w = 0.36
    v650 = [m["650M"]["A_topL"], m["650M"]["B_top2L_dp"],
            m["650M"]["C_top2L_dp_loop3"]]
    v300 = [m["300M"]["A_topL"], m["300M"]["B_top2L_dp"],
            m["300M"]["C_top2L_dp_loop3"]]
    axL.bar(x - w / 2, v650, w, color=C["main"], label="650M")
    axL.bar(x + w / 2, v300, w, color=C["amber"], label="300M")
    for i, (a, b) in enumerate(zip(v650, v300)):
        axL.text(i - w / 2, a + 0.0005, "%.4f" % a, ha="center", fontsize=9,
                 color=C["main"], fontweight="bold")
        axL.text(i + w / 2, b + 0.0005, "%.4f" % b, ha="center", fontsize=9,
                 color="#9A7B35", fontweight="bold")
    axL.set_xticks(x)
    axL.set_xticklabels(labels, fontsize=9.5)
    axL.set_ylim(0, 0.026)
    axL.set_ylabel("pair-F1（bpRNA 测试集）", fontsize=10, color=C["ink"])
    axL.set_title("(a) 解码器 gap-bridge：结构约束反而降精度", fontsize=11,
                  loc="left", pad=8, color=C["ink"])
    axL.legend(fontsize=9.5, frameon=False, loc="upper right")
    style(axL)
    axL.annotate("DP 丢一半精度：\n0.0190 → 0.0078", xy=(1, v650[1]),
                 xytext=(0.6, 0.0215), fontsize=9.5, color=C["coral"],
                 fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=C["coral"], lw=1.2))

    axR.set_xlim(0, 1)
    axR.set_ylim(0, 1)
    axR.axis("off")
    rows = [
        ("实验问句", "「缺配对解码器」→ 随便加个 DP 就能解吗？", C["ink"]),
        ("结果", "A 贪心 0.019 → B 非交叉 DP 0.0078\n300M 同构（0.0148→0.0038）", C["coral"]),
        ("为什么", "弱分数下 DP 全局最优被噪声带偏\nv5 的 0.20 依赖训练过的强分数", "#707070"),
        ("缺口定位", "缺的不是解码算法，是\n「与表征联合训练的配对网络」", C["deep"]),
    ]
    y = 0.94
    for title, body, col in rows:
        axR.text(0.02, y, title, fontsize=10.5, fontweight="bold", color=col,
                 transform=axR.transAxes, va="top")
        axR.text(0.05, y - 0.07, body, fontsize=9, color="#4A4A4A",
                 transform=axR.transAxes, va="top", linespacing=1.5)
        y -= 0.24
    axR.set_title("(b) gap 的精确定位：需联合训练的配对网络", fontsize=11,
                  loc="left", pad=8, color=C["ink"])

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_gapbridge_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_gapbridge_v5 saved")


# ================= 页 7：S8 热图 + 条形图 v5 =================
def fig_s8pair_v5():
    heat = load("s8_attention_heatmap.json")
    s8 = load("s8_contact.json")
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.6, 4.4),
                                   gridspec_kw={"width_ratios": [1.1, 1]})

    mat = heat["trained"]
    ri_mat = heat["randinit"]
    diff = np.array(mat) - np.array(ri_mat)
    im = axL.imshow(diff, aspect="auto", cmap="RdBu_r",
                    vmin=-np.abs(diff).max(), vmax=np.abs(diff).max())
    cb = fig.colorbar(im, ax=axL, fraction=0.045, pad=0.02)
    cb.set_label("Δr（训练 − randinit）", fontsize=8.5)
    cb.ax.tick_params(labelsize=7.5)
    axL.set_xlabel("head", fontsize=9.5, color=C["ink"])
    axL.set_ylabel("layer", fontsize=9.5, color=C["ink"])
    pk = np.unravel_index(np.argmax(diff), diff.shape)
    axL.annotate("峰值 Δr @L%dH%d" % (pk[0], pk[1]),
                 (pk[1], pk[0]), fontsize=8.5, color=C["ink"],
                 ha="center", va="bottom",
                 xytext=(pk[1], pk[0] + 2.5),
                 arrowprops=dict(arrowstyle="->", color=C["ink"], lw=0.9))
    axL.set_title("(a) 训练增益热图：650M（Δr = trained − randinit）",
                  fontsize=10.5, loc="left", pad=8, color=C["ink"])

    scales = ["30M", "100M", "650M"]
    prec = [s8["models"][s] for s in scales]
    fold = [s8["fold_over_chance"][s] for s in scales]
    ri_fold = [s8["randinit_fold"][s] for s in scales]
    rand = s8["chance_baseline"]
    x = np.arange(4)
    labels = scales + ["100M\nrinalmo 语料"]
    all_prec = prec + [s8["models"]["100M-rinalmo语料"]]
    all_fold = fold + [s8["fold_over_chance"]["100M-rinalmo语料"]]
    cols = [C["main"], C["main"], C["deep"], C["teal"]]
    axR.bar(x, all_prec, 0.55, color=cols)
    axR.axhline(rand, ls=":", lw=1.3, color=C["coral"])
    axR.text(3.45, rand + 0.00012, "随机基线 0.00444", fontsize=8.5,
             color=C["coral"], ha="right")
    for i, (p, r) in enumerate(zip(all_prec, all_fold)):
        axR.text(i, p + 0.00018, "%.2f×" % r, ha="center", fontsize=9.2,
                 fontweight="bold", color=C["deep"])
    axR.set_xticks(x)
    axR.set_xticklabels(labels, fontsize=9)
    axR.set_ylabel("接触对预测精度", fontsize=10, color=C["ink"])
    axR.set_ylim(0, 0.0082)
    axR.set_title("(b) 精度尺度轴：30M→650M 1.19×→1.53×（语料 +9%）",
                  fontsize=10.5, loc="left", pad=8, color=C["ink"])
    style(axR)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_s8pair_v5.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("fig_s8pair_v5 saved")


if __name__ == "__main__":
    fig_dumbbell_v5()
    fig_cov_v5()
    fig_h4_v5()
    fig_gapbridge_v5()
    fig_s8pair_v5()
    print("BATCH2 DONE")
