#!/bin/bash
# keep watch_all alive (idempotent; cron every 2 min)
if ! pgrep -f "python -u -m rna_sc.watch_all" > /dev/null; then
  cd /home/cunyuliu/rna-sc
  setsid nohup /home/cunyuliu/miniconda3/envs/toktokenbench/bin/python -u -m rna_sc.watch_all >> /mnt/cunyuliu/rna-sc/logs/watch_all.log 2>&1 < /dev/null &
fi
