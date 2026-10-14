"""T4.3.7 语料谱扩展 GPU watcher v5（2026-10-14 稳定版）：

臂队列（语料就绪即发，有卡即上）：
  1) RNA-Sc-100M/300M_s17_marscorpus   （mars_corpus.parquet）
  2) RNA-Sc-100M/300M_s17_rnacentral   （rnacentral_corpus.parquet，构建中）
配置：与 rinalmocorpus 臂同构——2.0B iso-token 预算、seed 17、
patience 5 早停、epoch-loop 支持小语料。
幂等：run 目录 .launch 标记（防重复提交）。
"""
import os
import subprocess
import time

MNT = "/mnt/cunyuliu/rna-sc"
CORPUS = os.path.join(MNT, "data", "mars_corpus.parquet")
CORPUS_RNA = os.path.join(MNT, "data", "rnacentral_corpus.parquet")
AUDIT = os.path.join(MNT, "evidence", "t437_mars_corpus_audit.json")
AUDIT_RNA = os.path.join(MNT, "evidence", "t437_rnacentral_corpus_audit.json")
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"

ARMS = [
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_marscorpus",
     "logs/RNA-Sc-100M_s17_marscorpus.log", 12.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_marscorpus",
     "logs/RNA-Sc-300M_s17_marscorpus.log", 10.0),
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_rnacentral",
     "logs/RNA-Sc-100M_s17_rnacentral.log", 12.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_rnacentral",
     "logs/RNA-Sc-300M_s17_rnacentral.log", 10.0),
]


def free_gb(gpu):
    out = subprocess.run(
        ["nvidia-smi", "--id=%d" % gpu, "--query-gpu=memory.free",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True).stdout.strip()
    try:
        return float(out) / 1024.0
    except ValueError:
        return 0.0


def launched(run_dir):
    return os.path.exists(os.path.join(MNT, run_dir, ".launch"))


def mark_launched(run_dir):
    os.makedirs(os.path.join(MNT, run_dir), exist_ok=True)
    with open(os.path.join(MNT, run_dir, ".launch"), "w") as fh:
        fh.write(time.strftime("%F %T\n"))


def launch(model_id, run_dir, log_rel, device):
    log = os.path.join(MNT, log_rel)
    corpus = CORPUS_RNA if "rnacentral" in run_dir else CORPUS
    tag = "rnacentral" if "rnacentral" in run_dir else "marscorpus"
    cmd = [PY, "-m", "rna_sc.train", "--model", model_id, "--seed", "17",
           "--device", str(device),
           "--out-dir", os.path.join(MNT, run_dir),
           "--corpus-tag", tag,
           "--budget-nt", "2000000000",
           "--early-stop-patience", "5",
           "--train-parquet", corpus]
    with open(log, "w") as lf:
        subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=lf,
                         start_new_session=True)
    mark_launched(run_dir)
    print("[t437-watch] launched %s on GPU%d -> %s" %
          (model_id, device, log), flush=True)


def corpus_ready(run_dir):
    if "rnacentral" in run_dir:
        return os.path.exists(CORPUS_RNA) and os.path.exists(AUDIT_RNA)
    return os.path.exists(CORPUS) and os.path.exists(AUDIT)


def main():
    t0 = time.time()
    while True:
        if all(launched(d) for _, d, _, _ in ARMS):
            print("[t437-watch] all arms launched, exit", flush=True)
            return
        remaining = [(m, d, l, n) for m, d, l, n in ARMS
                     if not launched(d) and corpus_ready(d)]
        if not remaining:
            print("[t437-watch] waiting for corpora %d min" %
                  ((time.time() - t0) // 60), flush=True)
            time.sleep(600)
            continue
        for gpu in (2, 3, 5, 0, 1, 4):
            if not remaining:
                break
            fg = free_gb(gpu)
            model_id, run_dir, log_rel, need = remaining[0]
            if fg >= need:
                launch(model_id, run_dir, log_rel, gpu)
                remaining = remaining[1:]
                time.sleep(120)
        if remaining:
            print("[t437-watch] waiting for GPUs: %s" %
                  [r[1] for r in remaining], flush=True)
            time.sleep(600)


if __name__ == "__main__":
    main()
