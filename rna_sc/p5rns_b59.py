"""P5 shuffle separation on b59 arms (Day 26 gap-fill, MLM protocol v2).

PROTOCOL MATCH to the main-line P5 (p5_shuffle_threshold.json):
MLM likelihood separation, native minus position-shuffled, SAME mask
positions, nats/token. v1 of this script used unmasked teacher-forcing
NLL which is NOT comparable (models only predict at [MASK]); that run
is discarded (negative separation = protocol artifact).

Per sequence (len>=24, cap 192):
  1. choose 15% positions (seeded, min 1) as mask idx
  2. native input: ids with mask idx -> MASK; targets: orig ids at
     mask idx, IGNORE elsewhere
  3. shuffled input: position-shuffled ids, SAME mask idx (indexes
     refer to the shuffled sequence); targets: shuffled ids at those
     idx
  4. separation = NLL_native - NLL_shuffled (per-token mean over mask
     positions)
150 rRNA + 150 structured non-rRNA (tRNA/snoRNA/snRNA/SRP/misc/tmRNA)
from family_validation.

Usage:
  python -m rna_sc.p5rns_b59 --run RNA-Sc-30M_s17_b59 --device 3
"""
from __future__ import annotations

import argparse
import json
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.model import MASK
from rna_sc.probe import load_encoder
from rna_sc.s14_rns import make_random_pool, rns_k, stream_real, ks_check
from rna_sc.s14_rns import ALPHABET, KS

OUTDIR = "/mnt/cunyuliu/rna-sc/evidence"
IGNORE = -100


def embed_one_by_one(model, dev, seqs, L_pick, len_cap=192):
    model = model.to(dev).eval()
    outs = []
    with torch.no_grad():
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s if b in ALPHABET][:len_cap]
            if len(ids) < 4:
                continue
            x = torch.tensor([ids], device=dev)
            _, _, hids = model(x, return_all_hiddens=True)
            h = hids[L_pick][0].float().mean(0)
            outs.append(h.cpu())
    return torch.stack(outs)


def mlm_nll(model, dev, ids, mask_idx):
    x = list(ids)
    for i in mask_idx:
        x[i] = MASK
    x = torch.tensor([x], device=dev)
    t = [IGNORE] * len(ids)
    for i in mask_idx:
        t[i] = ids[i]
    t = torch.tensor([t], device=dev)
    with torch.no_grad():
        logits, _ = model(x, targets=t)
    logp = torch.log_softmax(logits[0], -1)
    tot = 0.0
    for i in mask_idx:
        tot -= float(logp[i, ids[i]])
    return tot / max(1, len(mask_idx))


def p5_separation_mlm(model, dev, n_per_class=150, seed=17):
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    rrna, non = [], []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(batch_size=50_000,
                              columns=["split_membership",
                                       "canonical_sequence", "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm != "family_validation":
                continue
            s = "".join(b for b in seq.upper().replace("T", "U")
                        if b in ALPHABET)
            if len(s) < 24 or len(s) > 160:
                continue
            rt_clean = (rt or "").strip()
            if rt_clean == "rRNA":
                if len(rrna) < n_per_class * 4:
                    rrna.append(s)
            elif rt_clean in ("tRNA", "snoRNA", "snRNA", "SRP_RNA",
                              "misc_RNA", "tmRNA"):
                if len(non) < n_per_class * 4:
                    non.append(s)
        if len(rrna) >= n_per_class * 4 and len(non) >= n_per_class * 4:
            break
    rng = random.Random(seed)
    rng.shuffle(rrna)
    rng.shuffle(non)
    rrna, non = rrna[:n_per_class], non[:n_per_class]

    def sep(seqs, tag):
        r = random.Random(seed + 1)
        nats, shfs = [], []
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s if b in ALPHABET][:192]
            n = len(ids)
            k = max(1, int(round(0.15 * n)))
            mask_idx = sorted(r.sample(range(n), k))
            nats.append(mlm_nll(model, dev, ids, mask_idx))
            lst = list(ids)
            r.shuffle(lst)
            shfs.append(mlm_nll(model, dev, lst, mask_idx))
        # main-line P5 convention: separation = NLL_shuffled - NLL_native
        # (positive = shuffling costs structure information). Sign set
        # after calibration against p5_shuffle_threshold.json 30M row
        # (randinit ~0 on both sides, trained 30M +0.80 vs main +1.07).
        return float(np.mean(shfs) - np.mean(nats))

    return {"rRNA_sep": round(sep(rrna, "rrna"), 4),
            "nonrRNA_sep": round(sep(non, "non"), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--device", type=int, default=5)
    ap.add_argument("--n-real", type=int, default=1500)
    ap.add_argument("--random-init", type=int, default=None)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = stream_real(args.n_real)
    rand, p_mono, p_di = make_random_pool(real, 3)
    d_ks, p_ks = ks_check([len(s) for s in real], [len(s) for s in rand])
    checks = {"ks_d": d_ks, "ks_p": p_ks, "passed": p_ks > 0.05}
    print("checks:", json.dumps(checks))
    if not checks["passed"]:
        print("C9.1 HARD FAIL")
        return 1

    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % args.run)
    run_label = args.run
    if args.random_init is not None:
        from rna_sc.model import RNAMLMEncoder
        torch.manual_seed(args.random_init)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        run_label = "%s_randinit%d" % (args.run, args.random_init)
    L = ck["cfg"]["arch"]["n_layers"]
    L_pick = max(0, min(L - 1, int(round(0.75 * (L - 1)))))
    re = embed_one_by_one(model, dev, real, L_pick)
    ae = embed_one_by_one(model, dev, rand, L_pick)
    means, _ = rns_k(re, ae, KS, dev)
    print("RNS:", {k: round(v, 4) for k, v in means.items()})

    print("P5 MLM separation (150+150)...")
    p5 = p5_separation_mlm(model, dev)
    print("P5:", json.dumps(p5))

    out = {"run": run_label, "layer": L_pick, "layer_frac": 0.75,
           "RNS": {str(k): round(v, 4) for k, v in means.items()},
           "P5_mlm_separation": p5, "checks": checks,
           "protocol": "RNS s14 (one-by-one, len<=192) + P5 MLM "
                       "same-mask-positions separation v2 (v1 "
                       "unmasked-NLL run discarded: protocol mismatch)"}
    outp = "%s/p5rns_%s.json" % (OUTDIR, run_label)
    with open(outp, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", outp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
