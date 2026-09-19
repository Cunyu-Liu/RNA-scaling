#!/bin/bash
# S4xS9 cross: randinit + mommatch controls on BOTH splits (10M scale).
# Question: does random-split leakage exploitation require trained weight
# structure? Compares against trained 10M rows already in the ledger.
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/eval_matrix_s4x9.log

echo "===S4X9 start $(date)===" >> $LOG
for M in RNA-Sc-10M_s17_randinit17 RNA-Sc-10M_s17_mommatch17 RNA-Sc-100M_s17_randinit17; do
  echo "===S4X9 $M $(date)===" >> $LOG
  timeout 2400 $PY -m rna_sc.eval_matrix --model $M --device 6 >> $LOG 2>&1
  RC=$?
  echo "===S4X9 $M rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===S4X9 ABORT $M===" >> $LOG; exit 1; fi
done
echo "===S4X9 all done $(date)===" >> $LOG
