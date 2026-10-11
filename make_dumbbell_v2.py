"""fig_layer_budget_dumbbell v2：加 3-seed 复测标注（口径分离）。

图主体保持 inc12 正式协议数据（seed17 单次：650M +1.15pp），
但给 650M 柱加复测标注框：3-seed 复测均值 0.4464±0.012
（650M 领先 300M +6.4pp，seed17 的 650M<300M 为 probe 波动）。
同时哑铃面板 A 的 650M 注释补充复测最优层窗口 L24-27。
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
C_GREEN = "#1B7A3D"

arms = ["30M", "100M", "300M", "650M"]
l2b = [t[a]["f1_2B"]["layer"] for a in arms]
l59 = [t[a]["f1_5.9B"]["layer"] for a in arms]
f2b = [t[a]["f1_2B"]["f1"] for a in arms]
f59 = [t[a]["f1_5.9B"]["f1"] for a in arms]
deltas = [t[a]["budget_delta_pp"] for a in arms]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.6),
                               gridspec_kw={"width_ratios": [1, 1]})

# ---------- 面板 A：最优层哑铃 ----------
y = np.arange(len(arms))
for i in range(len(arms)):
    axA.plot([l2b[i], l59[i]], [y[i], y[i]], color=C_GREY, lw=2.5,
             zorder=1, alpha=0.6)
    axA.scatter(l2b[i], y[i], s=140, color=C_2B, zorder=3, marker="o")
    axA.scatter(l59[i], y[i], s=150, color=C_59B, zorder=3, marker="D")
    axA.annotate("L%d" % l2b[i], (l2b[i], y[i] + 0.22), fontsize=10,
                 ha="center", color=C_2B, fontweight="bold")
    axA.annotate("L%d" % l59[i], (l59[i], y[i] + 0.22), fontsize=10,
                 ha="center", color=C_59B, fontweight="bold")
axA.axvspan(0, 27 * 0.33, color="#f5f5f5", zorder=0)
axA.annotate("650M 深度反转：预算翻倍\n最优层 L8（30%）→ L25（93%）\n复测最优层窗口 L24-27（深层带）",
             xy=(16, 3), xytext=(1.5, 2.45), fontsize=9.5, color=C_59B,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.6))
axA.set_yticks(y)
axA.set_yticklabels(arms, fontsize=11)
axA.invert_yaxis()
axA.set_xlabel("probe 最优层位置（层号）", fontsize=10.5)
axA.set_title("A. 各尺度最优层：2B（●）→ 5.9B（◆）", fontsize=11.5, pad=10)
axA.set_xlim(-0.5, 28)
axA.spines[["top", "right"]].set_visible(False)

# ---------- 面板 B：F1 对比（正式协议 + 复测标注）----------
x = np.arange(len(arms))
w = 0.38
axB.bar(x - w / 2, f2b, w, color=C_2B, label="2.0B")
axB.bar(x + w / 2, f59, w, color=C_59B, label="5.9B")
for i in range(len(arms)):
    axB.text(i - w / 2, f2b[i] + 0.006, "%.4f" % f2b[i], ha="center",
             fontsize=9, color=C_2B, fontweight="bold")
    axB.text(i + w / 2, f59[i] + 0.006, "%.4f" % f59[i], ha="center",
             fontsize=9, color=C_59B, fontweight="bold")
    sign = "+" if deltas[i] > 0 else "−"
    col = C_GREEN if deltas[i] > 0 else C_GREY
    axB.text(i, max(f2b[i], f59[i]) + 0.026,
             "%s%.2fpp" % (sign, abs(deltas[i])),
             ha="center", fontsize=10.5, color=col, fontweight="bold")

# 650M 复测标注框
axB.annotate("3-seed 复测（8000/4000）：650M 0.4464±0.012\n"
             "vs 300M 0.3826±0.013 → 650M 领先 +6.4pp\n"
             "（seed17 单次的 650M<300M 系 probe 波动）",
             xy=(3 + w / 2, f59[3]), xytext=(1.15, 0.445),
             fontsize=9, color=C_GREEN, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.4),
             bbox=dict(boxstyle="round,pad=0.35", fc="#F0F9F0",
                       ec=C_GREEN, lw=1.0))
# 复测均值虚线柱（650M）
axB.bar(3 + w / 2, 0.4464, w * 0.55, color=C_GREEN, alpha=0.55,
        hatch="//", zorder=2, label="650M 复测均值")
axB.legend(fontsize=9, frameon=False, loc="upper left")
axB.set_xticks(x)
axB.set_xticklabels(arms, fontsize=11)
axB.set_ylim(0.15, 0.50)
axB.set_ylabel("family 切分 rna_type F1（各自最优层）", fontsize=10)
axB.set_title("B. 预算效应：小尺度受损、300M 起受益\n（650M 柱为 inc12 单次；绿虚线 = 3-seed 复测均值）",
              fontsize=10.5, pad=10)
axB.spines[["top", "right"]].set_visible(False)
axB.text(0.02, 0.03,
         "inc12 协议：final-ckpt probe，family 切分，最优层；复测 seed 29/43/61",
         transform=axB.transAxes, fontsize=8, color="#555")

fig.suptitle("预算 × 尺度 × 层迁移（析因 4/4 + 650M 3-seed 复测）：深度反转是欠训伪象",
             fontsize=13, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig_layer_budget_dumbbell_v2.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
