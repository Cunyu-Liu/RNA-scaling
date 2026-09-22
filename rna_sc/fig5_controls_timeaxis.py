"""T4.1.5: Figure 5 — mechanistic controls + pretraining-time axis.

Three panels (line-2-unique evidence, the "controlled" story):
  (a) Control exclusion: trained vs randinit vs moment-matched best-layer
      F1 across 1M/10M/30M/100M — the gain (shaded) survives both
      controls and grows with scale (H2/H3 excluded);
  (b) Pretraining-time trajectories: best F1 vs nt for the four scales
      (10M attrition valley visible; 30M/100M rise; 1M flat);
  (c) Best-layer relative depth vs nt (10M layer downshift L16->L1 as
      the attrition signature).

Data: evidence/s4_randinit_table.json, s5_mommatch_table.json,
      s6_cross_scale.json (all deterministic inc12 protocol).
Output: figs/fig5_controls_timeaxis.{png,pdf}
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "figs", "fig5_controls_timeaxis")

s4 = json.load(open(os.path.join(MNT, "evidence/s4_randinit_table.json")))
s5 = json.load(open(os.path.join(MNT, "evidence/s5_mommatch_table.json")))
s6 = json.load(open(os.path.join(MNT, "evidence/s6_cross_scale.json")))

scales = ["1M", "10M", "30M", "100M"]

fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))

ax = axes[0]
xs = list(range(len(scales)))
tr = [s4[s]["trained"] for s in scales]
ri = [s4[s]["randinit"] for s in scales]
mm = [s5[s]["mommatch"] for s in scales]
ax.plot(xs, tr, "o-", color="#1a6faf", lw=2.2, ms=8, label="trained")
ax.plot(xs, mm, "^--", color="#e67e22", lw=1.8, ms=7,
        label="moment-matched (H3 ctrl)")
ax.plot(xs, ri, "s:", color="#c0392b", lw=1.8, ms=7,
        label="random-init (H2 ctrl)")
ax.fill_between(xs, ri, tr, color="#1a6faf", alpha=0.12)
for x, t, r in zip(xs, tr, ri):
    ax.annotate("+%.3f" % (t - r), (x, (t + r) / 2), ha="center",
                fontsize=8, color="#1a6faf")
ax.set_xticks(xs)
ax.set_xticklabels(scales)
ax.set_xlabel("model scale")
ax.set_ylabel("best-layer family-split F1")
ax.set_title("(a) Controls excluded: gain survives\nweight statistics (H2/H3)")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25)

ax = axes[1]
colors = {"1M": "#7f8c8d", "10M": "#c0392b", "30M": "#27ae60",
          "100M": "#1a6faf"}
for scale in scales:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_f1"] for p in pts],
            "-o", color=colors[scale], lw=1.8, ms=4,
            label="%s" % scale)
peak10 = max(s6["10M"], key=lambda p: p["best_f1"])
ax.annotate("10M peak %.3f" % peak10["best_f1"],
            (peak10["nt_B"], peak10["best_f1"]),
            textcoords="offset points", xytext=(10, 6), fontsize=8,
            color="#c0392b")
ax.axvline(peak10["nt_B"], color="#c0392b", ls=":", lw=1)
ax.set_xlabel("pretraining exposure (B nt)")
ax.set_ylabel("best-layer F1 (time axis)")
ax.set_title("(b) Attrition valley at 10M;\n30M/100M keep rising")
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25)

ax = axes[2]
for scale in scales:
    pts = s6[scale]
    ax.plot([p["nt_B"] for p in pts], [p["best_rel"] for p in pts],
            "-s", color=colors[scale], lw=1.8, ms=4, label="%s" % scale)
ax.annotate("10M layer downshift\n(attrition signature)",
            (1.9, 0.05), fontsize=8, color="#c0392b", ha="right")
ax.set_xlabel("pretraining exposure (B nt)")
ax.set_ylabel("best-layer relative depth")
ax.set_ylim(-0.05, 1.05)
ax.set_title("(c) Layer migration: 10M collapses to\nearly layers; large scales deepen")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25)

fig.suptitle("Fig 5 — Mechanistic controls and pretraining-time dynamics "
             "(controlled family, line 2)", y=1.03, fontsize=11.5)
fig.tight_layout()
fig.savefig(OUT + ".png", dpi=200, bbox_inches="tight")
fig.savefig(OUT + ".pdf", bbox_inches="tight")
print("saved", OUT + ".png/.pdf")
print("panel a: deltas", {s: round(s4[s]["delta"], 4) for s in scales})
print("10M peak at nt_B=%.1f f1=%.4f" % (peak10["nt_B"],
                                          peak10["best_f1"]))
