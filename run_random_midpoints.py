"""random 通道中间点补测：双通道背离曲线（结果三左图核心证据）。

预注册判据（run_b59_random.py 的延伸）：若 random-split 分数随预训练曝光
上涨（模型记住更多 → 随机切分兑现更多）而 family-split 平/降 → 双通道背离
= 泄漏红利的动态签名。

管线与 eval_matrix 完全一致：family_validation 池 24000 行、i%5 划分
train/eval（19200/4800）、balanced_linear_probe（class-weighted Adam）。
与主 ledger 独立（结果写 random_midpoints_results.jsonl，不干扰终态行）。
每尺度 3 个中间点（1.0/3.0/5.0B）+ 已有两端点（2B 终态、5.8B 终态）。
"""
import json
import os
import subprocess
import time

import torch

from rna_sc.eval_matrix import balanced_linear_probe
from rna_sc.probe import collect_states, load_encoder

RUNS = "/mnt/cunyuliu/rna-sc/runs"
OUT = "/mnt/cunyuliu/rna-sc/eval/random_midpoints_results.jsonl"
LOG = "/home/cunyuliu/rna-sc/logs/random_midpoints_eval.log"

PLAN = {
    "RNA-Sc-30M_s17_b59": [1000000000, 3000000000, 5000000000],
    "RNA-Sc-100M_s17_b59": [1000000000, 3000000000, 5000000000],
    "RNA-Sc-300M_s17_b59": [1000000000, 3000000000, 5000000000],
    "RNA-Sc-650M_s17_b59": [1000000000, 3000000000, 5000000000],
}


def pick_gpu():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,memory.free,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True).stdout.strip().splitlines()
    best, best_free = None, 0.0
    for row in out:
        idx, free, util = row.split(",")
        free_gb = float(free) / 1024.0
        try:
            u = float(util.replace("%", "").strip())
        except ValueError:
            u = 0.0
        if u < 70 and free_gb > 11.0 and free_gb > best_free:
            best, best_free = int(idx), free_gb
    return best


def already(run, nt):
    if not os.path.exists(OUT):
        return False
    for line in open(OUT):
        r = json.loads(line)
        if r.get("run") == run and r.get("ckpt_nt") == nt:
            return True
    return False


def main():
    t0 = time.time()
    n_done = 0
    log = open(LOG, "a")
    log.write("\n[%s] random midpoints start\n" % time.ctime())
    log.flush()
    for run, nts in PLAN.items():
        for nt in nts:
            if already(run, nt):
                log.write("[%s] skip %s %d (done)\n" % (time.ctime(), run, nt))
                continue
            gpu = pick_gpu()
            if gpu is None:
                log.write("[%s] no idle GPU, wait 600s\n" % time.ctime())
                time.sleep(600)
                gpu = pick_gpu()
                if gpu is None:
                    continue
            dev = "cuda:%d" % gpu
            log.write("[%s] %s nt=%d gpu=%d start\n" % (
                time.ctime(), run, nt, gpu))
            log.flush()
            try:
                model, ck = load_encoder(os.path.join(RUNS, run),
                                         ckpt_nt=nt)
                model.eval().to(dev)
                L = ck["cfg"]["arch"]["n_layers"]
                n_train, n_eval = 19200, 4800
                X_all, y_all = collect_states(model, dev,
                                              "family_validation",
                                              n_train + n_eval, L)
                idx_ev = [i for i in range(len(y_all)) if i % 5 == 0]
                idx_tr = [i for i in range(len(y_all)) if i % 5 != 0]
                X_tr = [torch.stack([X_all[li][i] for i in idx_tr])
                        for li in range(L)]
                y_tr = [y_all[i] for i in idx_tr]
                X_ev = [torch.stack([X_all[li][i] for i in idx_ev])
                        for li in range(L)]
                y_ev = [y_all[i] for i in idx_ev]
                accs, f1s = balanced_linear_probe(X_tr, y_tr, X_ev, y_ev,
                                                  dev, layer_seed=17)
                row = {"run": run + "_ck%d" % nt, "ckpt_nt": nt,
                       "best_f1_macro": round(max(f1s), 4),
                       "best_layer": f1s.index(max(f1s)),
                       "n_layers": L, "split": "random",
                       "n_train": len(y_tr), "n_eval": len(y_ev),
                       "protocol": "probe-balanced", "utc": time.ctime()}
                with open(OUT, "a") as fh:
                    fh.write(json.dumps(row) + "\n")
                n_done += 1
                log.write("[%s] %s nt=%d done f1=%s\n" % (
                    time.ctime(), run, nt, row["best_f1_macro"]))
                del model
                torch.cuda.empty_cache()
            except Exception as e:
                log.write("[%s] %s nt=%d ERR %s\n" % (
                    time.ctime(), run, nt, repr(e)[:200]))
            log.flush()
    log.write("[%s] random midpoints done: %d ok, %.1f min\n" % (
        time.ctime(), n_done, (time.time() - t0) / 60))
    log.close()


if __name__ == "__main__":
    main()
