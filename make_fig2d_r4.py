"""fig2d_v4_readout_logic: 页 6 右上重画 —— 理顺"思路混乱"批评。

用户困惑拆解成三问三答，每问配判据：
  问1（知识在吗）：对级 AUC 0.95 —— 对真配对 (i,j)，模型给的配对分数
      能否把真伙伴排在假伙伴前面？AUC 0.95 = 排序知识充足
  问2（缺什么）：DP pair-F1 0.20 —— 从同一批分数里选互斥配对集，
      全局最优解码反而被噪声带偏 → 缺的不是"更聪明的解码算法"
      （gap-bridge B/C 实测：加非交叉 DP/环长先验反而更差）
  问3（缺口在哪）：Partner-Oracle 0.998 —— 把配对答案直接喂给解码器
      精度近满分 → 知识在表征里、解码管线没问题，缺的是
      「与表征联合训练的配对评分网络」
面板 A（头阶梯）保留但压缩。
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
     "ink": "#3A3A3A", "acc": "#C27BA0"}
C_AUC = "#1B7A3D"

rh = json.load(open(os.path.join(E, "readout_heads_650M.json")))
v5 = json.load(open(os.path.join(E, "v5_readout_head.json")))
v3 = json.load(open(os.path.join(E, "readout_heads_v3.json")))
gb = json.load(open(os.path.join(E, "gapbridge_decoder_v2.json")))

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.8, 4.8),
                               gridspec_kw={"width_ratios": [1, 1.3]})

# ---------- 面板 A：头阶梯（头容量非瓶颈）----------
heads = ["线性头", "池化×16", "注意力头", "对称注意力"]
vals = [rh["models"]["650M"][k] for k in ["linear", "pool16", "attn", "attn_symm"]]
rvals = [rh["models"]["650M_randinit"][k] for k in ["linear", "pool16", "attn", "attn_symm"]]
x = np.arange(4)
w = 0.38
axA.bar(x - w/2, vals, w, color=C["main"], label="预训练 650M + 头")
axA.bar(x + w/2, rvals, w, color=C["coral"], alpha=0.75,
        label="randinit + 同头")
for i, v in enumerate(vals):
    axA.text(i - w/2, v + 0.005, "%.3f" % v, ha="center", fontsize=8.6,
             color=C["main"], fontweight="bold")
for i, v in enumerate(rvals):
    axA.text(i + w/2, v + 0.005, "%.3f" % v, ha="center", fontsize=8,
             color=C["coral"])
axA.set_xticks(x)
axA.set_xticklabels(heads, fontsize=9.5)
axA.set_ylim(0.45, 0.70)
axA.set_ylabel("下游 macro-F1（frozen 表征 + 头）", fontsize=9.5)
axA.set_title("② 读出：换 4 代头只 +0.025——头容量非瓶颈", fontsize=10.5,
              loc="left", pad=8, color=C["ink"])
axA.legend(fontsize=8.4, frameon=False, loc="upper left")
axA.spines[["top", "right"]].set_visible(False)
axA.text(0.02, 0.03, "任务：rnp_type 分类 | 头只读表征不进主干", transform=axA.transAxes,
         fontsize=7.6, color="#555")

# ---------- 面板 B：三问三答瀑布 ----------
labels = ["① 排序知识\nAUC\n「真伙伴排得\n上假伙伴前？」",
          "② 互斥配对解码\nDP pair-F1\n「选唯一伙伴」",
          "③ 结构先验加码\ngap-bridge\n「非交叉DP+\n环长≥3」",
          "④ Oracle 上限\n「答案直喂\n解码器」"]
bvals = [0.95, v5["models"]["650M"]["pair_f1_dp"],
         gb["models"]["650M"]["C_top2L_dp_loop3"],
         v3["models"]["650M"]["partner_oracle"]]
cols = [C_AUC, C["coral"], C["amber"], C["acc"]]
xb = np.arange(4)
axB.bar(xb, bvals, 0.55, color=cols)
for i, v in enumerate(bvals):
    axB.text(i, v + 0.02, "%.3f" % v, ha="center", fontsize=10.5,
             fontweight="bold", color=cols[i])
axB.set_xticks(xb)
axB.set_xticklabels(labels, fontsize=8.2)
axB.set_ylim(0, 1.12)
axB.set_ylabel("同一 650M 表征，不同提问方式", fontsize=9.5)
axB.set_title("③ 缺口定位：知识在（0.95）——缺联合训练的配对网络", fontsize=10.5,
              loc="left", pad=8, color=C["ink"])
axB.spines[["top", "right"]].set_visible(False)
axB.annotate("① 排序知识满格：\n真伙伴 vs 假伙伴 AUC 0.95\n→ 知识在表征里",
             xy=(0, bvals[0]), xytext=(-0.15, 0.62),
             fontsize=8.6, color=C_AUC,
             arrowprops=dict(arrowstyle="->", color=C_AUC, lw=1.1))
axB.annotate("② 解码掉崖 0.95→0.20：\n全局最优被弱分数噪声带偏",
             xy=(1, bvals[1]), xytext=(0.55, 0.42),
             fontsize=8.6, color=C["coral"], fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C["coral"], lw=1.2))
axB.annotate("③ 经典结构先验无效：\nDP 掉半（0.019→0.0078）、环长再降\n→ 缺的不是解码算法",
             xy=(2, bvals[2]), xytext=(1.15, 0.68),
             fontsize=8.6, color="#9A7B35",
             arrowprops=dict(arrowstyle="->", color="#9A7B35", lw=1.1))
axB.annotate("④ 知识在表征里：\n答案直喂解码器 = 0.998\n→ 缺「与表征联合训练的\n    配对评分网络」",
             xy=(3, bvals[3]), xytext=(2.35, 0.88),
             fontsize=8.6, color=C["acc"],
             arrowprops=dict(arrowstyle="->", color=C["acc"], lw=1.2))

fig.suptitle("读出与缺口（三问三答）：头容量非瓶颈；缺联合训练的配对网络",
             fontsize=12, y=1.00)
fig.tight_layout()
out = os.path.join(FIG, "fig2d_v4_readout_logic.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
plt.close(fig)
print("saved", out)
print("B values:", bvals)
