#!/usr/bin/env bash
# Launch the supervisor (owns the wave: GPU-pick by real free memory,
# relaunch on crash with resume). Run ONE supervisor at a time.
set -uo pipefail
ROOT=/home/cunyuliu/rna-sc
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
cd "$ROOT"
mkdir -p /mnt/cunyuliu/rna-sc/logs
export PYTHONUNBUFFERED=1
setsid nohup $PY -m rna_sc.supervisor \
  > /mnt/cunyuliu/rna-sc/logs/supervisor.log 2>&1 < /dev/null &
echo "supervisor pid $! -> /mnt/cunyuliu/rna-sc/logs/supervisor.log"
