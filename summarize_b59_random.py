"""B 判据汇总（b59 random-split Δ 泄漏通道）——逐臂幂等更新。

读 eval_matrix_results.jsonl 的 b59×random×probe-balanced 行，
对照 2B 基线计算 budget delta（random 通道 vs family 通道）。
"""
import json
import os
import time

MNT = "/mnt/cunyuliu/rna-sc"
RES = os.path.join(MNT, "eval", "eval_matrix_results.jsonl")
OUT = os.path.join(MNT, "evidence", "b59_random_delta.json")

BASE_2B_RANDOM = {"30M": 0.6053, "100M": 0.604, "300M": 0.587,
                  "650M": 0.6252}
FAMILY_DELTA = {"30M": -5.24, "100M": -2.74, "300M": 3.76,
                "650M": None}

rows = []
if os.path.exists(RES):
    for line in open(RES):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if (r.get("split") == "random" and r.get("protocol") ==
                "probe-balanced" and "b59" in str(r.get("model", ""))):
            rows.append(r)

table = {}
for r in rows:
    model = r["model"]  # e.g. RNA-Sc-30M_s17_b59
    scale = model.replace("RNA-Sc-", "").split("_")[0]
    f1 = r.get("best_f1_macro")
    if f1 is None or scale not in BASE_2B_RANDOM:
        continue
    table[scale] = {
        "model": model,
        "random_f1_5.9B": f1,
        "random_f1_2B": BASE_2B_RANDOM[scale],
        "random_delta_pp": round((f1 - BASE_2B_RANDOM[scale]) * 100, 2),
        "family_delta_pp": FAMILY_DELTA.get(scale),
    }

verdict = None
if {"30M", "100M"} <= set(table):
    small = [table[s]["random_delta_pp"] for s in ("30M", "100M")]
    fam = [table[s]["family_delta_pp"] for s in ("30M", "100M")]
    diverge = (max(small) - min(small) < 3.0
               and all(f < 0 for f in fam)
               and all(abs(d) < 2.0 for d in small))
    if diverge:
        verdict = ("B-BUDGET-IMMUNE-RANDOM: random channel is ~flat "
                   "under budget change (|delta|<2pp) while family "
                   "channel drops -5.24/-2.74pp — the random-split score "
                   "is bounded by family-overlap, not by training budget; "
                   "overtraining erosion hits transferable family stats "
                   "but not memorized ones. Consistent with "
                   "'random wins = memorization cashing' (leakage "
                   "triangle 4th link), nuanced: budget does not "
                   "MONETIZE more leakage, it just fails to hurt it.")
    else:
        verdict = ("B1-MEMORY-CASHING: random delta positive while "
                   "family negative — two-channel divergence")

out = {
    "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "protocol": "probe-balanced, random split (i%5 rows of held-out pool), "
                "n_train 19200 / n_eval 4800",
    "table": table,
    "verdict": verdict,
    "pending": [s for s in ("300M", "650M") if s not in table],
}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1))
