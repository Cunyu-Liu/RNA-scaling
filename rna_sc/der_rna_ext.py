"""Red-team E extension: de-rRNA re-analysis for EXTERNAL model probes.

Companion to der_rna.py (which covers the RNA-Sc family). Reads the
external ledger eval/probe_results_ext.jsonl (RNA-FM-96M,
RiNALMo-micro-36M; per_class_f1 rows, v2 reruns with class names),
recomputes macro-F1 excluding rRNA classes per layer, and reports:
  - best layer under de-rRNA F1 vs full F1
  - whether the layer-behavior shape (monotonic decline / mid-late
    single peak) survives rRNA exclusion

Output: evidence/derRNA_external.json

Usage: python -m rna_sc.der_rna_ext
"""
from __future__ import annotations

import json

EXT_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/derRNA_external.json"
RUNS = ("RNA-FM-96M", "RiNALMo-micro-36M", "RiNALMo-rinalmo", "RiNALMo-rinalmo-mega", "RiNALMo-rinalmo-giga")


def macro_f1_excluding(per_class_f1, exclude_prefixes=("rRNA",)):
    vals = [v for k, v in per_class_f1.items()
            if v is not None and not any(
                k.startswith(p) or p in k for p in exclude_prefixes)]
    return (sum(vals) / len(vals)) if vals else None


def layer_shape(f1s):
    """Classify the layer curve shape: monotonic_down / single_peak /
    flat / other."""
    n = len(f1s)
    peak = max(range(n), key=lambda i: f1s[i])
    if peak == 0 and all(f1s[i] >= f1s[i + 1] - 0.005
                         for i in range(n - 1)):
        return "monotonic_down", peak
    if peak == n - 1 and all(f1s[i] <= f1s[i + 1] + 0.005
                             for i in range(n - 1)):
        return "monotonic_up", peak
    if 0 < peak < n - 1:
        return "single_peak", peak
    return "other", peak


def main() -> int:
    rows = []
    with open(EXT_OUT) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("per_class_f1"):
                rows.append(r)

    out = {"note": "de-rRNA external re-analysis (red-team E ext); "
                   "v2 probe rows with per_class_f1",
           "models": {}}
    for run in RUNS:
        rs = sorted([r for r in rows if r["run"] == run],
                    key=lambda r: r["layer"])
        if not rs:
            continue
        L = rs[0]["n_layers"]
        f1_all = [r["f1_macro"] for r in rs]
        f1_der = []
        for r in rs:
            v = macro_f1_excluding(r["per_class_f1"])
            f1_der.append(v if v is not None else float("nan"))
        shape_all, peak_all = layer_shape(f1_all)
        ok = [v for v in f1_der if v == v]
        shape_der, peak_der = (layer_shape(ok) if ok else ("n/a", None))
        best_all = max(f1_all)
        best_der = max(ok) if ok else None
        out["models"][run] = {
            "n_layers": L,
            "f1_all_by_layer": [round(v, 4) for v in f1_all],
            "f1_der_by_layer": [round(v, 4) if v == v else None
                                for v in f1_der],
            "best_f1_all": round(best_all, 4),
            "best_f1_der": round(best_der, 4) if best_der else None,
            "best_layer_all": peak_all,
            "best_layer_der": peak_der,
            "shape_all": shape_all,
            "shape_der": shape_der,
            "shape_survives": shape_all == shape_der,
            "rel_peak_shift": (round((peak_der - peak_all) / (L - 1), 3)
                               if peak_der is not None else None)}
        print("%-18s L=%d all: best=%.4f@L%d %s | der: best=%.4f@L%d %s "
              "| survives=%s" % (
                  run, L, best_all, peak_all, shape_all,
                  best_der if best_der else float("nan"),
                  peak_der if peak_der is not None else -1,
                  shape_der, shape_all == shape_der))

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
