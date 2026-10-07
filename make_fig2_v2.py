"""fig2 v2 (request #5): restructure the four-panel structure-emergence figure
with one clear takeaway per panel and explicit per-panel reading guide.

Panels (2x2, generous spacing, one conclusion each):
 (a) Family task: layer curves show scale-dependent migration (10M early,
     650M late-hump) — trained solid, randinit dashed below.
 (b) de-rRNA intervention (P1): removing the rRNA channel RESTORES deep
     monotone depth at 650M — reversal is corpus-channel saturation.
 (c) Structure task: flat curves, randinit overlap — no attrition, no
     pretraining gain on linear readout (task dichotomy).
 (d) Forward covariance: structure knowledge DOES emerge (superlinear at
     650M, randinit≈0) — knowledge present, readout-limited.
All numbers from evidence JSONs. Output: fig2_layerwise_v2.{png,pdf}
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"

SCALE_COLORS = {"1M": "#A0A0A0", "10M": "#C0392B", "30M": "#1B7A3D",
                "100M": "#2F5C8F", "300M": "#E07B39", "650M": "#6A3D9A"}
C_MAIN, C_WARN, C_GOOD, C_GREY = "#2F5C8F", "#B03030", "#1B7A3D", "#8A8A8A"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.0, width=0.8, labelsize=8)
    ax.grid(alpha=0.22, ls=":", lw=0.6)
    ax.set_axisbelow(True)


def takeaway(ax, text, ok=True):
    ax.text(0.985, 0.03, text, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.2, fontweight="bold", color=C_GOOD if ok else C_WARN,
            bbox=dict(fc="#F3FAF3" if ok else "#FDF3F3",
                      ec=C_GOOD if ok else C_WARN,
                      boxstyle="round,pad=0.3", alpha=0.95))


def final_layers(run):
    rows = {}
    for line in open(os.path.join(EV, "probe_results.jsonl")):
        r = json.loads(line)
        if r.get("run") != run or r.get("n_train", 0) < 4000:
            continue
        nt = r.get("ckpt_nt")
        if nt is None:
            continue
        rows.setdefault(nt, {})[r["layer"]] = r["f1_macro"]
    if not rows:
        return None
    final_nt = max(rows)
    d = rows[final_nt]
    L = max(d) + 1
    if set(d) != set(range(L)):
        return None
    return [(li / (L - 1), d[li]) for li in range(L)]


fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.8))

# ---------- (a) family task layer curves ----------
ax = axes[0][0]
for scale, run in [("10M", "RNA-Sc-10M_s17"), ("30M", "RNA-Sc-30M_s17"),
                   ("100M", "RNA-Sc-100M_s17"), ("300M", "RNA-Sc-300M_s17"),
                   ("650M", "RNA-Sc-650M_s17")]:
    pts = final_layers(run)
    if not pts:
        continue
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-",
            color=SCALE_COLORS[scale], lw=1.9, label=scale)
    bx, by = max(pts, key=lambda p: p[1])
    ax.scatter([bx], [by], s=60, color=SCALE_COLORS[scale], zorder=5,
               edgecolors="white", linewidths=0.7)
pts10 = final_layers("RNA-Sc-10M_s17_randinit17")
if pts10:
    ax.plot([p[0] for p in pts10], [p[1] for p in pts10], "--",
            color="#999", lw=1.1, label="10M randinit")
ax.annotate("10M peak at L1\n(attrition: mid-layers eroded)",
            xy=(0.05, 0.173), xytext=(0.30, 0.06), fontsize=8,
            color="#555", arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
ax.annotate("650M best L8\n(early return — see b)",
            xy=(0.296, 0.363), xytext=(0.52, 0.36), fontsize=8,
            color="#555", arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
ax.set_xlabel("relative depth", fontsize=9)
ax.set_ylabel("probe macro-F1 (rna_type, family split)", fontsize=9)
ax.set_title("(a) 家族判别任务：层迁移随规模变化\nFamily task — where does family info live?",
             fontsize=9.8, loc="left", pad=6)
ax.legend(fontsize=7.8, loc="lower right", framealpha=0.92)
takeaway(ax, "读法：峰值星标 = 每尺度最佳层\n10M 塌到浅层，30M–300M 深化，650M 回浅", ok=False)
style_ax(ax)

# ---------- (b) P1 de-rRNA intervention ----------
ax = axes[0][1]
p1 = json.load(open(E + "/p1_derna_discriminator.json"))
for scale, entry in p1.items():
    layers = entry["all_layers"]
    xs = [l["rel"] for l in layers]
    ys = [l["f1"] for l in layers]
    ax.plot(xs, ys, "-o", color=SCALE_COLORS[scale], lw=1.9, ms=4,
            label="%s (18-class, no rRNA)" % scale)
    b = entry["best"]
    ax.scatter([b["rel"]], [b["f1"]], s=80, marker="*", zorder=6,
               color=SCALE_COLORS[scale], edgecolors="white", linewidths=0.7)
ax.annotate("650M: monotone to L27 (rel 1.0), F1 0.4585\n深层逆转消失 — 语料主通道假说获干预证实",
            xy=(1.0, 0.4585), xytext=(0.30, 0.475), fontsize=8.2, color=C_GOOD,
            arrowprops=dict(arrowstyle="->", color=C_GOOD, lw=1.0))
ax.set_xlabel("relative depth", fontsize=9)
ax.set_ylabel("de-rRNA probe F1 (18 classes)", fontsize=9)
ax.set_title("(b) 去除 rRNA 通道（P1 干预实验）\nIntervention: drop the dominant rRNA channel",
             fontsize=9.8, loc="left", pad=6)
ax.legend(fontsize=7.8, loc="lower right", framealpha=0.92)
takeaway(ax, "读法：拿掉占 63.6% 的 rRNA 后\n650M 最佳层回到深层（L27/28）", ok=True)
style_ax(ax)

# ---------- (c) structure task flat curves ----------
ax = axes[1][0]
best_tr = {"1M": (0.5526, 6), "10M": (0.5663, 6), "30M": (0.5756, 3),
           "100M": (0.589, 22), "300M": (0.5978, 22), "650M": (0.5973, 15)}
best_ri = {"1M": 0.5452, "10M": 0.5678, "30M": 0.5786, "100M": 0.5855,
           "300M": 0.5899, "650M": 0.5909}
xs_c = np.arange(6)
ax.plot(xs_c, [best_tr[s][0] for s in best_tr], "-o", color=C_MAIN, lw=2.0,
        ms=7, label="trained (best layer)", markeredgecolor="white",
        markeredgewidth=0.8)
ax.plot(xs_c, [best_ri[s] for s in best_ri], "-s", color=C_GREY, lw=1.7,
        ms=6, label="randinit (same arch)", markeredgecolor="white",
        markeredgewidth=0.7)
for i, s in enumerate(best_tr):
    ax.annotate("%.3f|%.3f" % (best_tr[s][0], best_ri[s]), (xs_c[i], 0.6015),
                ha="center", fontsize=7.2, color="#555")
ax.set_xticks(xs_c)
ax.set_xticklabels(list(best_tr.keys()), fontsize=8.6)
ax.set_ylim(0.535, 0.612)
ax.set_ylabel("bpRNA paired-position F1", fontsize=9)
ax.set_xlabel("scale", fontsize=9)
ax.set_title("(c) 结构任务（线性探针）：增益≈0\nStructure task — linear readout sees nothing",
             fontsize=9.8, loc="left", pad=6)
ax.legend(fontsize=7.8, loc="lower right", framealpha=0.92)
takeaway(ax, "读法：trained vs randinit 全档 |Δ|≤0.016\n上方数字 = trained|randinit", ok=False)
style_ax(ax)

# ---------- (d) forward covariance emergence ----------
ax = axes[1][1]
cov_s = json.load(open(E + "/covariation_test.json"))
cov_650 = json.load(open(E + "/covariation_test_650M.json"))
cov = {"1M": cov_s["1M"]["cov_minus_ctrl"], "10M": cov_s["10M"]["cov_minus_ctrl"],
       "30M": cov_650["30M"]["cov_minus_ctrl"],
       "100M": cov_s["100M"]["cov_minus_ctrl"] if "100M" in cov_s else cov_650.get("100M", {}).get("cov_minus_ctrl"),
       "650M": cov_650["650M"]["cov_minus_ctrl"]}
params = [1.0, 10.0, 30.0, 100.0, 666.0]
vals = [cov["1M"], cov["10M"], cov["30M"], cov["100M"], cov["650M"]]
ax.plot(params, vals, "-o", color=C_GOOD, lw=2.0, ms=8,
        markeredgecolor="white", markeredgewidth=0.8)
for x, y, s in zip(params, vals, ["1M", "10M", "30M", "100M", "650M"]):
    ax.annotate("%s\n+%.3f" % (s, y), (x, y), textcoords="offset points",
                xytext=(0, 12), ha="center", fontsize=7.8, fontweight="bold")
ax.axhline(0, color="#999", lw=0.8)
ax.set_xscale("log")
ax.set_ylim(-0.015, 0.135)
ax.set_xlabel("parameters (M)", fontsize=9)
ax.set_ylabel("forward covariance COV − CTRL", fontsize=9)
ax.set_title("(d) 前向共变（免探针）：结构知识真实涌现\nForward covariance — knowledge IS there",
             fontsize=9.8, loc="left", pad=6)
ax.annotate("650M +0.096 = 100M 的 4.7 倍（超线性）\nrandinit ≈ 0（100% 预训练来源）",
            xy=(666, 0.096), xytext=(8, 0.115), fontsize=8.2, color=C_GOOD,
            arrowprops=dict(arrowstyle="->", color=C_GOOD, lw=1.0))
takeaway(ax, "读法：c 的“零增益”是线性读出的局限\n结构知识在 (d) 超线性增长", ok=True)
style_ax(ax)

fig.suptitle("结构涌现四面板：(a) 家族层迁移 → (b) P1 干预定因 → (c) 线性读出墙 → (d) 前向证据",
             fontsize=11, fontweight="bold", x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.955])
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, "fig2_layerwise_v2.%s" % ext), dpi=200,
                bbox_inches="tight")
plt.close(fig)
print("fig2_v2 saved")
