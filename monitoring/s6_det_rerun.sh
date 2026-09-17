#!/bin/bash
# S6 timeline midpoints: deterministic-probe (inc12) uniform rerun
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
python3 - <<'PYIN'
import json
p = '/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl'
lines = open(p).readlines()
keep = [l for l in lines if '_ck' not in json.loads(l)['run']]
open(p, 'w').writelines(keep)
print('cleared legacy _ck rows:', len(lines) - len(keep))
PYIN
for RUN in RNA-Sc-1M_s17 RNA-Sc-10M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  case $RUN in
    RNA-Sc-1M_s17) NTS='100000000 300000000 500000000 700000000 900000000 1100000000 1300000000 1500000000 1700000000';;
    RNA-Sc-10M_s17) NTS='100000000 200000000 300000000 400000000 500000000 600000000 700000000 800000000 900000000 1000000000 1100000000 1200000000 1300000000 1400000000 1500000000 1600000000 1700000000 1800000000 1900000000';;
    RNA-Sc-30M_s17) NTS='100000000 300000000 500000000 700000000 900000000';;
    RNA-Sc-100M_s17) NTS='200000000 500000000 1000000000 1500000000';;
  esac
  for NT in $NTS; do
    echo '===S6DET '$RUN' @'$NT'==='
    CUDA_VISIBLE_DEVICES=3 $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/$RUN --ckpt-nt $NT --device 0
  done
done
echo '===S6DET ALL DONE==='
