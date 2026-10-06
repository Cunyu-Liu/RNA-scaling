"""Rfam-enriched corpus training arm (D-3 / T4.3.4, pre-registered).

Thin wrapper: trains with --train-parquet r22_train_rfamcap.parquet
(Rfam-annotated, family-capped corpus) while validate() keeps
streaming the ORIGINAL split parquet (fixes the rw1 train-only
validation artifact by construction). Launch discipline: manual only
(train_s3_rfamcap), NEVER into supervisor wave (same rule as rw1).
Usage:
  python -m rna_sc.train_s3_rfamcap --model RNA-Sc-100M --device 3
"""
import argparse
import subprocess
import sys

PY = sys.executable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="RNA-Sc-100M")
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--budget-nt", type=int, default=2_000_000_000)
    args = ap.parse_args()
    tag = "rfamcap"
    scale = args.model.split("-")[-1]
    out = "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-%s_s%d_%s" % (scale, args.seed, tag)
    cmd = [PY, "-m", "rna_sc.train", "--model", args.model,
           "--seed", str(args.seed), "--device", str(args.device),
           "--out-dir", out, "--corpus-tag", tag,
           "--budget-nt", str(args.budget_nt),
           "--train-parquet",
           "/mnt/cunyuliu/rna-sc/data/r22_train_rfamcap.parquet"]
    print("launch:", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
