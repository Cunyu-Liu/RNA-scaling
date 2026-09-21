"""S14 v2 family-stratified RNS x probe-performance cross-validation
(T3.5.5 / C9.4 acceptance).

For each family (rna_type class): mean RNS_k of that family's sequences
(30M model, the scale where representation quality saturated) vs that
family's per-class probe F1 (same model). High-DI families predicted
worse RNS? Or independent? Spearman + scatter.

Also family-stratified RNS by scale (1M vs 100M): which families gain
most representation separation with scale.

Outputs: evidence/s14_family_crossval.json (+ stdout table).

Usage: python -m rna_sc.s14_family --device 6 [--n-per-family 60]
"""
from __future__ import annotations

import argparse
import json
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc.s14_rns import make_random_pool, embed

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_family_crossval.json"
ALPHABET = "ACGU"
MODEL = "RNA-Sc-30M_s17"      # representation-saturation scale
MODEL_SMALL = "RNA-Sc-1M_s17"
K = 10


def stream_family_seqs(max_per_fam, seed=17):
    """family_validation pool grouped by rna_type (top families)."""
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    by_fam = {}
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence",
                     "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm != "family_validation":
                continue
            by_fam.setdefault(rt, [])
            if len(by_fam[rt]) < max_per_fam:
                by_fam[rt].append(seq.upper().replace("T", "U")[:256])
        if sum(len(v) for v in by_fam.values()) >= \
                max_per_fam * 12:
            break
    # keep families with enough sequences
    return {f: v for f, v in by_fam.items() if len(v) >= max_per_fam}


def per_family_rns(model, device, fam_seqs, rand_seqs, k, seed=17):
    """RNS per family: share of each real point's k-NN (in combined
    real+rand pool) that are random, averaged per family."""
    real_all, fam_of = [], []
    for f, seqs in fam_seqs.items():
        for s in seqs:
            real_all.append(s)
            fam_of.append(f)
    re = embed(model, device, real_all, layer_pick_for(model))
    ae = embed(model, device, rand_seqs, layer_pick_for(model))
    R = torch.nn.functional.normalize(re.to(device), dim=1)
    A = torch.nn.functional.normalize(ae.to(device), dim=1)
    Srr = R @ R.T
    Sra = R @ A.T
    rr = Srr.clone()
    rr.diagonal().fill_(-2.0)
    best_rr, _ = rr.topk(k, dim=1)
    best_ra, _ = Sra.topk(k, dim=1)
    cand = torch.cat([best_rr, best_ra], dim=1)
    thresh, _ = cand.topk(k, dim=1)
    t = thresh[:, -1].unsqueeze(1)
    n_rand = (Sra >= t).float().sum(1).clamp(max=k)
    share = (n_rand / k).cpu().tolist()
    fam_rns = {}
    for f, s in zip(fam_of, share):
        fam_rns.setdefault(f, []).append(float(s))
    return {f: round(float(np.mean(v)), 4)
            for f, v in fam_rns.items()}


LAYER_CACHE = {}


def layer_pick_for(model):
    return LAYER_CACHE.get("pick", 8)


def probe_family_f1(run):
    """per-class F1 at best layer from official probe rows."""
    rows = []
    with open(PROBE_OUT) as fh:
        for line in fh:
            r = json.loads(line)
            if r["run"] != run:
                continue
            if r.get("n_train", 0) < 4000 or r.get("ckpt_nt") is None:
                continue
            rows.append(r)
    final_nt = max(r["ckpt_nt"] for r in rows)
    best = {r["layer"]: r for r in rows if r["ckpt_nt"] == final_nt}
    layers = sorted(best.values(), key=lambda r: r["layer"])
    brow = max(layers, key=lambda r: r["f1_macro"])
    L = len(layers)
    LAYER_CACHE["pick"] = min(brow["layer"], L - 1)
    return brow.get("per_class_f1") or {}


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                r[order[t]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) *
           sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-per-family", type=int, default=60)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    fam_seqs = stream_family_seqs(args.n_per_family)
    print("families: %d (%s)" % (len(fam_seqs),
                                 sorted(fam_seqs.keys())))
    all_real = [s for v in fam_seqs.values() for s in v]
    rand, _, _ = make_random_pool(all_real, 3)

    # probe F1 first (also sets layer pick from the best layer)
    pf1 = probe_family_f1(MODEL)
    print("layer pick:", LAYER_CACHE["pick"])

    model, ck = load_encoder(
        "/mnt/cunyuliu/rna-sc/runs/%s" % MODEL)
    fam_rns_30m = per_family_rns(model, dev, fam_seqs, rand, K)
    del model
    torch.cuda.empty_cache()
    model, ck = load_encoder(
        "/mnt/cunyuliu/rna-sc/runs/%s" % MODEL_SMALL)
    fam_rns_1m = per_family_rns(model, dev, fam_seqs, rand, K)
    del model
    torch.cuda.empty_cache()

    fams = sorted(set(fam_rns_30m) & set(pf1))
    xs = [fam_rns_30m[f] for f in fams]
    ys = [pf1[f] for f in fams if f in pf1]
    fams = [f for f in fams if f in pf1]
    rho = spearman([fam_rns_30m[f] for f in fams],
                   [pf1[f] for f in fams])
    gain = {f: round(fam_rns_1m[f] - fam_rns_30m[f], 4) for f in fams}

    out = {
        "model": MODEL, "k": K,
        "n_per_family": args.n_per_family,
        "families": {f: {"rns_30M": fam_rns_30m[f],
                         "rns_1M": fam_rns_1m[f],
                         "rns_gain_1M_to_30M": gain[f],
                         "probe_f1": round(pf1[f], 4)}
                     for f in fams},
        "spearman_rns_vs_probef1": round(rho, 4) if rho else None,
        "interpretation": {
            "rho<0": "low-RNS (well-separated) families probe better "
                     "— RNS is a valid zero-supervision screening "
                     "indicator (E14a)",
            "rho~0": "representation separation independent of "
                     "downstream usefulness (E14b decoupling at "
                     "family level)"},
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("%-14s %-9s %-9s %-9s %-9s" % ("family", "RNS@30M", "RNS@1M",
                                         "gain", "probeF1"))
    for f in fams:
        print("%-14s %-9.4f %-9.4f %-+9.4f %-9.4f" % (
            f, fam_rns_30m[f], fam_rns_1m[f], gain[f], pf1[f]))
    print("spearman(RNS, probeF1) =", out["spearman_rns_vs_probef1"])
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
