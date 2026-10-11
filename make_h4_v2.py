"""H4 图 v2：全过程涌现曲线（300M/650M 逐 ckpt 数据补齐后重画）。

升级点（用户需求）：左图从"星标"升级为全过程曲线——
  1M/10M/30M/100M 原有时间线（s6_cross_scale）+
  300M/650M 新增逐 ckpt 行（本次 _ck probe 产出，全层扫描取最优）。
b59 的 5.9B 终态仍保留（虚线参考）。
数据源：s6_cross_scale.json + probe_results.jsonl 的新 _ck 行。
"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

s6 = json.load(open(os.path.join(E, "s6_cross_scale.json")))
fv = json.load(open(os.path.join(E, "factorial_verdict.json")))

# 收集 300M/650M 新 _ck 行（n_train>=20000，family split）
rows = defaultdict(lambda: defaultdict(float))
for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
    r = json.loads(line)
    run = r.get("run", "")
    if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
        continue
    if run.startswith("RNA-Sc-300M_s17_ck") \
            or run.startswith("RNA-Sc-650M_s17_ck"):
        nt = r.get("ckpt_nt")
        if nt:
            rows[run][nt] = max(rows[run][nt], r["f1_macro"])

C = {"1M": "#9aa5b1", "10M": "#e08214", "30M": "#3572b0",
     "100M": "#2F5C8F", "300M": "#1B7A3D", "650M": "#B03030"}

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.8, 4.4))

# 左：全过程时间线（六尺度全曲线）
for arm in ["1M", "10M", "30M", "100M"]:
    pts = s6[arm]
    axL.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
             color=C[arm], lw=1.7, marker="o", ms=3.5, label=arm)
for arm, key in [("300M", "RNA-Sc-300M_s17_ck"),
                 ("650M", "RNA-Sc-650M_s17_ck")]:
    sub = {nt: f for k, v in rows.items() if k.startswith(key)
           for nt, f in v.items()}
    if sub:
        nts = sorted(sub)
        axL.plot([n / 1e9 for n in nts], [sub[n] for n in nts],
                 color=C[arm], lw=2.2, marker="*", ms=9, label=arm + "（新）")
    else:
        axL.scatter([1.9], [fv["table"][arm]["f1_2B"]["f1"]], s=140,
                    marker="*", color=C[arm], zorder=5, label=arm + "（单点）")

axL.axvline(0.35, color="#e08214", ls=":", lw=1.1)
axL.text(0.36, 0.12, "10M 磨蚀谷窗口", fontsize=8, color="#e08214",
         rotation=90, va="bottom")
axL.set_xlabel("训练预算（B nt）", fontsize=10.5)
axL.set_ylabel("最优层 F1（family 切分）", fontsize=10.5)
axL.set_ylim(0.10, 0.45)
axL.set_title("H4 涌现时间线：六尺度全过程（300M/650M 已补曲线）",
              fontsize=11, pad=10)
axL.legend(fontsize=8.2, frameon=False, loc="lower right", ncol=2)
axL.spines[["top", "right"]].set_visible(False)

# 右：双预算最优层（不变）
t = fv["table"]
arms = ["30M", "100M", "300M", "650M"]
rel2b = [t[a]["f1_2B"]["rel"] for a in arms]
rel59 = [t[a]["f1_5.9B"]["rel"] for a in arms]
x = range(4)
w = 0.38
axR.bar([i - w / 2 for i in x], rel2b, w, color="#2F5C8F",
        label="2.0B 最优层深度")
axR.bar([i + w / 2 for i in x], rel59, w, color="#B03030",
        label="5.9B 最优层深度")
for i in range(4):
    axR.text(i - w / 2, rel2b[i] + 0.02, "L%d" % t[arms[i]]["f1_2B"]["layer"],
             ha="center", fontsize=9.5, color="#2F5C8F", fontweight="bold")
    axR.text(i + w / 2, rel59[i] + 0.02, "L%d" % t[arms[i]]["f1_5.9B"]["layer"],
             ha="center", fontsize=9.5, color="#B03030", fontweight="bold")
axR.set_xticks(list(x))
axR.set_xticklabels(arms, fontsize=11)
axR.set_ylim(0, 1.12)
axR.set_ylabel("最优层相对深度", fontsize=10)
axR.set_title("H4 链②：5.9B 修复 650M 磨蚀（L8→L25）", fontsize=11, pad=10)
axR.legend(fontsize=9.5, frameon=False, loc="upper left")
axR.spines[["top", "right"]].set_visible(False)
axR.annotate("磨蚀被预算修复", xy=(3 + w / 2, rel59[3]), xytext=(1.9, 0.55),
             fontsize=9.5, color="#B03030",
             arrowprops=dict(arrowstyle="->", color="#B03030", lw=1.3))

fig.suptitle("H4 磨蚀/容量门控：全过程曲线 + 双预算证据", fontsize=13, y=1.0)
fig.tight_layout()
out = os.path.join(FIG, "fig_h4_v2_fullcurve.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("saved", out)
for arm, key in [("300M", "RNA-Sc-300M_s17_ck"),
                 ("650M", "RNA-Sc-650M_s17_ck")]:
    sub = {nt: f for k, v in rows.items() if k.startswith(key)
           for nt, f in v.items()}
    print(arm, "curve pts:", sorted((round(n / 1e9, 2),
                                     round(sub[n], 4))
                                    for n in sub) if sub else "NO DATA YET")
