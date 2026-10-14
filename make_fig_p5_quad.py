"""fig_p5_quad: 页 5 上图最终版——2×2 四面板，2B/5.9B 分开画。

行 = 预算臂（上：2B 全六尺度；下：5.9B 四尺度全过程）
列 = 指标（左：最优层 F1 时间轴；右：最优层相对深度时间轴）
回答用户"图 B 和图 C 都缺 300M/650M 和 5.9B 中间点、要求分开画"的完整版。
数据：s6_cross_scale + probe_results.jsonl（_ck 行，含本轮补测的 b59 36 点）。
"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A"}
SC = {"1M": "#C9CDD2", "10M": "#E5B45A", "30M": "#6FAE9B",
      "100M": "#7BA3C7", "300M": "#4878A8", "650M": "#2E5170"}


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors=C["ink"], labelsize=8.5, length=3, width=0.7)
    ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
    ax.set_axisbelow(True)


def timeline(run_base, include_main=True):
    """返回 [(nt_B, best_f1, best_rel)]。"""
    rows = defaultdict(dict)
    lay = {}
    for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
        r = json.loads(line)
        if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
            continue
        run = r.get("run", "")
        nt = r.get("ckpt_nt")
        want = run.startswith(run_base + "_ck") \
            or (include_main and run == run_base) \
            or (run_base.endswith("_b59") and run == run_base)
        if nt and want:
            rows[nt][r["layer"]] = max(rows[nt].get(r["layer"], 0),
                                       r["f1_macro"])
            lay[nt] = r.get("n_layers", 1)
    out = []
    for nt in sorted(rows):
        d = rows[nt]
        if len(d) < max(1, lay.get(nt, 1) // 2):
            continue
        bl = max(d, key=d.get)
        out.append((nt / 1e9, round(d[bl], 4), round(bl / (lay[nt] - 1), 3)))
    return out


s6 = json.load(open(os.path.join(E, "s6_cross_scale.json")))

fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.0),
                         gridspec_kw={"height_ratios": [1, 1]})

# ============ 上行：2B 臂 ============
ax = axes[0][0]
for scale in ["1M", "10M", "30M", "100M"]:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
            "-o", color=SC[scale], lw=1.7, ms=3.8, label=scale)
for arm in ["300M", "650M"]:
    pts = timeline("RNA-Sc-%s_s17" % arm)
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-*",
                color=SC[arm], lw=2.0, ms=7, label=arm)
ax.annotate("10M 磨蚀谷", xy=(1.4, 0.172), xytext=(0.4, 0.08),
            fontsize=9, color="#9A7B35",
            arrowprops=dict(arrowstyle="->", color="#9A7B35", lw=1.0))
ax.set_ylabel("最优层 F1（family）", fontsize=9.5, color=C["ink"])
ax.set_xlim(0, 2.2)
ax.set_ylim(0.05, 0.56)
ax.set_title("(a) 2B 臂 · F1 时间轴（六尺度全）", fontsize=10.5,
             loc="left", pad=6, color=C["ink"])
ax.legend(fontsize=7.8, frameon=False, loc="lower right", ncol=2)
style(ax)

ax = axes[0][1]
for scale in ["1M", "10M", "30M", "100M"]:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_rel"] for p in pts],
            "-s", color=SC[scale], lw=1.6, ms=3.2)
for arm in ["300M", "650M"]:
    pts = timeline("RNA-Sc-%s_s17" % arm)
    if pts:
        ax.plot([p[0] for p in pts], [p[2] for p in pts], "-*",
                color=SC[arm], lw=2.0, ms=6)
ax.annotate("10M 层坍缩 L1\n（磨蚀签名）", (1.35, 0.06), fontsize=8.5,
            color="#9A7B35", ha="left")
ax.set_ylabel("最优层相对深度", fontsize=9.5, color=C["ink"])
ax.set_ylim(-0.05, 1.05)
ax.set_xlim(0, 2.2)
ax.set_title("(b) 2B 臂 · 层迁移时间轴", fontsize=10.5, loc="left", pad=6,
             color=C["ink"])
style(ax)

# ============ 下行：5.9B 臂 ============
ax = axes[1][0]
for arm in ["30M", "100M", "300M", "650M"]:
    pts = timeline("RNA-Sc-%s_s17_b59" % arm, include_main=False)
    if not pts:
        continue
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o",
            color=SC[arm], lw=1.9, ms=5, label=arm)
    for p in (pts[0], pts[-1]):
        ax.annotate("%.3f" % p[1], (p[0], p[1]),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=7.2, color=SC[arm])
ax.annotate("30M 过训磨蚀：\n0.341 → 0.194", xy=(5.8, 0.194),
            xytext=(3.1, 0.12), fontsize=8.6, color="#B26A50",
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#B26A50", lw=1.0))
ax.set_xlabel("预训练曝光（B nt）", fontsize=9.5, color=C["ink"])
ax.set_ylabel("最优层 F1（family）", fontsize=9.5, color=C["ink"])
ax.set_xlim(0, 6.6)
ax.set_ylim(0.05, 0.56)
ax.set_title("(c) 5.9B 臂 · F1 全过程（10 点/尺度，中间点已补测）",
             fontsize=10.5, loc="left", pad=6, color=C["ink"])
ax.legend(fontsize=8, frameon=False, loc="lower right")
style(ax)

ax = axes[1][1]
for arm in ["30M", "100M", "300M", "650M"]:
    pts = timeline("RNA-Sc-%s_s17_b59" % arm, include_main=False)
    if not pts:
        continue
    ax.plot([p[0] for p in pts], [p[2] for p in pts], "-s",
            color=SC[arm], lw=1.9, ms=4.5)
ax.annotate("650M 层深全程爬升\nL6→L27", xy=(5.8, 0.96), xytext=(2.6, 0.72),
            fontsize=8.6, color=C["deep"], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C["deep"], lw=1.0))
ax.set_xlabel("预训练曝光（B nt）", fontsize=9.5, color=C["ink"])
ax.set_ylabel("最优层相对深度", fontsize=9.5, color=C["ink"])
ax.set_xlim(0, 6.6)
ax.set_ylim(-0.05, 1.05)
ax.set_title("(d) 5.9B 臂 · 层迁移时间轴（中间点已补测）", fontsize=10.5,
             loc="left", pad=6, color=C["ink"])
style(ax)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_p5_quad.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p5_quad saved")
for arm in ["30M", "100M", "300M", "650M"]:
    pts = timeline("RNA-Sc-%s_s17_b59" % arm, include_main=False)
    print(arm, "b59 n_pts:", len(pts), "rel last:", pts[-1] if pts else None)
