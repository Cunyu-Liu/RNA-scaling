"""MLM batch streaming over the frozen release22 split (zero-copy, nt-budgeted).

- Streams split parquet via pyarrow row groups (29M rows never materialized).
- MLM 15% masking (80/10/10) drawn per-sequence deterministically (zlib CRC32
  sequence id + global seed) so every run/epoch sees identical masks.
- Exposure counted in valid (non-pad) nt, exactly the TokBench nt convention.
- Long sequences are chunked into non-overlapping context windows (training
  windows; no overlap double counting).
"""
from __future__ import annotations

import random
import zlib

import pyarrow.parquet as pq

ALPHABET = "ACGU"
IGNORE = -100
PAD_ID, MASK_ID, CLS_ID = 4, 5, 6


def _canon(s: str) -> str:
    s = s.upper().replace("T", "U")
    return s


def _encode(seq: str) -> list[int]:
    return [ALPHABET.index(b) for b in seq]


def _seq_id(canon: str) -> int:
    return zlib.crc32(canon.encode("utf-8"))


def _apply_mlm(ids, seed: int):
    """Deterministic 80/10/10 masking. Returns (inputs, targets)."""
    rng = random.Random(seed)
    T = len(ids)
    n_mask = max(1, int(round(0.15 * T)))
    idx = list(range(T))
    rng.shuffle(idx)
    sel = sorted(idx[:n_mask])
    inputs = list(ids)
    targets = [IGNORE] * T
    for rank, i in enumerate(sel):
        targets[i] = ids[i]
        r = rng.random()
        if r < 0.8:
            inputs[i] = MASK_ID
        elif r < 0.9:
            inputs[i] = rng.randrange(4)
        # else keep original
    return inputs, targets


def iter_mlm_batches(path: str, split: str, seed: int, context_nt: int,
                      batch_nt: int, corpus_nseq: int | None = None,
                      max_batches: int | None = None,
                      cluster_allowlist: set | None = None):
    """Yield dict batches: ids/targets (B, T) lists + valid-nt count.

    corpus_nseq caps the number of distinct sequences consumed from this
    split (S2 corpus-size axis, prefix variant — legacy control arm).
    cluster_allowlist (S2 cluster-stratified variant, 2026-09-15): only
    sequences whose cluster_id is in the allowlist are streamed; requires
    reading the cluster_id column.
    """
    pf = pq.ParquetFile(path)
    columns = ["split_membership", "canonical_sequence"]
    if cluster_allowlist is not None:
        columns.append("cluster_id")
    rows: list[tuple[list[int], list[int]]] = []
    cur_max = 0
    n_seq_seen = 0
    batches = 0

    def flush():
        if not rows:
            return None
        T = max(len(x[0]) for x in rows)
        ids = [r[0] + [PAD_ID] * (T - len(r[0])) for r in rows]
        tgt = [r[1] + [IGNORE] * (T - len(r[1])) for r in rows]
        valid_nt = sum(len(r[0]) for r in rows)
        return {"ids": ids, "targets": tgt, "valid_nt": valid_nt,
                "n_seq": len(rows)}

    def would_overflow(L: int) -> bool:
        if not rows:
            return False
        return (len(rows) + 1) * max(cur_max, L) > batch_nt

    for rb in pf.iter_batches(batch_size=50_000, columns=columns):
        d = rb.to_pydict()
        for i, (sm, seq) in enumerate(zip(d["split_membership"],
                                          d["canonical_sequence"])):
            if sm != split:
                continue
            if cluster_allowlist is not None and \
                    d["cluster_id"][i] not in cluster_allowlist:
                continue
            if corpus_nseq is not None and n_seq_seen >= corpus_nseq:
                break
            c = _canon(seq)
            if len(c) < 2:
                continue
            sid = _seq_id(c)
            start = 0
            while start < len(c):
                chunk = c[start:start + context_nt]
                start += len(chunk)
                ids = _encode(chunk)
                inputs, targets = _apply_mlm(ids, (sid ^ seed) & 0xFFFFFFFF)
                L = len(inputs)
                if would_overflow(L):
                    b = flush()
                    if b is not None:
                        yield b
                        batches += 1
                        if max_batches is not None and batches >= max_batches:
                            return
                    rows, cur_max = [], 0
                rows.append((inputs, targets))
                cur_max = max(cur_max, L)
            n_seq_seen += 1
        if corpus_nseq is not None and n_seq_seen >= corpus_nseq:
            break
    b = flush()
    if b is not None:
        yield b


def count_valid_nt(batch) -> int:
    return int(batch["valid_nt"])
