"""S12 stage 2: cmscan per-family CM scores -> decoupling index (H6).

For each family in the identity table (sampled members), scan members against
Rfam.cm with cmscan and record the best-scoring hit bit-score per sequence
(that's the family's CM self-consistency). Decoupling index per family:

    DI = mean_pairwise_identity / (mean_cm_bit_score / max_family_bit_score)

High DI = low sequence identity despite high CM match (structure-conserved,
sequence-divergent) -> H6 predicts later/worse contact emergence.

cmscan of ~2000 families x 40 seqs against the FULL Rfam DB is far too slow;
instead we extract the family's OWN CM from Rfam.cm (by family name) and
score just that CM against the sampled members using cmsearch (1 CM vs ~40
seqs — minutes total for a subsample of families).

v1 scope: top-300 families by member count (statistically the ones that
matter for emergence analysis), 20 seqs each.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import pyarrow.parquet as pq

SPLIT = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
RFAM_CM = "/mnt/cunyuliu/rna-sc/data/Rfam.cm"
IDENT = "/mnt/cunyuliu/rna-sc/evidence/s12_family_identity.json"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s12_decoupling_index.json"
WORK = "/mnt/cunyuliu/rna-sc/data/s12_work"

CMS = "/home/cunyuliu/miniconda3/envs/infernal/bin/cmsearch"
CMSCAN = "/home/cunyuliu/miniconda3/envs/infernal/bin/cmscan"

N_FAMILIES = 300
SAMPLE_PER_FAMILY = 20


def extract_family_cm(fam: str) -> str | None:
    """Pull the single family's CM block out of Rfam.cm (INFERNAL format:
    blocks start 'INFERNAL' and carry ACC line with family accession)."""
    # family names in release22 may be accessions like RF00001 or names;
    # Rfam.cm ACC lines use accessions (RFxxxxx). Try both.
    pass


def main():
    ap = argparse.ArgumentParser()
    args = ap.parse_args()
    with open(IDENT) as fh:
        ident = json.load(fh)
    fams = list(ident["families"].items())[:N_FAMILIES]
    os.makedirs(WORK, exist_ok=True)

    # 1) stream sampled sequences per family (first N hits in file order)
    import collections
    want = {fam: SAMPLE_PER_FAMILY for fam, _ in fams}
    fam_seqs = collections.defaultdict(list)
    for rb in pq.ParquetFile(SPLIT).iter_batches(
            batch_size=200_000,
            columns=["family_annotation", "canonical_sequence"]):
        d = rb.to_pydict()
        for fam, seq in zip(d["family_annotation"], d["canonical_sequence"]):
            if fam in want and len(fam_seqs[fam]) < want[fam]:
                fam_seqs[fam].append(seq[:400])
        if sum(len(v) for v in fam_seqs.values()) >= \
                N_FAMILIES * SAMPLE_PER_FAMILY * 0.9:
            break

    # 2) write one combined FASTA with family tags
    fasta = os.path.join(WORK, "families.fa")
    with open(fasta, "w") as fh:
        for fam, seqs in fam_seqs.items():
            for i, s in enumerate(seqs):
                fh.write(">%s_%d\n%s\n" % (fam.replace(" ", "_"), i, s))

    # 3) cmscan: sequences vs full Rfam DB (pressed) — top hit per sequence
    tbl = os.path.join(WORK, "cmscan.tbl")
    cmd = [CMSCAN, "--tblout", tbl, "--nohmmonly", "-Z", "2.0",
           "--cut_ga", RFAM_CM, fasta]
    print("[cmscan] running %d seqs vs Rfam.cm ..." % sum(
        len(v) for v in fam_seqs.values()), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if not os.path.exists(tbl):
        print(r.stderr[-2000:])
        sys.exit(1)

    # 4) parse best hit per sequence; aggregate per family
    best = {}
    with open(tbl) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 16:
                continue
            target, _, _, _, _, score = parts[0], parts[2], parts[3], \
                parts[4], parts[5], None
            # cols: target name, accession, query name, ... (cmscan tbl:
            # target=seq, query=CM) score col index 14
            seqname = parts[0]
            famname = parts[2]
            bits = float(parts[14])
            if seqname not in best or bits > best[seqname][1]:
                best[seqname] = (famname, bits)

    per_fam = collections.defaultdict(list)
    for seqname, (famname, bits) in best.items():
        per_fam[seqname.rsplit("_", 1)[0]].append(bits)

    rows = {}
    for fam, meta in fams:
        bits = per_fam.get(fam.replace(" ", "_"), [])
        if not bits:
            continue
        rows[fam] = {
            **meta,
            "n_seq_hit": len(bits),
            "mean_cm_bits": round(sum(bits) / len(bits), 2),
            "mean_cm_bits_max": round(max(bits), 2),
        }
    # decoupling index: identity / normalized CM score
    max_bits = max((r["mean_cm_bits"] for r in rows.values()), default=1.0)
    for fam, r in rows.items():
        norm_cm = r["mean_cm_bits"] / max_bits
        r["decoupling_index"] = round(
            r["mean_pairwise_identity"] / max(1e-6, norm_cm), 4)

    with open(OUT, "w") as fh:
        json.dump({"generated": __import__("datetime").datetime.utcnow()
                   .isoformat() + "Z", "n_families": len(rows),
                   "method": "identity/(cmscan mean bits normalized); "
                             "top-%d fams x %d seqs" % (N_FAMILIES,
                                                         SAMPLE_PER_FAMILY),
                   "families": rows}, fh, indent=2)
    top = sorted(rows.items(), key=lambda kv: -kv[1]["decoupling_index"])[:10]
    print("[S12] done: %d families. Top-10 decoupled:" % len(rows))
    for fam, r in top:
        print("  %s: DI=%.3f (id=%.3f, cm=%.1f bits)" % (
            fam, r["decoupling_index"], r["mean_pairwise_identity"],
            r["mean_cm_bits"]))


if __name__ == "__main__":
    main()
