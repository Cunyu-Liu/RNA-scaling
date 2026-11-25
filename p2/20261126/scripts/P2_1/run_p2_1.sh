#!/bin/bash
set -euo pipefail
CODE=/home/cunyuliu/rna-sc-p2/code_git
PY=/home/cunyuliu/rna-sc-p2/venv/bin/python
ROOT=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2
OUT=$ROOT/results/P2_1
LOGS=$ROOT/logs/P2_1
mkdir -p "$OUT/units" "$LOGS"
cd "$CODE"
export PYTHONPATH="$CODE"
export PYTHONUNBUFFERED=1

run_unit() {
    local run=$1
    local nt=$2
    local random_init=$3
    local unit
    if [ "$random_init" = "17" ]; then
        unit=${run}_randinit17
    else
        unit=${run}_ckpt${nt}
    fi
    echo "=== P2_1 START $unit $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
    local free_mib
    free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk 'NR==1 {print $1}')
    if [ "$free_mib" -lt 10240 ]; then
        echo "INSUFFICIENT_GPU_FREE_MIB=$free_mib; required=10240; stopping without protocol reduction"
        return 2
    fi
    local random_args=()
    if [ "$random_init" = "17" ]; then
        random_args=(--random-init 17)
    fi
    "$PY" -m rna_sc.probe_structure_p2_1 \
        --run-dir "$ROOT/weights/$run" \
        --ckpt-nt "$nt" \
        --device 0 \
        --n-train-seqs 8000 \
        --n-eval-seqs 1500 \
        --probe-batch-size 512 \
        --bprna "$ROOT/data/bpRNA_parsed.parquet" \
        --out-jsonl "$OUT/units/$unit/layers.jsonl" \
        --prediction-out "$OUT/units/$unit/predictions.npz" \
        --unit-summary-out "$OUT/units/$unit/summary.json" \
        --cache-dir "$OUT/cache/$unit" \
        "${random_args[@]}" \
        > "$LOGS/$unit.log" 2>&1
    echo "=== P2_1 COMPLETE $unit $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

run_unit RNA-Sc-100M_s17_rfamcap 1800083135 none
run_unit RNA-Sc-100M_s17_rfamcap 1900086380 none
run_unit RNA-Sc-30M_s17_rfamcap 1900086380 none
run_unit RNA-Sc-30M_s17_rfamcap 1800083135 none
run_unit RNA-Sc-100M_s17_rfamcap 1900086380 17
run_unit RNA-Sc-30M_s17_rfamcap 1900086380 17
echo "=== P2_1 ALL_SIX_UNITS_COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
