"""fig_cov_v5_r2: 页 6 左图 COV 重画 —— 回答用户"纵轴是什么意思"。

前向共变指标（cov_minus_ctrl）的通俗解释加进图：
  cov = 把真实配对位 i 突变成互补碱基后，模型在配对位 j 预测互补碱基的概率变化
  ctrl = 同样突变，但读非配对照位 k —— 应无变化
  cov−ctrl = 净信号：模型"知道" i 和 j 该互补配对
650M 0.096 的意义：randinit=0（信号全部来自预训练）、超线性增长、
  是线性读出（+0.02~0.03）的 4 倍 —— 知识存在但读出受限。
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


cov = json.load(open(os.path.join(E, "covariation_test.json")))
cov650 = json.load(open(os.path.join(E, "covariation_test_650M.json")))
scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
vals = []
for s in scales:
    if s in cov:
        vals.append(cov[s]["cov_minus_ctrl"])
    else:
        vals.append(cov650[s]["cov_minus_ctrl"])
ri = cov650["650M_randinit17"]["cov_minus_ctrl"]

fig, ax = plt.subplots(figsize=(9.0, 5.2))
xs = [1.0, 10.0, 30.0, 100.0, 302.0, 666.0]
ax.plot(xs, vals, "o-", color=C["main"], lw=2.2, ms=9,
        markeredgecolor="white", markeredgewidth=1.3)
ax.fill_between(xs, 0, vals, color=C["main"], alpha=0.08)
for x, y, s in zip(xs, vals, scales):
    ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 11),
                ha="center", fontsize=8.5, fontweight="bold",
                color=SC.get(s, C["ink"]))
    ax.annotate("%.3f" % y, (x, y), textcoords="offset points",
                xytext=(0, -16), ha="center", fontsize=8, color="#707070")
ax.axhline(ri, ls=":", lw=1.3, color=C["coral"])
ax.text(0.985, 0.007, "randinit 同架构对照 ≈ 0\n（信号全部来自预训练）",
        fontsize=8.2, color=C["coral"], ha="right", va="bottom",
        transform=ax.get_yaxis_transform())

# 超线性区标注
ax.annotate("300M→650M 段每参数增益反升\n（超线性：参数 ×2.2，COV ×2.04）",
            xy=(484, 0.072), xytext=(0.115, 0.075),
            fontsize=8.8, color="#9A7B35", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#9A7B35", lw=1.0))
ax.annotate("0.096 = 线性读出增益（+0.02~0.03）的 ~4 倍\n→ 结构知识主要存于前向计算中",
            xy=(666, 0.096), xytext=(0.30, 0.108),
            fontsize=8.8, color=C["deep"], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C["deep"], lw=1.0))

# 度量解释框（左下）
ax.text(0.025, 0.955,
        "指标定义（纵轴）\n"
        "在真实配对位 i 引入突变 → 读模型对配对位 j 的互补碱基概率变化（cov）\n"
        "同样的突变读非配对照位 k（ctrl，应无变化）→ 纵轴 = cov − ctrl 净信号\n"
        "含义：模型前向计算中是否编码了「i 与 j 互补配对」的结构知识",
        transform=ax.transAxes, fontsize=7.6, va="top", color="#4A4A4A",
        bbox=dict(boxstyle="round,pad=0.45", fc="#F7F9FA", ec="#D5D5D5",
                  lw=0.7))

ax.set_xscale("log")
ax.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
ax.set_ylabel("前向共变净信号（cov − ctrl）", fontsize=10, color=C["ink"])
ax.set_ylim(-0.006, 0.135)
ax.set_title("① 知识存在：前向共变随尺度单调超线性增长（650M +0.096）",
             fontsize=11.5, loc="left", pad=8, color=C["ink"])
style(ax)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_cov_v5_r2.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_cov_v5_r2 saved, vals:", vals)
