"""Phase 1: MMseqs2 homology clustering (80/80 and 90/90 sensitivity).

Wraps `mmseqs easy-cluster` on the deduplicated canonical nucleotide sequences.
Clustering is a CPU task (allowed). Cluster membership is written back per
canonical sequence for split stratification.

Note: MMseqs clustering of nucleotide sequences is run in nucleotide mode so
that identity and coverage are computed on the nucleotide alignment.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from array import array
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def write_fasta(pf: pq.ParquetFile, path: Path) -> int:
    rows = 0
    with open(path, "w") as handle:
        for batch in pf.iter_batches(batch_size=50_000, columns=["canonical_sequence"]):
            for sequence in batch.column(0).to_pylist():
                handle.write(f">{rows}\n{sequence}\n")
                rows += 1
            if rows % 1_000_000 < 50_000:
                print(f"FASTA approximately {rows:,} rows", flush=True)
    if rows != pf.metadata.num_rows:
        raise ValueError(f"FASTA rows {rows} != parquet rows {pf.metadata.num_rows}")
    return rows


def count_fasta_headers(path: Path) -> int:
    rows = 0
    with open(path) as handle:
        for line in handle:
            rows += int(line.startswith(">"))
    return rows


def run_mmseqs_cluster(
    fasta: Path,
    out_prefix: Path,
    min_seq_id: float,
    coverage: float,
    cov_mode: int = 1,
    threads: int = 32,
    tmp_dir: Path = Path("/mnt/cunyuliu/tokenizer-benchmark/tmp"),
    split_memory_limit: str = "16G",
) -> Path:
    cmd = [
        "mmseqs", "easy-cluster",
        str(fasta),
        str(out_prefix),
        str(tmp_dir / "mmseqs_easy_tmp"),
        "--min-seq-id", str(min_seq_id),
        "-c", str(coverage),
        "--cov-mode", str(cov_mode),
        "--threads", str(threads),
        "--split-memory-limit", split_memory_limit,
    ]
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    return Path(str(out_prefix) + "_cluster.tsv")


def read_cluster_assignments(tsv: Path, n_sequences: int) -> array:
    member_to_rep = array("I", range(n_sequences))
    with open(tsv) as handle:
        for line in handle:
            fields = line.strip().split()
            if len(fields) < 2:
                continue
            rep, member = int(fields[0]), int(fields[1])
            member_to_rep[member] = rep
    return member_to_rep


def write_cluster_parquet(
    pf: pq.ParquetFile,
    member_to_rep: array,
    out_path: Path,
) -> int:
    schema = pf.schema_arrow.append(pa.field("cluster_id", pa.string()))
    tmp_path = Path(str(out_path) + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    rows = 0
    with pq.ParquetWriter(tmp_path, schema, compression="snappy") as writer:
        for batch in pf.iter_batches(batch_size=50_000):
            size = len(batch)
            cluster_ids = pa.array([str(rep) for rep in member_to_rep[rows:rows + size]])
            out_batch = batch.append_column("cluster_id", cluster_ids)
            writer.write_batch(out_batch)
            rows += size
    tmp_path.rename(out_path)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dedup-parquet", required=True, type=Path)
    ap.add_argument("--out-cluster-parquet", required=True, type=Path)
    ap.add_argument("--out-fasta", required=True, type=Path)
    ap.add_argument("--min-seq-id", type=float, default=0.8)
    ap.add_argument("--coverage", type=float, default=0.8)
    ap.add_argument("--cov-mode", type=int, default=1)
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--tmp-dir", type=Path, default=Path("/mnt/cunyuliu/tokenizer-benchmark/tmp"))
    ap.add_argument("--split-memory-limit", default="16G")
    ap.add_argument("--keep-cluster-files", action="store_true")
    args = ap.parse_args()

    pf = pq.ParquetFile(args.dedup_parquet)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    fasta = args.tmp_dir / "seqs.fa"
    tsv = args.tmp_dir / "cluster_cluster.tsv"
    if tsv.exists():
        print(f"reuse completed cluster TSV {tsv}", flush=True)
    else:
        if fasta.exists():
            rows = count_fasta_headers(fasta)
            if rows != pf.metadata.num_rows:
                raise ValueError(f"Existing FASTA rows {rows} != parquet rows {pf.metadata.num_rows}")
            print(f"reuse complete FASTA {fasta}", flush=True)
        else:
            write_fasta(pf, fasta)
        tsv = run_mmseqs_cluster(
            fasta, args.tmp_dir / "cluster", args.min_seq_id, args.coverage,
            args.cov_mode, args.threads, args.tmp_dir, args.split_memory_limit
        )
    member_to_rep = read_cluster_assignments(tsv, pf.metadata.num_rows)
    args.out_cluster_parquet.parent.mkdir(parents=True, exist_ok=True)
    rows = write_cluster_parquet(pf, member_to_rep, args.out_cluster_parquet)
    n_clusters = len(set(member_to_rep))
    print(f"sequences={rows:,} clusters={n_clusters:,}")
    print(f"wrote {args.out_cluster_parquet}")
    if args.keep_cluster_files:
        args.out_fasta.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fasta, args.out_fasta)
        shutil.copy(tsv, Path(str(args.out_fasta) + ".tsv"))


if __name__ == "__main__":
    main()
