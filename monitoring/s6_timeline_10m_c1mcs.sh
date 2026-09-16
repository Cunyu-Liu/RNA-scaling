#!/bin/bash
# S6 attrition vs multi-epoch: 10M-c1Mcs (2.2-epoch corpus) timeline
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
NT_LIST="100000000 300000000 500000000 700000000"
for NT in $NT_LIST; do
  HAS=$(ls /mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17_c1Mcs/ | $PY -c "
import sys
target = $NT
best, bf = None, 6e8
for name in sys.stdin:
    name = name.strip()
    if not name.startswith(ckpt_nt): continue
    nt = int(name.split(_nt)[1].split(_)[0])
    if abs(nt - target) < bf: best, bf = nt, abs(nt - target)
print(best if bf < 6e7 else )")
  if [ -z "$HAS" ]; then echo "[s6-c1mcs] no ckpt near $NT, skip"; continue; fi
  if $PY -c "
import json,sys
target = $NT
have = set()
for line in open(\"/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl\"):
    d = json.loads(line)
    if d[\"run\"].startswith(\"RNA-Sc-10M_s17_c1Mcs_ck\") and d.get(\"n_train\",0)>=20000 and d.get(\"ckpt_nt\"):
        if abs(d[\"ckpt_nt\"] - target) < 60000000: have.add(d[\"ckpt_nt\"])
sys.exit(0 if have else 1)" 2>/dev/null; then
    echo "[s6-c1mcs] ~$NT already probed"; continue
  fi
  echo "[s6-c1mcs] probing @${NT}nt"
  CUDA_VISIBLE_DEVICES=$1 $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17_c1Mcs --ckpt-nt $NT --device 0
done
echo "[s6-c1mcs] done"
