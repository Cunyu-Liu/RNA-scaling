#!/bin/bash
# S6 remaining scales: 1M (19 ckpts, fast) + 100M (sparse: 0.2/0.5/1.0/1.5B)
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
probe_if_needed() {
  RUN=$1; NT=$2; GPU=$3
  if $PY -c "
import json,sys
base, target = \"$RUN\", $NT
have = set()
for line in open(\"/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl\"):
    d = json.loads(line)
    if d[\"run\"].startswith(base) and d.get(\"n_train\",0)>=20000 and d.get(\"ckpt_nt\"):
        if abs(d[\"ckpt_nt\"] - target) < 60000000:
            have.add(d[\"ckpt_nt\"])
sys.exit(0 if have else 1)"; then
    echo "[s6x] $RUN ~$NT already probed"
    return
  fi
  echo "[s6x] probing $RUN @${NT}nt"
  CUDA_VISIBLE_DEVICES=$GPU $PY -m rna_sc.probe --run-dir /mnt/cunyuliu/rna-sc/runs/$RUN --ckpt-nt $NT --device 0
}
for NT in 100000000 300000000 500000000 700000000 900000000 1100000000 1300000000 1500000000 1700000000; do
  probe_if_needed RNA-Sc-1M_s17 $NT 3
done
for NT in 200000000 500000000 1000000000 1500000000; do
  probe_if_needed RNA-Sc-100M_s17 $NT 3
done
echo "[s6x] all done"
