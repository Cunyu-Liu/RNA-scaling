"""Watcher: when RNA-Sc-1M_s17 hits DONE, auto-run final probe + linkage.

Runs as a daemon: polls the training log every 5 min; on DONE, launches
probe (20k/4k, per-class F1) on a free GPU, then s12_linkage, then appends
a TRAINING_LOG entry. Exits after handling.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

LOG = "/mnt/cunyuliu/rna-sc/logs/RNA-Sc-1M_s17.log"
RUN_DIR = "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-1M_s17"
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
TLOG = "/home/cunyuliu/rna-sc/TRAINING_LOG.md"
PROBE_LOG = "/mnt/cunyuliu/rna-sc/logs/probe_1M_final_auto.log"


def free_gpu() -> int:
    import torch
    best, best_free = -1, 0
    for i in range(torch.cuda.device_count()):
        try:
            free, _ = torch.cuda.mem_get_info(i)
        except Exception:
            continue
        if free > best_free:
            best, best_free = i, free
    return best if best_free > 2 << 30 else 6


def done_line() -> str | None:
    try:
        with open(LOG) as fh:
            for line in fh:
                if line.startswith("DONE rnasc_1M"):
                    return line.strip()
    except FileNotFoundError:
        pass
    return None


def main():
    print("[watch-1M] polling ...", flush=True)
    while True:
        d = done_line()
        if d:
            break
        time.sleep(300)
    print("[watch-1M] DONE detected: %s" % d, flush=True)
    gpu = free_gpu()
    print("[watch-1M] probing on GPU %d" % gpu, flush=True)
    env = dict(os.environ)
    with open(PROBE_LOG, "w") as lf:
        subprocess.run(
            [PY, "-m", "rna_sc.probe", "--run-dir", RUN_DIR,
             "--device", str(gpu)],
            cwd="/home/cunyuliu/rna-sc", stdout=lf, stderr=lf, timeout=7200)
    with open(PROBE_LOG) as fh:
        tail = fh.read()[-2000:]
    print("[watch-1M] probe tail:\n%s" % tail, flush=True)
    r = subprocess.run(
        [PY, "-m", "rna_sc.s12_linkage", "--run", "RNA-Sc-1M_s17"],
        cwd="/home/cunyuliu/rna-sc", capture_output=True, text=True)
    print("[watch-1M] linkage:\n%s" % r.stdout[-1500:], flush=True)
    with open(TLOG, "a") as fh:
        fh.write("\n### 1M COMPLETE (auto-watcher %s)\n- %s\n- final probe: "
                 "logs/probe_1M_final_auto.log (20k/4k, per-class F1)\n"
                 "- s12_linkage: evidence/s12_linkage.json (run=1M)\n"
                 % (time.strftime("%Y-%m-%d %H:%M"), d))
    print("[watch-1M] all done", flush=True)


if __name__ == "__main__":
    main()
