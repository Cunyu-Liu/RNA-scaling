"""fig_p5_split_v2: 页 5 上图重画——2B 与 5.9B 分开画 + 5.9B 补全中间点。

布局：1×2 双面板。
  左（2B 臂）：1M/10M/30M/100M 原时间轴 + 300M/650M ckpt 轴（*）——预训练曝光 0-2.2B
  右（5.9B 臂）：30M/100M/300M/650M 四尺度中间点（0.4-5.8B）——预算扩展轴
两图 y 轴同范围可比。数据：s6_cross_scale + probe_results _ck 行 + b59 中间点（本轮补测）。
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
    ax.tick_params(colors=C["ink"], labelsize=9, length=3, width=0.7)
    ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
    ax.set_axisbelow(True)


def collect(base_run, b59=False):
    """family-split 全层 best F1 by ckpt_nt。"""
    rows = defaultdict(dict)
    for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
        r = json.loads(line)
        if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
            continue
        run = r.get("run", "")
        nt = r.get("ckpt_nt")
        want = (run == base_run) or (b59 and run.startswith(base_run + "_ck")) \
            or (not b59 and run.startswith(base_run + "_ck"))
        if nt and want:
            rows[nt][r["layer"]] = max(rows[nt].get(r["layer"], 0),
                                       r["f1_macro"])
    out = {}
    for nt, layers in rows.items():
        bl = max(layers, key=layers.get)
        out[nt] = (layers[bl], bl, r.get("n_layers", 1))
    return out


s6 = json.load(open(os.path.join(E, "s6_cross_scale.json")))
fv = json.load(open(os.path.join(E, "factorial_verdict.json")))

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.2, 4.6),
                               gridspec_kw={"width_ratios": [1.15, 1]})

# ---------- 左：2B 臂（全六尺度）----------
for scale in ["1M", "10M", "30M", "100M"]:
    pts = s6[scale]
    axL.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
             "-o", color=SC[scale], lw=1.7, ms=3.8, label=scale)
# 300M/650M 2B ckpt 轴
for arm, col in [("300M", C["main"]), ("650M", C["deep"])]:
    d = collect("RNA-Sc-%s_s17" % arm)
    if d:
        nts = sorted(d)
        axL.plot([n / 1e9 for n in nts], [d[n][0] for n in nts], "-*",
                 color=col, lw=2.0, ms=8, label=arm)
# 10M 磨蚀谷标注
axL.annotate("10M 磨蚀谷", xy=(1.4, 0.172), xytext=(0.35, 0.09),
             fontsize=9, color="#9A7B35",
             arrowprops=dict(arrowstyle="->", color="#9A7B35", lw=1.0))
axL.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
axL.set_ylabel("最优层 F1（family 切分）", fontsize=10, color=C["ink"])
axL.set_xlim(0, 2.2)
axL.set_ylim(0.05, 0.56)
axL.set_title("(a) 2B 臂：全六尺度时间轴（300M/650M 已补全）", fontsize=11,
              loc="left", pad=8, color=C["ink"])
axL.legend(fontsize=8.4, frameon=False, loc="lower right", ncol=2)
style(axL)

# ---------- 右：5.9B 臂（四尺度中间点）----------
for arm in ["30M", "100M", "300M", "650M"]:
    d = collect("RNA-Sc-%s_s17_b59" % arm, b59=True)
    if not d:
        continue
    nts = sorted(d)
    axR.plot([n / 1e9 for n in nts], [d[n][0] for n in nts], "-o",
             color=SC[arm], lw=1.9, ms=5.2, label=arm)
    for n in nts:
        axR.annotate("%.3f" % d[n][0], (n / 1e9, d[n][0]),
                     textcoords="offset points", xytext=(0, 7),
                     ha="center", fontsize=7.4, color=SC[arm])
# 2B 终点参照线（每尺度 2B 值做水平参考）
for arm, y in [("30M", 0.2466), ("100M", 0.3263),
               ("300M", 0.3445), ("650M", 0.3632)]:
    axR.axhline(y, color=SC[arm], ls=":", lw=0.8, alpha=0.55)
    axR.text(6.05, y + 0.004, "%s@2B %.3f" % (arm, y), fontsize=7.2,
             color=SC[arm], ha="right", va="bottom")
axR.set_xlabel("预训练曝光（B nt）", fontsize=10, color=C["ink"])
axR.set_ylabel("最优层 F1（family 切分）", fontsize=10, color=C["ink"])
axR.set_xlim(0, 6.6)
axR.set_ylim(0.05, 0.56)
axR.set_title("(b) 5.9B 臂：预算扩展全过程（中间点已补测）", fontsize=11,
              loc="left", pad=8, color=C["ink"])
axR.legend(fontsize=8.4, frameon=False, loc="lower right")
style(axR)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_p5_split_v2.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p5_split_v2 saved")
# 数据点数报告
for arm in ["30M", "100M", "300M", "650M"]:
    d = collect("RNA-Sc-%s_s17_b59" % arm, b59=True)
    print(arm, "b59 points:", len(d), sorted(round(k / 1e9, 2) for k in d))
