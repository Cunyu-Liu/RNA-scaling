"""双预算层迁移图：4 尺度 × 2B/5.9B 最优层位置（2026-10-10 用户需求）。

回应"页 3 和页 4 都没看到 650M 的更新，各参数量的最优层的 2b 和 5.9b
分别画个图"。

面板 A（最优层位置哑铃图）：
  每个尺度一根线：2B 最优层（蓝点）→ 5.9B 最优层（红点），
  直观看预算翻倍把最优层推向哪里。650M 的 8→25 是最戏剧性的。
  背景灰带标注"浅/中/深"区。

面板 B（最优层处 F1 对比）：
  分组柱：2B vs 5.9B 在各自最优层的 F1 —— 预算效应一图全览
  （30M/100M 负、300M/650M 正，U 型右半完整）。

数据源：evidence/factorial_verdict.json（inc12 协议，4/4 收口）。
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
nl = {"30M": 12, "100M": 23, "300M": 24, "650M": 27}
n_layers = [nl[a] for a in arms]
deltas = [t[a]["budget_delta_pp"] for a in arms]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.4),
                               gridspec_kw={"width_ratios": [1, 1]})

# ---------- 面板 A：最优层位置哑铃 ----------
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
    axA.annotate("%.0f%%" % (100 * t[arms[i]]["f1_2B"]["rel"]),
                 (l2b[i], y[i] - 0.30), fontsize=8, ha="center", color=C_2B)
    axA.annotate("%.0f%%" % (100 * t[arms[i]]["f1_5.9B"]["rel"]),
                 (l59[i], y[i] - 0.30), fontsize=8, ha="center", color=C_59B)
# 深浅带
for frac, lab in [(0.33, "浅层带"), (0.66, None)]:
    axA.axvline(max(n_layers) * frac, color="#ddd", lw=0.8, ls=":")
axA.axvspan(0, max(n_layers) * 0.33, color="#f5f5f5", zorder=0)
axA.text(max(n_layers) * 0.16, 3.62, "浅", fontsize=9, color="#aaa",
         ha="center")
axA.text(max(n_layers) * 0.5, 3.62, "中层带", fontsize=9, color="#aaa",
         ha="center")
axA.text(max(n_layers) * 0.84, 3.62, "深层带", fontsize=9, color="#aaa",
         ha="center")
# 650M 高亮标注
axA.annotate("650M 深度反转：预算翻倍\n最优层 L8（30%）→ L25（93%）",
             xy=(16, 3), xytext=(2.5, 2.55), fontsize=10, color=C_59B,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.6))
axA.set_yticks(y)
axA.set_yticklabels(arms, fontsize=11)
axA.invert_yaxis()
axA.set_xlabel("probe 最优层位置（层号）", fontsize=10.5)
axA.set_title("A. 各尺度最优层：2B（●）→ 5.9B（◆）", fontsize=11.5, pad=10)
axA.set_xlim(-0.5, max(n_layers) + 0.5)
axA.spines[["top", "right"]].set_visible(False)

# ---------- 面板 B：最优层 F1 对比 ----------
x = np.arange(len(arms))
w = 0.38
axB.bar(x - w/2, f2b, w, color=C_2B, label="2.0B")
axB.bar(x + w/2, f59, w, color=C_59B, label="5.9B")
for i in range(len(arms)):
    axB.text(i - w/2, f2b[i] + 0.006, "%.4f" % f2b[i], ha="center",
             fontsize=9, color=C_2B, fontweight="bold")
    axB.text(i + w/2, f59[i] + 0.006, "%.4f" % f59[i], ha="center",
             fontsize=9, color=C_59B, fontweight="bold")
    sign = "+" if deltas[i] > 0 else "−"
    col = C_GREEN if deltas[i] > 0 else C_GREY
    axB.text(i, max(f2b[i], f59[i]) + 0.026, "%s%.2fpp" % (sign, abs(deltas[i])),
             ha="center", fontsize=10.5, color=col, fontweight="bold")
axB.set_xticks(x)
axB.set_xticklabels(arms, fontsize=11)
axB.set_ylim(0.15, 0.44)
axB.set_ylabel("family 切分 rna_type F1（各自最优层）", fontsize=10)
axB.set_title("B. 预算效应：小尺度受损、300M 起受益（U 型右半完整）",
              fontsize=11.5, pad=10)
axB.legend(fontsize=10, frameon=False, loc="upper left")
axB.spines[["top", "right"]].set_visible(False)
axB.text(0.02, 0.03, "inc12 协议：final-ckpt probe，family 切分，最优层；4/4 收口 2026-10-10",
         transform=axB.transAxes, fontsize=8, color="#555")

fig.suptitle("预算 × 尺度 × 层迁移（析因 4/4 收口）：650M 深度反转是欠训伪象",
             fontsize=13, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig_layer_budget_dumbbell.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
print("layers 2B:", l2b, "5.9B:", l59)
print("f1 2B:", f2b, "5.9B:", f59)
