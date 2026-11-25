#!/usr/bin/python3
# Input SHA-256 (verified 2026-11-25):
# s6_timeline.json: 6bc40b65b19beb490fa96a027e5306d654c0574a33145538a99edba0b94c81a0
# s12_linkage_RNA-Sc-30M_s17_c1Mcs.json: a257f3a39953d45cf3b36defbe2f97f2b2bc66bdbfe34aba7fb8bde55fca6143
# s12_linkage_RNA-Sc-100M_s17.json: 6fc2e543a568c4e013e60146cab4d7fa8ac70541a6d173b87644416a40a039f0
# s12_linkage_RNA-Sc-300M_s17.json: 4e8e672060f4bc7059d2fbbd816e037125c851beb6fd428f1c7078f6b00b0cb8
# s12_linkage_RNA-Sc-650M_s17.json: 604b1cbac59f12b7b51ca9b3cf1a5604c8a3d74f62d227f60862c9544e20119c
# p1_derna_discriminator.json: d3d42da799f9c6db772c7ab205d1f2315a1f9cebead45eaad8af07a33fd5daea
# p02a_main_table.csv: e9a8da1753b88de74dab6cc9402a904c5e47c2abf34c12801b55f2d10dfb0b3d

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EVIDENCE = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence")
P0_TABLE = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125/p02a_main_table.csv")
OUT = Path(__file__).resolve().parent

with (EVIDENCE / "s6_timeline.json").open() as handle:
    timeline = json.load(handle)["timeline"]
with (EVIDENCE / "p1_derna_discriminator.json").open() as handle:
    p1 = json.load(handle)
with P0_TABLE.open(newline="") as handle:
    main_rows = {row["scale"]: row for row in csv.DictReader(handle)}

s12_files = {
    "30M\nc1Mcs": "s12_linkage_RNA-Sc-30M_s17_c1Mcs.json",
    "100M": "s12_linkage_RNA-Sc-100M_s17.json",
    "300M": "s12_linkage_RNA-Sc-300M_s17.json",
    "650M": "s12_linkage_RNA-Sc-650M_s17.json",
}
rho = []
for filename in s12_files.values():
    with (EVIDENCE / filename).open() as handle:
        record = json.load(handle)
    assert record["n_families"] == 10
    rho.append(record["spearman_DI_vs_bestlayer"])

nt = [row["ckpt_nt"] / 1e9 for row in timeline]
f1 = [row["best_f1"] for row in timeline]
rel = [row["best_rel_depth"] for row in timeline]
peak = max(range(len(f1)), key=f1.__getitem__)
assert f1[peak] == 0.2549 and timeline[peak]["best_layer"] == 11
assert timeline[-1]["best_layer"] == 1 and f1[-1] == 0.1731
assert p1["650M"]["best"] == {"layer": 27, "rel": 1.0, "f1": 0.4585}

scales = ["100M", "300M", "650M"]
n_layers = {"100M": 23, "300M": 24, "650M": 28}
full_rel = [int(main_rows[s]["best_layers"].split(";")[0]) / (n_layers[s] - 1) for s in scales]
der_rel = [p1[s]["best"]["rel"] for s in scales]
full_layers = [int(main_rows[s]["best_layers"].split(";")[0]) for s in scales]
der_layers = [p1[s]["best"]["layer"] for s in scales]

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 10.5,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "axes.linewidth": 1.2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})
BLUE = "#0F4D92"
BLUE2 = "#3775BA"
GREEN = "#42949E"
RED = "#B64342"
GRAY = "#767676"
LIGHT = "#CFCECE"

fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.8))
ax_a, ax_b, ax_c, ax_d = axes.ravel()

ax_a.plot(nt, f1, color=BLUE, marker="o", markersize=4.5, linewidth=2.0)
ax_a.scatter([nt[peak]], [f1[peak]], s=65, color=RED, zorder=4)
ax_a.annotate(f"Peak {f1[peak]:.4f} (L{timeline[peak]['best_layer']})",
              (nt[peak], f1[peak]), xytext=(12, 10), textcoords="offset points", color=RED)
