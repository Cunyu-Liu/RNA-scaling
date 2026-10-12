"""gap-bridge 解码器实验图（用户问"后续补了吗，结果怎么样"）。

数据：gapbridge_decoder_v2.json（650M + 300M × 三解码策略）。
结论：简单结构约束（非交叉 DP + 环长先验）无法桥接 gap——
弱分数下 DP 反而损失一半精度 → 缺口定位在"需训练的配对网络"
（PairNet/ResNet 级），结构先验本身不够。
图式：分组柱 A/B/C × 2 模型 + 结论标注。
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

d = json.load(open(os.path.join(E, "gapbridge_decoder_v2.json")))
m = d["models"]

C_A = "#2F5C8F"
C_B = "#e08214"
C_C = "#B03030"

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.2),
                               gridspec_kw={"width_ratios": [1.2, 1]})

# 左：三策略 × 两模型
labels = ["A: top-L 贪心\n（S8 基线）", "B: +非交叉 DP\n（top-2L 约束）",
          "C: B + 环长≥3\n（结构先验）"]
x = np.arange(3)
w = 0.36
v650 = [m["650M"]["A_topL"], m["650M"]["B_top2L_dp"],
        m["650M"]["C_top2L_dp_loop3"]]
v300 = [m["300M"]["A_topL"], m["300M"]["B_top2L_dp"],
        m["300M"]["C_top2L_dp_loop3"]]
axL.bar(x - w/2, v650, w, color=C_A, label="650M")
axL.bar(x + w/2, v300, w, color=C_B, label="300M")
for i, (a, b) in enumerate(zip(v650, v300)):
    axL.text(i - w/2, a + 0.0005, "%.4f" % a, ha="center", fontsize=9,
             color=C_A, fontweight="bold")
    axL.text(i + w/2, b + 0.0005, "%.4f" % b, ha="center", fontsize=9,
             color=C_B, fontweight="bold")
axL.set_xticks(x)
axL.set_xticklabels(labels, fontsize=9.5)
axL.set_ylim(0, 0.026)
axL.set_ylabel("pair-F1（bpRNA 测试集）", fontsize=10)
axL.set_title("(a) 解码器 gap-bridge 实验：结构约束反而降精度", fontsize=11,
              pad=10)
axL.legend(fontsize=9.5, frameon=False, loc="upper right")
axL.spines[["top", "right"]].set_visible(False)
axL.annotate("DP 丢掉一半精度：\n0.0190 → 0.0078", xy=(1, v650[1]),
             xytext=(0.6, 0.0215), fontsize=9.5, color=C_C,
             fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C_C, lw=1.3))

# 右：结论面板（定位缺口）
axR.set_xlim(0, 1)
axR.set_ylim(0, 1)
axR.set_xticks([])
axR.set_yticks([])
for sp in axR.spines.values():
    sp.set_visible(False)
texts = [
    ("实验问句", "「缺配对解码器」→ 随便加个 DP 就能解吗？"),
    ("结果", "A 贪心 0.019 → B 非交叉 DP 0.0078 → C +环长 0.0078\n"
     "300M 同构（0.0148→0.0038）：结构约束反而损失一半精度"),
    ("为什么", "弱分数（logistic 排序）下，DP 的全局最优\n"
     "会被边缘分数噪声带偏——把局部高置信对挤掉；\n"
     "v5 的 0.20 依赖训练过的 PairNet 强分数"),
    ("缺口精确定位", "不是「缺一个解码算法」\n"
     "而是「缺与解码器联合训练的配对网络」\n"
     "（NucleicBERT 用 ResNet 头同理由）→ 二期方向"),
]
y = 0.95
for title, body in texts:
    axR.text(0.03, y, title, fontsize=11, fontweight="bold",
             color="#2F5C8F", transform=axR.transAxes, va="top")
    axR.text(0.06, y - 0.055, body, fontsize=8.8, color="#333",
             transform=axR.transAxes, va="top", linespacing=1.5)
    y -= 0.25
axR.set_title("(b) gap 的精确定位：需联合训练的配对网络", fontsize=11,
              loc="left", pad=10)

fig.suptitle("「然后呢」：解码器 gap-bridge 实测——简单结构约束不解药，"
             "缺口在配对网络与解码的联合", fontsize=12, y=1.0)
fig.tight_layout()
out = os.path.join(FIG, "fig_gapbridge.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
print("650M:", v650, "300M:", v300)
