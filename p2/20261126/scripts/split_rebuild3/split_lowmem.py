"""Streaming homology-aware splitting with the original assignment rules."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from split import _stable_accept, load_family_annotations, load_family_clan


def collect_stats(pf: pq.ParquetFile, family_annot: dict[str, str]):
    all_clusters = set()
    fam_by_cluster = {}
    family_counts = Counter()
    family_clusters = {}
    rows = 0
    for batch in pf.iter_batches(batch_size=50_000, columns=["accessions", "cluster_id"]):
        data = batch.to_pydict()
        for accessions, cluster in zip(data["accessions"], data["cluster_id"]):
            all_clusters.add(cluster)
            rep_urs = accessions.split("\t", 1)[0]
            family = family_annot.get(rep_urs)
            if family is not None:
                fam_by_cluster.setdefault(cluster, set()).add(family)
                family_counts[family] += 1
                family_clusters.setdefault(family, set()).add(cluster)
        rows += len(batch)
        if rows % 1_000_000 < 50_000:
            print(f"split stats approximately {rows:,} rows", flush=True)
    return all_clusters, fam_by_cluster, family_counts, family_clusters


def build_cluster_split(all_clusters, fam_by_cluster, family_counts, family_clusters):
    eligible = {
        family for family, count in family_counts.items()
        if count >= 100 and len(family_clusters[family]) >= 10
    }
    family_split = {
        family: _stable_accept(
            f"fam:{family}",
            [("family_test", 0.10), ("family_validation", 0.10), ("keep", 0.80)],
        )
        for family in sorted(eligible)
    }
    cluster_split = {}
    for cluster, families in fam_by_cluster.items():
        held = [
            family for family in families
            if family in family_split and family_split[family] != "keep"
        ]
        if held:
            if any(family_split[family] == "family_test" for family in held):
                cluster_split[cluster] = "family_test"
            else:
                cluster_split[cluster] = "family_validation"
    for cluster in all_clusters:
        if cluster not in cluster_split:
            cluster_split[cluster] = _stable_accept(
                f"cl:{cluster}", [("train", 0.98), ("validation", 0.01), ("test", 0.01)]
            )
    return eligible, cluster_split


def verify_cluster_split(cluster_split: dict[str, str], oracle_path: Path) -> None:
    table = pq.read_table(oracle_path, columns=["cluster_id", "split"])
    data = table.to_pydict()
    oracle = dict(zip(data["cluster_id"], data["split"]))
    if cluster_split != oracle:
        missing = set(oracle) - set(cluster_split)
        extra = set(cluster_split) - set(oracle)
        mismatches = sum(cluster_split.get(key) != value for key, value in oracle.items())
        raise ValueError(
            f"cluster split mismatch: missing={len(missing)} extra={len(extra)} mismatches={mismatches}"
        )
    print(f"cluster split exact for {len(oracle):,} clusters", flush=True)


def write_split(
    pf: pq.ParquetFile,
    out_path: Path,
    family_annot: dict[str, str],
    family_clan: dict[str, str],
    eligible: set[str],
    cluster_split: dict[str, str],
) -> Counter:
    schema = pf.schema_arrow
    schema = schema.append(pa.field("family_annotation", pa.string()))
    schema = schema.append(pa.field("split_membership", pa.string()))
    schema = schema.append(pa.field("clan_annotation", pa.string()))
    schema = schema.append(pa.field("eligible_family", pa.bool_()))
    tmp_path = Path(str(out_path) + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    counts = Counter()
    rows = 0
    with pq.ParquetWriter(tmp_path, schema, compression="snappy") as writer:
        for batch in pf.iter_batches(batch_size=50_000):
            data = batch.to_pydict()
            families = []
            splits = []
            clans = []
            eligible_flags = []
            for accessions, cluster in zip(data["accessions"], data["cluster_id"]):
                rep_urs = accessions.split("\t", 1)[0]
                family = family_annot.get(rep_urs)
                split = cluster_split[cluster]
                families.append(family)
                splits.append(split)
                clans.append(family_clan.get(family))
                eligible_flags.append(family in eligible)
                counts[split] += 1
            batch = batch.append_column("family_annotation", pa.array(families, pa.string()))
            batch = batch.append_column("split_membership", pa.array(splits, pa.string()))
            batch = batch.append_column("clan_annotation", pa.array(clans, pa.string()))
            batch = batch.append_column("eligible_family", pa.array(eligible_flags, pa.bool_()))
            writer.write_batch(batch)
            rows += len(batch)
            if rows % 1_000_000 < 50_000:
                print(f"split output approximately {rows:,} rows", flush=True)
    tmp_path.rename(out_path)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster-parquet", required=True, type=Path)
    ap.add_argument("--rfam-annotations", required=True, type=Path)
    ap.add_argument("--family-clan", type=Path, default=None)
    ap.add_argument("--cluster-split-oracle", required=True, type=Path)
    ap.add_argument("--out-parquet", required=True, type=Path)
    args = ap.parse_args()

    family_annot = load_family_annotations(args.rfam_annotations)
    family_clan = load_family_clan(args.family_clan) if args.family_clan else {}
    pf = pq.ParquetFile(args.cluster_parquet)
    all_clusters, fam_by_cluster, family_counts, family_clusters = collect_stats(pf, family_annot)
    eligible, cluster_split = build_cluster_split(
        all_clusters, fam_by_cluster, family_counts, family_clusters
    )
    verify_cluster_split(cluster_split, args.cluster_split_oracle)
    counts = write_split(
        pf, args.out_parquet, family_annot, family_clan, eligible, cluster_split
    )
    print("split counts:")
    for split, count in sorted(counts.items()):
        print(f"  {split}: {count:,}")
    print(f"wrote {args.out_parquet}")


if __name__ == "__main__":
    main()
