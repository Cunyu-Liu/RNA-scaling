#!/usr/bin/env bash
# Launch the RNA-Sc multi-GPU training wave (SPEC line-2 priority order).
# Usage: bash launch_wave1.sh          (from /home/cunyuliu/rna-sc)
# Rules: ledger claims prevent duplicates; GPU assignment by free memory.
set -uo pipefail

ROOT=/home/cunyuliu/rna-sc
RUNS=/mnt/cunyuliu/rna-sc/runs
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
export PYTHONUNBUFFERED=1

cd "$ROOT"
mkdir -p "$RUNS" /mnt/cunyuliu/rna-sc/logs

launch () {  # model seed gpu corpus_nseq corpus_tag
  local model=$1 seed=$2 gpu=$3 nseq=${4:-} tag=${5:-full}
  local out="$RUNS/${model}_s${seed}${tag:+_$tag}"
  out="$RUNS/${model}_s${seed}$( [ "$tag" != "full" ] && echo "_$tag" )"
  local log="/mnt/cunyuliu/rna-sc/logs/${model}_s${seed}$( [ "$tag" != "full" ] && echo "_$tag" ).log"
  local claimed=$($PY - <<EOF
import sys; sys.path.insert(0, "$ROOT")
from rna_sc import ledger
r = ledger.claim("$model", $seed, $gpu, "$out", corpus_tag="$tag")
print("YES" if r["claimed"] else "NO")
EOF
)
  if [ "$claimed" != "YES" ]; then
    echo "SKIP $model s$seed $tag (already running/done)"
    return 0
  fi
  mkdir -p "$out"
  local nseq_arg=""
  [ -n "$nseq" ] && nseq_arg="--corpus-nseq $nseq --corpus-tag $tag"
  setsid nohup $PY -m rna_sc.train --model "$model" --seed "$seed" \
    --device "$gpu" --out-dir "$out" $nseq_arg > "$log" 2>&1 < /dev/null &
  echo "LAUNCHED $model s$seed $tag on GPU$gpu (pid $!) -> $log"
}

# Wave 1 (priority): 30M main + 10M main + 30M c1M corpus arm + 1M main
launch RNA-Sc-30M  17 6
launch RNA-Sc-10M  17 1
launch RNA-Sc-30M  17 7 1000000 c1M
launch RNA-Sc-1M   17 7

echo "wave launched; check: $PY -m rna_sc.status"
