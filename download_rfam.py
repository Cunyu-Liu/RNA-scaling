"""T4.3.5c 三库增补下载器（2026-10-08）：补齐 RiNALMo 语料的 7M 缺口。

通道探测结果（服务器实测）：
  - Rfam CURRENT fasta_files/：每家族 RFxxxxx.fa.gz 全开放（✅ 可补）
  - NCBI nt.gz：blast FASTA（60GB+ 全核酸库——含 mRNA/基因组，与 ncRNA
    语料匹配需重过滤，二期评估）
  - Ensembl fasta/：物种目录（ncrna/ 子目录）

本脚本：下载 Rfam 全家族 fasta（簇级代表序列 ~按家族），与 R22 去重后
并入 rinalmo_corpus —— Rfam 是结构性 ncRNA 注释库，与 RNAcentral 高度
互补（RNAcentral 吸收了 Rfam 序列，但版本/覆盖可能有时差）。

策略（预注册）：
  1. 拉 Rfam 家族索引（4 万+ 文件——按embl列表页抓全部 RFxxxxx.fa.gz）
  2. 解压、长度过滤 16-8192、与 R22 unique 集去重
  3. 新增序列（source=rfam）+ 现有 14.03M 合并 → v2 语料
  4. 审计更新：补齐前后序列数/簇数对照
"""
import gzip
import json
import os
import re
import subprocess
import time
import urllib.request

MNT = "/mnt/cunyuliu/rna-sc"
WORK = os.path.join(MNT, "data", "rinalmo_corpus_work")
RFAM_DIR = os.path.join(WORK, "rfam_download")
BASE = "https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/fasta_files/"
OUT_AUDIT = os.path.join(MNT, "evidence", "t435c_rfam_audit.json")


def list_families():
    html = urllib.request.urlopen(BASE, timeout=60).read().decode()
    fams = re.findall(r'href="(RF\d+\.fa\.gz)"', html)
    return fams


def download_all(fams):
    os.makedirs(RFAM_DIR, exist_ok=True)
    n_ok = n_skip = n_fail = 0
    t0 = time.time()
    for i, f in enumerate(fams):
        dst = os.path.join(RFAM_DIR, f)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            n_skip += 1
            continue
        try:
            urllib.request.urlretrieve(BASE + f, dst)
            n_ok += 1
        except Exception as e:
            n_fail += 1
            print("[rfam] FAIL %s: %s" % (f, e), flush=True)
        if (i + 1) % 200 == 0:
            print("[rfam] %d/%d ok=%d skip=%d fail=%d (%.1f min)" %
                  (i + 1, len(fams), n_ok, n_skip, n_fail,
                   (time.time() - t0) / 60), flush=True)
    return n_ok, n_skip, n_fail


def main():
    fams = list_families()
    print("[rfam] 家族文件数:", len(fams), flush=True)
    n_ok, n_skip, n_fail = download_all(fams)
    # 汇总序列统计
    n_seq = 0
    for f in os.listdir(RFAM_DIR):
        if not f.endswith(".fa.gz"):
            continue
        with gzip.open(os.path.join(RFAM_DIR, f), "rt", errors="ignore") as fh:
            n_seq += sum(1 for line in fh if line.startswith(">"))
    audit = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_family_files": len(fams),
        "downloaded": n_ok, "skipped": n_skip, "failed": n_fail,
        "total_sequences_in_rfam_fastas": n_seq,
        "note": "Rfam family-level fastas fetched; next step: len-filter, "
                "dedup vs R22 unique set, merge into corpus v2",
    }
    json.dump(audit, open(OUT_AUDIT, "w"), indent=1)
    print("[rfam] DONE: %d files, %d sequences, audit -> %s" %
          (n_ok + n_skip, n_seq, OUT_AUDIT), flush=True)


if __name__ == "__main__":
    main()
