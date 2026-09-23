"""Preprint main figure 1: layer-band migration across scale.

Reads probe_results.jsonl (official rows: final ckpt + n_train>=4000),
plots per-layer probe F1 vs relative depth, one curve per run, faceted
annotation of best layer. Outputs PNG + PDF in /mnt/cunyuliu/rna-sc/figs.

GPU-free (pure matplotlib on CPU) — this is a plotting script, not
training/eval: no CUDA requirement applies.
"""
from __future__ import annotations

import collections
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUTDIR = "/mnt/cunyuliu/rna-sc/figs"

RUNS = [
    ("RNA-Sc-1M_s17", "1M", "#888888"),
    ("RNA-Sc-10M_s17", "10M", "#1f77b4"),
    ("RNA-Sc-30M_s17", "30M", "#2ca02c"),
    ("RNA-Sc-100M_s17", "100M", "#d62728"),
    ("RNA-Sc-650M_s17", "650M", "#9467bd"),
    ("RNA-Sc-10M_s17_randinit17", "10M-randinit", "#7f7f7f"),
]
SCALE_F1 = {"1M": 0.1650, "10M": 0.1535, "30M": 0.2651, "100M": 0.3394,
            "650M": 0.3632}


def official_layers(run):
    rows = []
    with open(PROBE_OUT) as fh:
        for line in fh:
            r = json.loads(line)
            if r["run"] != run:
                continue
            rows.append(r)
    elig = [r for r in rows if r.get("n_train", 0) >= 4000
            and r.get("ckpt_nt") is not None]
    if not elig:
        return None
    final_nt = max(r["ckpt_nt"] for r in elig)
    by_layer = {r["layer"]: r for r in elig if r["ckpt_nt"] == final_nt}
    if not by_layer or by_layer.keys() != set(range(max(by_layer) + 1)):
        return None
    L = max(by_layer) + 1
    return [(r["layer"] / (L - 1), by_layer[r["layer"]]["f1_macro"])
            for r in range(L)] if False else \
        [(li / (L - 1), by_layer[li]["f1_macro"]) for li in range(L)]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for run, label, color in RUNS:
        pts = official_layers(run)
        if pts is None:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        lw = 2.2 if label in ("1M", "10M", "30M", "100M") else 1.2
        ls = "--" if "randinit" in label or "-s2" in label else "-"
        ax.plot(xs, ys, color=color, lw=lw, ls=ls, label=label, alpha=0.9)
        bx, by = max(pts, key=lambda p: p[1])
        ax.scatter([bx], [by], color=color, marker="*", s=90, zorder=5,
                   edgecolors="black", linewidths=0.4)
    ax.set_xlabel("relative depth (layer / (L-1))")
    ax.set_ylabel("linear-probe macro-F1 (rna_type, family-level split)")
    ax.set_title("Layer-band migration with scale: probe-F1 vs depth")
    ax.axvspan(0, 0.33, color="#f2f2f2", zorder=0)
    ax.axvspan(0.66, 1.0, color="#f7f2f2", zorder=0)
    ax.text(0.16, ax.get_ylim()[1] * 0.97, "early", ha="center",
            va="top", fontsize=8, color="#666")
    ax.text(0.5, ax.get_ylim()[1] * 0.97, "middle", ha="center",
            va="top", fontsize=8, color="#666")
    ax.text(0.83, ax.get_ylim()[1] * 0.97, "late", ha="center",
            va="top", fontsize=8, color="#666")
    ax.legend(fontsize=7, ncol=2, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    png = os.path.join(OUTDIR, "fig1_layer_migration.png")
    fig.savefig(png, dpi=180)
    fig.savefig(os.path.join(OUTDIR, "fig1_layer_migration.pdf"))
    print("saved", png)


if __name__ == "__main__":
    main()
