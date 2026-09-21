"""Red-team fix E (mandatory): de-rRNA stratified re-analysis.

Reviewer E: "rRNA is 56% of the corpus — are all your emergence
conclusions just 'rRNA regularity' in another guise?"

v1 (this module): re-aggregate EXISTING probe rows with rRNA class
EXCLUDED — per_class_f1 is in every jsonl row, so macro-F1 over the
non-rRNA classes is recomputable without re-running probes. If the
scale trend / 10M valley / layer migration survive de-rRNA, the
conclusions are corpus-robust.

Outputs: evidence/derRNA_stratified.json with per-model comparisons
(rRNA-in vs rRNA-out macro-F1, best layer, layer-migration direction).

Usage: python -m rna_sc.der_rna
"""
from __future__ import annotations

import collections
import json

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/derRNA_stratified.json"
FAMILY_RUNS = {
    "1M": ["RNA-Sc-1M_s17", "RNA-Sc-1M_s29", "RNA-Sc-1M_s43"],
    "10M": ["RNA-Sc-10M_s17", "RNA-Sc-10M_s29", "RNA-Sc-10M_s43"],
    "30M": ["RNA-Sc-30M_s17", "RNA-Sc-30M_s29", "RNA-Sc-30M_s43"],
    "100M": ["RNA-Sc-100M_s17", "RNA-Sc-100M_s29", "RNA-Sc-100M_s43"],
}


def official_rows(run):
    rows = []
    with open(PROBE_OUT) as fh:
        for line in fh:
            r = json.loads(line)
            if r["run"] != run:
                continue
            if r.get("n_train", 0) < 4000 or r.get("ckpt_nt") is None:
                continue
            rows.append(r)
    if not rows:
        return []
    final_nt = max(r["ckpt_nt"] for r in rows)
    best = {r["layer"]: r for r in rows if r["ckpt_nt"] == final_nt}
    return sorted(best.values(), key=lambda r: r["layer"])


def macro_f1_excluding(per_class_f1, exclude_prefixes=("rRNA",)):
    vals = [v for k, v in per_class_f1.items()
            if v is not None and not any(
                k.startswith(p) or p in k for p in exclude_prefixes)]
    return (sum(vals) / len(vals)) if vals else None


def main() -> int:
    out = {"note": "de-rRNA stratified re-analysis (red-team E); "
                   "recomputed from per_class_f1 in existing jsonl",
           "scales": {}}
    print("%-6s %-28s %-9s %-9s %-7s %-9s %-9s %-7s" % (
        "scale", "run", "F1(all)", "F1(-rRNA)", "bestL", "F1b(-rRNA)",
        "bL(-rRNA)", "n_cls"))
    for scale, runs in FAMILY_RUNS.items():
        per_run = []
        for run in runs:
            rows = official_rows(run)
            if not rows:
                continue
            best_all = max(rows, key=lambda r: r["f1_macro"])
            # best layer by DE-RRNA macro-F1
            best_der = None
            for r in rows:
                pf = r.get("per_class_f1") or {}
                f1x = macro_f1_excluding(pf)
                if f1x is None:
                    continue
                r2 = {"layer": r["layer"], "f1_der": round(f1x, 4)}
                if best_der is None or f1x > best_der["f1_der"]:
                    best_der = r2
            ncls = len(best_all.get("per_class_f1") or {})
            per_run.append({
                "run": run,
                "f1_all": best_all["f1_macro"],
                "best_layer_all": best_all["layer"],
                "best_rel_all": round(best_all["layer"] /
                                      max(1, len(rows) - 1), 3),
                "f1_der": best_der["f1_der"] if best_der else None,
                "best_layer_der": (best_der["layer"] if best_der
                                   else None),
                "best_rel_der": (round(best_der["layer"] /
                                       max(1, len(rows) - 1), 3)
                                 if best_der else None),
                "n_classes": ncls})
            print("%-6s %-28s %-9.4f %-9s %-7d %-9s %-9s %-7d" % (
                scale, run, best_all["f1_macro"],
                best_der["f1_der"] if best_der else "-",
                best_all["layer"],
                best_der["f1_der"] if best_der else "-",
                best_der["layer"] if best_der else "-", ncls))
        if per_run:
            f1s_all = [p["f1_all"] for p in per_run]
            f1s_der = [p["f1_der"] for p in per_run if p["f1_der"]]
            rels_der = [p["best_rel_der"] for p in per_run
                        if p["best_rel_der"] is not None]
            out["scales"][scale] = {
                "n_runs": len(per_run),
                "f1_all_mean": round(sum(f1s_all) / len(f1s_all), 4),
                "f1_der_mean": (round(sum(f1s_der) / len(f1s_der), 4)
                                if f1s_der else None),
                "best_rel_der_mean": (round(sum(rels_der) / len(rels_der), 3)
                                      if rels_der else None),
                "runs": per_run}

    # verdict checks
    sc = out["scales"]
    checks = {}
    if all(k in sc for k in ("1M", "10M", "30M", "100M")):
        f1_der = [sc[k]["f1_der_mean"] for k in
                  ("1M", "10M", "30M", "100M")]
        checks["scale_trend_survives"] = bool(
            f1_der[2] > f1_der[1] and f1_der[3] > f1_der[2])
        checks["10M_valley_survives"] = bool(f1_der[1] < f1_der[0])
        rels = [sc[k]["best_rel_der_mean"] for k in
                ("1M", "10M", "30M", "100M")]
        checks["layer_migration_direction"] = {
            "1M": rels[0], "10M": rels[1], "30M": rels[2],
            "100M": rels[3],
            "30M_deeper_than_1M": bool(rels[2] > rels[0]),
            "100M_deepest": bool(rels[3] >= max(rels[:3]))}
    out["verdict_checks"] = checks
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    print(json.dumps(checks, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
