#!/bin/bash
# Deterministic-probe rerun of all final-ckpt runs (inc12 protocol)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
for R in RNA-Sc-1M_s17 RNA-Sc-10M_s17 RNA-Sc-30M_s17 RNA-Sc-30M_s17_c1M RNA-Sc-30M_s17_c1Mcs RNA-Sc-30M_s29_c1Mcs RNA-Sc-100M_s17 RNA-Sc-100M_s29 RNA-Sc-100M_s43 RNA-Sc-10M_s17_c1Mcs RNA-Sc-10M_s17_c5Mcs; do
  echo "===DETPROBE $R==="
  CUDA_VISIBLE_DEVICES=3 $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/$R --device 0
done
echo "===ALL DONE==="
