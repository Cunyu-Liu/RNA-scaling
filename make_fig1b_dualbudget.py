"""fig1_v2 (b) 面板双预算升级：U 型迁移曲线 2B vs 5.9B。

用户需求（目标续跑）：页 3 的 650M 更新需要与 5.9B 数据联动。
原 (b) 只有 2B 点 + 过时的"corpus channel saturation"注释。
新 (b)：2B（蓝实线）与 5.9B（红虚线）双曲线，650M 点 0.296→0.926，
注释改为"欠训伪象，5.9B 恢复深 L25"。

数据：s1_final_verdict layer_migration_endpoint（2B）+
factorial_verdict（5.9B best_rel）。
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_2B = "#2F5C8F"
C_59B = "#B03030"
SCALE_COLORS = {"1M": "#bbb", "10M": "#e08214", "30M": "#3572b0",
                "100M": "#2F5C8F", "300M": "#1B7A3D", "650M": "#B03030"}
PARAMS_M = {"1M": 1, "10M": 10, "30M": 30, "100M": 100, "300M": 300,
            "650M": 650}

s1 = json.load(open(os.path.join(E, "s1_final_verdict.json")))
verdict = s1["checks"]["layer_migration_endpoint"]
verdict = {k: v for k, v in verdict.items() if isinstance(v, float)}
verdict["300M"] = 0.957
fv = json.load(open(os.path.join(E, "factorial_verdict.json")))
fv_t = fv["table"]

order = ["1M", "10M", "30M", "100M", "300M", "650M"]
order59 = ["30M", "100M", "300M", "650M"]

fig, axb = plt.subplots(figsize=(6.4, 4.0))

# 2B 曲线
rels2b = [verdict[s] for s in order]
xs2b = [PARAMS_M[s] for s in order]
axb.plot(xs2b, rels2b, "-", color=C_2B, lw=2.0, zorder=3,
         label="2.0B（主臂）")
axb.scatter(xs2b, rels2b, s=64, color=[SCALE_COLORS[s] for s in order],
            zorder=5, edgecolors="white", linewidths=0.8)
# 5.9B 曲线
rels59 = [fv_t[s]["f1_5.9B"]["rel"] for s in order59]
xs59 = [PARAMS_M[s] for s in order59]
axb.plot(xs59, rels59, "--", color=C_59B, lw=2.2, zorder=4,
         label="5.9B（b59 臂）")
axb.scatter(xs59, rels59, s=84, marker="D",
            color=[SCALE_COLORS[s] for s in order59], zorder=6,
            edgecolors="white", linewidths=0.8)
for x, y, s in zip(xs2b, rels2b, order):
    axb.annotate(s, (x, y), textcoords="offset points", xytext=(0, 9),
                 ha="center", fontsize=8.5, fontweight="bold",
                 color=SCALE_COLORS[s])
# 650M 双点标注
axb.annotate("", xy=(650, fv_t["650M"]["f1_5.9B"]["rel"]),
             xytext=(650, verdict["650M"]),
             arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.6))
axb.annotate("650M 回浅 = 欠训伪象\n5.9B 恢复 L25（0.93）",
             xy=(650, (verdict["650M"] + fv_t["650M"]["f1_5.9B"]["rel"]) / 2),
             xytext=(240, 0.45), fontsize=9, color=C_59B,
             fontweight="bold", ha="center",
             arrowprops=dict(arrowstyle="->", color=C_59B, lw=1.2))
axb.annotate("10M 磨蚀谷（0.14）", xy=(10, 0.141), xytext=(30, 0.02),
             fontsize=8.2, color="#555", ha="center",
             arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
axb.annotate("容量期：30M→300M\n峰值深度 0.73→0.96", xy=(100, 0.864),
             xytext=(48, 0.52), fontsize=8.2, color="#555", ha="center",
             arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))

axb.set_xscale("log")
axb.set_ylim(-0.05, 1.12)
axb.set_xlabel("parameters (M)", fontsize=9.5)
axb.set_ylabel("best-layer relative depth", fontsize=9.5)
axb.set_title("U-shaped migration: best depth vs scale — 2B vs 5.9B",
              fontsize=10.5, loc="left", pad=8)
axb.legend(fontsize=9, frameon=False, loc="upper left")
axb.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, "fig1b_layer_dualbudget.%s" % ext),
                dpi=200, bbox_inches="tight")
print("saved fig1b_layer_dualbudget.png")
print("2B rels:", dict(zip(order, [round(v, 3) for v in rels2b])))
print("5.9B rels:", dict(zip(order59, [round(v, 3) for v in rels59])))
