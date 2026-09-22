"""Mega->giga fine-grained comparison (user challenge 2026-09-22).

Quartile bands may dilute the mega->giga trend. This computes:
  1. seed-averaged per-layer curves (s17+s29 mean)
  2. layer-ALIGNED diff on common L0-29 (absolute layer index)
  3. plateau stats: top-10 layer mean, last-12 mean, layer counts
     above thresholds (0.20/0.23/0.24/0.25)
  4. best-layer gain vs plateau gain vs layer-aligned mean gain

Output: evidence/mega_giga_aligned.json
Usage: python -m rna_sc.mega_giga_aligned
"""
from __future__ import annotations

import json

EXT_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/mega_giga_aligned.json"
PAIRS = {"mega": ("RiNALMo-rinalmo-mega", "RiNALMo-rinalmo-mega_pseed29"),
         "giga": ("RiNALMo-rinalmo-giga", "RiNALMo-rinalmo-giga_pseed29")}
THRESHOLDS = (0.20, 0.23, 0.24, 0.25)


def curve(run):
    rows = [json.loads(l) for l in open(EXT_OUT)]
    rs = sorted([r for r in rows if r["run"] == run],
                key=lambda r: r["layer"])
    return [r["f1_macro"] for r in rs]


def seed_mean(pair):
    a, b = curve(pair[0]), curve(pair[1])
    assert len(a) == len(b)
    return [(x + y) / 2 for x, y in zip(a, b)]


def stats(f1s):
    top10 = sorted(f1s, reverse=True)[:10]
    return {
        "n_layers": len(f1s),
        "best": max(f1s),
        "top10_mean": round(sum(top10) / 10, 4),
        "last12_mean": round(sum(f1s[-12:]) / 12, 4),
        "count_ge": {str(t): sum(1 for f in f1s if f >= t)
                     for t in THRESHOLDS}}


def main() -> int:
    m = seed_mean(PAIRS["mega"])
    g = seed_mean(PAIRS["giga"])
    n_common = min(len(m), len(g))
    diffs = [round(g[i] - m[i], 4) for i in range(n_common)]
    pos = sum(1 for d in diffs if d > 0)
    max_d, max_i = max((d, i) for i, d in enumerate(diffs))

    out = {
        "note": "layer-ALIGNED (absolute index) seed-averaged "
                "mega vs giga; plus plateau stats",
        "mega_seed_mean_curve": [round(v, 4) for v in m],
        "giga_seed_mean_curve": [round(v, 4) for v in g],
        "layer_aligned_diff_L0_29": diffs,
        "layer_aligned": {
            "n_layers_compared": n_common,
            "giga_higher_at": "%d/%d" % (pos, n_common),
            "mean_diff": round(sum(diffs) / n_common, 4),
            "max_diff": {"layer": max_i, "diff": max_d},
            "mid_band_L4_9_mean_diff": round(
                sum(diffs[4:10]) / 6, 4),
            "deep_L23_29_mean_diff": round(
                sum(diffs[23:30]) / 7, 4)},
        "mega_stats": stats(m),
        "giga_stats": stats(g),
        "gains_4_4x_params": {
            "best_layer": round(max(g) - max(m), 4),
            "top10_mean": round(
                stats(g)["top10_mean"] - stats(m)["top10_mean"], 4),
            "last12_mean": round(
                stats(g)["last12_mean"] - stats(m)["last12_mean"], 4),
            "layer_aligned_mean": round(sum(diffs) / n_common, 4)}}

    print("layer-aligned (L0-29, seed-avg): giga higher at %d/%d "
          "layers, mean diff %+.4f, max %+.4f@L%d"
          % (pos, n_common, out["layer_aligned"]["mean_diff"],
             max_d, max_i))
    print("mid band (L4-9): %+.4f | deep (L23-29): %+.4f"
          % (out["layer_aligned"]["mid_band_L4_9_mean_diff"],
             out["layer_aligned"]["deep_L23_29_mean_diff"]))
    print("gains (4.4x params): best %+.4f | top10 %+.4f | "
          "last12 %+.4f | aligned-mean %+.4f"
          % tuple(out["gains_4_4x_params"].values()))
    print("layers>=0.24: mega %d/30 vs giga %d/33"
          % (out["mega_stats"]["count_ge"]["0.24"],
             out["giga_stats"]["count_ge"]["0.24"]))

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
