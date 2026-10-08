"""语料 parquet schema 适配（2026-10-08）：

iter_mlm_batches 需要 split_membership + canonical_sequence 列。
重写 rinalmo_corpus_v1.parquet 为标准 schema：
  canonical_sequence, split_membership='train', cluster_id, length
同时保存旧列为 source。幂等：schema 已对时跳过。
"""
import time

import pyarrow as pa
import pyarrow.parquet as pq

SRC = "/mnt/cunyuliu/rna-sc/data/rinalmo_corpus_v1.parquet"
TMP = SRC + ".tmp"

pf = pq.ParquetFile(SRC)
names = pf.schema_arrow.names
if "split_membership" in names:
    print("schema already compatible:", names)
    raise SystemExit(0)

t0 = time.time()
w = None
n = 0
for rg in range(pf.num_row_groups):
    t = pf.read_row_group(rg)
    seqs = t.column("seq").to_pylist()
    clusters = t.column("cluster_id").to_pylist()
    lens = t.column("seq_len").to_pylist()
    srcs = t.column("source").to_pylist() if "source" in t.column_names \
        else ["r22"] * len(seqs)
    out = pa.table({
        "canonical_sequence": seqs,
        "split_membership": ["train"] * len(seqs),
        "cluster_id": clusters,
        "length": [str(x) for x in lens],
        "source": srcs,
    })
    if w is None:
        w = pq.ParquetWriter(TMP, out.schema)
    w.write_table(out)
    n += out.num_rows
    if rg % 20 == 0:
        print("row group %d/%d, %d rows" % (rg, pf.num_row_groups, n),
              flush=True)
if w is not None:
    w.close()
import os
os.replace(TMP, SRC)
print("rewritten: %d rows in %.1f min -> %s" %
      (n, (time.time() - t0) / 60, SRC))
