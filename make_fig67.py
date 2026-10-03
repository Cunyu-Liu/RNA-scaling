"""Fig 6/7: budget-axis factorial + cross-model RNS scatter.

fig6: 100M budget pair (2B vs 5.9B) + randinit reference, with layer
annotations — the overtraining negative effect visualized.
fig7: 8-model RNS@10 vs random-split F1 scatter with Spearman −0.60.

Reads evidence jsons only; matplotlib, no seaborn.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"

# ---------- fig 6: budget axis ----------
fv = json.load(open(E + "/factorial_verdict.json"))
rows = fv["table"]

fig, ax = plt.subplots(figsize=(6.4, 4.4))
xs, ys, labels, layers = [], [], [], []
ref = {"randinit_5.9B": 0.1577}
for scale in ["30M", "100M", "300M", "650M"]:
    r = rows.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_5.9B")
    if f2 and f2.get("f1") is not None:
        xs.append(0); ys.append(f2["f1"])
        labels.append(scale + " @2.0B"); layers.append("L%d" % f2["layer"])
    if f5 and f5.get("f1") is not None:
        xs.append(1); ys.append(f5["f1"])
        labels.append(scale + " @5.9B"); layers.append("L%d" % f5["layer"])

ax.scatter(xs, ys, s=120, c=["#25658C" if x == 0 else "#B03030" for x in xs],
           zorder=3)
# connect 100M pair
r100 = rows.get("100M", {})
if r100.get("f1_2B") and r100.get("f1_5.9B"):
    ax.annotate("", xy=(1, r100["f1_5.9B"]["f1"]),
                xytext=(0, r100["f1_2B"]["f1"]),
                arrowprops=dict(arrowstyle="->", color="#B03030", lw=1.6))
    ax.text(0.5, (r100["f1_2B"]["f1"] + r100["f1_5.9B"]["f1"]) / 2,
            "−2.74pp", ha="center", va="center", fontsize=11,
            color="#B03030", fontweight="bold",
            bbox=dict(fc="white", ec="#B03030", alpha=0.9, boxstyle="round,pad=0.25"))
# randinit ref for 100M 5.9B
ax.axhline(0.1577, ls="--", lw=1, color="#888")
ax.text(1.02, 0.1577, "randinit@5.9B\n0.1577", fontsize=8, color="#555",
        va="center")
for x, y, l, lay in zip(xs, ys, labels, layers):
    dy = 0.012 if "@2" in l else -0.016
    ax.text(x, y + dy, l.split(" ")[0] + " " + lay, ha="center", fontsize=9)
ax.set_xticks([0, 1])
ax.set_xticklabels(["2.0B nt (main line)", "5.9B nt (full corpus)"])
ax.set_ylabel("family-split probe macro-F1")
ax.set_title("Budget axis (3×2 factorial): 100M overtraining negative;\n2.0B at/beyond compute-optimal on redundant corpus",
             fontsize=11)
ax.grid(alpha=0.25, ls=":")
ax.set_xlim(-0.5, 1.7)
fig.tight_layout()
fig.savefig(FIG + "/fig6_budget_axis.pdf")
fig.savefig(FIG + "/fig6_budget_axis.png", dpi=200)
print("fig6 saved")

# ---------- fig 7: cross-model RNS ----------
ex = json.load(open(E + "/s14_rns_ext.json"))
rns = ex["rns_k10"]
f1 = {}
for line in open("/mnt/cunyuliu/rna-sc/eval/eval_matrix_results.jsonl"):
    r = json.loads(line)
    if r.get("split") == "random" and r.get("protocol") == "probe-balanced":
        f1[r["model"]] = r["best_f1_macro"]
name_map = {"RNA-Sc-1M": "RNA-Sc-1M_s17", "RNA-Sc-10M": "RNA-Sc-10M_s17",
            "RNA-Sc-30M": "RNA-Sc-30M_s17", "RNA-Sc-100M": "RNA-Sc-100M_s17",
            "RiNALMo-micro": "RiNALMo-micro", "RiNALMo-mega": "RiNALMo-mega",
            "RiNALMo-giga": "RiNALMo-giga", "RNA-FM-96M": "RNA-FM-96M"}
pairs = [(k, rns[k], f1[mk]) for k, mk in name_map.items()
         if k in rns and mk in f1]

fig, ax = plt.subplots(figsize=(6.4, 4.4))
ours = [(n, r, f) for n, r, f in pairs if n.startswith("RNA-Sc")]
ext = [(n, r, f) for n, r, f in pairs if not n.startswith("RNA-Sc")]
ax.scatter([r for _, r, _ in ours], [f for _, _, f in ours], s=110,
           c="#25658C", label="ours (controlled family)", zorder=3)
ax.scatter([r for _, r, _ in ext], [f for _, _, f in ext], s=110,
           c="#B7791F", marker="s", label="published models", zorder=3)
for n, r, f in pairs:
    ax.annotate(n, (r, f), textcoords="offset points", xytext=(6, 4),
                fontsize=8)
sp = ex.get("spearman_rns_randomF1", -0.60)
ax.text(0.97, 0.95, "Spearman ρ = %.2f (n=%d)" % (sp, len(pairs)),
        transform=ax.transAxes, ha="right", va="top", fontsize=11,
        fontweight="bold",
        bbox=dict(fc="white", ec="#25658C", alpha=0.9))
ax.set_xlabel("RNS@10 (lower = representation closer to real-manifold)")
ax.set_ylabel("random-split family F1")
ax.set_title("Cross-model RNS vs random-split performance:\nmodel-level reliability axis (RiNALMo vs RNA-FM extremes)",
             fontsize=11)
ax.legend(fontsize=9, loc="center right")
ax.grid(alpha=0.25, ls=":")
fig.tight_layout()
fig.savefig(FIG + "/fig7_rns_crossmodel.pdf")
fig.savefig(FIG + "/fig7_rns_crossmodel.png", dpi=200)
print("fig7 saved")
