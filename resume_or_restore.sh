#!/usr/bin/env bash
# resume_or_restore.sh —— RNA-LM 课题集群重启恢复脚本（2026-10-14）
#
# 设计原则（对应 BACKUP_MANIFEST_20261014.md）：
#   1. 先验证服务器资产（ckpt md5 / 语料 parquet 是否随 /mnt 存活）
#   2. ckpt 完好 → --resume-from 续训；ckpt 丢失 → 语料在则重训，语料也丢则重建语料
#   3. 恢复值守 cron（去掉 #PAUSED# 前缀）+ 重启值守进程
#   4. --dry-run 模式只报告不执行；--gpu N 指定起始卡
#
# 用法：bash resume_or_restore.sh [--dry-run] [--gpu 3]
set -uo pipefail

DRY_RUN=0
START_GPU=3
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --gpu) START_GPU="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

PY=/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python
ROOT=/home/cunyuliu/rna-sc
MNT=/mnt/cunyuliu/rna-sc
LOGDIR=$MNT/logs

say()  { echo "[resume] $*"; }
run()  { if [[ $DRY_RUN -eq 1 ]]; then say "DRY: $*"; else "$@"; fi; }

# ---- 0. 连通性与环境检查 ----
say "0) 连通性检查"
[[ -d $ROOT ]] || { say "FATAL: $ROOT 不存在（服务器未恢复）"; exit 1; }
[[ -x $PY ]]   || { say "FATAL: python 环境缺失"; exit 1; }
ls "$PY" > /dev/null 2>&1 || true

# ---- 1. 六臂状态评估 ----
# 格式: run_dir|ckpt 相对路径|期望 md5|语料 parquet|tag
ARMS=(
"RNA-Sc-100M_s17_marscorpus|ckpt_nt400023183_step041442.pt|5e24cf1eda5b5f2907a4015fb4fc9643|mars_corpus.parquet|marscorpus"
"RNA-Sc-300M_s17_marscorpus|ckpt_nt200010618_step020735.pt|4a7c6b1ad071b2b8e2a56dae275354e4|mars_corpus.parquet|marscorpus"
"RNA-Sc-100M_s17_rnacentral|ckpt_nt300017070_step035496.pt|0584adc68d3715f7e279edda42a18217|rnacentral_corpus.parquet|rnacentral"
"RNA-Sc-300M_s17_rnacentral|ckpt_nt200008577_step023645.pt|7e8b60398bb39c33164155bead7e2540|rnacentral_corpus.parquet|rnacentral"
"RNA-Sc-30M_s17_marscorpus|NONE|-|mars_corpus.parquet|marscorpus"
"RNA-Sc-30M_s17_rnacentral|NONE|-|rnacentral_corpus.parquet|rnacentral"
)
MODEL_OF() { case "$1" in RNA-Sc-100M*) echo RNA-Sc-100M;; RNA-Sc-300M*) echo RNA-Sc-300M;; RNA-Sc-30M*) echo RNA-Sc-30M;; esac; }

declare -a TO_RESUME=()   # ckpt 完好，续训
declare -a TO_RETRAIN=()  # ckpt 丢，语料在，重训
declare -a TO_REBUILD=()  # 语料也丢，先重建语料

say "1) 六臂资产核验"
for entry in "${ARMS[@]}"; do
  IFS='|' read -r run ckpt md5 corpus tag <<< "$entry"
  rd=$MNT/runs/$run
  cp=$rd/$ckpt
  cpar=$MNT/data/$corpus
  if [[ $ckpt == NONE ]]; then
    if [[ -f $cpar ]]; then TO_RETRAIN+=("$entry"); st="RETRAIN(无ckpt,语料在)";
    else TO_REBUILD+=("$entry"); st="REBUILD(语料缺失)"; fi
  elif [[ -f $cp ]] && [[ "$(md5sum "$cp" | cut -d' ' -f1)" == "$md5" ]]; then
    TO_RESUME+=("$entry"); st="RESUME(ckpt md5 一致)"
  elif [[ -f $cpar ]]; then
    TO_RETRAIN+=("$entry"); st="RETRAIN(ckpt 丢/损坏,语料在)"
  else
    TO_REBUILD+=("$entry"); st="REBUILD(ckpt+语料均缺)"
  fi
  printf '  %-34s %s\n' "$run" "$st"
