"""T4.1 external-model line figure (section 4.10: corpus > params).

Two panels from existing evidence (no GPU needed, plotting only):
  (a) Param axis, same ncRNA corpus: RiNALMo micro/mega/giga best-layer
      F1 vs params (log-x): 18x params -> +2.6pp (near-flat), with the
      controlled family overlaid for contrast;
  (b) Corpus axis, ~same params: RNA-FM 96M (general transcriptome)
      0.1335 vs RiNALMo micro 36M (ncRNA) 0.2407 -> +11pp corpus effect
      at SMALLER params.

Data: eval/probe_results_ext.jsonl + evidence/ext_full_layers.json.
Output: figs/fig_ext_corpus_vs_params.{png,pdf}
"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "figs", "fig_ext_corpus_vs_params")

ext = {}
with open(os.path.join(MNT, "eval", "probe_results_ext.jsonl")) as fh:
    for line in fh:
        r = json.loads(line)
        ext.setdefault(r["run"], []).append(r)


def best_f1(run):
    rows = [r for r in ext[run]
            if r.get("probe_seed", 17) == 17 and r.get("layer") is not None]
    if not rows:
        return None, None
    b = max(rows, key=lambda r: r["f1_macro"])
    return b["f1_macro"], b["layer"]


rinalmo = {}
for run in ext:
    if "rinalmo" not in run.lower():
        continue
    if "pseed" in run:
        continue
    tag = ("micro" if "micro" in run else
           "mega" if "mega" in run else
           "giga" if "giga" in run else None)
    if tag and tag not in rinalmo:
        f1, L = best_f1(run)
        if f1:
            rinalmo[tag] = (f1, L)

rnafm_f1, rnafm_L = best_f1("RNA-FM-96M")

ctrl = json.load(open(os.path.join(MNT, "evidence",
                                   "s1_final_verdict.json")))["five_scale_table"]
ctrl_pts = [(1e6, ctrl["1M"]["f1_mean"]), (1e7, ctrl["10M"]["f1_mean"]),
            (3e7, ctrl["30M"]["f1_mean"]), (1e8, ctrl["100M"]["f1_mean"])]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

ax = axes[0]
p_x = [36e6, 148e6, 650e6]
p_y = [rinalmo["micro"][0], rinalmo["mega"][0], rinalmo["giga"][0]]
ax.plot([math.log10(x) for x in p_x], p_y, "o-", color="#8e44ad", lw=2,
        ms=8, label="RiNALMo (same ncRNA corpus)")
for x, y, t in zip(p_x, p_y, ["micro 36M", "mega 148M", "giga 650M"]):
    ax.annotate(f"{t}\n{y:.4f}", (math.log10(x), y),
                textcoords="offset points", xytext=(8, -4), fontsize=8)
c_x = [math.log10(x) for x, _ in ctrl_pts]
c_y = [y for _, y in ctrl_pts]
ax.plot(c_x, c_y, "s--", color="#1a6faf", lw=1.8, ms=6, alpha=0.8,
        label="RNA-Sc controlled family (R22)")
ax.set_xlabel("log10(params)")
ax.set_ylabel("best-layer family-split F1 (rna_type)")
ax.set_title("(a) Param axis (same corpus):\n18x params -> +2.6pp (near-flat)")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25)

ax = axes[1]
names = ["RNA-FM 96M\n(general transcriptome)",
         "RiNALMo micro 36M\n(ncRNA corpus)"]
vals = [rnafm_f1, rinalmo["micro"][0]]
bars = ax.bar([0, 1], vals, color=["#b8860b", "#2e8b57"], width=0.5,
              alpha=0.85)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.004, f"{v:.4f}",
            ha="center", fontsize=10)
ax.set_xticks([0, 1])
ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel("best-layer family-split F1")
ax.set_ylim(0, max(vals) * 1.25)
ax.set_title("(b) Corpus axis (~same era, smaller params):\nncRNA corpus +11pp")
ax.grid(alpha=0.25, axis="y")

fig.suptitle("Corpus composition dominates family-level transfer over "
             "parameter count (external-model line, section 4.10)",
             y=1.02, fontsize=11)
fig.tight_layout()
fig.savefig(OUT + ".png", dpi=200, bbox_inches="tight")
fig.savefig(OUT + ".pdf", bbox_inches="tight")
print("saved", OUT + ".png/.pdf")
print("rinalmo:", rinalmo, "rnafm:", (rnafm_f1, rnafm_L))
