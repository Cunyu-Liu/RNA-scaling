#!/bin/bash
# v0.4+ Batch E: S5 moment-matched control (T2.2.2, H3), 4 scales serial on GPU6
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/v05_mommatch.log
RUNS=/mnt/cunyuliu/rna-sc/runs

echo "===V05E start $(date)===" >> $LOG
for R in RNA-Sc-1M_s17 RNA-Sc-10M_s17 RNA-Sc-30M_s17 RNA-Sc-100M_s17; do
  echo "===V05E mommatch $R $(date)===" >> $LOG
  $PY -m rna_sc.probe --run-dir $RUNS/$R --device 6 --moment-matched 17 >> $LOG 2>&1
  RC=$?
  echo "===V05E $R rc=$RC===" >> $LOG
  if [ $RC -ne 0 ]; then echo "===V05E ABORT on $R rc=$RC===" >> $LOG; exit 1; fi
done

echo "===V05E verify===" >> $LOG
$PY - <<'EOF' >> $LOG 2>&1
import json
from collections import defaultdict
by = defaultdict(int)
lays = defaultdict(set)
for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
    r = json.loads(line)
    if "mommatch" in r["run"]:
        by[r["run"]] += 1
        lays[r["run"]].add(r["layer"])
for k in sorted(by):
    print(k, "rows=%d" % by[k], "layers=%d" % len(lays[k]))
if not by:
    print("ERROR: no mommatch rows found")
EOF
echo "===V05E all done $(date)===" >> $LOG
