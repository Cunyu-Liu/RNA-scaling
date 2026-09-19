"""T0.2.6 Fig: DELTA(random-family) vs model scale, per protocol.

Preprint Fig 3 candidate: two panels sharing the scale axis.
  Left : family-split vs random-split F1 per scale (paired lines) —
         the divergence grows with scale.
  Right: DELTA (random - family) per scale, both protocols —
         balanced rises monotonically (+0.055 -> +0.434); meanpool stays
         ~0 or negative at small scale.

Data: evidence/eval_matrix_v1_delta.json (produced by eval_matrix v1).
Output: figs/fig_eval_matrix_delta.{png,pdf}
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IN_JSON = "/mnt/cunyuliu/rna-sc/evidence/eval_matrix_v1_delta.json"
FIG = "/mnt/cunyuliu/rna-sc/figs/fig_eval_matrix_delta"

SCALES = ["1M", "10M", "30M", "100M"]
X = [1, 10, 30, 100]
MODELS = {"1M": "RNA-Sc-1M_s17", "10M": "RNA-Sc-10M_s17",
          "30M": "RNA-Sc-30M_s17", "100M": "RNA-Sc-100M_s17"}
PROTOS = [("probe-balanced", "#C44E52", "o", "probe (class-balanced)"),
          ("probe-meanpool", "#4C72B0", "s", "probe (day-1 mean-pool)")]


def main() -> int:
    d = json.load(open(IN_JSON))["deltas"]
    fam = {p: [] for p, *_ in PROTOS}
    ran = {p: [] for p, *_ in PROTOS}
    delta = {p: [] for p, *_ in PROTOS}
    for s in SCALES:
        for p, *_ in PROTOS:
            cell = d["%s|%s" % (MODELS[s], p)]
            fam[p].append(cell["family"])
            ran[p].append(cell["random"])
            delta[p].append(cell["delta"])

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(9.2, 3.6), sharex=True)
    for p, c, mk, lbl in PROTOS:
        ax1.plot(X, fam[p], color=c, marker=mk, ls="--", label=None)
        ax1.plot(X, ran[p], color=c, marker=mk, ls="-",
                 label="%s | random split" % lbl)
        ax1.plot(X, fam[p], color=c, marker=mk, ls="--",
                 label="%s | family split" % lbl, alpha=0.75)
    ax1.set_xscale("log")
    ax1.set_xticks(X)
    ax1.set_xticklabels(SCALES)
    ax1.set_xlabel("parameters (M)")
    ax1.set_ylabel("macro-F1 (rna_type)")
    ax1.set_title("family split vs random split")
    ax1.legend(fontsize=7, loc="upper left", framealpha=0.9)
    ax1.grid(alpha=0.3)

    for p, c, mk, lbl in PROTOS:
        ax2.plot(X, delta[p], color=c, marker=mk, label=lbl)
    ax2.axhline(0.0, color="gray", lw=0.8, ls=":")
    ax2.set_xscale("log")
    ax2.set_xticks(X)
    ax2.set_xticklabels(SCALES)
    ax2.set_xlabel("parameters (M)")
    ax2.set_ylabel("DELTA = random - family (macro-F1)")
    ax2.set_title("protocol sensitivity grows with scale")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.suptitle(
        "Random-split gains over family-split scale monotonically with "
        "model size (controlled RNA-Sc family, 2.0B nt each)",
        fontsize=9, y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig("%s.%s" % (FIG, ext), dpi=200, bbox_inches="tight")
    print("saved", FIG + ".{png,pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
