"""Rfam-enriched corpus arm (D-3 / T4.3.4, pre-registered orthogonal test).

Purpose: isolate the CORPUS factor with architecture held fixed. The
+0.10 structure gap (RiNALMo-giga 0.728 vs ours 0.6255 at 650M) is a
joint corpus-architecture-recipe effect with corpus as leading suspect
(Q18 qualification). The orthogonal test: train OUR architecture on a
Rfam-annotated, family-balanced corpus. If the structure gain
reproduces, the corpus factor is confirmed.

Construction (pre-registered):
- Universe = train split rows with non-empty family_annotation
  (Rfam families, ~67% of train rows).
- Per-family cap: at most `cap` sequences per Rfam family
  (flattening the RF00177 5S-rRNA dominance, mirroring RiNALMo's
  structured ncRNA corpus emphasis).
- Every recipe knob identical to the main line: same tokenizer, MLM
  15%, same model spec, same optimizer/schedule, same 2.0B-nt budget,
  same validate() on the ORIGINAL pool (kept untouched for
  comparability — unlike rw1 whose train-only parquet produced the
  best_val=0.0 artifact; that lesson is baked in here).

Output parquet keeps the same column schema as the source split so
the streaming path (iter_mlm_batches) works unchanged; split column
is rewritten to train-only rows (validate streams the original pool).
"""
from __future__ import annotations

import argparse
import json

import pyarrow as pa
import pyarrow.parquet as pq

SPLIT = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
         "release22_split_8080.parquet")
OUT_PARQUET = "/mnt/cunyuliu/rna-sc/data/r22_train_rfamcap.parquet"
OUT_META = "/mnt/cunyuliu/rna-sc/data/r22_train_rfamcap.json"
SEED = 17

COLS = ["canonical_sequence_hash", "canonical_sequence", "rna_type",
        "length", "length_bin", "num_accessions", "accessions",
        "cluster_id", "family_annotation", "split_membership",
        "clan_annotation", "eligible_family"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=4000,
                    help="max sequences per Rfam family")
    args = ap.parse_args()
    cap = args.cap

    import random
    rng = random.Random(SEED)

    pf = pq.ParquetFile(SPLIT)
    kept_rows = {c: [] for c in COLS}
    fam_count: dict[str, int] = {}
    fam_seen: dict[str, list] = {}
    n_train = 0
    n_annot = 0

    for rb in pf.iter_batches(batch_size=200_000, columns=COLS):
        d = rb.to_pydict()
        for i in range(len(d["split_membership"])):
            sm = d["split_membership"][i]
            if sm != "train":
                continue
            n_train += 1
            fa = d["family_annotation"][i]
            if not fa or str(fa) == "":
                continue
            n_annot += 1
            fa = str(fa)
            fam_seen.setdefault(fa, []).append(i)
            # store row block reference lazily later

    # second pass: emit capped rows (reservoir-free: count then slice)
    # (kept simple: re-stream and emit rows whose per-family running
    #  index < cap; deterministic under fixed row order)
    emitted = 0
    fam_emitted: dict[str, int] = {}
    for rb in pf.iter_batches(batch_size=200_000, columns=COLS):
        d = rb.to_pydict()
        for i in range(len(d["split_membership"])):
            if d["split_membership"][i] != "train":
                continue
            fa = d["family_annotation"][i]
            if not fa or str(fa) == "":
                continue
            fa = str(fa)
            c = fam_emitted.get(fa, 0)
            if c >= cap:
                continue
            fam_emitted[fa] = c + 1
            for col in COLS:
                kept_rows[col].append(d[col][i])
            emitted += 1

    n_fams = len(fam_emitted)
    nt = sum(len(s) for s in kept_rows["canonical_sequence"])
    meta = {
        "arm": "rfamcap",
        "cap_per_family": cap,
        "train_rows_total": n_train,
        "train_rows_annotated": n_annot,
        "families": n_fams,
        "rows_emitted": emitted,
        "total_nt": nt,
        "seed": SEED,
        "note": ("validate() streams the ORIGINAL split parquet "
                 "(untouched) — no rw1-style train-only validation "
                 "artifact; corpus_tag=rfamcap"),
    }
    table = pa.table({c: kept_rows[c] for c in COLS})
    pq.write_table(table, OUT_PARQUET)
    json.dump(meta, open(OUT_META, "w"), indent=1)
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
