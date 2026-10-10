"""页 11 H4 补充图：磨蚀/层迁移 × 预算 × 尺度（2026-10-10 用户需求）。

用户需求："页 10 H4 的 2b 5.9b，还有 300 650m 参数量模型补充。"
（注：H4 证据实际在页 11 假设证据①；H4 = 磨蚀/容量门控假设）

双面板：
  左：s6_cross_scale 涌现时间线（1M-100M，best_rel 深度轨迹 + F1）——
      H4 原证据：磨蚀谷（10M 深度先降后升的 U）。
      补充 300M/650M/5.9B 数据点（factorial_verdict）作为终态星标。
  右：双预算最优层（来自 fig_layer_budget_dumbbell 数据）——
      H4 的预算维度扩展：5.9B 让 650M 最佳层从 L8 回到 L25
      （磨蚀被预算修复 = 磨蚀是训练动态而非容量规律）。

数据源：s6_cross_scale.json + factorial_verdict.json
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

s6 = json.load(open(os.path.join(E, "s6_cross_scale.json")))
fv = json.load(open(os.path.join(E, "factorial_verdict.json")))
t = fv["table"]

C_1M = "#9aa5b1"
C_10M = "#e08214"
C_30M = "#3572b0"
C_100M = "#2F5C8F"
C_300M = "#1B7A3D"
C_650M = "#B03030"

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.8, 4.4))

# ---------- 左：涌现时间线（H4 核心）+ 300M/650M 终态 ----------
for arm, col in [("1M", C_1M), ("10M", C_10M), ("30M", C_30M), ("100M", C_100M)]:
    pts = s6[arm]
    xs = [p["nt_B"] for p in pts]
    f1s = [p["best_f1"] for p in pts]
    rels = [p["best_rel"] for p in pts]
    axL.plot(xs, f1s, color=col, lw=1.8, marker="o", ms=4,
             label="%s（2B 内）" % arm)
# 300M/650M 2B 终态（单一最优 F1，factorial）
axL.scatter([1.9, 1.9], [t["300M"]["f1_2B"]["f1"], t["650M"]["f1_2B"]["f1"]],
            s=150, marker="*", color=[C_300M, C_650M], zorder=5)
axL.annotate("300M@2B 0.3445", (1.9, t["300M"]["f1_2B"]["f1"]),
             xytext=(1.15, 0.395), fontsize=9, color=C_300M,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_300M, lw=1.2))
axL.annotate("650M@2B 0.3632", (1.9, t["650M"]["f1_2B"]["f1"]),
             xytext=(1.15, 0.412), fontsize=9, color=C_650M,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_650M, lw=1.2))
axL.axvline(0.35, color="#e08214", ls=":", lw=1.2)
axL.text(0.35, 0.135, " 10M 磨蚀谷窗口", fontsize=8.5, color="#e08214",
         rotation=90, va="bottom")
axL.set_xlabel("训练预算（B nt）", fontsize=10.5)
axL.set_ylabel("最优层 F1（family 切分）", fontsize=10.5)
axL.set_ylim(0.10, 0.44)
axL.set_title("H4 链①：涌现时间线 + 300M/650M 补充（2B）", fontsize=11.5, pad=10)
axL.legend(fontsize=8.5, frameon=False, loc="lower right", ncol=2)
axL.spines[["top", "right"]].set_visible(False)

# ---------- 右：层迁移 × 预算（H4 预算维度扩展） ----------
arms = ["30M", "100M", "300M", "650M"]
l2b = [t[a]["f1_2B"]["layer"] / t[a]["f1_2B"]["layer"] for a in arms]
rel2b = [t[a]["f1_2B"]["rel"] for a in arms]
rel59 = [t[a]["f1_5.9B"]["rel"] for a in arms]
x = np.arange(4)
w = 0.38
axR.bar(x - w/2, rel2b, w, color="#2F5C8F", label="2.0B 最优层深度")
axR.bar(x + w/2, rel59, w, color="#B03030", label="5.9B 最优层深度")
for i in range(4):
    axR.text(i - w/2, rel2b[i] + 0.02, "L%d" % t[arms[i]]["f1_2B"]["layer"],
             ha="center", fontsize=9.5, color="#2F5C8F", fontweight="bold")
    axR.text(i + w/2, rel59[i] + 0.02, "L%d" % t[arms[i]]["f1_5.9B"]["layer"],
             ha="center", fontsize=9.5, color="#B03030", fontweight="bold")
axR.set_xticks(x)
axR.set_xticklabels(arms, fontsize=11)
axR.set_ylim(0, 1.12)
axR.set_ylabel("最优层相对深度（0=浅，1=深）", fontsize=10)
axR.set_title("H4 链②：5.9B 修复 650M 磨蚀（L8→L25，30%→93%）",
              fontsize=11.5, pad=10)
axR.legend(fontsize=9.5, frameon=False, loc="upper left")
axR.spines[["top", "right"]].set_visible(False)
axR.annotate("磨蚀被预算修复：\n容量门控是训练动态，\n非容量规律",
             xy=(3 + w/2, rel59[3]), xytext=(1.8, 0.55),
             fontsize=9.5, color="#B03030",
             arrowprops=dict(arrowstyle="->", color="#B03030", lw=1.4))

fig.suptitle("H4 磨蚀/容量门控：双预算 + 全尺度证据（300M/650M 已补）",
             fontsize=13, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig_h4_budget_scale.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
