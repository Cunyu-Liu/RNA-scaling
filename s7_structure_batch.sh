#!/bin/bash
# S7 structure probe batch: 4 scales x full bpRNA sampling, serial on GPU6
# (GPU6 has 40GB - the probe uses ~3-5GB per model; serial avoids contention
# with 650M training on GPU2)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/s7_structure_probe.log

echo "===S7STR start $(date)===" >> $LOG
for R in RNA-Sc-1M_s17 RNA-Sc-10M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  echo "===S7STR $R $(date)===" >> $LOG
  timeout 5400 $PY -m rna_sc.probe_structure \
    --run-dir /mnt/cunyuliu/rna-sc/runs/$R --device 6 \
    --n-train-seqs 8000 --n-eval-seqs 1500 >> $LOG 2>&1
  RC=$?
  echo "===S7STR $R rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===S7STR ABORT $R rc=$RC===" >> $LOG; exit 1; fi
done

echo "===S7STR controls: randinit x2 scales===" >> $LOG
for R in RNA-Sc-10M_s17 RNA-Sc-100M_s17; do
  echo "===S7STR ${R}_randinit17 $(date)===" >> $LOG
  timeout 5400 $PY -m rna_sc.probe_structure \
    --run-dir /mnt/cunyuliu/rna-sc/runs/$R --device 6 \
    --n-train-seqs 8000 --n-eval-seqs 1500 \
    --random-init 17 >> $LOG 2>&1
  RC=$?
  echo "===S7STR ${R}_ri rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===S7STR ABORT ri $R===" >> $LOG; exit 1; fi
done
echo "===S7STR all done $(date)===" >> $LOG
