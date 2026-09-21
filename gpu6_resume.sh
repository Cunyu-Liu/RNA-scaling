#!/bin/bash
# Resume GPU6 batch after external-job squeeze cleared:
# 1) 100M randinit structure control (retry, 3h budget)
# 2) S13b full version (8000 train seqs, 3h budget)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/gpu6_resume_batch.log

echo "===RESUME start $(date)===" >> $LOG
echo "===RI100M retry $(date)===" >> $LOG
timeout 10800 $PY -m rna_sc.probe_structure \
  --run-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-100M_s17 --device 6 \
  --n-train-seqs 8000 --n-eval-seqs 1500 --random-init 17 >> $LOG 2>&1
echo "===RI100M rc=$?===" >> $LOG

echo "===S13B full $(date)===" >> $LOG
timeout 10800 $PY -m rna_sc.s13b_bell --device 6 \
  --n-train-seqs 8000 --n-eval-seqs 1500 >> $LOG 2>&1
echo "===S13B rc=$?===" >> $LOG
echo "===RESUME all done $(date)===" >> $LOG
