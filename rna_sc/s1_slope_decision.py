"""T2.1.3 slope decision at the 100M point (R1 pre-registered rule).

Question: does probe F1 keep improving from 30M -> 100M strongly enough
to justify a 650M run? Rule (pre-registered in SPEC/TASKS):
  slope = (F1_100M - F1_30M) / (log10(100) - log10(30))   [F1 per decade]
  CI    = bootstrap 95% over seeds
  slope > eps (eps=0.03 F1/decade) -> launch 650M
  slope <= eps                                    -> stop at 100M

Reads only official probes (final ckpt + 20k) from probe_results.jsonl.
Usage: python -m rna_sc.s1_slope_decision
Output: evidence/s1_slope_decision.json + console report
"""
from __future__ import annotations

import collections
import json
import math
import random

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s1_slope_decision.json"
EPS = 0.03          # F1 points per decade (pre-registered)
N_BOOT = 2000

FAMILY = {
    "30M": ["RNA-Sc-30M_s17", "RNA-Sc-30M_s29", "RNA-Sc-30M_s43"],
    "100M": ["RNA-Sc-100M_s17", "RNA-Sc-100M_s29", "RNA-Sc-100M_s43"],
}


def official_best_f1(run):
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
    fin = [r for r in elig if r["ckpt_nt"] == final_nt]
    if not fin:
        return None
    return max(r["f1_macro"] for r in fin)


def main():
    rng = random.Random(17)
    vals = {}
    for fam, runs in FAMILY.items():
        f1s = [official_best_f1(r) for r in runs]
        f1s = [x for x in f1s if x is not None]
        vals[fam] = f1s
        print("%s: n=%d F1=%s" % (fam, len(f1s),
                                  ["%.4f" % x for x in f1s]))
    if not vals["30M"] or not vals["100M"]:
        print("INSUFFICIENT DATA — need both 30M and 100M official probes")
        return

    d_dec = math.log10(100) - math.log10(30)
    obs = (sum(vals["100M"]) / len(vals["100M"]) -
           sum(vals["30M"]) / len(vals["30M"])) / d_dec

    boots = []
    for _ in range(N_BOOT):
        b30 = [rng.choice(vals["30M"]) for _ in vals["30M"]]
        b100 = [rng.choice(vals["100M"]) for _ in vals["100M"]]
        boots.append((sum(b100) / len(b100) - sum(b30) / len(b30)) / d_dec)
    boots.sort()
    lo = boots[int(0.025 * N_BOOT)]
    hi = boots[int(0.975 * N_BOOT)]

    decision = "650M" if lo > EPS else ("stop" if hi < EPS else "ambiguous")
    report = {
        "rule": "slope=(F1_100M-F1_30M)/log10-decade; eps=%.3f" % EPS,
        "f1_30M_seeds": vals["30M"],
        "f1_100M_seeds": vals["100M"],
        "slope_per_decade": round(obs, 4),
        "bootstrap_ci95": [round(lo, 4), round(hi, 4)],
        "decision": decision,
        "note": "ambiguous means CI straddles eps — decide by budget/"
                "timeline (preprint priority favors stop-and-write)",
    }
    with open(OUT, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
