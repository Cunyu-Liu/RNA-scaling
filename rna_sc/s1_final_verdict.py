"""Five-scale final verdict (T2.1.3 closeout, post-650M).

Runs AFTER watch_all auto-probes the 650M final ckpt:
  1. five-scale table (1M/10M/30M/100M/650M, s17 primary; 3-seed for
     1M-100M), best-layer F1 + rel depth
  2. slope re-estimate (30M->100M->650M chain, 650M single seed s17)
  3. verdict vs pre-registered rules: superlinear continuation held?
     attrition valley depth at 650M? layer-migration endpoint?
  4. writes evidence/s1_final_verdict.json

Usage: python -m rna_sc.s1_final_verdict
"""
from __future__ import annotations

import collections
import json
import math
import random

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s1_final_verdict.json"
N_BOOT = 2000
EPS = 0.03

FAMILY = {
    "1M": ["RNA-Sc-1M_s17", "RNA-Sc-1M_s29", "RNA-Sc-1M_s43"],
    "10M": ["RNA-Sc-10M_s17", "RNA-Sc-10M_s29", "RNA-Sc-10M_s43"],
    "30M": ["RNA-Sc-30M_s17", "RNA-Sc-30M_s29", "RNA-Sc-30M_s43"],
    "100M": ["RNA-Sc-100M_s17", "RNA-Sc-100M_s29", "RNA-Sc-100M_s43"],
    "650M": ["RNA-Sc-650M_s17"],
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


def best_row(rows):
    if not rows:
        return None
    return max(rows, key=lambda r: r["f1_macro"])


def slope(f1s, params):
    pairs = [(math.log10(p), f) for p, f in zip(params, f1s)
             if f is not None]
    if len(pairs) < 2:
        return None
    n = len(pairs)
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx if sxx else None


def main() -> int:
    out = {"five_scale_table": {}, "checks": {}}
    table = {}
    for scale, runs in FAMILY.items():
        per_run = []
        for run in runs:
            rows = official_rows(run)
            b = best_row(rows)
            if b is None:
                continue
            per_run.append({
                "run": run,
                "f1": b["f1_macro"],
                "best_layer": b["layer"],
                "n_layers": b["n_layers"],
                "rel": round(b["layer"] / max(1, b["n_layers"] - 1), 3)})
        if not per_run:
            out["five_scale_table"][scale] = {"status": "PENDING"}
            continue
        f1s = [p["f1"] for p in per_run]
        table[scale] = {
            "runs": per_run,
            "f1_mean": round(sum(f1s) / len(f1s), 4),
            "f1_std": (round(
                (sum((f - sum(f1s) / len(f1s)) ** 2
                     for f in f1s) / len(f1s)) ** 0.5, 4)
                if len(f1s) > 1 else 0.0),
            "n_seeds": len(f1s),
            "rel_mean": round(sum(p["rel"] for p in per_run) / len(per_run), 3)}
        print("%-5s n_seed=%d f1=%.4f+-%.4f rel=%.3f" % (
            scale, len(f1s), table[scale]["f1_mean"],
            table[scale]["f1_std"], table[scale]["rel_mean"]))
    out["five_scale_table"] = table

    m = table.get
    checks = {}
    if all(k in table for k in ("1M", "10M", "30M", "100M", "650M")):
        f65 = table["650M"]["f1_mean"]
        checks["650M_above_100M"] = bool(
            f65 > table["100M"]["f1_mean"])
        checks["650M_gain_pp"] = round(
            (f65 - table["100M"]["f1_mean"]) * 100, 1)
        params = [1e6, 1e7, 3e7, 1e8, 6.5e8]
        means = [table[k]["f1_mean"] for k in
                 ("1M", "10M", "30M", "100M", "650M")]
        checks["full_slope_f1_per_decade"] = round(
            slope(means, params), 4)
        checks["slope_100M_650M"] = round(
            slope([means[3], means[4]], [params[3], params[4]]), 4)
        checks["slope_above_eps"] = bool(
            checks["slope_100M_650M"] > EPS)
        checks["10M_valley_at_650M_era"] = bool(
            table["10M"]["f1_mean"] < table["1M"]["f1_mean"])
        checks["layer_migration_endpoint"] = {
            "1M": table["1M"]["rel_mean"],
            "10M": table["10M"]["rel_mean"],
            "30M": table["30M"]["rel_mean"],
            "100M": table["100M"]["rel_mean"],
            "650M": table["650M"]["rel_mean"],
            "monotone_deepening": bool(
                table["30M"]["rel_mean"] > table["1M"]["rel_mean"] and
                table["650M"]["rel_mean"] >= table["100M"]["rel_mean"])}
    out["checks"] = checks
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    print(json.dumps(checks, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
