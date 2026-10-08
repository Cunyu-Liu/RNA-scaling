"""T4.3.5 RiNALMo 语料复刻臂（官方语料配方 × 自训架构）——CPU 侧语料构建。

完全复刻 RiNALMo 论文 Methods 4.3 配方：
  源库：RNAcentral（本地 R22 29M 行 = 主库）+ Rfam/nt/Ensembl fasta（有缓存则并入）
  过滤：长度 16-8192；去重（canonical hash）
  聚类：mmseqs easy-linclust --min-seq-id 0.7 -c 0.8（论文 36M → 17M 簇）
  追加（B1 零泄漏纪律）：剔除与 split8080 held-out
  （family_validation/family_test/validation/test）canonical 重叠的序列

产物：/mnt/cunyuliu/rna-sc/data/rinalmo_corpus_v1.parquet
      （列：seq, cluster_id, seq_len, source）
审计：evidence/t435_corpus_audit.json（对照论文口径）
分阶段幂等（.done 标记）；CPU 任务不占 GPU。
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import time

MNT = "/mnt/cunyuliu/rna-sc"
DATA = os.path.join(MNT, "data")
WORK = os.path.join(DATA, "rinalmo_corpus_work")
EVID = os.path.join(MNT, "evidence")
SPLIT_8080 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
              "release22_split_8080.parquet")
OUT_PARQUET = os.path.join(DATA, "rinalmo_corpus_v1.parquet")
OUT_AUDIT = os.path.join(EVID, "t435_corpus_audit.json")
MMSEQS = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/mmseqs"
PYENV = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
HELD_SPLITS = {"family_validation", "family_test", "validation", "test"}


def _done(stage):
    return os.path.exists(os.path.join(WORK, stage + ".done"))


def _mark(stage, note=""):
    with open(os.path.join(WORK, stage + ".done"), "w") as fh:
        fh.write("%s %s\n" % (time.strftime("%F %T"), note))


def _norm(seq: str) -> str:
    s = seq.upper().replace("T", "U")
    return "".join(c for c in s if c in "ACGU")


def stage_extract():
    import pyarrow.parquet as pq
    os.makedirs(WORK, exist_ok=True)
    out_fasta = os.path.join(WORK, "all_raw.fasta")
    n_rows, n_ext = 0, 0
    sources = {"r22": 0}
    with open(out_fasta, "w") as out:
        pf = pq.ParquetFile(SPLIT_8080)
        for rg in range(pf.num_row_groups):
            t = pf.read_row_group(rg, columns=["canonical_sequence",
                                                "split_membership"])
            for i in range(t.num_rows):
                s = _norm(t.column("canonical_sequence")[i].as_py() or "")
                if not (16 <= len(s) <= 8192):
                    continue
                out.write(">r%06d\n%s\n" % (n_rows, s))
                n_rows += 1
                sources["r22"] += 1
        for pattern, tag in [(os.path.join(DATA, "rfam_seq*.fasta"), "rfam"),
                             (os.path.join(DATA, "nt_seq*.fasta"), "nt"),
                             (os.path.join(DATA, "ensembl*.fasta"), "ensembl")]:
            for f in glob.glob(pattern):
                seq, hdr = [], ""
                with open(f) as fh:
                    for line in fh:
                        if line.startswith(">"):
                            if seq:
                                s = _norm("".join(seq))
                                if 16 <= len(s) <= 8192:
                                    out.write(">e%d_%06d\n%s\n" % (n_ext, n_rows, s))
                                    n_rows += 1
                                    n_ext += 1
                                    sources[tag] = sources.get(tag, 0) + 1
                            hdr, seq = line[1:].strip(), []
                        else:
                            seq.append(line.strip())
                if seq:
                    s = _norm("".join(seq))
                    if 16 <= len(s) <= 8192:
                        out.write(">e%d_%06d\n%s\n" % (n_ext, n_rows, s))
                        n_rows += 1
                        n_ext += 1
                        sources[tag] = sources.get(tag, 0) + 1
    _mark("extract", json.dumps({"rows": n_rows, "sources": sources}))
    print("[t435] extract done:", n_rows, sources, flush=True)


def stage_rmdup():
    """去重：canonical 序列 set（Python 内存法，29M 短序列可行）。"""
    seen = set()
    raw = os.path.join(WORK, "all_raw.fasta")
    out = os.path.join(WORK, "all_uniq.fasta")
    n_in = n_out = 0
    with open(raw) as fh, open(out, "w") as fo:
        hdr, seq = None, []
        for line in fh:
            if line.startswith(">"):
                if hdr is not None:
                    n_in += 1
                    s = "".join(seq)
                    if s not in seen:
                        seen.add(s)
                        n_out += 1
                        fo.write("%s\n%s\n" % (hdr, s))
                hdr, seq = line.strip(), []
            else:
                seq.append(line.strip())
        if hdr is not None:
            n_in += 1
            s = "".join(seq)
            if s not in seen:
                seen.add(s)
                n_out += 1
                fo.write("%s\n%s\n" % (hdr, s))
    _mark("rmdup", json.dumps({"in": n_in, "unique": n_out}))
    print("[t435] rmdup done: %d -> %d" % (n_in, n_out), flush=True)


def stage_cluster():
    uniq = os.path.join(WORK, "all_uniq.fasta")
    cov = os.path.join(WORK, "mmseqs_out")
    nproc = str(min(os.cpu_count() or 8, 48))
    subprocess.run([MMSEQS, "easy-linclust", uniq, cov,
                    os.path.join(WORK, "tmp"), "--min-seq-id", "0.7",
                    "-c", "0.8", "--threads", nproc], check=True)
    _mark("cluster")
    print("[t435] cluster done", flush=True)


def stage_dedup_eval():
    """B1 零泄漏：剔 held-out canonical 重叠（含反向互补规范式）。"""
    import pyarrow.parquet as pq

    comp = str.maketrans("ACGU", "UGCA")

    def canon(s):
        s = _norm(s)
        rc = s[::-1].translate(comp)
        return min(s, rc) if s else s

    held = set()
    pf = pq.ParquetFile(SPLIT_8080)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=["canonical_sequence",
                                            "split_membership"])
        sp = t.column("split_membership").to_pylist()
        sq = t.column("canonical_sequence").to_pylist()
        for s, m in zip(sq, sp):
            if m in HELD_SPLITS:
                held.add(canon(s or ""))
    print("[t435] held-out canon hashes:", len(held), flush=True)

    # id->seq 索引（unique fasta）
    idx = {}
    cur, seq = None, []
    with open(os.path.join(WORK, "all_uniq.fasta")) as fh:
        for line in fh:
            if line.startswith(">"):
                if cur is not None:
                    idx[cur] = "".join(seq)
                cur, seq = line.strip()[1:], []
            else:
                seq.append(line.strip())
        if cur is not None:
            idx[cur] = "".join(seq)

    tsv = os.path.join(WORK, "mmseqs_out_cluster.tsv")
    out_tsv = os.path.join(WORK, "clusters_dedup.tsv")
    n_total = n_removed = 0
    with open(tsv) as fh, open(out_tsv, "w") as fo:
        for line in fh:
            rep, member = line.split("\t")[:2]
            n_total += 1
            s = idx.get(member, "")
            if s and canon(s) in held:
                n_removed += 1
                continue
            fo.write(line)
    _mark("dedup_eval", json.dumps({"removed": n_removed,
                                    "kept": n_total - n_removed}))
    print("[t435] dedup_eval: removed %d / %d" % (n_removed, n_total), flush=True)


def stage_parquet():
    import pyarrow as pa
    import pyarrow.parquet as pq
    import numpy as np

    idx = {}
    cur, seq = None, []
    with open(os.path.join(WORK, "all_uniq.fasta")) as fh:
        for line in fh:
            if line.startswith(">"):
                if cur is not None:
                    idx[cur] = "".join(seq)
                cur, seq = line.strip()[1:], []
            else:
                seq.append(line.strip())
        if cur is not None:
            idx[cur] = "".join(seq)

    seqs, clusters, lens, srcs = [], [], [], []
    n_clusters = set()
    with open(os.path.join(WORK, "clusters_dedup.tsv")) as fh:
        for line in fh:
            rep, member = line.split("\t")[:2]
            s = idx.get(member, "")
            if not s:
                continue
            seqs.append(s)
            clusters.append(rep)
            lens.append(len(s))
            srcs.append("r22" if member.startswith("r") else "ext")
            n_clusters.add(rep)
    tbl = pa.table({"seq": seqs, "cluster_id": clusters,
                    "seq_len": lens, "source": srcs})
    pq.write_table(tbl, OUT_PARQUET)
    audit = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "protocol": "RiNALMo Methods 4.3 replica: RNAcentral R22 + ext fasta "
                    "(if cached), len 16-8192, dedup, mmseqs easy-linclust "
                    "0.7/0.8, held-out overlap removed (B1)",
        "n_sequences": len(seqs),
        "n_clusters": len(n_clusters),
        "paper_reference": {"RiNALMo": "36M seqs / 17M clusters"},
        "len_dist": {"p5": float(np.percentile(lens, 5)),
                     "p50": float(np.percentile(lens, 50)),
                     "p95": float(np.percentile(lens, 95))},
        "total_nt": int(sum(lens)),
        "out_parquet": OUT_PARQUET,
    }
    json.dump(audit, open(OUT_AUDIT, "w"), indent=1)
    _mark("parquet", json.dumps({"seqs": len(seqs),
                                 "clusters": len(n_clusters)}))
    print("[t435] parquet done: %d seqs / %d clusters -> %s" %
          (len(seqs), len(n_clusters), OUT_PARQUET), flush=True)


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(EVID, exist_ok=True)
    t0 = time.time()
    for stage, fn in [("extract", stage_extract), ("rmdup", stage_rmdup),
                      ("cluster", stage_cluster),
                      ("dedup_eval", stage_dedup_eval),
                      ("parquet", stage_parquet)]:
        if _done(stage):
            print("[t435] skip done:", stage)
            continue
        print("[t435] STAGE:", stage, flush=True)
        fn()
    print("[t435] ALL DONE %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
