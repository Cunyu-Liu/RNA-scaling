"""S3 reweighted-corpus training arm (T2.3.3): 30M model, family-flattened corpus.

Reuses the frozen recipe (train.run) with a data-source override: instead
of the raw release22 split, streams the exploded reweighted parquet
built by s3_reweight_corpus.py. All recipe knobs identical to the
30M-full control arm (RNA-Sc-30M_s17) EXCEPT the sampling distribution
— the single-variable discipline of the S3 axis.

manifest/logs land in runs/RNA-Sc-30M_s17_rw1 with corpus_tag=rw1 so
the ledger/watch_all/probe chain picks it up like any other arm.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc import train as train_mod
from rna_sc.data import iter_mlm_batches, count_valid_nt

RW_PARQUET = "/mnt/cunyuliu/rna-sc/data/r22_train_reweighted.parquet"


def patched_iter(path, split, seed, context_nt, batch_nt, corpus_nseq=None,
                 max_batches=None, cluster_allowlist=None):
    """iter_mlm_batches against the reweighted parquet (split column is
    literal 'train' for every row; replica shifts the mask stream seed)."""
    return iter_mlm_batches(path, "train", seed, context_nt, batch_nt,
                            corpus_nseq=corpus_nseq, max_batches=max_batches,
                            cluster_allowlist=cluster_allowlist)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="RNA-Sc-30M")
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--data", default=RW_PARQUET)
    ap.add_argument("--corpus-tag", default="rw1")
    ap.add_argument("--smoke-nt", type=int, default=None)
    ap.add_argument("--resume-from", default=None)
    args = ap.parse_args()

    real_split = train_mod.SPLIT_8080
    train_mod.SPLIT_8080 = args.data
    try:
        train_mod.run(
            args.model, args.seed, args.device, args.out_dir,
            corpus_nseq=None, corpus_tag=args.corpus_tag,
            smoke_nt=args.smoke_nt, resume_from=args.resume_from,
            cluster_allowlist=None)
    finally:
        train_mod.SPLIT_8080 = real_split
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
