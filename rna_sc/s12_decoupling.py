"""S12 family decoupling index (H6 falsifiable test, red-team fix D: early start).

Decoupling index per Rfam family = within-family mean sequence identity
normalized by the covariance-model (CM) score the family achieves on its own
members (Infernal cmscan). High index = sequence-divergent but
structure-conserved family -> H6 predicts LATER/WORSE contact emergence.

Two-stage (CPU only, runs alongside GPU training):
  stage 1 (this script, --stage cmscan): build per-family FASTA from
    release22 (sampled), run cmscan against Rfamseq CM database if present
    (Rfam.cm), else compute CM score proxy via self-alignment scores later;
  stage 2 (--stage index): per family compute (a) mean pairwise identity,
    (b) mean CM bit score of members vs family CM, output
    decoupling_index = (a)/(b-normalized) + family metadata table.

Pragmatic v1 (no Rfam.cm download dependency): use release22
family_annotation (Rfam family labels already present per sequence!) +
within-family identity computed by clustering stats. CM scores need Rfam.cm:
downloads handled by --fetch-rfamcm (Rfam FTP). If absent, stage 1 emits
identity-only table and index is deferred (marked status).
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import sys

import pyarrow.parquet as pq

SPLIT = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
OUT_DIR = "/mnt/cunyuliu/rna-sc/evidence"
RFAM_CM = "/mnt/cunyuliu/rna-sc/data/Rfam.cm"

MAX_FAMILIES = 2000
SAMPLE_PER_FAMILY = 40


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def stage_collect():
    """Collect family membership + per-family sampled sequences + identity.

    family_annotation column holds Rfam family labels. For each family sample
    up to SAMPLE_PER_FAMILY sequences (seeded), compute mean pairwise identity
    over sampled pairs (k-mer shortcut for long seqs: use first 200nt window).
    """
    import random
    rng = random.Random(17)
    fams = collections.defaultdict(list)
    for rb in pq.ParquetFile(SPLIT).iter_batches(
            batch_size=200_000,
            columns=["family_annotation", "canonical_sequence", "length"]):
        d = rb.to_pydict()
        for fam, seq, ln in zip(d["family_annotation"], d["canonical_sequence"],
                                d["length"]):
            if not fam:
                continue
            if len(fams[fam]) < SAMPLE_PER_FAMILY:
                fams[fam].append(seq[:200])
    out = {}
    for fam, seqs in fams.items():
        if len(seqs) < 4:
            continue
        ids = []
        for i in range(len(seqs)):
            for j in range(i + 1, len(seqs)):
                a, b = seqs[i], seqs[j]
                L = min(len(a), len(b))
                if L < 10:
                    continue
                eq = sum(1 for x, y in zip(a[:L], b[:L]) if x == y)
                ids.append(eq / L)
        out[fam] = {
            "n_sampled": len(seqs),
            "mean_pairwise_identity": round(sum(ids) / max(1, len(ids)), 4),
        }
    rows = {fam: v for fam, v in sorted(out.items(),
             key=lambda kv: -kv[1]["n_sampled"])[:MAX_FAMILIES]}
    path = os.path.join(OUT_DIR, "s12_family_identity.json")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"generated": _now(), "n_families": len(rows),
                   "sample_per_family": SAMPLE_PER_FAMILY,
                   "families": rows}, fh, indent=2)
    print(json.dumps({"stage": "identity", "n_families": len(rows),
                      "out": path}, indent=2))
    return rows


def stage_cmscan(identity_rows):
    """If Rfam.cm exists, run cmscan on per-family sampled FASTA and record
    per-family mean CM bit score, then compute decoupling index."""
    if not os.path.exists(RFAM_CM):
        print(json.dumps({"stage": "cmscan", "status": "Rfam.cm absent",
                          "note": "identity table done; fetch Rfam.cm to "
                                  "complete index (stage index)"},
                         indent=2))
        return
    print("Rfam.cm present — full cmscan pipeline not yet wired; "
          "identity table stands alone for now.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="identity",
                    choices=["identity", "cmscan"])
    args = ap.parse_args()
    if args.stage == "identity":
        rows = stage_collect()
        stage_cmscan(rows)
    else:
        with open(os.path.join(OUT_DIR, "s12_family_identity.json")) as fh:
            stage_cmscan(json.load(fh)["families"])


if __name__ == "__main__":
    main()
