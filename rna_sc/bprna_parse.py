"""T1.1.1 bpRNA dataset parser (bpseq -> parquet + family counts).

Source: /mnt/cunyuliu/BPfold_data/bpRNA (bpRNA-1M(2.0) TR0/VL0/TS0
standard splits, .bpseq format: "pos base partner_idx", partner 0 =
unpaired). Family label from filename: bpRNA_{SOURCE}_{id}.bpseq.

Outputs (acceptance: parser unit test + family count table):
  /mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet
    columns: [name, source, split, seq, pairs] where pairs is a list of
    [i, j] partner indices (1-based, i < j) — canonical pairing
    representation for downstream structure probes (S8/S13b).
  /mnt/cunyuliu/rna-sc/evidence/bpRNA_family_counts.json
    per-split x source counts + length stats.

Usage: python -m rna_sc.bprna_parse [--check-only]
"""
from __future__ import annotations

import argparse
import json
import os

import pyarrow as pa
import pyarrow.parquet as pq

SRC = "/mnt/cunyuliu/BPfold_data/bpRNA"
OUT_PARQUET = "/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/bpRNA_family_counts.json"

SPLITS = {"TR0": "train", "VL0": "validation", "TS0": "test"}
ALPHABET = "ACGU"


def parse_bpseq(path: str):
    """Parse one .bpseq -> (name, source, seq, pairs).

    Pairs are emitted once per pair (i < j). Non-ACGU bases are kept as
    lowercase canonical (N/X etc. mapped to nearest? NO — kept as-is in
    the sequence string; probing layers may mask them later). partner
    column: 0 = unpaired; a pair (i, j) appears at both i and j.
    """
    name = os.path.basename(path).replace(".bpseq", "")
    parts = name.split("_")
    source = parts[1] if len(parts) >= 3 else "UNK"
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            toks = line.split()
            if len(toks) != 3:
                continue
            try:
                pos, base, partner = int(toks[0]), toks[1], int(toks[2])
            except ValueError:
                continue
            rows.append((pos, base, partner))
    rows.sort(key=lambda r: r[0])
    if not rows:
        return name, source, "", []
    if [r[0] for r in rows] != list(range(1, len(rows) + 1)):
        # non-contiguous positions: re-index densely (keep order)
        remap = {r[0]: i + 1 for i, r in enumerate(rows)}
        rows = [(remap[r[0]], r[1], r[2] if r[2] == 0 else remap.get(
            r[2], 0)) for r in rows]
    seq = "".join(r[1] for r in rows).upper().replace("T", "U")
    partner = {r[0]: r[2] for r in rows}
    pairs = []
    for i in range(1, len(rows) + 1):
        j = partner.get(i, 0)
        if j > i:
            pairs.append([i, j])
        elif 0 < j < i:
            pass  # already emitted when visiting the smaller index
    return name, source, seq, pairs


def pair_stats(pairs):
    if not pairs:
        return {"n_pairs": 0}
    spans = [j - i for i, j in pairs]
    return {"n_pairs": len(pairs),
            "long_range_ge24": sum(1 for s in spans if s >= 24),
            "median_span": sorted(spans)[len(spans) // 2]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true",
                    help="parse only, no output writes (unit-test mode)")
    args = ap.parse_args()

    n_ok, n_bad, n_pairs_total, n_long = 0, 0, 0, 0
    table = {"rows": []}
    fam_counts = {}
    for split_dir, split_name in SPLITS.items():
        files = sorted(os.listdir(os.path.join(SRC, split_dir)))
        for f in files:
            if not f.endswith(".bpseq"):
                continue
            path = os.path.join(SRC, split_dir, f)
            try:
                name, source, seq, pairs = parse_bpseq(path)
            except Exception as e:  # noqa: BLE001
                n_bad += 1
                print("BAD %s: %s" % (f, e))
                continue
            if len(seq) < 2:
                n_bad += 1
                continue
            n_ok += 1
            n_pairs_total += len(pairs)
            st = pair_stats(pairs)
            n_long += st.get("long_range_ge24", 0)
            fam_counts.setdefault(split_name, {}).setdefault(
                source, [0, 0])
            fam_counts[split_name][source][0] += 1
            fam_counts[split_name][source][1] += len(seq)
            table["rows"].append((name, source, split_name, seq, pairs))
            if args.check_only and n_ok >= 50:
                break
        if args.check_only:
            break

    # unit-test assertions (acceptance: parser unit test)
    assert n_bad == 0, "parse failures: %d" % n_bad
    assert n_pairs_total > 0
    # sanity: every pair j > i and within length
    for name, _, _, seq, pairs in table["rows"][:200]:
        for i, j in pairs:
            assert 1 <= i < j <= len(seq), (name, i, j, len(seq))
    print("parsed OK: %d seqs, %d bad, %d pairs (%d long-range >=24nt)"
          % (n_ok, n_bad, n_pairs_total, n_long))

    if args.check_only:
        print("check-only mode: no writes")
        return 0

    os.makedirs(os.path.dirname(OUT_PARQUET), exist_ok=True)
    names = [r[0] for r in table["rows"]]
    sources = [r[1] for r in table["rows"]]
    splits = [r[2] for r in table["rows"]]
    seqs = [r[3] for r in table["rows"]]
    pairs_col = [r[4] for r in table["rows"]]
    tab = pa.table({
        "name": pa.array(names, pa.string()),
        "source": pa.array(sources, pa.string()),
        "split": pa.array(splits, pa.string()),
        "seq": pa.array(seqs, pa.string()),
        "pairs": pa.array(pairs_col, pa.list_(pa.list_(pa.int32()))),
    })
    pq.write_table(tab, OUT_PARQUET)
    print("wrote", OUT_PARQUET, tab.num_rows, "rows")

    counts = {}
    for split_name, srcs in fam_counts.items():
        counts[split_name] = {
            s: {"n_seq": v[0],
                "mean_len": round(v[1] / v[0], 1)}
            for s, v in srcs.items()}
    out = {"n_seq_total": n_ok, "n_pairs_total": n_pairs_total,
           "n_long_range_pairs": n_long,
           "families_by_split": counts,
           "split_sizes": {k: sum(v["n_seq"] for v in c.values())
                           for k, c in counts.items()}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote", OUT_JSON)
    print(json.dumps(out["split_sizes"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
