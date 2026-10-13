"""T4.3.7 RNAcentral 通用语料臂构建（04 语料谱方案 stage-2）：

源：/mnt/cunyuliu/rnacentral_active.fasta（32.7GB，RNAcentral active
序列，含 rRNA/miRNA/lncRNA 等全类型——"通用全 RNA"语料点）。
协议与 MARS 臂完全一致：norm ACGU、len 16-8192、B1 held-out 剔除。

目标规模（RNA-FM 参照：23.7M 序列 100% CD-HIT 去重后的通用语料）：
为控制构建时间与磁盘，抽前 ~36M 行构建（覆盖 RNA-FM 语料量级）。

产物：/mnt/cunyuliu/rna-sc/data/rnacentral_corpus.parquet
审计：evidence/t437_rnacentral_corpus_audit.json
"""
from __future__ import annotations

import json
import os
import time

MNT = "/mnt/cunyuliu/rna-sc"
SRC = "/mnt/cunyuliu/rnacentral_active.fasta"
OUT = os.path.join(MNT, "data", "rnacentral_corpus.parquet")
AUDIT = os.path.join(MNT, "evidence", "t437_rnacentral_corpus_audit.json")
SPLIT_8080 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
              "release22_split_8080.parquet")
HELD = {"family_validation", "family_test", "validation", "test"}
TARGET_SEQS = 36_000_000


def norm(seq: str) -> str:
    s = seq.upper().replace("T", "U").strip()
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

    schema = pa.schema([
        ("canonical_sequence", pa.string()),
        ("split_membership", pa.string()),
        ("cluster_id", pa.string()),
        ("length", pa.string()),
        ("source", pa.string()),
    ])
    n_total = n_kept = n_leak = n_short = 0
    w = None
    buf_s, buf_c, buf_l = [], [], []
    FLUSH_N = 500_000

    def flush():
        nonlocal w, buf_s, buf_c, buf_l
        if not buf_s:
            return
        tbl = pa.table({"canonical_sequence": buf_s,
                        "split_membership": ["train"] * len(buf_s),
                        "cluster_id": buf_c, "length": buf_l,
                        "source": ["rnacentral_active"] * len(buf_s)},
                       schema=schema)
        if w is None:
            w = pq.ParquetWriter(OUT, schema)
        w.write_table(tbl)
        buf_s, buf_c, buf_l = [], [], []

    seq = []
    with open(SRC, "r") as fh:
        for line in fh:
            if line.startswith(">"):
                if seq:
                    c = norm("".join(seq))
                    n_total += 1
                    if len(c) < 16 or len(c) > 8192:
                        n_short += 1
                    elif c in held:
                        n_leak += 1
                    else:
                        buf_s.append(c)
                        buf_c.append("rc_%d" % n_kept)
                        buf_l.append(str(len(c)))
                        n_kept += 1
                    seq = []
                    if len(buf_s) >= FLUSH_N:
                        flush()
                    if n_total >= TARGET_SEQS:
                        break
            else:
                seq.append(line.strip())
    if seq:
        c = norm("".join(seq))
        n_total += 1
        if len(c) < 16 or len(c) > 8192:
            n_short += 1
        elif c not in held:
            buf_s.append(c)
            buf_c.append("rc_%d" % n_kept)
            buf_l.append(str(len(c)))
            n_kept += 1
    flush()
    if w is not None:
        w.close()

    nt = 0
    pf2 = pq.ParquetFile(OUT)
    for rg in range(pf2.num_row_groups):
        t = pf2.read_row_group(rg, columns=["length"])
        nt += sum(int(x) for x in t.column("length").to_pylist())
    audit = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "protocol": "rnacentral_active.fasta head-scan (target %dM seqs) "
                    "-> norm ACGU, len 16-8192, held-out removed (B1)"
                    % (TARGET_SEQS // 1_000_000),
        "n_total_scanned": n_total,
        "n_kept": n_kept,
        "n_leak_removed": n_leak,
        "n_len_filtered": n_short,
        "total_nt": nt,
        "out_parquet": OUT,
    }
    json.dump(audit, open(AUDIT, "w"), indent=1)
    print("DONE: kept %d / leak %d / len-filt %d / nt %.2fB -> %s" %
          (n_kept, n_leak, n_short, nt / 1e9, OUT), flush=True)


if __name__ == "__main__":
    main()
