"""S14 v2 time axis: RNS across TRAINING TIME for 10M (attrition model).

The 10M probe F1 peaks at ~0.5B nt then attrits to 0.17 by 2.0B.
Question: does representation quality (RNS) also attrit, or does it
keep improving — i.e. is the attrition purely a downstream-head
phenomenon (decoupling at the time axis)?

Uses 10M_s17 mid ckpts: ~0.5B (peak), ~1.0B, ~1.5B, final 2.0B.
Same embed/rns_k machinery as s14_rns.py (layer_frac=0.75 layer).

Output: evidence/s14_timeaxis.json
Usage: python -m rna_sc.s14_timeaxis --device 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc import s14_rns

RUN_DIR = "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_timeaxis.json"
NT_TARGETS = (500_000_000, 1_000_000_000, 1_500_000_000, 2_000_000_000)


def ckpt_at(run_dir, nt_target):
    cks = sorted([f for f in os.listdir(run_dir) if f.startswith("ckpt_")],
                 key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    return min(cks, key=lambda f: abs(
        int(f.split("_nt")[1].split("_")[0]) - nt_target))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=3)
    ap.add_argument("--n-real", type=int, default=1500)
    ap.add_argument("--layer-frac", type=float, default=0.75)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = s14_rns.stream_real(args.n_real)
    rand, _, _ = s14_rns.make_random_pool(real, 3)
    print("real=%d rand=%d" % (len(real), len(rand)))

    results = {}
    for nt_t in NT_TARGETS:
        ck_name = ckpt_at(RUN_DIR, nt_t)
        nt_actual = int(ck_name.split("_nt")[1].split("_")[0])
        model, ck = load_encoder(RUN_DIR, ckpt_nt=nt_actual)
        L = ck["cfg"]["arch"]["n_layers"]
        L_pick = max(0, min(L - 1, int(round(args.layer_frac * (L - 1)))))
        re = s14_rns.embed(model, dev, real, L_pick)
        ae = s14_rns.embed(model, dev, rand, L_pick)
        means, _ = s14_rns.rns_k(re, ae, s14_rns.KS, dev)
        results["nt_%.1fB" % (nt_actual / 1e9)] = {
            "ckpt": ck_name, "layer": L_pick,
            "RNS": {str(k): round(v, 4) for k, v in means.items()}}
        print("nt=%.1fB (%s) L%d RNS: %s" % (
            nt_actual / 1e9, ck_name, L_pick,
            {k: round(v, 4) for k, v in means.items()}))
        del model
        torch.cuda.empty_cache()

    with open(OUT, "w") as fh:
        json.dump({"run": "RNA-Sc-10M_s17", "layer_frac": args.layer_frac,
                   "n_real": len(real), "n_rand": len(rand),
                   "results": results,
                   "question": "RNS time-course vs probe-F1 attrition "
                               "(0.5B peak -> 2.0B 0.17)"}, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
