#!/bin/bash
# S7 structure probe watchdog for 650M@5.9B (2026-10-05)
# Triggers when: 650M_b59 DONE + family probe rows exist + S7 rows absent.
# Idempotent: exits silently once all 28 S7 layers are present.
set -u
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
ROOT=/home/cunyuliu/rna-sc
MNT=/mnt/cunyuliu/rna-sc
RUN=RNA-Sc-650M_s17_b59
LOCK=$MNT/logs/s7_650m_b59_watchdog.lock
DONEFLAG=$MNT/logs/s7_650m_b59_done.flag

[ -f "$DONEFLAG" ] && exit 0
[ -f "$LOCK" ] && exit 0

STATUS=$($PY -c "import json; print(json.load(open('$MNT/runs/$RUN/manifest.json')).get('status',''))" 2>/dev/null)
[ "$STATUS" = "DONE" ] || exit 0

FAM=$($PY - << 'EOF'
import json
run = "RNA-Sc-650M_s17_b59"
rows = [json.loads(l) for l in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl")]
elig = [r for r in rows if r.get("run") == run and r.get("n_train", 0) >= 4000 and r.get("ckpt_nt")]
print(len(elig) > 0)
EOF
)
[ "$FAM" = "True" ] || exit 0

S7DONE=$($PY - << 'EOF'
import json, os
run = "RNA-Sc-650M_s17_b59"
p = "/mnt/cunyuliu/rna-sc/eval/probe_structure_results.jsonl"
if not os.path.exists(p):
    print("False")
else:
    rows = [json.loads(l) for l in open(p)]
    layers = {r.get("layer") for r in rows if r.get("run") == run}
    print(len(layers) >= 28)
EOF
)
[ "$S7DONE" = "True" ] && { touch "$DONEFLAG"; echo "[s7-watchdog-650m] already complete (28 layers)"; exit 0; }

GPU=$(nvidia-smi --query-gpu=index,memory.free,utilization.gpu --format=csv,noheader,nounits | awk -F, "\$2>=8000 && \$3<50 {print \$1; exit}")
if [ -z "$GPU" ]; then echo "[s7-watchdog-650m] no free GPU >=8GB this cycle, will retry"; exit 0; fi
touch "$LOCK"
cd $ROOT
CUDA_VISIBLE_DEVICES=$GPU nohup $PY -u -m rna_sc.probe_structure   --run-dir $MNT/runs/$RUN --device 0   > $MNT/logs/s7_650m_b59.log 2>&1
RC=$?
rm -f "$LOCK"
if [ $RC -eq 0 ]; then
  touch "$DONEFLAG"
  echo "[s7-watchdog-650m] probe finished rc=0"
else
  echo "[s7-watchdog-650m] probe rc=$RC (will retry next cycle; lock removed)"
fi
exit 0
