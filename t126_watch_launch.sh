#!/bin/bash
# T1.2.6 full-FT line launcher v2: wait for a GPU with >=22GB real free
# (allocator-truth, headroom for co-tenant ramp), then run
# fullft_lowdata v1.1 (10M/100M/650M). Retries up to 5 attempts on
# failure (OOM from co-tenant ramp), 30 min between attempts.
set -u
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd /home/cunyuliu/rna-sc
LOG=/mnt/cunyuliu/rna-sc/logs/t126_fullft_650m.log
MARK=/mnt/cunyuliu/rna-sc/logs/t126_fullft_650m.done
OUT=/mnt/cunyuliu/rna-sc/evidence/t126_fullft.json

[ -f "$MARK" ] && { echo "t126 already done"; exit 0; }
echo "===t126 watcher v2 start $(date)===" >> $LOG
DEADLINE=$(( $(date +%s) + 96*3600 ))
ATTEMPT=0
while [ $(date +%s) -lt $DEADLINE ] && [ $ATTEMPT -lt 5 ]; do
  GPU=$($PY - <<'PYEOF'
import sys
sys.path.insert(0, "/home/cunyuliu/rna-sc")
from rna_sc import gpu_pick
try:
    print(gpu_pick.pick(22.0))
except Exception:
    print(-1)
PYEOF
)
  if [ "$GPU" -ge 0 ] 2>/dev/null; then
    ATTEMPT=$((ATTEMPT+1))
    echo "===t126 attempt $ATTEMPT launch gpu=$GPU $(date)===" >> $LOG
    timeout 21600 $PY -m rna_sc.fullft_lowdata --device $GPU >> $LOG 2>&1
    rc=$?
    echo "===t126 fullft rc=$rc $(date)===" >> $LOG
    if [ $rc -eq 0 ] && [ -f "$OUT" ] && $PY -c "import json,sys;d=json.load(open('$OUT'));sys.exit(0 if '650M' in d['scales'] else 1)" 2>/dev/null; then
      $PY -c "import json;d=json.load(open('$OUT'));print('scales:',list(d['scales'].keys()))" >> $LOG
      touch "$MARK"
      exit 0
    fi
    echo "[t126-watch] attempt $ATTEMPT failed (rc=$rc); retry in 30min $(date)" >> $LOG
    sleep 1800
  else
    echo "[t126-watch] no free GPU yet $(date)" >> $LOG
    sleep 600
  fi
done
echo "===t126 watcher exhausted (attempts=$ATTEMPT) $(date)===" >> $LOG
exit 1
