"""fig_layer_budget v3（用户需求轮 6）：
图 B：650M 复测值直接覆盖正式柱（去掉绿虚线双轨）。
图 A：三尺度 2B→5.9B 哑铃，300M 的 2B 点明确加粗显示。
数据：factorial_verdict（2B 正式）+ b59_reseed（650M 复测均值 0.4464）。
650M 5.9B 柱高直接用复测均值（用户指定覆盖），delta 标注同步换算。
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
# 650M 5.9B 用复测均值（用户指定覆盖）
f59_650m = 0.4464

C_2B = "#2F5C8F"
C_59B = "#B03030"
C_GREY = "#8A8A8A"
C_GREEN = "#1B7A3D"

arms = ["30M", "100M", "300M", "650M"]
l2b = [t[a]["f1_2B"]["layer"] for a in arms]
l59 = [t[a]["f1_5.9B"]["layer"] for a in arms]
f2b = [t[a]["f1_2B"]["f1"] for a in arms]
f59 = [t[a]["f1_5.9B"]["f1"] for a in arms]
f59[3] = f59_650m  # 650M 覆盖
deltas = [round(100 * (b - a), 2) for a, b in zip(f2b, f59)]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.6))

# ---------- 面板 A：哑铃（2B→5.9B，全部四尺度，300M 明确标注）----------
y = np.arange(len(arms))
for i in range(len(arms)):
    axA.plot([l2b[i], l59[i]], [y[i], y[i]], color=C_GREY, lw=2.5,
             zorder=1, alpha=0.65)
    axA.scatter(l2b[i], y[i], s=150, color=C_2B, zorder=3, marker="o",
                edgecolors="white", linewidths=1.2)
    axA.scatter(l59[i], y[i], s=160, color=C_59B, zorder=3, marker="D",
                edgecolors="white", linewidths=1.0)
    axA.annotate("2B: L%d" % l2b[i], (l2b[i], y[i] + 0.24), fontsize=9.5,
                 ha="center", color=C_2B, fontweight="bold")
    axA.annotate("5.9B: L%d" % l59[i], (l59[i], y[i] + 0.24), fontsize=9.5,
                 ha="center", color=C_59B, fontweight="bold")
axA.axvspan(0, 27 * 0.33, color="#f5f5f5", zorder=0)
axA.annotate("650M 深度反转：L8→L25\n（300M 稳定深层 L22→L22）",
             xy=(16, 3), xytext=(1.0, 2.5), fontsize=9.5, color=C_59B,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.6))
axA.set_yticks(y)
axA.set_yticklabels(arms, fontsize=11)
axA.invert_yaxis()
axA.set_xlabel("probe 最优层位置（2B ● / 5.9B ◆）", fontsize=10.5)
axA.set_title("A. 各尺度最优层：2B → 5.9B（四尺度全量）", fontsize=11.5,
              pad=10)
axA.set_xlim(-0.5, 28)
axA.spines[["top", "right"]].set_visible(False)

# ---------- 面板 B：F1（650M 复测直接覆盖）----------
x = np.arange(len(arms))
w = 0.38
axB.bar(x - w / 2, f2b, w, color=C_2B, label="2.0B")
axB.bar(x + w / 2, f59, w, color=C_59B, label="5.9B")
for i in range(len(arms)):
    axB.text(i - w / 2, f2b[i] + 0.006, "%.4f" % f2b[i], ha="center",
             fontsize=9, color=C_2B, fontweight="bold")
    tag = "*" if i == 3 else ""
    axB.text(i + w / 2, f59[i] + 0.006, tag + "%.4f" % f59[i],
             ha="center", fontsize=9, color=C_59B, fontweight="bold")
    sign = "+" if deltas[i] > 0 else "−"
    col = C_GREEN if deltas[i] > 0 else C_GREY
    axB.text(i, max(f2b[i], f59[i]) + 0.026,
             "%s%.2fpp" % (sign, abs(deltas[i])),
             ha="center", fontsize=10.5, color=col, fontweight="bold")
axB.set_xticks(x)
axB.set_xticklabels(arms, fontsize=11)
axB.set_ylim(0.15, 0.52)
axB.set_ylabel("family 切分 rna_type F1（各自最优层）", fontsize=10)
axB.set_title("B. 预算效应：小尺度受损、300M 起受益\n（*650M@5.9B = 3-seed 复测均值，已覆盖）",
              fontsize=10.5, pad=10)
axB.legend(fontsize=9.5, frameon=False, loc="upper left")
axB.spines[["top", "right"]].set_visible(False)
axB.text(0.02, 0.03,
         "inc12 协议（20k/4k）；650M@5.9B 为 seed 29/43/61 复测均值 0.4464±0.012（3/3 seed 领先 300M）",
         transform=axB.transAxes, fontsize=8, color="#555")

fig.suptitle("预算 × 尺度 × 层迁移：650M 深度反转是欠训伪象（复测覆盖版）",
             fontsize=13, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig_layer_budget_v3.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
print("f2b:", f2b)
print("f59(650M=retest):", f59)
print("deltas:", deltas)
