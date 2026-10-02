"""3x2 factorial verdict: 2B vs 5.9B budget effect + Claim-14 test.

Reads probe_results.jsonl for the 2B main arms and the b59 5.9B arms
across 30M/100M/300M/650M, builds:
  - per-scale budget delta (F1_b59 - F1_2B)
  - Claim-14 test at 300M: is the 5.9B gain insignificant?
  - budget-effect vs parameter-effect decomposition (2x2 sub-matrices)

Writes evidence/factorial_verdict.json.
"""
from __future__ import annotations

import argparse
import json
import os

MNT = "/mnt/cunyuliu/rna-sc"
PROBE = os.path.join(MNT, "eval", "probe_results.jsonl")
OUT = os.path.join(MNT, "evidence", "factorial_verdict.json")

SCALES = ["30M", "100M", "300M", "650M"]


def best_f1(run: str) -> dict | None:
    rows = []
    with open(PROBE) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("run") == run:
                rows.append(r)
    elig = [r for r in rows if r.get("n_train", 0) >= 4000
            and r.get("ckpt_nt") is not None]
    if not elig:
        return None
    final_nt = max(r["ckpt_nt"] for r in elig)
    final_rows = [r for r in elig if r["ckpt_nt"] == final_nt]
    best = max(final_rows, key=lambda r: r.get("f1_macro", 0.0))
    return {"f1": best["f1_macro"], "layer": best["layer"],
            "rel": best.get("rel_depth"), "ckpt_nt": final_nt}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()

    table = {}
    for s in SCALES:
        r2 = best_f1("RNA-Sc-%s_s17" % s)
        r59 = best_f1("RNA-Sc-%s_s17_b59" % s)
        entry = {"f1_2B": r2, "f1_5.9B": r59}
        if r2 and r59:
            entry["budget_delta_pp"] = round(
                (r59["f1"] - r2["f1"]) * 100, 2)
        table[s] = entry

    c14 = None
    t300 = table.get("300M")
    if t300 and "budget_delta_pp" in t300:
        # Claim-14: boundary holds if 5.9B gain is NOT significant.
        # pre-registered significance bar: >= +1.0 pp on F1 (family probe,
        # inc12 protocol; seed noise on 100M is +-1.5pp so 1.0pp is a
        # conservative single-seed bar)
        c14 = {"delta_pp": t300["budget_delta_pp"],
               "bar_pp": 1.0,
               "boundary_holds": t300["budget_delta_pp"] < 1.0}

    budget_effect = None
    e100, e650 = table.get("100M"), table.get("650M")
    if e100 and e650 and all("budget_delta_pp" in x for x in (e100, e650)):
        budget_effect = {
            "budget_delta_100M_pp": e100["budget_delta_pp"],
            "budget_delta_650M_pp": e650["budget_delta_pp"],
            "interaction_note": "budget x scale interaction from the "
            "100M/650M rows (3x2 minus 300M anchor col)"}

    out = {"generated": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ"),
           "protocol": "inc12 final-ckpt probe, family split, best layer",
           "table": table, "claim14_300M": c14,
           "budget_effect": budget_effect,
           "notes": "rw1 val_loss in manifests is 0.0 by design (train_s3_rw "
                    "validates on the original pool); use probe F1 only."}
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
