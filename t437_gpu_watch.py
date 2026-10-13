"""T4.3.7 语料谱扩展 GPU watcher（2026-10-13，04 方案执行版）：

MARS 语料已落盘（mars_corpus.parquet + audit）。RNAcentral 语料臂
（rnacentral_active.fasta 重建）构建为 stage-2（MARS 双臂先跑）。

提交顺序（有卡即发，无卡 10 分钟轮询）：
  1) RNA-Sc-100M_s17_marscorpus（判据 A 核心区间）
  2) RNA-Sc-300M_s17_marscorpus
配置与 rinalmocorpus 臂完全同构：--train-parquet mars_corpus.parquet，
2.0B nt iso-token 预算，seed 17，corpus-tag marscorpus。
日志：logs/t437_gpu_watch.log；幂等（manifest 存在即已提交）。
"""
import os
import subprocess
import time

MNT = "/mnt/cunyuliu/rna-sc"
CORPUS = os.path.join(MNT, "data", "mars_corpus.parquet")
AUDIT = os.path.join(MNT, "evidence", "t437_mars_corpus_audit.json")
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
LOG = os.path.join(MNT, "logs", "t437_gpu_watch.log")

ARMS = [
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_marscorpus",
     "logs/RNA-Sc-100M_s17_marscorpus.log", 26.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_marscorpus",
     "logs/RNA-Sc-300M_s17_marscorpus.log", 12.0),
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
    return os.path.exists(os.path.join(MNT, run_dir, "manifest.json"))


def launch(model_id, run_dir, log_rel, device):
    log = os.path.join(MNT, log_rel)
    cmd = [PY, "-m", "rna_sc.train", "--model", model_id, "--seed", "17",
           "--device", str(device),
           "--out-dir", os.path.join(MNT, run_dir),
           "--corpus-tag", "marscorpus",
           "--budget-nt", "2000000000",
           "--early-stop-patience", "5",
           "--train-parquet", CORPUS]
    with open(log, "w") as lf:
        subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=lf,
                         start_new_session=True)
    print("[t437-watch] launched %s on GPU%d -> %s" %
          (model_id, device, log), flush=True)


def main():
    assert os.path.exists(CORPUS) and os.path.exists(AUDIT), \
        "corpus not ready"
    while True:
        remaining = [(m, d, l, n) for m, d, l, n in ARMS
                     if not launched(d)]
        if not remaining:
            print("[t437-watch] all arms launched, exit", flush=True)
            return
        for gpu in (2, 3, 5, 0, 1, 4, 7):
            if gpu == 6:
                continue
            fg = free_gb(gpu)
            model_id, run_dir, log_rel, need = remaining[0]
            if fg >= need:
                launch(model_id, run_dir, log_rel, gpu)
                remaining = remaining[1:]
                if not remaining:
                    return
                time.sleep(120)
        print("[t437-watch] waiting: %s" % [r[0] for r in remaining],
              flush=True)
        time.sleep(600)


if __name__ == "__main__":
    main()
