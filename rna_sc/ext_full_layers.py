"""External-line full-layer summary table (user request 2026-09-22).

Every run in probe_results_ext.jsonl already stores the FULL layer
curve; this aggregates them into a per-model layer matrix (rel-depth
banded) + saves evidence/s?_ext_full_layers.json + a printable table.

Usage: python -m rna_sc.ext_full_layers
"""
from __future__ import annotations

import json

EXT_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/ext_full_layers.json"

DISPLAY = {
    "RNA-FM-96M": "RNA-FM-96M s17",
    "RNA-FM-96M_pseed29": "RNA-FM-96M s29",
    "RiNALMo-rinalmo": "RiNALMo-micro s17",
    "RiNALMo-rinalmo_pseed29": "RiNALMo-micro s29",
    "RiNALMo-rinalmo-mega": "RiNALMo-mega s17",
    "RiNALMo-rinalmo-mega_pseed29": "RiNALMo-mega s29",
    "RiNALMo-rinalmo-giga": "RiNALMo-giga s17",
    "RiNALMo-rinalmo-giga_pseed29": "RiNALMo-giga s29",
    "RiNALMo-micro-36M": "RiNALMo-micro v1(=s17)",
}

BAND_EDGES = (0.25, 0.5, 0.75)


def band_means(f1s, L):
    bands = {"early(0-25%)": [], "mid(25-50%)": [],
             "late(50-75%)": [], "top(75-100%)": []}
    for i, f in enumerate(f1s):
        rel = i / (L - 1)
        if rel < BAND_EDGES[0]:
            bands["early(0-25%)"].append(f)
        elif rel < BAND_EDGES[1]:
            bands["mid(25-50%)"].append(f)
        elif rel < BAND_EDGES[2]:
            bands["late(50-75%)"].append(f)
        else:
            bands["top(75-100%)"].append(f)
    return {k: round(sum(v) / len(v), 4) if v else None
            for k, v in bands.items()}


def main() -> int:
    rows = [json.loads(l) for l in open(EXT_OUT)]
    out = {"note": "full per-layer F1 for every external run; "
                   "rel-depth bands are within-model normalized",
           "models": {}}
    print("%-24s %5s %6s | %-7s %-7s %-7s %-7s | full curve" % (
        "model", "L", "best", "early", "mid", "late", "top"))
    for run, disp in DISPLAY.items():
        rs = sorted([r for r in rows if r["run"] == run],
                    key=lambda r: r["layer"])
        if not rs:
            continue
        f1s = [r["f1_macro"] for r in rs]
        L = rs[0]["n_layers"]
        best_i = max(range(len(f1s)), key=lambda i: f1s[i])
        bands = band_means(f1s, L)
        out["models"][disp] = {
            "n_layers": L, "best_layer": best_i,
            "best_f1": f1s[best_i],
            "best_rel": round(best_i / (L - 1), 3),
            "layer_f1": f1s,
            "band_means": bands,
            "monotonic_prefix_max": max(f1s[:3]) if L >= 3 else None,
            "final_layer_f1": f1s[-1]}
        print("%-24s %5d %3d/%.3f | %.4f  %.4f  %.4f  %.4f | %s" % (
            disp, L, best_i, f1s[best_i],
            bands["early(0-25%)"], bands["mid(25-50%)"],
            bands["late(50-75%)"], bands["top(75-100%)"],
            " ".join("%.2f" % f for f in f1s)))

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
