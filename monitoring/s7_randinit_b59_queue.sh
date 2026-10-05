#!/bin/bash
# S7 b59 randinit queue (2026-10-05): run the three missing S7
# randinit17 controls sequentially on one GPU.
# 30M -> 100M -> 300M; idempotent per-run layer-count check.
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
ROOT=/home/cunyuliu/rna-sc
MNT=/mnt/cunyuliu/rna-sc
GPU=$1
JSONL=$MNT/eval/probe_structure_results.jsonl

for SCALE in 30M 100M 300M; do
  RUN=RNA-Sc-${SCALE}_s17_b59
  NEED=$($PY -c "
import json, os
run = \"${RUN}_randinit17\"
p = \"$JSONL\"
n = 0
if os.path.exists(p):
    for l in open(p):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get(\"run\") == run:
            n += 1
print(\"NO\" if n > 0 else \"YES\")
" 2>/dev/null)
  if [ "$NEED" = "NO" ]; then
    echo "[s7-randinit-queue] $RUN randinit17 already present, skip"
    continue
  fi
  echo "[s7-randinit-queue] starting $RUN randinit17 on GPU$GPU"
  cd $ROOT
  CUDA_VISIBLE_DEVICES=$GPU $PY -u -m rna_sc.probe_structure \
    --run-dir $MNT/runs/$RUN --random-init 17 --device 0 \
    > $MNT/logs/s7_${SCALE}_b59_randinit17.log 2>&1
  RC=$?
  echo "[s7-randinit-queue] $RUN randinit17 rc=$RC"
done
echo "[s7-randinit-queue] all done"
