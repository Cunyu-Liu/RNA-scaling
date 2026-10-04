"""Fig 6 v2: two-point budget axis + Claim-14 falsification mark."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"

fv = json.load(open(E + "/factorial_verdict.json"))
rows = fv["table"]
c14 = fv.get("claim14_300M", {})

fig, ax = plt.subplots(figsize=(6.8, 4.6))
xs, ys, labels, layers = [], [], [], []
for scale in ["30M", "100M", "300M", "650M"]:
    r = rows.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_5.9B")
    if f2 and f2.get("f1") is not None:
        xs.append(0); ys.append(f2["f1"])
        labels.append(scale + " @2.0B"); layers.append("L%d" % f2["layer"])
    if f5 and f5.get("f1") is not None:
        xs.append(1); ys.append(f5["f1"])
        labels.append(scale + " @5.9B"); layers.append("L%d" % f5["layer"])

ax.scatter(xs, ys, s=130, c=["#25658C" if x == 0 else "#B03030" for x in xs],
           zorder=3)

# connect pairs with annotations
r100 = rows.get("100M", {}); r300 = rows.get("300M", {})
if r100.get("f1_2B") and r100.get("f1_5.9B"):
    ax.annotate("", xy=(1, r100["f1_5.9B"]["f1"]),
                xytext=(0, r100["f1_2B"]["f1"]),
                arrowprops=dict(arrowstyle="->", color="#B03030", lw=1.7))
    ax.text(0.5, (r100["f1_2B"]["f1"] + r100["f1_5.9B"]["f1"]) / 2 - 0.004,
            "100M: −2.74pp\n(overtrained)", ha="center", fontsize=9.5,
            color="#B03030", fontweight="bold",
            bbox=dict(fc="white", ec="#B03030", alpha=0.92, boxstyle="round,pad=0.25"))
if r300.get("f1_2B") and r300.get("f1_5.9B"):
    ax.annotate("", xy=(1, r300["f1_5.9B"]["f1"]),
                xytext=(0, r300["f1_2B"]["f1"]),
                arrowprops=dict(arrowstyle="->", color="#1B7A3D", lw=1.7))
    ax.text(0.5, (r300["f1_2B"]["f1"] + r300["f1_5.9B"]["f1"]) / 2 + 0.006,
            "300M: +3.76pp\n(undertrained @2B)", ha="center", fontsize=9.5,
            color="#1B7A3D", fontweight="bold",
            bbox=dict(fc="white", ec="#1B7A3D", alpha=0.92, boxstyle="round,pad=0.25"))

# 650M@2B reference line (the whole-line prior best)
ax.axhline(0.3632, ls="--", lw=1.1, color="#777")
ax.text(0.02, 0.3645, "650M@2B = 0.3632 (prior line best)", fontsize=8.5,
        color="#555")

for x, y, l, lay in zip(xs, ys, labels, layers):
    dy = 0.010 if "@2" in l else -0.014
    ax.text(x, y + dy, l.split(" ")[0] + " " + lay, ha="center", fontsize=9)

if c14:
    ax.text(0.97, 0.04,
            "Claim-14 (pre-registered): boundary_holds = %s\n(bar +1.0pp; measured %+0.2fpp)"
            % (str(c14.get("boundary_holds")).lower(), c14.get("delta_pp", 0)),
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5,
            fontweight="bold", color="#B03030",
            bbox=dict(fc="white", ec="#B03030", alpha=0.92))

ax.set_xticks([0, 1])
ax.set_xticklabels(["2.0B nt (main line)", "5.9B nt (full corpus)"])
ax.set_ylabel("family-split probe macro-F1")
ax.set_ylim(0.23, 0.41)
ax.set_title("Budget × scale sign flip: 100M overtrained / 300M undertrained at 2.0B;\n300M@5.9B 0.3821 > entire 2.0B line incl. 650M (Chinchilla-style interaction)",
             fontsize=10.5)
ax.grid(alpha=0.25, ls=":")
ax.set_xlim(-0.55, 1.75)
fig.tight_layout()
fig.savefig(FIG + "/fig6_budget_axis.pdf")
fig.savefig(FIG + "/fig6_budget_axis.png", dpi=200)
print("fig6 v2 saved (2 points + Claim-14 falsification)")
