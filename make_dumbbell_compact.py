"""页 3 用的紧凑版哑铃图：各尺度最优层 2B vs 5.9B（单面板，7.2:2.0 比例）。

用户需求："各个参数量的最优层的 2b 和 5.9b 可以分别画个图看看"
放置：页 3（结果① 层迁移主题）左下图位（0.5, 4.42, 7.2 x 2.05）。
数据源：evidence/factorial_verdict.json
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

fv = json.load(open(os.path.join(E, "factorial_verdict.json")))
t = fv["table"]

C_2B = "#2F5C8F"
C_59B = "#B03030"
C_GREY = "#8A8A8A"

arms = ["30M", "100M", "300M", "650M"]
l2b = [t[a]["f1_2B"]["layer"] for a in arms]
l59 = [t[a]["f1_5.9B"]["layer"] for a in arms]

fig, ax = plt.subplots(figsize=(7.2, 2.05))
y = np.arange(len(arms))
for i in range(len(arms)):
    ax.plot([l2b[i], l59[i]], [y[i], y[i]], color=C_GREY, lw=2,
            zorder=1, alpha=0.65)
    ax.scatter(l2b[i], y[i], s=70, color=C_2B, zorder=3, marker="o")
    ax.scatter(l59[i], y[i], s=75, color=C_59B, zorder=3, marker="D")
    ax.annotate("L%d" % l2b[i], (l2b[i], y[i] + 0.18), fontsize=8.5,
                ha="center", color=C_2B, fontweight="bold")
    ax.annotate("L%d" % l59[i], (l59[i], y[i] + 0.18), fontsize=8.5,
                ha="center", color=C_59B, fontweight="bold")
ax.annotate("650M 深度反转：L8→L25（30%→93%）\n预算翻倍修复回浅",
            xy=(16, 3), xytext=(1.2, 3.35), fontsize=8.5, color=C_59B,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.3))
ax.set_yticks(y)
ax.set_yticklabels(arms, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("probe 最优层位置（2B ● / 5.9B ◆）", fontsize=8.5)
ax.set_title("各尺度最优层：2.0B → 5.9B（预算翻倍的层迁移效应）",
             fontsize=9.5, pad=4)
ax.set_xlim(-0.5, 27.5)
ax.set_ylim(3.75, -0.55)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(pad=0.4)
out = os.path.join(FIG, "fig_layer_dumbbell_compact.png")
fig.savefig(out, dpi=220, bbox_inches="tight")
print("saved", out)
