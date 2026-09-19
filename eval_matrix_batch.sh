#!/bin/bash
# T0.2.6 eval_matrix v1 remaining scales (1M/30M/100M) serial on GPU6
# 10M already done (ledger). Each model: 2 protocols x 2 splits.
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/eval_matrix_v1.log

echo "===EVM start $(date)===" >> $LOG
for M in RNA-Sc-1M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  echo "===EVM $M $(date)===" >> $LOG
  timeout 3600 $PY -m rna_sc.eval_matrix --model $M --device 6 >> $LOG 2>&1
  RC=$?
  echo "===EVM $M rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===EVM ABORT $M rc=$RC===" >> $LOG; exit 1; fi
done
echo "===EVM all done $(date)===" >> $LOG
