"""T2.2.3 S6 emergence timeline analysis (pretraining-time axis).

Reads probe rows for RNA-Sc-10M_s17_ck* (19 ckpts, 100M..1900M nt)
plus the final-ckpt rows (RNA-Sc-10M_s17) and produces:
  - evidence/s6_timeline.json: per-ckpt best F1, best layer, band means
  - figs/fig_s6_emergence.png/pdf: F1-vs-nt curves per band + best layer

Emergence definitions (pre-registered):
  - F1 emergence point: first ckpt where best-layer F1 >= 50% of final
  - layer-migration point: first ckpt where argmax layer rel_depth
    leaves the early band (rel > 0.33)
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EVAL_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/s6_timeline.json"
FIG_DIR = "/mnt/cunyuliu/rna-sc/figs"


def main() -> int:
    by_ck = defaultdict(dict)     # ckpt_nt -> layer -> f1
    final = {}                    # final run rows: layer -> f1
    for line in open(EVAL_OUT):
        d = json.loads(line)
        r = d["run"]
        if d.get("n_train", 0) < 20000:
            continue
        if r.startswith("RNA-Sc-10M_s17_ck") and d.get("n_layers") == 20:
            by_ck[d["ckpt_nt"]][d["layer"]] = d["f1_macro"]
        elif r == "RNA-Sc-10M_s17" and d.get("n_layers") == 20 \
                and d.get("ckpt_nt", 0) >= 1_900_000_000:
            final[d["layer"]] = d["f1_macro"]
            fnt = d.get("ckpt_nt") or 0
            by_ck.setdefault(fnt, {})
            by_ck[fnt].update({d["layer"]: d["f1_macro"]})

    cks = sorted(by_ck)
    if not cks:
        print("no S6 rows yet")
        return 1
    L = 20
    timeline = []
    for nt in cks:
        rows = by_ck[nt]
        if not rows:
            continue
        best_l = max(rows, key=rows.get)
        bands = {"early": [], "middle": [], "late": []}
        for li, f in rows.items():
            r = li / (L - 1)
            bands["early" if r <= 0.33 else
                  ("middle" if r <= 0.66 else "late")].append(f)
        timeline.append({
            "ckpt_nt": nt,
            "best_layer": best_l,
            "best_rel_depth": round(best_l / (L - 1), 3),
            "best_f1": round(rows[best_l], 4),
            "band_early": round(sum(bands["early"]) /
                                max(1, len(bands["early"])), 4),
            "band_middle": round(sum(bands["middle"]) /
                                 max(1, len(bands["middle"])), 4),
            "band_late": round(sum(bands["late"]) /
                               max(1, len(bands["late"])), 4),
        })

    final_f1 = timeline[-1]["best_f1"]
    final_rel = timeline[-1]["best_rel_depth"]
    f1_emerg = next((t["ckpt_nt"] for t in timeline
                     if t["best_f1"] >= 0.5 * final_f1), None)
    mig_emerg = next((t["ckpt_nt"] for t in timeline
                      if t["best_rel_depth"] > 0.33), None)

    res = {"model": "RNA-Sc-10M_s17", "n_ckpts": len(timeline),
           "final_best_f1": final_f1,
           "final_best_rel_depth": final_rel,
           "f1_emergence_nt": f1_emerg,
           "layer_migration_nt": mig_emerg,
           "timeline": timeline}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(res, fh, indent=2)
    print("F1 emergence:", f1_emerg, "layer migration:", mig_emerg,
          "final:", final_f1, "rel:", final_rel)

    nt = [t["ckpt_nt"] / 1e9 for t in timeline]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    for band, color in [("early", "#4C72B0"), ("middle", "#DD8452"),
                        ("late", "#55A868")]:
        ax.plot(nt, [t["band_" + band] for t in timeline],
                marker="o", ms=3, color=color, label=band)
    ax.set_xlabel("pretraining nt (B)")
    ax.set_ylabel("band mean macro-F1")
    ax.legend()
    ax.set_title("S6 emergence: 10M, band F1 vs pretraining")
    ax = axes[1]
    ax.plot(nt, [t["best_f1"] for t in timeline], marker="*",
            color="#C44E52", label="best layer F1")
    ax.set_xlabel("pretraining nt (B)")
    ax.set_ylabel("best-layer macro-F1")
    ax2 = ax.twinx()
    ax2.plot(nt, [t["best_rel_depth"] for t in timeline], marker=".",
             color="#8172B3", label="best layer rel_depth")
    ax2.set_ylabel("best layer rel_depth")
    ax.set_title("best-layer migration over pretraining")
    fig.tight_layout()
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, "fig_s6_emergence.png"), dpi=180)
    fig.savefig(os.path.join(FIG_DIR, "fig_s6_emergence.pdf"))
    print("saved figs/fig_s6_emergence.png/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
