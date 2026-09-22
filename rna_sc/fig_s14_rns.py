"""T4.1.5c: S14 RNS representation-quality figure (H8).

Two panels from existing evidence (no GPU needed, plotting only):
  (a) RNS@10 vs model scale (1M..100M + randinit band + 650M add-on)
  (b) RNS vs pretraining nt (10M time axis, peak 1.0B) overlaid with
      probe F1 trajectory (peak 0.5B) — the two-peak misalignment.

Data: evidence/s14_rns.json, s14_rns_650m.json, s14_timeaxis.json.
Output: figs/fig_s14_rns.{png,pdf}
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "figs", "fig_s14_rns")

d = json.load(open(os.path.join(MNT, "evidence", "s14_rns.json")))
d65 = json.load(open(os.path.join(MNT, "evidence", "s14_rns_650m.json")))
dt = json.load(open(os.path.join(MNT, "evidence", "s14_timeaxis.json")))

res = d["results"]
scale_pts = []
for run, r in res.items():
    if "randinit" in run:
        continue
    size = run.split("-")[-1].split("_")[0]      # 1M/10M/30M/100M
    scale_pts.append((size, r["RNS"]["10"], False))
scale_pts.append(("650M", d65["RNS"]["10"], True))
order = ["1M", "10M", "30M", "100M", "650M"]
scale_pts.sort(key=lambda t: order.index(t[0]))

ri_vals = [r["RNS"]["10"] for run, r in res.items() if "randinit" in run]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

ax = axes[0]
xs = list(range(len(scale_pts)))
ys = [t[1] for t in scale_pts]
ax.plot(xs, ys, "o-", color="#1a6faf", lw=2, ms=7, label="trained")
ax.axhspan(min(ri_vals), max(ri_vals), color="#d9534f", alpha=0.15,
           label="randinit band (0.54-0.58)")
ax.axhline(0.5, color="#999", ls=":", lw=1)
ax.set_xticks(xs)
ax.set_xticklabels([t[0] for t in scale_pts])
ax.set_xlabel("model scale (params)")
ax.set_ylabel("RNS@10 (lower = better rep. quality)")
ax.set_title("(a) Scale axis: plateau after 30M\n(representation ≠ downstream F1)")
ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
for x, y in zip(xs, ys):
    ax.annotate(f"{y:.3f}", (x, y), textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=7.5)

ax = axes[1]
keys = list(dt["results"].keys())
nts = [float(k.replace("nt_", "").replace("B", "")) for k in keys]
rns = [dt["results"][k]["RNS"]["10"] for k in keys]
f1 = {0.5: 0.244, 0.7: 0.204, 1.0: 0.2, 1.5: 0.18, 1.9: 0.1731}
ax.plot(nts, rns, "s-", color="#2e8b57", lw=2, ms=6, label="RNS@10 (x0.5)")
ax2 = ax.twinx()
f1x = sorted(f1)
f1y = [f1[x] for x in f1x]
ax2.plot(f1x, f1y, "^--", color="#b8860b", lw=1.8, ms=6,
         label="probe F1 (macro)")
ax.axvline(1.0, color="#2e8b57", ls=":", lw=1)
ax2.axvline(0.5, color="#b8860b", ls=":", lw=1)
ax.set_xlabel("pretraining exposure (B nt, 10M model)")
ax.set_ylabel("RNS@10 (x0.5 scale)", color="#2e8b57")
ax2.set_ylabel("probe F1", color="#b8860b")
ax.set_title("(b) Time axis: RNS peak 1.0B vs F1 peak 0.5B\n(organization degrades later than transfer)")
lines = ax.get_lines() + ax2.get_lines()
ax.legend(lines, [l.get_label() for l in lines], loc="lower left",
          fontsize=8, framealpha=0.9)

fig.suptitle("S14: representation quality (RNS) decouples from downstream "
             "transfer across scale and time (H8)", y=1.02, fontsize=11)
fig.tight_layout()
fig.savefig(OUT + ".png", dpi=200, bbox_inches="tight")
fig.savefig(OUT + ".pdf", bbox_inches="tight")
print("saved", OUT + ".png/.pdf")
print("scale axis:", [(t[0], t[1]) for t in scale_pts])
print("time axis RNS:", list(zip(nts, rns)))
