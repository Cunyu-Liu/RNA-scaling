#!/bin/bash
# S14 family crossval with OOM-retry across GPUs (external jobs
# intermittently squeeze any single GPU; retry on other cards).
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/s14_family.log

for DEV in 6 1 3 7 0 4 5; do
  echo "===S14F try GPU$DEV $(date)===" >> $LOG
  timeout 3000 $PY -m rna_sc.s14_family --device $DEV \
    --n-per-family 60 >> $LOG 2>&1
  RC=$?
  echo "===S14F GPU$DEV rc=$RC===" >> $LOG
  if [ $RC -eq 0 ]; then
    echo "===S14F DONE on GPU$DEV===" >> $LOG
    exit 0
  fi
  sleep 120
done
echo "===S14F ALL-GPU-FAILED===" >> $LOG
exit 1
