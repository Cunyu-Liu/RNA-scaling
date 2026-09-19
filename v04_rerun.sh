#!/bin/bash
# v0.4 Batch A: S4 randinit deterministic rerun (inc12 protocol), 4 scales serial on GPU6
# Launched 2026-09-19; log: /mnt/cunyuliu/rna-sc/logs/v04_randinit_rerun.log
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/v04_randinit_rerun.log
RUNS=/mnt/cunyuliu/rna-sc/runs

echo "===V04A start $(date)===" >> $LOG
for R in RNA-Sc-1M_s17 RNA-Sc-10M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  echo "===V04A randinit $R $(date)===" >> $LOG
  $PY -m rna_sc.probe --run-dir $RUNS/$R --device 6 --random-init 17 >> $LOG 2>&1
  RC=$?
  echo "===V04A $R rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===V04A ABORT on $R rc=$RC===" >> $LOG; exit 1; fi
done

echo "===V04A verify: jsonl randinit rows===" >> $LOG
$PY - <<'EOF' >> $LOG 2>&1
import json
from collections import defaultdict
by = defaultdict(int)
lays = defaultdict(set)
for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
    r = json.loads(line)
    if "randinit" in r["run"]:
        by[r["run"]] += 1
        lays[r["run"]].add(r["layer"])
for k in sorted(by):
    print(k, "rows=%d" % by[k], "layers=%d" % len(lays[k]))
EOF

echo "===V04A Batch B: 10M-c1Mcs timeline ckpts $(date)===" >> $LOG
for NT in 100011217 300021677 500027239 700044056; do
  echo "===V04B RNA-Sc-10M_s17_c1Mcs @$NT $(date)===" >> $LOG
  $PY -m rna_sc.probe --run-dir $RUNS/RNA-Sc-10M_s17_c1Mcs --device 6 --ckpt-nt $NT >> $LOG 2>&1
  RC=$?
  echo "===V04B nt=$NT rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===V04B ABORT nt=$NT rc=$RC===" >> $LOG; exit 1; fi
done

echo "===V04B verify: c1Mcs _ck rows===" >> $LOG
$PY - <<'EOF' >> $LOG 2>&1
import json
from collections import defaultdict
by = defaultdict(int)
for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
    r = json.loads(line)
    if "c1Mcs" in r["run"] and "_ck" in r["run"]:
        by[r["run"]] += 1
for k in sorted(by):
    print(k, "rows=%d" % by[k])
EOF

echo "===V04 all done $(date)===" >> $LOG
