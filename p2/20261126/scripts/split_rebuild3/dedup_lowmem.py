"""Exact hash deduplication using ordered hash-prefix partitions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from dedup import dedup


def partition_input(source: Path, partition_dir: Path, n_partitions: int) -> None:
    paths = [partition_dir / f"input_{i:02x}.parquet" for i in range(n_partitions)]
    manifest = partition_dir / "input_partitions.json"
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved["n_partitions"] != n_partitions or saved["source"] != str(source):
            raise ValueError("Existing partition manifest does not match this run")
        if all(path.stat().st_size > 0 for path in paths):
            return
        raise ValueError("Partition manifest exists but input partitions are incomplete")
    if any(path.exists() for path in paths):
        raise ValueError("Some final input partitions exist without a complete manifest")

    pf = pq.ParquetFile(source)
    hash_index = pf.schema_arrow.names.index("canonical_sequence_hash")
    tmp_paths = [Path(str(path) + ".tmp") for path in paths]
    for path in tmp_paths:
        if path.exists():
            path.unlink()
    writers = [pq.ParquetWriter(path, pf.schema_arrow, compression="snappy") for path in tmp_paths]
    rows = 0
    try:
        for batch in pf.iter_batches(batch_size=100_000):
            prefixes = pc.utf8_slice_codeunits(batch.column(hash_index), 0, 1)
            for i, writer in enumerate(writers):
                indices = pc.indices_nonzero(pc.equal(prefixes, f"{i:x}"))
                if len(indices):
                    writer.write_batch(batch.take(indices))
            rows += len(batch)
            if rows % 1_000_000 < 100_000:
                print(f"partitioned approximately {rows:,} rows", flush=True)
    finally:
        for writer in writers:
            writer.close()
    for tmp_path, path in zip(tmp_paths, paths):
        tmp_path.rename(path)
    manifest.write_text(json.dumps({
        "source": str(source),
        "source_rows": rows,
        "n_partitions": n_partitions,
    }, indent=2, sort_keys=True) + "\n")
    print(f"partitioned {rows:,} rows into {n_partitions} files", flush=True)


def combine_parts(parts: list[Path], out_path: Path) -> int:
    tmp_path = Path(str(out_path) + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    writer = None
    rows = 0
    previous_hash = None
    try:
        for part in parts:
            pf = pq.ParquetFile(part)
            if writer is None:
                writer = pq.ParquetWriter(tmp_path, pf.schema_arrow, compression="snappy")
            for batch in pf.iter_batches(batch_size=100_000):
                hashes = batch.column(batch.schema.names.index("canonical_sequence_hash")).to_pylist()
                if hashes and previous_hash is not None and hashes[0] < previous_hash:
                    raise ValueError(f"Hash order violation at partition {part}")
                if any(right < left for left, right in zip(hashes, hashes[1:])):
                    raise ValueError(f"Hash order violation inside partition {part}")
                previous_hash = hashes[-1] if hashes else previous_hash
                writer.write_batch(batch)
                rows += len(batch)
    finally:
        if writer is not None:
            writer.close()
    tmp_path.rename(out_path)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-parquet", required=True, type=Path)
    ap.add_argument("--out-parquet", required=True, type=Path)
    ap.add_argument("--work-dir", required=True, type=Path)
    ap.add_argument("--n-partitions", type=int, default=16)
    args = ap.parse_args()
    if args.n_partitions != 16:
        raise ValueError("This implementation uses the 16 one-digit hexadecimal hash prefixes")

    args.work_dir.mkdir(parents=True, exist_ok=True)
    partition_input(args.canonical_parquet, args.work_dir, args.n_partitions)
    parts = []
    for i in range(args.n_partitions):
        source = args.work_dir / f"input_{i:02x}.parquet"
        part = args.work_dir / f"dedup_{i:02x}.parquet"
        if not part.exists():
            tmp_part = Path(str(part) + ".tmp")
            if tmp_part.exists():
                tmp_part.unlink()
            df = pl.read_parquet(source)
            result = dedup(df)
            result.write_parquet(tmp_part)
            tmp_part.rename(part)
            print(f"dedup partition {i:02x}: input={len(df):,} unique={len(result):,}", flush=True)
            del df, result
        parts.append(part)

    rows = combine_parts(parts, args.out_parquet)
    print(f"unique_canonical={rows:,}")
    print(f"wrote {args.out_parquet}")
    if rows != 29_012_227:
        raise SystemExit(f"Expected 29,012,227 unique rows, observed {rows:,}")


if __name__ == "__main__":
    main()
