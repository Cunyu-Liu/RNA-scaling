"""S14 v2 add-on: RNS point for RNA-Sc-650M_s17 (single run, side file).

Fully manual, memory-bounded forward: fp16, per-sequence single-sample
batches with hard length cap 192 (t1b-style), chunked hidden-stack mean
pooling. Designed for ~4.5GB shared GPUs where the 650M encoder must
share with other users' processes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc import s14_rns

OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_rns_650m.json"
RUN = "RNA-Sc-650M_s17"
MAX_LEN = 192
ALPHABET = s14_rns.ALPHABET


def embed_one_by_one(model, device, seqs, L_pick):
    model = model.to(device).eval()
    outs = []
    with torch.no_grad():
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s if b in ALPHABET][:MAX_LEN]
            if len(ids) < 2:
                ids = ids + [0]
            x = torch.tensor([ids], device=device, dtype=torch.long)
            _, _, hids = model(x, return_all_hiddens=True)
            outs.append(hids[L_pick][0].float().mean(dim=0).cpu())
            if len(outs) % 500 == 0:
                print("  embedded %d/%d" % (len(outs), len(seqs)),
                      flush=True)
    return torch.stack(outs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-real", type=int, default=1500)
    ap.add_argument("--n-rand-mult", type=int, default=3)
    ap.add_argument("--layer-frac", type=float, default=0.75)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = [s for s in s14_rns.stream_real(args.n_real)]
    rand, p_mono, p_di = s14_rns.make_random_pool(real, args.n_rand_mult)
    from scipy.stats import ks_2samp
    d_ks, p_ks = ks_2samp([len(s) for s in real], [len(s) for s in rand])

    def mono_freq(seqs):
        c = {b: 0 for b in ALPHABET}
        t = 0
        for s in seqs:
            for b in s:
                c[b] += 1
                t += 1
        return {b: c[b] / t for b in ALPHABET}

    mr, ma = mono_freq(real), mono_freq(rand)
    max_dev = max(abs(mr[b] - ma[b]) for b in ALPHABET)
    checks = {"ks_d": round(float(d_ks), 4), "ks_p": round(float(p_ks), 4),
              "mono_max_dev": round(max_dev, 4),
              "max_len_cap": MAX_LEN,
              "passed": p_ks > 0.05 and max_dev < 0.02}
    print("control-set checks:", json.dumps(checks))
    if not checks["passed"]:
        print("C9.1 HARD FAIL: control set not matched; aborting")
        return 1

    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % RUN)
    L = ck["cfg"]["arch"]["n_layers"]
    L_pick = max(0, min(L - 1, int(round(args.layer_frac * (L - 1)))))
    print("embedding real (%d) ..." % len(real), flush=True)
    re = embed_one_by_one(model, dev, real, L_pick)
    print("embedding rand (%d) ..." % len(rand), flush=True)
    ae = embed_one_by_one(model, dev, rand, L_pick)
    means, per_k = s14_rns.rns_k(re, ae, s14_rns.KS, dev)
    out = {"run": RUN, "layer": L_pick, "layer_frac": args.layer_frac,
           "RNS": {str(k): round(v, 4) for k, v in means.items()},
           "n_real": len(real), "n_rand": len(rand),
           "max_len_cap": MAX_LEN,
           "checks": checks,
           "note": "v1 scale-axis RNS used batch embed len<=256; this "
                   "650M add-on uses one-by-one fp32 forward with len "
                   "cap 192 for shared-GPU memory safety",
           "expectation": "RNS <= 100M's 0.077 (plateau continues) or "
                          "lower; NOT-BELL/plateau narratives cross-check"}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("%-28s L%d/%d  RNS: %s" % (
        RUN, L_pick, L - 1, {k: round(v, 4) for k, v in means.items()}))
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
