"""S8 接触图证据图（2026-10-09 补齐 PPT 第 16 页 S8 缺口）。

数据：evidence/s8_contact.json（logistic 头 + APC + top-L 长程 precision@L）
图式：双面板
  左：主条形图（训练 vs randinit vs 随机基线，按尺度排列，标注倍数）
  右：语料对照放大（100M r22 vs 100M RiNALMo 语料复刻）
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FIG = "/mnt/cunyuliu/rna-sc/figs"
EVID = "/mnt/cunyuliu/rna-sc/evidence"
plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

d = json.load(open(os.path.join(EVID, "s8_contact.json")))
models = d["models"]
rand = d["randinit17"]
chance = d["chance_baseline"]

BLUE, ORANGE, GRAY, GREEN = "#3572b0", "#e08214", "#9aa5b1", "#3f9d6b"
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2),
                               gridspec_kw={"width_ratios": [2.6, 1]})

# --- 左：尺度轴主图 ---
scales = ["30M", "100M", "650M"]
x = range(len(scales))
w = 0.27
tv = [models[s] for s in scales]
rv = [rand[s] for s in scales]
b1 = ax1.bar([i - w for i in x], tv, w, color=BLUE, label="预训练模型")
b2 = ax1.bar(list(x), rv, w, color=ORANGE, label="randinit 对照(seed 17)")
ax1.axhline(chance, color=GRAY, ls="--", lw=1.2)
ax1.text(2.42, chance, " 随机基线 0.0044", fontsize=8.5, color=GRAY,
         va="center", ha="left")
for i, (t, r) in enumerate(zip(tv, rv)):
    ax1.text(i - w, t + 0.00012, "%.2f×" % (t / chance), fontsize=9,
             ha="center", color=BLUE, fontweight="bold")
    ax1.text(i, r + 0.00012, "%.2f×" % (r / chance), fontsize=9,
             ha="center", color=ORANGE)
    ax1.annotate("", xy=(i - w / 2, t), xytext=(i - w / 2, r),
                 arrowprops=dict(arrowstyle="->", color="#666", lw=1))
ax1.set_xticks(list(x))
ax1.set_xticklabels(scales, fontsize=11)
ax1.set_ylabel("长程接触 precision@L（APC 修正）", fontsize=10.5)
ax1.set_ylim(0, max(tv) * 1.3)
ax1.set_title("S8 无监督接触预测：随尺度单调上升，randinit 压制在基线附近",
              fontsize=11.5, pad=10)
ax1.legend(fontsize=9, frameon=False, loc="upper left")
ax1.spines[["top", "right"]].set_visible(False)
ax1.text(0.02, 0.955, "层 70% 深度 | logistic 头 [hi,hj,|hi−hj|,hi·hj] | 对≥24nt | n=1305",
         transform=ax1.transAxes, fontsize=8, color="#555")

# --- 右：语料对照（100M）---
labels = ["r22 语料\n(v1, 14M)", "RiNALMo 语料\n复刻(v1, 14M*)"]
vals = [models["100M"], models["100M-rinalmo语料"]]
b = ax2.bar([0, 1], vals, 0.45, color=[GRAY, GREEN])
ax2.axhline(chance, color=GRAY, ls="--", lw=1.2)
ax2.text(1.28, chance, " 随机", fontsize=8.5, color=GRAY, va="center")
ax2.axhline(rand["100M"], color=ORANGE, ls=":", lw=1.2)
ax2.text(1.28, rand["100M"], " randinit", fontsize=8.5, color=ORANGE,
         va="center")
for i, v in enumerate(vals):
    ax2.text(i, v + 0.00012, "%.2f×" % (v / chance), fontsize=10,
             ha="center", fontweight="bold",
             color=GRAY if i == 0 else GREEN)
ax2.annotate("", xy=(0.5, vals[1]), xytext=(0.5, vals[0]),
             arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.4))
ax2.text(0.55, (vals[0] + vals[1]) / 2 + 0.00004, "+9%（同架构同预算）",
         fontsize=9, color=GREEN, fontweight="bold")
ax2.set_xticks([0, 1])
ax2.set_xticklabels(labels, fontsize=9.5)
ax2.set_ylim(0, max(vals) * 1.35)
ax2.set_title("100M 语料成分对照", fontsize=11.5, pad=10)
ax2.spines[["top", "right"]].set_visible(False)
ax2.text(0.02, 0.955, "*同 RiNALMo 配方(R22+Rfam 家族 fasta 去重后)",
         transform=ax2.transAxes, fontsize=8, color="#555")

fig.suptitle("S8 接触图证据：结构信号随尺度涌现，语料成分贡献独立增量",
             fontsize=13, y=1.02)
fig.tight_layout()
out = os.path.join(FIG, "fig_s8_contact.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
