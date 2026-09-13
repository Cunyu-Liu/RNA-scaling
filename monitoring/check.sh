#!/usr/bin/env bash
# RNA-Sc training monitor: run via crontab every 2h. Writes status + alerts.
PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
ROOT=/home/cunyuliu/rna-sc
OUT=/mnt/cunyuliu/rna-sc/status
mkdir -p "$OUT"
cd "$ROOT"
$PY -m rna_sc.status > "$OUT/status.txt" 2>&1
$PY -m rna_sc.ledger sync >> "$OUT/status.txt" 2>&1
# alert conditions
$PY - <<PYEOF >> "$OUT/status.txt" 2>&1
import json, subprocess, sys, datetime
rows = json.load(open("/mnt/cunyuliu/rna-sc/status.json"))["rows"]
problems = []
for r in rows:
    if r.get("status") == "RUNNING" and r.get("cpu_fallback_count"):
        problems.append("CPU FALLBACK: %s count=%s STOP AND INVESTIGATE" % (r["run"], r["cpu_fallback_count"]))
    if r.get("status") == "RUNNING" and (r.get("progress_pct") or 0) < 1 and datetime.datetime.fromisoformat(json.load(open("/mnt/cunyuliu/rna-sc/status.json"))["generated"]).year == 2026:
        pass
if problems:
    print("ALERTS:\n" + "\n".join(problems))
else:
    print("no alerts")
PYEOF
tail -3 "$OUT/status.txt"
