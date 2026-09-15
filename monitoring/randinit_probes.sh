#!/bin/bash
# T2.2.1 S4 randinit probe expansion: 1M/30M/100M (10M done as randinit17)
# Runs sequentially on one GPU; CUDA asserted by probe.py itself.
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
GPU=$1
cd /home/cunyuliu/rna-sc
for RUN in RNA-Sc-1M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  if grep -q "${RUN}_randinit17 " /mnt/cunyuliu/rna-sc/eval/probe_results.jsonl 2>/dev/null; then
    echo "[s4] $RUN randinit already present, skip"
    continue
  fi
  echo "[s4] probing $RUN randinit17 on GPU$GPU"
  CUDA_VISIBLE_DEVICES=$GPU $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/$RUN --random-init 17 --device 0
done
echo "[s4] all done"
