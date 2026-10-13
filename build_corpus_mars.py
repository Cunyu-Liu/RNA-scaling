"""T4.3.7 MARS 语料臂构建（04 语料谱扩展方案）：

从 mars_ncrna_semantic30m_gzip_20261012/dataset/train 的 96 个 gzip shard
（24M 序列，sequence-only，一行一条）构建标准 schema parquet：
  canonical_sequence / split_membership=train / cluster_id / length

协议对齐 rinalmocorpus 臂（level-line 可比）：
  - len 16-8192 过滤（iter_mlm_batches 上界同池）
  - canonical 归一（T->U，只留 ACGU）
  - B1 零泄漏纪律：剔除与 split8080 held-out canonical 重叠的序列
  - cluster_id 用占位（per-seq 唯一）——该臂不需要簇级采样
    （2B 预算 = 语料的极小部分，按行序流式即可）

产物：/mnt/cunyuliu/rna-sc/data/mars_corpus.parquet
审计：evidence/t437_mars_corpus_audit.json
幂等：audit 存在即跳过。
"""
from __future__ import annotations

import gzip
import json
import os
import time

MNT = "/mnt/cunyuliu/rna-sc"
SRC_DIR = "/mnt/cunyuliu/mars_ncrna_semantic30m_gzip_20261012/dataset/train"
OUT = os.path.join(MNT, "data", "mars_corpus.parquet")
AUDIT = os.path.join(MNT, "evidence", "t437_mars_corpus_audit.json")
SPLIT_8080 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
              "release22_split_8080.parquet")
HELD = {"family_validation", "family_test", "validation", "test"}


def norm(seq: str) -> str:
    s = seq.upper().replace("T", "U").replace("X", "").strip()
    return "".join(c for c in s if c in "ACGU")


def main():
    if os.path.exists(AUDIT) and os.path.exists(OUT):
        print("already done, skip")
        return
    t0 = time.time()
    import pyarrow as pa
    import pyarrow.parquet as pq

    held = set()
    pf = pq.ParquetFile(SPLIT_8080)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=["canonical_sequence",
                                            "split_membership"])
        sm = t.column("split_membership").to_pylist()
        cs = t.column("canonical_sequence").to_pylist()
        for s, m in zip(cs, sm):
            if m in HELD:
                held.add(norm(s) if s else "")
    print("held-out pool: %d seqs (%.1f min)" %
          (len(held), (time.time() - t0) / 60), flush=True)

    shards = sorted(f for f in os.listdir(SRC_DIR) if f.endswith(".txt.gz"))
    n_total = n_kept = n_leak = n_short = 0
    w = None
    schema = pa.schema([
        ("canonical_sequence", pa.string()),
        ("split_membership", pa.string()),
        ("cluster_id", pa.string()),
        ("length", pa.string()),
        ("source", pa.string()),
    ])
    for si, sh in enumerate(shards):
        kept_s, kept_c, kept_l = [], [], []
        with gzip.open(os.path.join(SRC_DIR, sh), "rt") as fh:
            for line in fh:
                n_total += 1
                c = norm(line)
                if len(c) < 16 or len(c) > 8192:
                    n_short += 1
                    continue
                if c in held:
                    n_leak += 1
                    continue
                kept_s.append(c)
                kept_c.append("mars_%d_%d" % (si, len(kept_c)))
                kept_l.append(str(len(c)))
                n_kept += 1
        tbl = pa.table({"canonical_sequence": kept_s,
                        "split_membership": ["train"] * len(kept_s),
                        "cluster_id": kept_c, "length": kept_l,
                        "source": ["mars"] * len(kept_s)}, schema=schema)
        if w is None:
            w = pq.ParquetWriter(OUT, schema)
        w.write_table(tbl)
        if si % 16 == 0:
            print("shard %d/%d kept=%d leak=%d short=%d (%.1f min)" %
                  (si, len(shards), n_kept, n_leak, n_short,
                   (time.time() - t0) / 60), flush=True)
    if w is not None:
        w.close()
    import numpy as np
    lens = np.array([int(x) for x in kept_l[-100000:]])
    audit = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "protocol": "MARS semantic30m train shards (24M) -> norm ACGU, "
                    "len 16-8192, held-out overlap removed (B1)",
        "n_total_scanned": n_total,
        "n_kept": n_kept,
        "n_leak_removed": n_leak,
        "n_len_filtered": n_short,
        "total_nt": 0,
        "out_parquet": OUT,
    }
    nt = 0
    pf2 = pq.ParquetFile(OUT)
    for rg in range(pf2.num_row_groups):
        t = pf2.read_row_group(rg, columns=["length"])
        nt += sum(int(x) for x in t.column("length").to_pylist())
    audit["total_nt"] = nt
    json.dump(audit, open(AUDIT, "w"), indent=1)
    print("DONE: kept %d / leak %d / len-filt %d / nt %.2fB -> %s" %
          (n_kept, n_leak, n_short, nt / 1e9, OUT), flush=True)


if __name__ == "__main__":
    main()
