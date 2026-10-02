"""T3.5.8: RNS bootstrap variance (10x random-pool regeneration).

Q19-Q1 gap: paper uses 100 subsampled averages; we used a single full
pool. This regenerates the matched random pool 10 times (different
seeds) and reports per-scale RNS mean +/- std.

Output: evidence/s14_rns_bootstrap.json
"""
from __future__ import annotations

import argparse
import json
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc.s14_rns_ext import stream_real, rns_from_emb, ours_embedder

OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_rns_bootstrap.json"
RUNS = ["RNA-Sc-1M_s17", "RNA-Sc-30M_s17", "RNA-Sc-100M_s17"]
N_REAL = 1000
N_BOOT = 10


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    from rna_sc.s14_rns import make_random_pool
    real = stream_real(N_REAL)
    results = {}
    for run in RUNS:
        fn = ours_embedder(run, dev)
        re = fn(real)
        vals = []
        for b in range(N_BOOT):
            rand, _, _ = make_random_pool(real, 3, seed=100 + b)
            ae = fn(rand)
            vals.append(rns_from_emb(re, ae))
            del ae
        v = np.array(vals)
        results[run] = {"mean": round(float(v.mean()), 4),
                        "std": round(float(v.std()), 4),
                        "values": [round(float(x), 4) for x in v]}
        print(run, results[run], flush=True)
        del re, fn
        torch.cuda.empty_cache()
    json.dump({"n_boot": N_BOOT, "n_real": N_REAL, "results": results,
               "note": "10x random-pool regeneration; paper protocol = "
                       "100 subsamples. std vs scale-gap comparison in "
                       "interpretation"},
              open(OUT, "w"), indent=1)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
