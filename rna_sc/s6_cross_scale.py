"""T2.2.3 cross-scale S6 comparison: 1M/10M/30M/100M emergence timelines.

Combines _ck timeline rows (20k/4k family split, day-1 pooled probe) into
one figure: best-layer F1 vs pretraining nt, per scale, plus best-layer
rel_depth trajectories. Evidence table to evidence/s6_cross_scale.json.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EVAL = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s6_cross_scale.json"
FIG = "/mnt/cunyuliu/rna-sc/figs/fig_s6_cross_scale"

PREFIXES = {
    "1M": ("RNA-Sc-1M_s17", 18),
    "10M": ("RNA-Sc-10M_s17", 20),
    "30M": ("RNA-Sc-30M_s17", 12),
    "100M": ("RNA-Sc-100M_s17", 23),
}
COLORS = {"1M": "#937860", "10M": "#DD8452", "30M": "#4C72B0",
          "100M": "#55A868"}


def main() -> int:
    data = {s: defaultdict(dict) for s in PREFIXES}
    for line in open(EVAL):
        d = json.loads(line)
        if d.get("n_train", 0) < 20000:
            continue
        for s, (base, L) in PREFIXES.items():
            r = d["run"]
            if (r == base or r.startswith(base + "_ck")) \
                    and d.get("n_layers") == L and d.get("ckpt_nt"):
                data[s][d["ckpt_nt"]][d["layer"]] = d["f1_macro"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3))
    res = {}
    for s, (base, L) in PREFIXES.items():
        pts = []
        for nt in sorted(data[s]):
            rows = data[s][nt]
            if len(rows) < L // 2:
                continue
            best = max(rows, key=rows.get)
            pts.append((nt / 1e9, best / (L - 1), rows[best]))
        res[s] = [{"nt_B": round(a, 3), "best_rel": round(b, 3),
                   "best_f1": round(c, 4)} for a, b, c in pts]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        axes[0].plot(xs, [p[2] for p in pts], marker="o", ms=4,
                     color=COLORS[s], label="%s (n=%d)" % (s, len(pts)))
        axes[1].plot(xs, [p[1] for p in pts], marker="o", ms=4,
                     color=COLORS[s], label=s)
    axes[0].set_xlabel("pretraining nt (B)")
    axes[0].set_ylabel("best-layer macro-F1")
    axes[0].set_title("S6 cross-scale: F1 vs pretraining time")
    axes[0].legend()
    axes[1].set_xlabel("pretraining nt (B)")
    axes[1].set_ylabel("best-layer rel_depth")
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].set_title("best-layer migration (dashed=attrition direction)")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIG + ".png", dpi=180)
    fig.savefig(FIG + ".pdf")
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2)
    for s, pts in res.items():
        print(s, ":", pts[0] if pts else None, "->", pts[-1] if pts else None)
    print("saved", FIG + ".png/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
