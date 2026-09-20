#!/bin/bash
# cleanup stray probe_structure processes, then relaunch fixed randinit batch
set -u
for p in $(pgrep -f "rna_sc.probe_structure" 2>/dev/null); do
  [ "$p" != "$$" ] && kill "$p" 2>/dev/null
done
for p in $(pgrep -f "bash s7_structure_batch.sh" 2>/dev/null); do
  [ "$p" != "$$" ] && kill "$p" 2>/dev/null
done
sleep 2
N=$(pgrep -f "rna_sc.probe_structure" 2>/dev/null | grep -v "$$" | wc -l)
echo "remaining probe procs: $N"

PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/s7_ri_fixed.log
echo "===RI-fix start $(date)===" >> $LOG
for R in RNA-Sc-10M_s17 RNA-Sc-100M_s17; do
  echo "===RI $R $(date)===" >> $LOG
  timeout 5400 $PY -m rna_sc.probe_structure \
    --run-dir /mnt/cunyuliu/rna-sc/runs/$R --device 6 \
    --n-train-seqs 8000 --n-eval-seqs 1500 \
    --random-init 17 >> $LOG 2>&1
  echo "===RI $R rc=$?===" >> $LOG
done
echo "===RI all done $(date)===" >> $LOG
