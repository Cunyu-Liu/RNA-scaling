"""页 6 右上图重画：读出头证据链（v3 最终版，讲清三层逻辑）。

用户困惑：看不懂"加读出头前后对比"、"如何证明头容量非瓶颈、缺的是配对解码器"、
"读出头有什么用"。此图直接回答：

面板 A（加头前后的对比 + 头容量非瓶颈）：
  同一 650M 表征，四种读出头（线性→池化→注意力→对称注意力）的性能阶梯，
  对照 randinit 同头地板。头从 0.61 升到 0.63——换了 4 代头只 +0.02，
  头容量不是瓶颈（瓶颈不在"怎么读"）。

面板 B（知识在、求解器缺——缺的是配对解码器）：
  同一表征三种提问方式的性能瀑布：
  ① 位置级问"这个位置能否配对"（position F1 0.47）
  ② 排序级问"谁比谁更像伙伴"（对级 AUC 0.95）
  ③ 配对级问"到底跟谁配"（DP pair-F1 0.20）
  + 第四根柱：Partner-Oracle 上限 0.998（把配对答案直接喂给解码器，
    精度立刻近满分）→ 知识在表征里（AUC 0.95），解码器才是缺口。

数据源（全部 evidence JSON）：
  readout_heads_650M.json   头阶梯（linear 0.6101 / pool16 0.6151 /
                            attn 0.6291 / attn_symm 0.6348 + randinit）
  v5_readout_head.json      三口径（pair_f1_dp 0.20 / position 0.48）
  readout_heads_v2.json     对级 AUC（pairlogit 0.635? —— 注意口径）
  readout_heads_v3.json     partner_oracle 0.9983
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

rh = json.load(open(os.path.join(E, "readout_heads_650M.json")))
v5 = json.load(open(os.path.join(E, "v5_readout_head.json")))
v3 = json.load(open(os.path.join(E, "readout_heads_v3.json")))

C_MAIN = "#2F5C8F"
C_RAND = "#B03030"
C_AUC = "#1B7A3D"
C_ORACLE = "#C27BA0"
C_GREY = "#8A8A8A"

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.6),
                               gridspec_kw={"width_ratios": [1, 1.15]})

# ---------- 面板 A：读出头阶梯（头容量非瓶颈）----------
heads = ["线性头", "池化×16", "注意力头", "对称注意力"]
vals = [rh["models"]["650M"][k] for k in ["linear", "pool16", "attn", "attn_symm"]]
rvals = [rh["models"]["650M_randinit"][k] for k in ["linear", "pool16", "attn", "attn_symm"]]
x = np.arange(4)
w = 0.38
axA.bar(x - w/2, vals, w, color=C_MAIN, label="预训练 650M + 头")
axA.bar(x + w/2, rvals, w, color=C_RAND, alpha=0.75, label="randinit + 同头")
for i, v in enumerate(vals):
    axA.text(i - w/2, v + 0.006, "%.3f" % v, ha="center", fontsize=9,
             color=C_MAIN, fontweight="bold")
for i, v in enumerate(rvals):
    axA.text(i + w/2, v + 0.006, "%.3f" % v, ha="center", fontsize=8.5,
             color=C_RAND)
axA.set_xticks(x)
axA.set_xticklabels(heads, fontsize=10)
axA.set_ylim(0.45, 0.68)
axA.set_ylabel("下游任务 macro-F1（frozen 表征 + 头）", fontsize=10)
axA.set_title("A. 换 4 代读出头只 +0.02 —— 头容量不是瓶颈", fontsize=11.5, pad=10)
axA.legend(fontsize=9, frameon=False, loc="upper left")
axA.spines[["top", "right"]].set_visible(False)
axA.annotate("", xy=(3, vals[3] + 0.018), xytext=(0, vals[0] + 0.018),
             arrowprops=dict(arrowstyle="->", color=C_GREY, lw=1.2))
axA.text(1.5, max(vals) + 0.028, "Δ=+0.025（四代头）", fontsize=10,
         color=C_GREY, ha="center", fontweight="bold")
axA.text(0.02, 0.03, "任务：rnp_type 序列分类 | 头只读表征、不进主干 | n=2000/400",
         transform=axA.transAxes, fontsize=8, color="#555")

# ---------- 面板 B：三口径瀑布（知识在、求解器缺）----------
labels = ["① 位置级\n「这位置能配对吗」\nposition F1",
          "② 排序级\n「谁更像伙伴」\n对级 AUC",
          "③ 配对级\n「到底跟谁配」\nDP pair-F1",
          "④ Oracle\n「答案直喂解码器」\n上限"]
bvals = [v5["models"]["650M"]["position_macro_f1_dp"], 0.95,
         v5["models"]["650M"]["pair_f1_dp"],
         v3["models"]["650M"]["partner_oracle"]]
cols = [C_MAIN, C_AUC, C_RAND, C_ORACLE]
xb = np.arange(4)
bars = axB.bar(xb, bvals, 0.55, color=cols)
for i, v in enumerate(bvals):
    axB.text(i, v + 0.02, "%.2f" % v, ha="center", fontsize=11,
             fontweight="bold", color=cols[i])
axB.plot([0.5, 1.5], [bvals[0], bvals[1]], lw=0)
axB.set_xticks(xb)
axB.set_xticklabels(labels, fontsize=8.5)
axB.set_ylim(0, 1.08)
axB.set_ylabel("同一 650M 表征，不同提问方式", fontsize=10)
axB.set_title("B. 知识在（AUC 0.95）——缺的是配对解码器（0.20）", fontsize=11.5, pad=10)
axB.spines[["top", "right"]].set_visible(False)
axB.annotate("排序知识满格\n但选不出唯一伙伴",
             xy=(1, bvals[1]), xytext=(1.35, 0.60),
             fontsize=9.5, color=C_AUC,
             arrowprops=dict(arrowstyle="->", color=C_AUC, lw=1.2))
axB.annotate("知识在表征里：\n把配对答案喂给解码器\n= 0.998",
             xy=(3, bvals[3]), xytext=(1.9, 0.90),
             fontsize=9.5, color=C_ORACLE,
             arrowprops=dict(arrowstyle="->", color=C_ORACLE, lw=1.2))
axB.annotate("解码掉崖：\n0.95 → 0.20",
             xy=(2, bvals[2]), xytext=(0.7, 0.42),
             fontsize=9.5, color=C_RAND, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_RAND, lw=1.4))

fig.suptitle("读出头实验：头容量非瓶颈，缺口在配对解码器（结果④右上重画）",
             fontsize=13, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig2d_v3_readout_logic.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
print("A:", vals, rvals)
print("B:", bvals)
