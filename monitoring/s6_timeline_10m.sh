#!/bin/bash
# T2.2.3 S6 emergence timeline: 10M s17 ckpts 100M..1900M nt (step 100M)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
NT_LIST="100000000 200000000 300000000 400000000 500000000 600000000 700000000 800000000 900000000 1000000000 1100000000 1200000000 1300000000 1400000000 1500000000 1600000000 1700000000 1800000000 1900000000"
for NT in $NT_LIST; do
  if grep -q "10M_s17_ck" /mnt/cunyuliu/rna-sc/eval/probe_results.jsonl 2>/dev/null; then
    if /home/cunyuliu/miniconda3/envs/toktokenbench/bin/python -c "
import json,sys
target = $NT
have = set()
for line in open(\"/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl\"):
    d = json.loads(line)
    if d[\"run\"].startswith(\"RNA-Sc-10M_s17_ck\") and d.get(\"n_train\",0) >= 20000:
        have.add(d[\"ckpt_nt\"])
ok = any(abs(h - target) < 60000000 for h in have)
sys.exit(0 if ok else 1)"; then
      echo "[s6] ckpt ~$NT already probed, skip"
      continue
    fi
  fi
  echo "[s6] probing 10M @${NT}nt"
  CUDA_VISIBLE_DEVICES=$1 $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17 --ckpt-nt $NT --device 0
done
echo "[s6] timeline complete"
