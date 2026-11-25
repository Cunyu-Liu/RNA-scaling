#!/bin/bash
set -euo pipefail
export PYTHONPATH="/home/cunyuliu/rna-sc-p2${PYTHONPATH:+:${PYTHONPATH}}"
exec /home/cunyuliu/rna-sc-p2/venv/bin/python "$@"
