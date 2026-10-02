"""T3.5.7: family-level RNS x forward co-variation (COV) correlation.

Q19-Q2 gap: protein paper has RNS vs TM-score (continuous structural
score, rho -0.70). Our RNA counterpart at the family level: mean RNS@10
per family vs mean COV-CTRL (forward co-variation sensitivity, Q10
data) per family, on the same family set.

Sources: s14_family_crossval.json (RNS per family, 30M) + Q10
cov_sensitivity evidence (per-scale COV; family split of the COV
test set derived from bpRNA family tags if per-family values exist;
otherwise per-family COV computed here for 30M on bpRNA TS0 seqs by
family source tag).

Output: evidence/s14_rns_cov.json
"""
from __future__ import annotations

import argparse
import json
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.s14_rns_ext import stream_real, rns_from_emb, ours_embedder

OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_rns_cov.json"
ALPHABET = "ACGU"


def spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def bpRNA_family_seqs(max_per_fam=40):
    import pyarrow.parquet as pq
    by_fam = {}
    t = pq.read_table("/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet")
    d = t.to_pydict()
    for seq, src, split in zip(d["seq"], d["source"], d["split"]):
        if split != "test":
            continue
        s = "".join(b for b in seq.upper().replace("T", "U")
                    if b in ALPHABET)[:192]
        if len(s) < 24:
            continue
        by_fam.setdefault(src, [])
        if len(by_fam[src]) < max_per_fam:
            by_fam[src].append(s)
    return {k: v for k, v in by_fam.items() if len(v) >= 12}


def cov_family(model, device, fam_seqs, seed=17):
    """Per-family masked-marginal NLL (continuous confidence proxy).
    Mask token = 5 (MASK id in rna_sc.model). One random position per
    pass, 5 passes per sequence, mean over family."""
    rng = random.Random(seed)
    fams = {}
    with torch.no_grad():
        for fam, seqs in fam_seqs.items():
            losses = []
            for s in seqs[:20]:
                ids = [ALPHABET.index(b) for b in s]
                if len(ids) < 4:
                    continue
                for _ in range(5):
                    j = rng.randrange(len(ids))
                    x = torch.tensor([ids], device=device)
                    xm = x.clone()
                    xm[0, j] = 5  # MASK
                    logits, _ = model(xm)
                    lp = -torch.nn.functional.cross_entropy(
                        logits[0, j].unsqueeze(0),
                        x[0, j].unsqueeze(0)).item()
                    losses.append(lp)
            fams[fam] = float(np.mean(losses))
    return fams


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    fam_seqs = bpRNA_family_seqs()
    fams = sorted(fam_seqs.keys())
    print("families:", fams, flush=True)

    # RNS per family (30M model, our saturation scale)
    run = "RNA-Sc-30M_s17"
    fn = ours_embedder(run, dev)
    real = [s for f in fams for s in fam_seqs[f]]
    fam_of = [f for f in fams for s in fam_seqs[f]]
    from rna_sc.s14_rns import make_random_pool
    rand, _, _ = make_random_pool(real, 3)
    re = fn(real)
    ae = fn(rand)
    # per-seq RNS
    R = torch.nn.functional.normalize(re, dim=1)
    A = torch.nn.functional.normalize(ae, dim=1)
    Sra = R @ A.T
    Srr = R @ R.T
    rr = Srr.clone(); rr.diagonal().fill_(-2.0)
    b1, _ = rr.topk(10, dim=1)
    b2, _ = Sra.topk(10, dim=1)
    cand = torch.cat([b1, b2], dim=1)
    th, _ = cand.topk(10, dim=1)
    t = th[:, -1].unsqueeze(1)
    n_rand = (Sra >= t).float().sum(1).clamp(max=10)
    per_rns = (n_rand / 10).cpu().numpy()

    fam_rns = {}
    for f in fams:
        idx = [i for i, ff in enumerate(fam_of) if ff == f]
        fam_rns[f] = float(np.mean(per_rns[idx]))

    # NLL per family (continuous proxy)
    from rna_sc.probe import load_encoder
    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % run)
    model = model.to(dev).eval()
    fam_nll = cov_family(model, dev, fam_seqs)

    a = np.array([fam_rns[f] for f in fams])
    b = np.array([fam_nll[f] for f in fams])
    res = {"model": run, "families": fams,
           "fam_rns": {f: round(fam_rns[f], 4) for f in fams},
           "fam_masked_nll": {f: round(fam_nll[f], 4) for f in fams},
           "spearman_rns_nll": round(spearman(a, b), 4),
           "pearson": round(float(np.corrcoef(a, b)[0, 1]), 4),
           "note": "continuous structural-confidence proxy = masked "
                   "marginal NLL per family (Hou-style); true partner-"
                   "level COV per family requires pair annotations on "
                   "family_validation pool (not available); this is the "
                   "closest honest counterpart"}
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
