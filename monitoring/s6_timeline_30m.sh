#!/bin/bash
# T2.2.3 S6 cross-scale: 30M s17 ckpts at 100M..1000M nt (available so far)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
NT_LIST="100000000 300000000 500000000 700000000 900000000"
for NT in $NT_LIST; do
  if /home/cunyuliu/miniconda3/envs/toktokenbench/bin/python -c "
import json,sys
target = $NT
have = set()
for line in open(\"/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl\"):
    d = json.loads(line)
    if d[\"run\"] == \"RNA-Sc-30M_s17_ck%d\" % target or (
       d[\"run\"] == \"RNA-Sc-30M_s17_ck\" and abs((d.get(\"ckpt_nt\") or 0) - target) < 60000000 and d.get(\"n_train\",0)>=20000):
        have.add(d.get(\"ckpt_nt\"))
sys.exit(0 if have else 1)" 2>/dev/null; then
    echo "[s6-30m] ckpt ~$NT already probed, skip"
    continue
  fi
  HAS=$(ls /mnt/cunyuliu/rna-sc/runs/RNA-Sc-30M_s17/ | /home/cunyuliu/miniconda3/envs/toktokenbench/bin/python -c "
import sys
target = $NT
best, bf = None, 6e8
for name in sys.stdin:
    name = name.strip()
    if not name.startswith('ckpt_nt'): continue
    nt = int(name.split('_nt')[1].split('_')[0])
    if abs(nt - target) < bf:
        best, bf = nt, abs(nt - target)
print(best if bf < 6e7 else '')")
  if [ -z "$HAS" ]; then
    echo "[s6-30m] no ckpt within 60M of $NT, skip"
    continue
  fi
  echo "[s6-30m] probing 30M @${NT}nt"
  CUDA_VISIBLE_DEVICES=$1 $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-30M_s17 --ckpt-nt $NT --device 0
done
echo "[s6-30m] done"
