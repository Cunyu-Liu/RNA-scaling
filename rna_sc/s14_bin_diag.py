"""Q19 bin-effect confound diagnosis: length vs RNS vs F1.

The protein paper found high-RNS bins degrade structure tasks (-40%).
We found the OPPOSITE direction in RNA (high-RNS bin pair-F1 HIGHER).
Prime suspect: length confounding — short sequences have (a) higher
paired-position density (easier F1), (b) higher RNS (fewer positions
-> k-NN in mean-pooled space more likely to hit random pool).

This script computes per-TS0-sequence: length, RNS, pair-F1, and the
length-stratified RNS-F1 relation, plus the length-RNS correlation.
Pure analysis on cached embeddings? We re-embed (cheap enough) and
emit evidence/s14_bin_diag.json.
"""
from __future__ import annotations

import argparse
import json
import math
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc.s14_bin_eval import (ALPHABET, BPRNA, K, LEN_CAP, BATCH,
                                 clean_seq, embed, load_bprna_pairs,
                                 macro_f1_pair, rns_per_real,
                                 make_random_pool, stream_real)

OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_bin_diag.json"
RUN = "RNA-Sc-100M_s17"


def spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = stream_real(1500)
    rand, _, _ = make_random_pool(real, 3)
    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % RUN)
    L = ck["cfg"]["arch"]["n_layers"]
    L_pick = max(0, min(L - 1, int(round(0.75 * (L - 1)))))
    ae = embed(model, dev, rand, L_pick)

    bprna = load_bprna_pairs()
    ts = [(clean_seq(s), p) for s, p, sp in bprna
          if sp == "test" and p is not None]

    lens, dens = [], []
    kept = []
    for s, pairs in ts:
        if not pairs or len(s) < 8:
            continue
        Ls = len(s)
        paired = sum(1 for (i, j) in pairs
                     if i < Ls and j < Ls) * 2
        kept.append(s)
        lens.append(Ls)
        dens.append(paired / Ls)

    # matrix RNS over the whole kept set at once (1 x 1 per-seq fails)
    all_emb = embed(model, dev, kept, L_pick)
    rnss = rns_per_real(all_emb, ae, K, dev).numpy()

    lens = np.array(lens); rnss = np.array(rnss); dens = np.array(dens)

    # length-stratified: RNS in short/long halves
    med = np.median(lens)
    short = lens <= med
    out = {
        "n": int(len(lens)),
        "median_len": float(med),
        "spearman_len_rns": spearman(lens, rnss),
        "rns_mean_short": float(rnss[short].mean()),
        "rns_mean_long": float(rnss[~short].mean()),
        "pair_density_short": float(dens[short].mean()),
        "pair_density_long": float(dens[~short].mean()),
        "pearson_len_rns": float(np.corrcoef(lens, rnss)[0, 1]),
        "note": "RNS of TS0 seqs vs random pool (100M, L 0.75); "
                "if len-RNS correlation is strongly negative, the "
                "inverted bin effect is length-confounded",
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
