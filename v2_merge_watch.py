"""T4.3.5c 语料 v2 合并 watcher（2026-10-08）：

Rfam 家族 fasta 下载完成（4227 文件 + audit JSON 落盘）后自动：
  1. 解析全部 RFxxxxx.fa.gz：长度 16-8192 过滤、canonical 清洗
  2. 与 v1 语料 unique 集去重（新增序列才保留）
  3. B1 纪律：剔除与 held-out canonical 重叠的序列
  4. 合并写 rinalmo_corpus_v2.parquet（v1 序列 + source=rfam 新增）
  5. 更新审计 JSON（v1 vs v2 对照）
输出 v2 后提示（日志）：由人工决策是否重训语料臂（v2 与 v1 差异审计后）。
幂等：v2.parquet 存在即退出。
"""
import gzip
import json
import os
import time

MNT = "/mnt/cunyuliu/rna-sc"
WORK = os.path.join(MNT, "data", "rinalmo_corpus_work")
RFAM_DIR = os.path.join(WORK, "rfam_download")
V1 = os.path.join(MNT, "data", "rinalmo_corpus_v1.parquet")
V2 = os.path.join(MNT, "data", "rinalmo_corpus_v2.parquet")
SPLIT_8080 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
              "release22_split_8080.parquet")
AUDIT_V2 = os.path.join(MNT, "evidence", "t435c_corpus_v2_audit.json")
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"

HELD_SPLITS = {"family_validation", "family_test", "validation", "test"}


def _norm(s):
    s = (s or "").upper().replace("T", "U")
    return "".join(c for c in s if c in "ACGU")


def _canon(s):
    s = _norm(s)
    rc = s[::-1].translate(str.maketrans("ACGU", "UGCA"))
    return min(s, rc) if s else s


def rfam_done():
    a = os.path.join(MNT, "evidence", "t435c_rfam_audit.json")
    return os.path.exists(a)


def main():
    print("[v2-watch] waiting for rfam download...", flush=True)
    while not rfam_done():
        time.sleep(300)
    if os.path.exists(V2):
        print("[v2-watch] v2 exists, exit", flush=True)
        return

    import pyarrow as pa
    import pyarrow.parquet as pq

    t0 = time.time()
    # 1) v1 unique 集
    v1_canon = set()
    pf = pq.ParquetFile(V1)
    v1_rows = []
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg)
        for seq, cl, ln, src in zip(t.column("canonical_sequence").to_pylist(),
                                    t.column("cluster_id").to_pylist(),
                                    t.column("length").to_pylist(),
                                    t.column("source").to_pylist()):
            v1_rows.append((seq, cl, int(ln), src))
            v1_canon.add(_canon(seq))
    print("[v2-watch] v1: %d rows, unique canon %d" % (len(v1_rows),
                                                       len(v1_canon)), flush=True)

    # 2) held-out 集
    held = set()
    pfs = pq.ParquetFile(SPLIT_8080)
    for rg in range(pfs.num_row_groups):
        t = pfs.read_row_group(rg, columns=["canonical_sequence",
                                            "split_membership"])
        for s, m in zip(t.column("canonical_sequence").to_pylist(),
                        t.column("split_membership").to_pylist()):
            if m in HELD_SPLITS:
                held.add(_canon(s))
    print("[v2-watch] held-out canon: %d" % len(held), flush=True)

    # 3) Rfam 新增
    n_rfam_raw = n_new = n_held_removed = 0
    new_rows = []
    for f in sorted(os.listdir(RFAM_DIR)):
        if not f.endswith(".fa.gz"):
            continue
        fam = f.replace(".fa.gz", "")
        seq, hdr = [], None
        with gzip.open(os.path.join(RFAM_DIR, f), "rt", errors="ignore") as fh:
            for line in fh:
                if line.startswith(">"):
                    if seq:
                        s = _norm("".join(seq))
                        n_rfam_raw += 1
                        if 16 <= len(s) <= 8192:
                            c = _canon(s)
                            if c in held:
                                n_held_removed += 1
                            elif c not in v1_canon:
                                v1_canon.add(c)
                                new_rows.append((s, fam, len(s), "rfam"))
                                n_new += 1
                    hdr, seq = line[1:].strip(), []
                else:
                    seq.append(line.strip())
            if seq:
                s = _norm("".join(seq))
                n_rfam_raw += 1
                if 16 <= len(s) <= 8192:
                    c = _canon(s)
                    if c in held:
                        n_held_removed += 1
                    elif c not in v1_canon:
                        v1_canon.add(c)
                        new_rows.append((s, fam, len(s), "rfam"))
                        n_new += 1
    print("[v2-watch] rfam: %d raw -> new %d (held-removed %d)" %
          (n_rfam_raw, n_new, n_held_removed), flush=True)

    # 4) 合并写 v2
    all_rows = v1_rows + new_rows
    tbl = pa.table({
        "canonical_sequence": [r[0] for r in all_rows],
        "split_membership": ["train"] * len(all_rows),
        "cluster_id": [r[1] for r in all_rows],
        "length": [str(r[2]) for r in all_rows],
        "source": [r[3] for r in all_rows],
    })
    pq.write_table(tbl, V2)
    audit = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "v1_sequences": len(v1_rows),
        "rfam_raw_sequences": n_rfam_raw,
        "rfam_new_unique_after_dedup_and_b1": n_new,
        "held_removed": n_held_removed,
        "v2_sequences": len(all_rows),
        "v2_total_nt": int(sum(r[2] for r in all_rows)),
        "note": "v2 = v1 + Rfam family fastas (deduped vs v1 + B1 "
                "held-out removal). Decision on retraining corpus arms "
                "pending this audit (if rfam_new < 100k, marginal).",
        "out_parquet": V2,
    }
    json.dump(audit, open(AUDIT_V2, "w"), indent=1)
    print("[v2-watch] DONE: v2 = %d seqs (%d rfam added) in %.1f min -> %s" %
          (len(all_rows), n_new, (time.time() - t0) / 60, V2), flush=True)


if __name__ == "__main__":
    main()
