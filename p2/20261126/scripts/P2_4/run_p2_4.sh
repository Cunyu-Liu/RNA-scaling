#!/usr/bin/env bash
set -euo pipefail
PROJECT=/home/cunyuliu/rna-sc-p2
ROOT=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2
OUT="$ROOT/results/P2_4"
PY="$PROJECT/venv/bin/python"
export PYTHONPATH="$PROJECT/p2_4:$PROJECT:$PROJECT/code_git"
export RNA_SC_P2_ROOT="$ROOT"
mkdir -p "$OUT/logs"
nvidia-smi > "$OUT/logs/nvidia_smi_prepare.txt"
"$PY" "$PROJECT/p2_4/prepare_p2_4.py" 2>&1 | tee "$OUT/logs/prepare.log"
nvidia-smi > "$OUT/logs/nvidia_smi_smoke.txt"
"$PY" "$PROJECT/p2_4/run_p2_4.py" --arm 100M --smoke 2>&1 | tee "$OUT/logs/smoke.log"
for arm in 100M 650M randinit; do
  nvidia-smi > "$OUT/logs/nvidia_smi_before_${arm}.txt"
  "$PY" "$PROJECT/p2_4/run_p2_4.py" --arm "$arm" --batch 4 2>&1 | tee "$OUT/logs/${arm}.log"
done
"$PY" "$PROJECT/p2_4/analyze_p2_4.py" 2>&1 | tee "$OUT/logs/analyze.log"
"$PY" "$PROJECT/p2_4/validate_p2_4.py" 2>&1 | tee "$OUT/logs/validate.log"
"$PY" "$PROJECT/p2_4/finalize_p2_4.py"
