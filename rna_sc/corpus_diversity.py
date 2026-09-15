"""T2.3.2 Corpus diversity metrics for the S2/S3 data-size axis (H5).

Per corpus arm, pre-registered diversity metrics on rna_type composition:
  - Shannon entropy H = -sum p_i log p_i
  - Gini-Simpson D = 1 - sum p_i^2
  - Vendi index: GPU-embedded variant deferred (needs model); a CPU
    k-mer-profile analog is explicitly labelled as proxy, never reported
    as the Vendi number (preprint uses the GPU version).

Arms (sequence-set definitions, methodologically explicit):
  - full  : all train rows of release22_split_8080
  - c1M   : prefix arm - first 1M train rows in parquet order (legacy)
  - c10M  : prefix arm - first 10M train rows
  - c1Mcs / c5Mcs : cluster-stratified (whole-cluster random, seed 17)

Two levels, both reported (cluster level is the design-matched one):
  - seq-level rna_type composition (context: rRNA ~56% bias)
  - cluster-level rna_type composition (unique clusters per rna_type)

Audit columns per arm: n_seq, n_cluster, epoch-coverage @ 2.0B nt budget,
top-3 rna_type shares (red-team E rRNA-bias cross-check).
Output: analysis/corpus_diversity.md + .json
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter

import pyarrow.parquet as pq

SPLIT = ("/mnt/cunyuliu/tokenizer-benchmark/data/"
         "derived/split/release22_split_8080.parquet")
SUB = "/mnt/cunyuliu/rna-sc/data/subsamples"
OUT_DIR = "/mnt/cunyuliu/rna-sc/evidence"

ARMS = [
    ("full", None, None),
    ("c1M", 1_000_000, None),
    ("c10M", 10_000_000, None),
    ("c1Mcs", None, "c1Mcs"),
    ("c5Mcs", None, "c5Mcs"),
]

NT_BUDGET = 2_000_000_000


def entropy(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log(c / n) for c in counts.values())


def gini_simpson(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return 1.0 - sum((c / n) ** 2 for c in counts.values())


def load_allowlist(tag: str) -> set:
    ids = pq.read_table(os.path.join(SUB, tag + ".parquet"))["cluster_id"]
    return set(ids.to_pylist())


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    allowlists = {}
    for _, _, tag in ARMS:
        if tag and tag not in allowlists:
            allowlists[tag] = load_allowlist(tag)

    rows = {"per_arm": {}}
    md = ["# T2.3.2 corpus diversity metrics (S2/S3 axis, H5)", "",
          "Arms: full / c1M(prefix) / c10M(prefix) / c1Mcs / c5Mcs. "
          "Prefix arms = first-N train rows in parquet order (legacy "
          "control). cs-arms = whole-cluster random, seed 17.",
          "Levels: seq-level rna_type composition AND cluster-level "
          "rna_type composition (design-matched sampling unit).", "",
          "| arm | n_seq | n_cluster | Shannon(seq) | GS(seq) | "
          "Shannon(clu) | GS(clu) | epoch@2Bnt | top3 rna_type |",
          "|---|---|---|---|---|---|---|---|---|"]

    for arm, nseq, tag in ARMS:
        cnt_seq: Counter = Counter()
        cnt_clu: Counter = Counter()
        seen_clusters: set = set()
        n_seq = 0
        total_nt = 0
        pf = pq.ParquetFile(SPLIT)
        cols = ["split_membership", "rna_type", "cluster_id", "length"]
        for rb in pf.iter_batches(batch_size=500_000, columns=cols):
            d = rb.to_pydict()
            stop = False
            for sm, rt, cid, L in zip(d["split_membership"], d["rna_type"],
                                      d["cluster_id"], d["length"]):
                if sm != "train":
                    continue
                if tag is not None and cid not in allowlists[tag]:
                    continue
                if nseq is not None and n_seq >= nseq:
                    stop = True
                    break
                cnt_seq[rt] += 1
                if cid not in seen_clusters:
                    seen_clusters.add(cid)
                    cnt_clu[rt] += 1
                n_seq += 1
                total_nt += L
            if stop:
                break
        epoch_cov = NT_BUDGET / total_nt if total_nt else 0.0
        top3 = ", ".join("%s=%.1f%%" % (rt, 100 * c / n_seq)
                         for rt, c in cnt_seq.most_common(3))
        H_seq, GS_seq = entropy(cnt_seq), gini_simpson(cnt_seq)
        H_clu, GS_clu = entropy(cnt_clu), gini_simpson(cnt_clu)
        rows["per_arm"][arm] = {
            "n_seq": n_seq, "n_cluster": len(seen_clusters), "nt": total_nt,
            "shannon_seq": round(H_seq, 4),
            "gini_simpson_seq": round(GS_seq, 4),
            "shannon_cluster": round(H_clu, 4),
            "gini_simpson_cluster": round(GS_clu, 4),
            "epoch_coverage_2Bnt": round(epoch_cov, 2),
            "top3_rna_type": top3,
        }
        md.append("| %s | %d | %d | %.4f | %.4f | %.4f | %.4f | %.2f | %s |" % (
            arm, n_seq, len(seen_clusters), H_seq, GS_seq, H_clu, GS_clu,
            epoch_cov, top3))
        print("[diversity] %s: n_seq=%d n_cluster=%d H_seq=%.4f GS_seq=%.4f"
              % (arm, n_seq, len(seen_clusters), H_seq, GS_seq), flush=True)

    with open(os.path.join(OUT_DIR, "corpus_diversity.json"), "w") as fh:
        json.dump(rows, fh, indent=2)
    with open(os.path.join(OUT_DIR, "corpus_diversity.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("[diversity] written evidence/corpus_diversity.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
