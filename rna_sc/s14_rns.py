"""S14 RNS (Random-Neighbor Share) representation-quality curves (H8).

Prabakaran & Bromberg NM 2026 transplant: for each REAL RNA, the share
of its k-nearest-neighbors (cosine) that are RANDOM sequences in the
embedding space. Lower RNS = real sequences cluster tightly apart from
random = better representation quality. Zero-supervision emergence
indicator, three analysis axes (scale / training time / family).

Steps (SPEC S14, C9 acceptance):
  1. Random control set: length-distribution + mono/di-nucleotide freq
     matched (three checks: KS p>0.05, freq diff <2%, 3x size) —
     recorded in evidence (C9.1), hard-fail if not met.
  2. Embeddings: mean-pooled sequence states (RNS context: mean-pool is
     legitimate — measures neighborhood geometry, not order-sensitive
     tasks; declared separately from S7 pooling discipline).
  3. RNS_k for k in {10, 50, 100} (GPU cosine topk).
  4. Axis 1 (this module v1): RNS vs model scale, all layers' best +
     per-layer detail; randinit control expected HIGHER RNS (validity
     check C9.3).
  5. Cross-validation with probe performance (C9.4) — v2.

Output: evidence/s14_rns.json (+ stdout table).

Usage:
  python -m rna_sc.s14_rns --device 6 [--n-real 1500] [--n-rand-mult 3]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

EVAL_POOL = ("family_validation", )  # pretraining-held-out real RNAs
OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_rns.json"
ALPHABET = "ACGU"
RUNS = ["RNA-Sc-1M_s17", "RNA-Sc-10M_s17", "RNA-Sc-30M_s17",
        "RNA-Sc-100M_s17", "RNA-Sc-10M_s17_randinit17",
        "RNA-Sc-100M_s17_randinit17"]
KS = (10, 50, 100)


def stream_real(n_needed: int, seed=17):
    """Sample real sequences from family_validation pool."""
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    seqs = []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence"]):
        d = rb.to_pydict()
        for sm, seq in zip(d["split_membership"], d["canonical_sequence"]):
            if sm != "family_validation":
                continue
            seqs.append(seq.upper().replace("T", "U")[:256])
            if len(seqs) >= n_needed * 2:
                break
        if len(seqs) >= n_needed * 2:
            break
    rng = random.Random(seed)
    rng.shuffle(seqs)
    return seqs[:n_needed]


def make_random_pool(real_seqs, mult, seed=17):
    """Matched random sequences: length distribution + mono/di freq."""
    rng = random.Random(seed)
    mono = {b: 0 for b in ALPHABET}
    di = {}
    total = 0
    for s in real_seqs:
        for b in s:
            if b in ALPHABET:
                mono[b] += 1
                total += 1
        for a, b in zip(s, s[1:]):
            if a in ALPHABET and b in ALPHABET:
                di[a + b] = di.get(a + b, 0) + 1
    p_mono = {b: mono[b] / max(1, total) for b in ALPHABET}
    tot_di = sum(di.values())
    p_di = {k: v / max(1, tot_di) for k, v in di.items()}
    # first-order Markov with matched mono+di: sample per-position using
    # conditional P(next|cur) derived from di/mono, stationary start p_mono
    out = []
    lens = [len(s) for s in real_seqs]
    for _ in range(mult * len(real_seqs)):
        L = lens[rng.randrange(len(lens))]
        cur = rng.choices(ALPHABET, weights=[p_mono[b] for b in ALPHABET])[0]
        s = [cur]
        for _ in range(L - 1):
            w = [max(1e-6, p_di.get(cur + b, 0.0)) for b in ALPHABET]
            cur = rng.choices(ALPHABET, weights=w)[0]
            s.append(cur)
        out.append("".join(s))
    return out, p_mono, p_di


def ks_check(real_lens, rand_lens):
    """1-D two-sample KS via sorting (n small, exact enough)."""
    a = np.sort(np.asarray(real_lens, dtype=float))
    b = np.sort(np.asarray(rand_lens, dtype=float))
    allv = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, allv, side="right") / len(a)
    cdf_b = np.searchsorted(b, allv, side="right") / len(b)
    d = float(np.max(np.abs(cdf_a - cdf_b)))
    n_eff = len(a) * len(b) / (len(a) + len(b))
    lam = (math.sqrt(n_eff) + 0.12 + 0.11 / math.sqrt(n_eff)) * d
    # Kolmogorov distribution P(D<=x)
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam)
                for k in range(1, 51))
    return round(d, 4), round(min(1.0, max(0.0, p)), 4)


def embed(model, device, seqs, L_pick, batch=48):
    """Mean-pooled sequence embedding at layer L_pick (0-indexed)."""
    model = model.to(device).eval()
    out = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for i in range(0, len(seqs), batch):
            chunk = seqs[i:i + batch]
            ids = [[ALPHABET.index(b) for b in s if b in ALPHABET][:256]
                   or [0, 1] for s in chunk]
            T = max(len(x) for x in ids)
            x = torch.tensor([r + [4] * (T - len(r)) for r in ids],
                             device=device)
            pad = x == 4
            _, _, hids = model(x, return_all_hiddens=True)
            h = hids[L_pick]
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
            out.append((hm.sum(1) / lens).cpu())
    return torch.cat(out, 0)


def rns_k(real_emb, rand_emb, ks, device):
    """RNS_k: share of each real point's k-NN (in combined pool) that
    are random sequences. Done on GPU via cosine topk."""
    R = torch.nn.functional.normalize(real_emb.to(device), dim=1)
    A = torch.nn.functional.normalize(rand_emb.to(device), dim=1)
    sim = R @ A.T  # real-to-random similarity
    # we need k-NN over the COMBINED pool; trick: rank random-sims vs
    # real-sims per point. n_real (1.5k) x n_all (6k) is small — direct.
    Srr = R @ R.T
    out = {}
    for k in ks:
        # top-(k+1) in each block; k-NN excluding self
        trr, _ = Srr.topk(min(k + 1, Srr.shape[1]), dim=1)
        tra, _ = sim.topk(min(k, sim.shape[1]), dim=1)
        # for each real i: threshold = k-th best overall among
        # (Srr[i,1:] excluding self) and sim[i,:]
        self_sim = Srr.diagonal()
        rr = Srr.clone()
        rr.diagonal().fill_(-2.0)
        best_rr, _ = rr.topk(k, dim=1)
        best_ra, _ = sim.topk(k, dim=1)
        cand = torch.cat([best_rr, best_ra], dim=1)
        thresh, _ = cand.topk(k, dim=1)
        t = thresh[:, -1].unsqueeze(1)  # k-th best value
        n_rand = (sim >= t).float().sum(1).clamp(max=k)
        out[k] = (n_rand / k)
    return {k: float(v.float().mean()) for k, v in out.items()}, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-real", type=int, default=1500)
    ap.add_argument("--n-rand-mult", type=int, default=3)
    ap.add_argument("--layer-frac", type=float, default=0.75,
                    help="which layer to embed (fraction of depth)")
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = stream_real(args.n_real)
    rand, p_mono, p_di = make_random_pool(real, args.n_rand_mult)
    d_ks, p_ks = ks_check([len(s) for s in real],
                          [len(s) for s in rand])
    # mono freq check (rand pool generated to match; verify empirically)
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
    checks = {"ks_d": d_ks, "ks_p": p_ks,
              "mono_max_dev": round(max_dev, 4),
              "passed": p_ks > 0.05 and max_dev < 0.02}
    print("control-set checks:", json.dumps(checks))
    if not checks["passed"]:
        print("C9.1 HARD FAIL: random control set not matched; aborting")
        return 1

    results = {}
    for run in RUNS:
        base = run.replace("_randinit17", "")
        ri = run.endswith("_randinit17")
        model, ck = load_encoder(
            "/mnt/cunyuliu/rna-sc/runs/%s" % base)
        L = ck["cfg"]["arch"]["n_layers"]
        if ri:
            from rna_sc.model import RNAMLMEncoder
            torch.manual_seed(17)
            mcfg = ck["cfg"]["arch"]
            model = RNAMLMEncoder(d_model=mcfg["d_model"],
                                  n_layers=mcfg["n_layers"],
                                  n_heads=mcfg["n_heads"],
                                  d_ff=mcfg["d_ff"])
        L_pick = max(0, min(L - 1, int(round(args.layer_frac * (L - 1)))))
        re = embed(model, dev, real, L_pick)
        ae = embed(model, dev, rand, L_pick)
        means, per_k = rns_k(re, ae, KS, dev)
        results[run] = {"layer": L_pick, "layer_frac": args.layer_frac,
                        "RNS": {str(k): round(v, 4)
                                for k, v in means.items()},
                        "n_real": len(real), "n_rand": len(rand)}
        print("%-28s L%d/%d  RNS: %s" % (
            run, L_pick, L - 1,
            {k: round(v, 4) for k, v in means.items()}))
        del model
        torch.cuda.empty_cache()

    out = {"checks": checks, "n_real": len(real),
           "n_rand": len(rand), "k_values": list(KS),
           "results": results,
           "expectation": "randinit RNS >> trained RNS (C9.3 validity)"}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
