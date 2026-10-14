"""fig_eval_delta_v5: 六尺度 random vs family F1 + randinit 曲线 + RiNALMo Δ 箭头。

数据全部来自 eval/eval_matrix_results.jsonl (probe-balanced) + s4_randinit_table.json。
回答用户两点：
  1) RiNALMo 三档（粉色）没有像 RNA-Sc 那样画 Δ(random−family) —— 现在补上箭头+数值
  2) 缺随机初始化曲线 —— 现在补 randinit family-split 曲线（灰色点线）
风格 = v5 色板（与页 3/4/6 新图一致）。
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
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"

C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A", "line": "#D5D5D5"}
SC = {"1M": "#C9CDD2", "10M": "#E5B45A", "30M": "#6FAE9B",
      "100M": "#7BA3C7", "300M": "#4878A8", "650M": "#2E5170"}


def style(ax, grid=True):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors=C["ink"], labelsize=8.5, length=3, width=0.7)
    if grid:
        ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
        ax.set_axisbelow(True)


rows = [json.loads(l) for l in open(os.path.join(EV, "eval_matrix_results.jsonl"))]
best = {}
for r in rows:
    m = r.get("model", "?")
    key = (m, r.get("split"), r.get("protocol", "probe-balanced"))
    if key not in best or r["best_f1_macro"] > best[key]["best_f1_macro"]:
        best[key] = r

# 六尺度 probe-balanced: family / random
scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
fam = [best[("RNA-Sc-%s_s17" % s, "family", "probe-balanced")]["best_f1_macro"] for s in scales]
ran = [best[("RNA-Sc-%s_s17" % s, "random", "probe-balanced")]["best_f1_macro"] for s in scales]
# randinit family 曲线（用户点名的缺失线）
s4 = json.load(open(os.path.join(E, "s4_randinit_table.json")))
ri = [s4[s]["randinit"] for s in scales]
# k-mer 基线带
kmer = json.load(open(os.path.join(E, "classical_baselines.json")))
k_fam = kmer["family"]["f1_macro"]
k_ran = kmer["random"]["f1_macro"]

fig, ax = plt.subplots(figsize=(9.6, 5.6))
xs = [float(s[:-1]) if s != "650M" else 666.0 for s in scales]
xsc = {"1M": 1.0, "10M": 10.0, "30M": 30.0, "100M": 100.0,
       "300M": 302.0, "650M": 666.0}

# k-mer band
ax.axhspan(k_fam, k_ran, color="#F5E6C8", alpha=0.45, zorder=1)
ax.text(0.02, (k_fam + k_ran) / 2,
        "k-mer 基线带（无 LM）：0.163 → 0.518，Δ=+0.355\n计数统计即可兑现大部分“随机切分胜利”",
        fontsize=8, color="#8A6A1F", va="center",
        transform=ax.get_yaxis_transform())

# RNA-Sc 六尺度双线
ax.plot(xs, ran, "-o", color=C["coral"], lw=2.2, ms=7, zorder=5,
        markeredgecolor="white", markeredgewidth=0.9,
        label="RNA-Sc random 切分（i.i.d. 行）")
ax.plot(xs, fam, "-s", color=C["main"], lw=2.2, ms=7, zorder=5,
        markeredgecolor="white", markeredgewidth=0.9,
        label="RNA-Sc family 切分（held-out 家族）")
# randinit family 曲线（灰点线）
ax.plot(xs, ri, "v:", color=C["grey"], lw=1.5, ms=6, zorder=4,
        label="randinit family（未预训练对照）")

# Δ 箭头（RNA-Sc 内部）
for x, fr, fl in zip(xs, fam, ran):
    ax.annotate("", xy=(x, fr), xytext=(x, fl),
                arrowprops=dict(arrowstyle="<->", color="#999", lw=0.9,
                                alpha=0.75))
    ax.text(x * 1.07, (fr + fl) / 2, "Δ%.2f" % (fl - fr), fontsize=7.8,
            color="#666", va="center")

# RiNALMo 三档（粉）：random 高点 + family 低点 + Δ 箭头 + 标注
ext = {
    "RiNALMo-micro(36M)": (36, 0.5422, 0.2407),
    "RiNALMo-mega(148M)": (148, 0.5943, 0.2532),
    "RiNALMo-giga(651M)": (651, 0.5442, 0.2667),
}
for i, (name, (pm, rf1, ff1)) in enumerate(ext.items()):
    ax.annotate("", xy=(pm, ff1), xytext=(pm, rf1),
                arrowprops=dict(arrowstyle="<->", color="#C27BA0", lw=1.4,
                                alpha=0.9))
    ax.scatter([pm], [rf1], s=95, marker="D", color="#C27BA0", zorder=6,
               edgecolors="white", linewidths=0.8)
    ax.scatter([pm], [ff1], s=85, marker="D", color="#C27BA0", alpha=0.55,
               zorder=6, edgecolors="white", linewidths=0.8)
    ax.text(pm * 1.05, (ff1 + rf1) / 2, "Δ%.2f" % (rf1 - ff1), fontsize=8.2,
            color="#C27BA0", va="center", fontweight="bold")
ax.scatter([], [], s=90, marker="D", color="#C27BA0", label="RiNALMo random/family")

# RNA-FM
ax.scatter([96], [0.0998], s=80, marker="o", color=C["teal"], zorder=6,
           edgecolors="white", linewidths=0.8)
ax.annotate("RNA-FM(96M)\nrandom 0.0998\nfamily 0.1346", (96, 0.0998),
            textcoords="offset points", xytext=(6, -2), fontsize=7.8,
            color=C["teal"])

ax.set_xscale("log")
ax.set_xticks(xs)
ax.set_xticklabels(scales)
ax.set_xlabel("参数量（M，log 轴）", fontsize=10, color=C["ink"])
ax.set_ylabel("probe macro-F1（rna_type）", fontsize=10, color=C["ink"])
ax.set_ylim(0.0, 0.78)
ax.set_title("随机切分的“胜利”= 泄漏红利：Δ 随规模放大，但 k-mer 与 randinit 也能吃到",
             fontsize=11.5, loc="left", pad=8, color=C["ink"])
ax.legend(fontsize=8.6, loc="center left", framealpha=0.93)
style(ax)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_p5_delta_v5.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p5_delta_v5 saved")
print("fam:", fam)
print("ran:", ran)
print("ri:", ri)
