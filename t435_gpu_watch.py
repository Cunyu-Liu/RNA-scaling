"""T4.3.5 GPU 自动开训 watcher（2026-10-08）：

语料构建完成后（rinalmo_corpus_v1.parquet + 审计 JSON 落盘），
轮询 GPU 显存——任一卡真实空闲 ≥ 28GB（100M 臂峰值 ~25GB + 余量）即提交：
  1) 100M 臂：RNA-Sc-100M_s17_rinalmocorpus（优先，对齐"语料>参数"判据核心区间）
  2) 300M 臂：第二个空卡时自动加发（wave 队列式，不与 supervisor 冲突——
     手动 train --train-parquet 路线，与 rfamcap 臂同一模式）

训练配置：统一配方（同主家族）+ --train-parquet 指向新语料 + 2.0B nt 预算
（iso-token 与主线可比）+ epoch-loop 补丁已支持小语料多 epoch 循环
（rfamcap 274M 语料验证过）。validate 保持原 split（rfamcap 教训已根除
val 空跑伪迹）。

日志：logs/t435_gpu_watch.log；幂等（.launch 标记防重复提交）。
"""
import json
import os
import subprocess
import time

MNT = "/mnt/cunyuliu/rna-sc"
DATA = os.path.join(MNT, "data")
LOGS = os.path.join(MNT, "logs")
CORPUS = os.path.join(DATA, "rinalmo_corpus_v1.parquet")
AUDIT = os.path.join(MNT, "evidence", "t435_corpus_audit.json")
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"

ARMS = [
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_rinalmocorpus",
     "logs/RNA-Sc-100M_s17_rinalmocorpus.log", 28.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_rinalmocorpus",
     "logs/RNA-Sc-300M_s17_rinalmocorpus.log", 33.0),
]


def corpus_ready():
    return os.path.exists(CORPUS) and os.path.exists(AUDIT)


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
           "--corpus-tag", "rinalmocorpus",
           "--budget-nt", "2000000000",
           "--train-parquet", CORPUS]
    with open(log, "w") as lf:
        subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=lf,
                         start_new_session=True)
    print("[t435-watch] launched %s on GPU%d -> %s" %
          (model_id, device, log), flush=True)


def main():
    print("[t435-watch] waiting for corpus build...", flush=True)
    while not corpus_ready():
        time.sleep(300)
    a = json.load(open(AUDIT))
    print("[t435-watch] corpus ready: %d seqs / %d clusters / %.1fB nt" %
          (a["n_sequences"], a["n_clusters"], a["total_nt"] / 1e9), flush=True)
    while True:
        all_done = True
        for model_id, run_dir, log_rel, need in ARMS:
            if launched(run_dir):
                continue
            all_done = False
            for gpu in range(8):
                if free_gb(gpu) >= need:
                    launch(model_id, run_dir, log_rel, gpu)
                    break
            else:
                print("[t435-watch] %s waiting: no GPU >= %.0fGB free" %
                      (model_id, need), flush=True)
        if all_done:
            print("[t435-watch] both arms launched, exit", flush=True)
            return
        time.sleep(600)


if __name__ == "__main__":
    main()
