"""fig_p5_v5_r2: 页 5 上图三面板（对照排除）升级版。

修复用户指出的缺口：
  1) 面板 b/c 只画 1M-100M —— 补 300M/650M 时间轴（ckpt 探针）
  2) 缺 5.9B（b59）预训练曝光点 —— 在 b 面板以菱形补 4 个尺度 @5.9B
数据源：s4_randinit_table / s5_mommatch_table / s6_cross_scale + probe ckpt 轴 + b59。
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


def load(name):
    return json.load(open(os.path.join(E, name)))


s4 = load("s4_randinit_table.json")
s5 = load("s5_mommatch_table.json")
s6 = load("s6_cross_scale.json")

# ckpt 时间轴（family split, probe_results.jsonl）——300M/650M
rows = {}
for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
    r = json.loads(line)
    if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
        continue
    run = r.get("run", "")
    nt = r.get("ckpt_nt")
    if nt and (run.startswith("RNA-Sc-300M_s17_ck")
               or run.startswith("RNA-Sc-650M_s17_ck")):
        rows.setdefault(run, {})[nt] = max(
            rows.setdefault(run, {}).get(nt, 0), r["f1_macro"])

fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.1))

# ---------- (a) 对照排除 ----------
ax = axes[0]
scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
xs = np.arange(len(scales))
tr = [s4[s]["trained"] for s in scales]
ri = [s4[s]["randinit"] for s in scales]
mm = [s5[s]["mommatch"] for s in scales]
ax.fill_between(xs, ri, tr, color=C["main"], alpha=0.10, zorder=1)
ax.plot(xs, tr, "o-", color=C["main"], lw=1.8, ms=6, zorder=4)
ax.plot(xs, mm, "^--", color=C["amber"], lw=1.4, ms=5.5, zorder=3)
ax.plot(xs, ri, "s:", color=C["coral"], lw=1.4, ms=5.5, zorder=3)
for x, t, r in zip(xs, tr, ri):
    ax.annotate("+%.3f" % (t - r), (x, (t + r) / 2), ha="center",
                fontsize=7.4, color="#5E7FA0")
ax.text(0.03, 0.94, "trained", transform=ax.transAxes, fontsize=9,
        color=C["main"], fontweight="bold")
ax.text(0.03, 0.86, "moment-matched（H3）", transform=ax.transAxes,
        fontsize=8, color=C["amber"])
ax.text(0.03, 0.78, "random-init（H2）", transform=ax.transAxes,
        fontsize=8, color=C["coral"])
ax.set_xticks(xs)
ax.set_xticklabels(scales)
ax.set_xlabel("模型尺度", fontsize=10, color=C["ink"])
ax.set_ylabel("最优层 family-split F1", fontsize=10, color=C["ink"])
ax.set_title("(a) 对照排除：增益不被权重统计解释", fontsize=11,
             loc="left", pad=8, color=C["ink"])
style(ax)

# ---------- (b) 时间轴 F1（全六尺度 + 5.9B）----------
ax = axes[1]
for scale in ["1M", "10M", "30M", "100M"]:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
            "-o", color=SC[scale], lw=1.6, ms=3.6, label=scale)
# 300M/650M ckpt 时间轴（新补）
for arm, key, col in [("300M", "RNA-Sc-300M_s17_ck", C["main"]),
                      ("650M", "RNA-Sc-650M_s17_ck", C["deep"])]:
    sub = {nt: f for k, v in rows.items() if k.startswith(key)
           for nt, f in v.items()}
    if sub:
        nts = sorted(sub)
        ax.plot([n / 1e9 for n in nts], [sub[n] for n in nts], "-*",
                color=col, lw=2.0, ms=8, label=arm + "（ckpt 轴）")
# 5.9B 点（b59 臂, family split）
fv = load("factorial_verdict.json")
b59 = {a: fv["table"][a]["f1_5.9B"]["f1"] for a in
       ("30M", "100M", "300M", "650M")}
ax.scatter([5.9] * 4, list(b59.values()), s=110, marker="D",
           color=[SC[a] for a in b59], zorder=6, edgecolors="white",
           linewidths=1.0)
ax.axvline(5.9, color=C["grey"], ls="--", lw=1.0, alpha=0.7)
ax.text(5.55, 0.46, "5.9B 全语料臂", fontsize=8.5, color="#707070",
        rotation=90, va="top", ha="right")
ax.annotate("650M@5.9B 0.3747", (5.9, 0.3747), xytext=(3.3, 0.44),
            fontsize=8.2, color=C["deep"], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C["deep"], lw=0.9))
ax.annotate("300M@5.9B 0.3777", (5.9, 0.3777), xytext=(3.3, 0.50),
            fontsize=8.2, color=C["main"], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C["main"], lw=0.9))
ax.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
ax.set_ylabel("最优层 F1（时间轴）", fontsize=10, color=C["ink"])
ax.set_xlim(0, 6.4)
ax.set_title("(b) 全六尺度时间轴 + 5.9B 点（300M/650M 补全）", fontsize=11,
             loc="left", pad=8, color=C["ink"])
ax.legend(fontsize=7.6, frameon=False, loc="lower right", ncol=2)
style(ax)

# ---------- (c) 层迁移时间轴（全六尺度）----------
ax = axes[2]
for scale in ["1M", "10M", "30M", "100M"]:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_rel"] for p in pts],
            "-s", color=SC[scale], lw=1.6, ms=3.4)
# 300M/650M ckpt 层深（用 probe best layer / n_layers）
for arm, key, col in [("300M", "RNA-Sc-300M_s17_ck", C["main"]),
                      ("650M", "RNA-Sc-650M_s17_ck", C["deep"])]:
    sub = {nt: f for k, v in rows.items() if k.startswith(key)
           for nt, f in v.items()}
    # 层深需从 probe_results 重取
    subrel = {}
    for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
        r = json.loads(line)
        if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
            continue
        run = r.get("run", "")
        nt = r.get("ckpt_nt")
        if nt and run.startswith(key):
            rel = r.get("layer") / (r.get("n_layers") - 1)
            subrel.setdefault(nt, 0)
            if r["f1_macro"] >= sub.get(nt, 0):
                subrel[nt] = rel
    if subrel:
        nts = sorted(subrel)
        ax.plot([n / 1e9 for n in nts], [subrel[n] for n in nts], "-*",
                color=col, lw=2.0, ms=8)
ax.annotate("10M 层坍缩至 L1\n（磨蚀签名）", (1.55, 0.06), fontsize=9,
            color="#9A7B35", ha="left")
ax.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
ax.set_ylabel("最优层相对深度", fontsize=10, color=C["ink"])
ax.set_ylim(-0.05, 1.05)
ax.set_xlim(0, 6.4)
ax.set_title("(c) 层迁移：全六尺度；10M 坍缩、650M 深化", fontsize=11,
             loc="left", pad=8, color=C["ink"])
style(ax)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_p5_v5_r2.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p5_v5_r2 saved")