done

# ---- 2. 语料重建（仅 TO_REBUILD 需要时） ----
if [[ ${#TO_REBUILD[@]} -gt 0 ]]; then
  say "2) 语料重建"
  need_mars=0; need_rc=0
  for entry in "${TO_REBUILD[@]}"; do
    IFS='|' read -r _ _ _ corpus _ <<< "$entry"
    [[ $corpus == mars_corpus.parquet ]] && need_mars=1
    [[ $corpus == rnacentral_corpus.parquet ]] && need_rc=1
  done
  [[ $need_mars -eq 1 ]] && run bash -c "cd $ROOT && $PY -u build_corpus_mars.py > $LOGDIR/build_mars_corpus.log 2>&1"
  [[ $need_rc   -eq 1 ]] && run bash -c "cd $ROOT && $PY -u build_corpus_rnacentral.py > $LOGDIR/build_rnacentral_corpus.log 2>&1"
fi

# ---- 3. 训练（续训优先，卡号从 START_GPU 起轮转）----
say "3) 提交训练"
gpu=$START_GPU
next_gpu() { gpu=$(( (gpu+1) % 8 )); [[ $gpu -eq 6 || $gpu -eq 7 ]] && next_gpu; true; }
submit() { # $1 run_dir $2 tag $3 corpus $4 ckpt(or NONE)
  local model; model=$(MODEL_OF "$1")
  local extra=()
  [[ $4 != NONE ]] && extra=(--resume-from "$MNT/runs/$1/$4")
  run bash -c "cd $ROOT && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
setsid nohup $PY -u -m rna_sc.train --model $model --seed 17 \
  --device $gpu --out-dir $MNT/runs/$1 --corpus-tag $2 \
  --budget-nt 2000000000 --early-stop-patience 5 \
  --train-parquet $MNT/data/$3 ${extra[*]:-} \
  > $LOGDIR/$1.log 2>&1 < /dev/null & echo launched:$1:GPU$gpu"
  next_gpu
}
for entry in "${TO_RESUME[@]}"; do
  IFS='|' read -r run ckpt _ corpus tag <<< "$entry"; submit "$run" "$tag" "$corpus" "$ckpt"
done
for entry in "${TO_RETRAIN[@]}"; do
  IFS='|' read -r run ckpt _ corpus tag <<< "$entry"; submit "$run" "$tag" "$corpus" "NONE"
done

# ---- 4. 值守恢复 ----
say "4) 值守 cron 恢复（去掉 #PAUSED# 前缀）"
if [[ $DRY_RUN -eq 1 ]]; then
  say "DRY: crontab -l | sed 's/^#PAUSED#//' | crontab -"
else
  crontab -l | sed 's/^#PAUSED#//' | crontab -
fi
say "   watch_all 重启"
run bash -c "cd $ROOT && (setsid nohup $PY -u -m rna_sc.watch_all >> $LOGDIR/watch_all.log 2>&1 < /dev/null &) ; sleep 3"
run bash -c "cd $ROOT && (setsid nohup $PY -u t437_gpu_watch.py >> $LOGDIR/t437_gpu_watch.log 2>&1 < /dev/null &) ; sleep 3"

say "5) 完成。30 分钟后请核对：ps aux | grep rna_sc.train；tail 各 $LOGDIR/RNA-Sc-*_s17*.log"
say "   （本地两条定时任务需在 TRAE 中手动 resume）"
exit 0