ax_a.annotate(f"Final {f1[-1]:.4f} (L{timeline[-1]['best_layer']})",
              (nt[-1], f1[-1]), xytext=(-105, 20), textcoords="offset points", color=BLUE)
ax_a.set(xlabel="Pretraining exposure (billion nt)", ylabel="Best-layer family macro-F1",
         title="a  10M family signal rises, then erodes", xlim=(0, 2.0), ylim=(0.14, 0.275))
ax_a.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])

ax_b.plot(nt, rel, color=BLUE2, marker="o", markersize=4.5, linewidth=2.0)
ax_b.scatter([nt[0], nt[-1]], [rel[0], rel[-1]], s=55, color=[RED, BLUE], zorder=4)
ax_b.annotate("L16 at 0.1B", (nt[0], rel[0]), xytext=(12, -2), textcoords="offset points")
ax_b.annotate("L1 at 1.9B", (nt[-1], rel[-1]), xytext=(-68, 22), textcoords="offset points")
ax_b.set(xlabel="Pretraining exposure (billion nt)", ylabel="Best-layer relative depth",
         title="b  Optimal family readout moves shallow", xlim=(0, 2.0), ylim=(-0.04, 1.04))
ax_b.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])
ax_b.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])

ys = list(range(len(scales)))
for y, x0, x1 in zip(ys, full_rel, der_rel):
    ax_c.plot([x0, x1], [y, y], color=LIGHT, linewidth=3, solid_capstyle="round", zorder=1)
ax_c.scatter(full_rel, ys, s=70, color=GRAY, marker="o", label="Full 19-class task", zorder=3)
ax_c.scatter(der_rel, ys, s=75, color=GREEN, marker="D", label="P1: rRNA removed (18 classes)", zorder=3)
for y, x, layer in zip(ys, full_rel, full_layers):
    ax_c.annotate(f"L{layer}", (x, y), xytext=(0, 10), textcoords="offset points", ha="center", color=GRAY)
for y, x, layer in zip(ys, der_rel, der_layers):
    ax_c.annotate(f"L{layer}", (x, y), xytext=(0, -18), textcoords="offset points", ha="center", color=GREEN)
ax_c.set_yticks(ys, scales)
ax_c.invert_yaxis()
ax_c.set(xlabel="Best-layer relative depth", title="c  P1 abolishes the 650M shallow reversal",
         xlim=(-0.03, 1.08), yticks=ys)
ax_c.legend(loc="upper left", ncol=1, fontsize=9.5)

bars = ax_d.bar(range(len(rho)), rho, width=0.62, color=[BLUE, BLUE2, GREEN, GRAY],
                edgecolor="#272727", linewidth=0.8)
for bar, value in zip(bars, rho):
    ax_d.text(bar.get_x() + bar.get_width() / 2, value - 0.025, f"{value:.3f}",
              ha="center", va="top", fontsize=10)
ax_d.axhline(0, color="#272727", linewidth=0.9)
ax_d.set_xticks(range(len(rho)), list(s12_files))
ax_d.set(ylabel=r"Spearman $\rho$ (DI, best layer)",
         title="d  DI–layer association attenuates with scale", ylim=(-0.56, 0.06))
ax_d.text(0.02, 0.05, "Class-level n = 10; descriptive E1", transform=ax_d.transAxes,
          fontsize=9.5, color=GRAY)

fig.suptitle("Where family signal resides: attrition, layer migration, and rRNA dependence",
             fontsize=15, fontweight="bold", y=0.995)
fig.text(0.5, 0.015,
         "Hypothesis M: post-hoc grade-B — chain (b) has intervention support; "
         "chains (a)/(c) are descriptive; tested quantitative forms are refuted.",
         ha="center", fontsize=10, color="#4D4D4D")
fig.tight_layout(pad=2.0, rect=(0, 0.055, 1, 0.96))

for suffix in ("png", "pdf"):
    fig.savefig(OUT / f"fig3_q4.{suffix}", dpi=300, facecolor="white")
plt.close(fig)
print(f"Wrote {OUT / 'fig3_q4.png'} and {OUT / 'fig3_q4.pdf'}")
