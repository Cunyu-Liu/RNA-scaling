#!/bin/bash
set -euo pipefail
CODE=/home/cunyuliu/rna-sc-p2/code_git
PY=/home/cunyuliu/rna-sc-p2/venv/bin/python
ROOT=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2
OUT=$ROOT/results/P2_1
LOGS=$ROOT/logs/P2_1
UNIT=RNA-Sc-30M_s17_rfamcap_randinit17
cd "$CODE"
export PYTHONPATH="$CODE"
export PYTHONUNBUFFERED=1
echo "=== P2_1 RESUME START $UNIT $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
FREE_MIB=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk 'NR==1 {print $1}')
if [ "$FREE_MIB" -lt 10240 ]; then
    echo "INSUFFICIENT_GPU_FREE_MIB=$FREE_MIB; required=10240"
    exit 2
fi
"$PY" -m rna_sc.probe_structure_p2_1 \
    --run-dir "$ROOT/weights/RNA-Sc-30M_s17_rfamcap" \
    --ckpt-nt 1900086380 \
    --random-init 17 \
    --device 0 \
    --n-train-seqs 8000 \
    --n-eval-seqs 1500 \
    --probe-batch-size 512 \
    --bprna "$ROOT/data/bpRNA_parsed.parquet" \
    --out-jsonl "$OUT/units/$UNIT/layers.jsonl" \
    --prediction-out "$OUT/units/$UNIT/predictions.npz" \
    --unit-summary-out "$OUT/units/$UNIT/summary.json" \
    --cache-dir "$OUT/cache/$UNIT" \
    > "$LOGS/$UNIT.log" 2>&1
echo "=== P2_1 ALL_SIX_UNITS_COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
