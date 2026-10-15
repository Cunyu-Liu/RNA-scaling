"""300M/650M random 中间点重跑：显式指定 GPU 4（避开 GPU6/7 cgroup 陷阱）。"""
import json
import os
import time

import torch

from rna_sc.eval_matrix import balanced_linear_probe
from rna_sc.probe import collect_states, load_encoder

RUNS = "/mnt/cunyuliu/rna-sc/runs"
OUT = "/mnt/cunyuliu/rna-sc/eval/random_midpoints_results.jsonl"
LOG = "/home/cunyuliu/rna-sc/logs/random_midpoints_eval.log"
DEV = "cuda:4"

PLAN = {
    "RNA-Sc-300M_s17_b59": [1000000000, 3000000000, 5000000000],
    "RNA-Sc-650M_s17_b59": [1000000000, 3000000000, 5000000000],
}


def already(run, nt):
    for line in open(OUT):
        r = json.loads(line)
        if r.get("run") == run and r.get("ckpt_nt") == nt:
            return True
    return False


t0 = time.time()
n_done = 0
log = open(LOG, "a")
log.write("\n[%s] fix batch (300M/650M on GPU4) start\n" % time.ctime())
log.flush()
for run, nts in PLAN.items():
    for nt in nts:
        if already(run, nt):
            continue
        log.write("[%s] %s nt=%d gpu=4 start\n" % (time.ctime(), run, nt))
        log.flush()
        try:
            model, ck = load_encoder(os.path.join(RUNS, run), ckpt_nt=nt)
            model.eval().to(DEV)
            L = ck["cfg"]["arch"]["n_layers"]
            n_train, n_eval = 19200, 4800
            X_all, y_all = collect_states(model, DEV, "family_validation",
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
                                              DEV, layer_seed=17)
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
log.write("[%s] fix batch done: %d ok, %.1f min\n" % (
    time.ctime(), n_done, (time.time() - t0) / 60))
log.close()
print("fix done", n_done)
