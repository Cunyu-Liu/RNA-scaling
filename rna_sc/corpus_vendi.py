"""T2.3.2b Vendi index (GPU-embedded variant) for the corpus axis.

Vendi index V = exp(H(q)), q over eigenvalues of the trace-normalized
Gram matrix (RBF kernel, median-heuristic bandwidth). Higher = more
diverse effective aspects.

Embedding: RNA-Sc-10M (s17, final ckpt) last-layer hidden states,
mean-pooled over tokens of the first 256-nt window. Mean-pool is
FORBIDDEN for supervised heads (order-blind) but acceptable here as an
unsupervised corpus-similarity statistic (documented in methods).

Sampling: 5000 seqs/arm, seed 43, uniform over the arm sequence set
(arm definitions shared with corpus_diversity.py).

CUDA required (assert, no silent CPU fallback).
Output: evidence/corpus_vendi.json
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import numpy as np
import pyarrow.parquet as pq
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.probe import load_encoder
from rna_sc.corpus_diversity import SPLIT, SUB, ARMS

RUN_10M = "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17"
OUT = "/mnt/cunyuliu/rna-sc/evidence/corpus_vendi.json"
N_SAMPLE = 5000
SEED = 43
CTX = 256
ALPHABET = "ACGU"


def load_allowlist(tag: str) -> set:
    ids = pq.read_table(os.path.join(SUB, tag + ".parquet"))["cluster_id"]
    return set(ids.to_pylist())


def _canon(s: str) -> str:
    return s.upper().replace("T", "U")


def sample_arm(arm, nseq, tag, allowlists, want: set[int]) -> list[str]:
    out = []
    pf = pq.ParquetFile(SPLIT)
    cols = ["split_membership", "cluster_id", "canonical_sequence"]
    i = 0
    for rb in pf.iter_batches(batch_size=500_000, columns=cols):
        d = rb.to_pydict()
        for sm, cid, seq in zip(d["split_membership"], d["cluster_id"],
                                d["canonical_sequence"]):
            if sm != "train":
                continue
            if tag is not None and cid not in allowlists[tag]:
                continue
            if nseq is not None and i >= nseq:
                return out
            if i in want:
                out.append(_canon(seq)[:CTX])
            i += 1
        if nseq is not None and i >= nseq:
            return out
    return out


def encode(seqs: list[str], model, device) -> np.ndarray:
    model.eval()
    embs = []
    with torch.no_grad():
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s if b in ALPHABET]
            if not ids:
                ids = [0]
            t = torch.tensor([ids], device=device)
            _, _, hids = model(t, return_all_hiddens=True)
            h = hids[-1][0]
            pooled = h.mean(dim=0)
            embs.append(pooled.float().cpu().numpy())
    return np.stack(embs)


def vendi(X: np.ndarray) -> float:
    D2 = ((X[:, None, :] - X[None, :, :]) ** 2).sum(-1)
    med = np.median(D2[np.triu_indices(len(X), 1)])
    if med <= 0:
        med = 1.0
    K = np.exp(-D2 / med)
    K = K / np.trace(K) * len(X)
    ev = np.linalg.eigvalsh(K)
    ev = np.clip(ev, 0, None)
    q = ev / ev.sum()
    nz = q[q > 1e-12]
    H = -(nz * np.log(nz)).sum()
    return float(math.exp(H))


def main() -> int:
    assert torch.cuda.is_available(), "CUDA required (no silent CPU fallback)"
    device = "cuda:0"
    model, ck = load_encoder(RUN_10M)
    model.to(device).eval()
    print("[vendi] encoder loaded from", ck.get("nt"), "nt", flush=True)

    allowlists = {}
    for _, _, tag in ARMS:
        if tag and tag not in allowlists:
            allowlists[tag] = load_allowlist(tag)

    audit = json.load(open(
        "/mnt/cunyuliu/rna-sc/evidence/corpus_diversity.json"))["per_arm"]

    results = {}
    for arm, nseq, tag in ARMS:
        n_pop = audit[arm]["n_seq"]
        rng = random.Random(SEED)
        want = set(rng.sample(range(n_pop), min(N_SAMPLE, n_pop)))
        seqs = sample_arm(arm, nseq, tag, allowlists, want)
        assert len(seqs) == len(want), (
            "sample mismatch %s: %d != %d" % (arm, len(seqs), len(want)))
        X = encode(seqs, model, device)
        V = vendi(X)
        results[arm] = {"vendi": round(V, 2), "n_sample": len(seqs)}
        print("[vendi] %s: V=%.2f (n=%d)" % (arm, V, len(seqs)), flush=True)

    with open(OUT, "w") as fh:
        json.dump({"model": "RNA-Sc-10M_s17 final",
                   "kernel": "RBF median-heuristic, trace-normalized",
                   "embedding": "last-layer mean-pool, first-256nt window",
                   "seed": SEED, "per_arm": results}, fh, indent=2)
    print("[vendi] saved", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
