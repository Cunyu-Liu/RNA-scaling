"""fig_p3_v5_r2: 页 3 图（Scaling 六档 + 层迁移双预算）升级。

与页 4 图的重复问题：页 3 改为"Scaling 主叙事"——
  (a) 六档 family F1（含 3-seed 均值）+ randinit 对照带（用户要求补的对照线）
  (b) 层迁移双预算哑铃（保留，但配色与页 4 区分）
页 4 保持"预算×尺度"专页（哑铃+复测柱）。数据源不变。
"""
import json
import os

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
     "ink": "#3A3A3A"}
SC = {"1M": "#C9CDD2", "10M": "#E5B45A", "30M": "#6FAE9B",
      "100M": "#7BA3C7", "300M": "#4878A8", "650M": "#2E5170"}


def style(ax, grid=True):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors=C["ink"], labelsize=8.5, length=3, width=0.7)
    if grid:
        ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
        ax.set_axisbelow(True)


def load(name):
    return json.load(open(os.path.join(E, name)))


fv = load("factorial_verdict.json")
s1 = load("s1_final_verdict.json")
s4 = load("s4_randinit_table.json")
t = fv["table"]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.3),
                               gridspec_kw={"width_ratios": [1, 1.1]})

# ---------- (a) Scaling 六档（3-seed 均值±std + randinit 对照）----------
scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
ft = s1["five_scale_table"]
means = [ft[s]["f1_mean"] if s in ft else None for s in scales]
stds = [ft[s]["f1_std"] if s in ft else None for s in scales]
# 300M/650M 单 seed
m300 = t["300M"]["f1_2B"]["f1"]
m650 = t["650M"]["f1_2B"]["f1"]
means = [ft["1M"]["f1_mean"], ft["10M"]["f1_mean"],
         ft["30M"]["f1_mean"], ft["100M"]["f1_mean"], m300, m650]
stds = [ft["1M"]["f1_std"], ft["10M"]["f1_std"], ft["30M"]["f1_std"],
        ft["100M"]["f1_std"], 0.0, 0.0]
ri = [s4[s]["randinit"] for s in scales]

xs = [1.0, 10.0, 30.0, 100.0, 302.0, 666.0]
axL.errorbar(xs, means, yerr=stds, fmt="o-", color=C["main"], lw=2.0,
             ms=7, capsize=3, elinewidth=1.0, capthick=1.0,
             label="family F1（1M-100M 3-seed；300M/650M s17）")
axL.plot(xs, ri, "v:", color=C["coral"], lw=1.5, ms=6,
         label="randinit 对照（同架构未预训练）")
axL.fill_between(xs, ri, means, color=C["main"], alpha=0.08)
for x, m, s in zip(xs, means, scales):
    axL.annotate(s, (x, m), textcoords="offset points", xytext=(0, 9),
                 ha="center", fontsize=8.5, fontweight="bold",
                 color=SC.get(s, C["ink"]))
# 增益标注
for x, m, r in zip(xs, means, ri):
    axL.annotate("+%.3f" % (m - r), (x, (m + r) / 2), ha="center",
                 fontsize=7.2, color="#5E7FA0")
axL.set_xscale("log")
axL.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
axL.set_ylabel("family-split probe F1", fontsize=10, color=C["ink"])
axL.set_title("(a) Scaling：六档 F1 与 randinit 对照", fontsize=11,
              loc="left", pad=8, color=C["ink"])
axL.legend(fontsize=8.6, frameon=False, loc="upper left")
style(axL)

# ---------- (b) 层迁移哑铃（保留原数据，配色区分页 4）----------
arms = ["30M", "100M", "300M", "650M"]
rel2b = [t[a]["f1_2B"]["rel"] for a in arms]
rel59 = [t[a]["f1_5.9B"]["rel"] for a in arms]
ys = np.arange(4)
for i, a in enumerate(arms):
    axR.plot([rel2b[i], rel59[i]], [i, i], "-", color="#D5D5D5",
             lw=2.2, zorder=1)
    axR.scatter(rel2b[i], i, s=95, color=C["teal"], zorder=3,
                edgecolors="white", linewidths=1.0)
    axR.scatter(rel59[i], i, s=120, color=C["amber"], marker="D", zorder=4,
                edgecolors="white", linewidths=1.0)
    axR.annotate("Δ%+.2f" % (rel59[i] - rel2b[i]),
                 ((rel2b[i] + rel59[i]) / 2, i + 0.22), ha="center",
                 fontsize=8.2, color="#707070")
axR.scatter([], [], s=95, color=C["teal"], label="2.0B")
axR.scatter([], [], s=120, color=C["amber"], marker="D", label="5.9B")
axR.set_yticks(ys)
axR.set_yticklabels(arms, fontsize=10)
axR.set_xlim(0, 1.08)
axR.set_xlabel("最优层相对深度", fontsize=10, color=C["ink"])
axR.set_title("(b) 层迁移：2B→5.9B 深层修复（650M L8→L25）", fontsize=11,
              loc="left", pad=8, color=C["ink"])
axR.legend(fontsize=9, frameon=False, loc="lower right")
axR.invert_yaxis()
style(axR, grid=False)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_p3_v5_r2.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p3_v5_r2 saved")
