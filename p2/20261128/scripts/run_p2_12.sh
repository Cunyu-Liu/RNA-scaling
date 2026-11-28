#!/bin/bash
# P2.12 — 100M/30M family budget-effect remeasure (4 tags, parallel). Reuses P2.11 protocol.
export PYTHONPATH=/home/cunyuliu/rna-sc-p2/code_git
PY=/home/cunyuliu/rna-sc-p2/venv-core/bin/python
W=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights
L=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/logs
cd /home/cunyuliu/rna-sc-p2
mkdir -p "$L"
$PY p2_11_family_remeasure.py --run-dir $W/RNA-Sc-100M_s17     --tag 100M_2B  > $L/p2_12_100M_2B.log 2>&1 &
$PY p2_11_family_remeasure.py --run-dir $W/RNA-Sc-100M_s17_b59 --tag 100M_59B > $L/p2_12_100M_59B.log 2>&1 &
$PY p2_11_family_remeasure.py --run-dir $W/RNA-Sc-30M_s17      --tag 30M_2B   > $L/p2_12_30M_2B.log 2>&1 &
$PY p2_11_family_remeasure.py --run-dir $W/RNA-Sc-30M_s17_b59  --tag 30M_59B  > $L/p2_12_30M_59B.log 2>&1 &
wait
echo P2_12_ALL_DONE