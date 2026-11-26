#!/usr/bin/env bash
set -euo pipefail

BASE=/teams/HoulabData_1788502323/liucunyu/rna-sc-p2
WORK="$BASE/data/split_rebuild3"
LOGS="$BASE/logs/split_rebuild3"
CODE=/home/cunyuliu/rna-sc-p2/split_rebuild3
PY=/home/cunyuliu/rna-sc-p2/venv/bin/python
exec 9>"$LOGS/pipeline.lock"
flock -n 9 || { echo "pipeline already running"; exit 0; }
export PATH=/home/cunyuliu/rna-sc-p2/tools/mmseqs-18.8cc5c/mmseqs/bin:$PATH
export POLARS_MAX_THREADS=${POLARS_MAX_THREADS:-2}

stage() {
    printf '%s %s\n' "$(date -Is)" "$1" | tee "$LOGS/pipeline_stage.txt"
}

stage ENVIRONMENT_CHECK
"$PY" -c 'import polars, pyarrow; assert polars.__version__ == "1.43.2", polars.__version__; assert pyarrow.__version__ == "25.0.0", pyarrow.__version__; print(polars.__version__, pyarrow.__version__)'

stage WAIT_SOURCE_DOWNLOAD
source_pid=$(cat "$LOGS/download.pid")
while kill -0 "$source_pid" 2>/dev/null; do sleep 60; done
test ! -e "$WORK/rnacentral_active.fasta.gz.aria2"
test "$(stat -c %s "$WORK/rnacentral_active.fasta.gz")" -eq 7281938321
gzip -t "$WORK/rnacentral_active.fasta.gz"

stage WAIT_RFAM_DOWNLOAD
rfam_pid=$(cat "$LOGS/download_rfam.pid")
while kill -0 "$rfam_pid" 2>/dev/null; do sleep 20; done
test "$(stat -c %s "$WORK/rfam_annotations.tsv.gz")" -eq 331006468
gzip -t "$WORK/rfam_annotations.tsv.gz"
if [[ ! -s "$WORK/rfam_annotations.tsv" ]]; then
    gzip -dc "$WORK/rfam_annotations.tsv.gz" > "$WORK/rfam_annotations.tsv"
fi

if [[ ! -s "$WORK/release22_primary.parquet" || ! -s "$WORK/release22_qc.parquet" ]]; then
    stage CANONICALIZE
    "$PY" "$CODE/canonicalize.py" \
        --release-fasta "$WORK/rnacentral_active.fasta.gz" \
        --out-parquet "$WORK/release22_primary.parquet" \
        --out-qc "$WORK/release22_qc.parquet"
fi

if [[ ! -s "$WORK/release22_dedup.parquet" ]]; then
    stage DEDUP
    "$PY" "$CODE/dedup_lowmem.py" \
        --canonical-parquet "$WORK/release22_primary.parquet" \
        --out-parquet "$WORK/release22_dedup.parquet" \
        --work-dir "$WORK/dedup_partitions" \
        --n-partitions 16
fi

if [[ ! -s "$WORK/release22_cluster_8080.parquet" ]]; then
    stage MMSEQS_CLUSTER_8080
    mkdir -p "$WORK/mmseqs"
    "$PY" "$CODE/cluster.py" \
        --dedup-parquet "$WORK/release22_dedup.parquet" \
        --out-cluster-parquet "$WORK/release22_cluster_8080.parquet" \
        --out-fasta "$WORK/release22_dedup.fa" \
        --min-seq-id 0.8 --coverage 0.8 --cov-mode 1 --threads 32 \
        --tmp-dir "$WORK/mmseqs" --keep-cluster-files
fi

stage VERIFY_REPRESENTATIVES
"$PY" "$CODE/verify_representatives.py" \
    --cluster-tsv "$WORK/mmseqs/cluster_cluster.tsv" \
    --cluster-split "$BASE/data/release22_cluster_split.parquet" \
    --n-sequences 29012227 \
    --output-json "$WORK/representative_verify.json"

if [[ ! -s "$WORK/release22_split_8080.candidate.parquet" ]]; then
    stage SPLIT_CANDIDATE
    "$PY" "$CODE/split_lowmem.py" \
        --cluster-parquet "$WORK/release22_cluster_8080.parquet" \
        --rfam-annotations "$WORK/rfam_annotations.tsv" \
        --cluster-split-oracle "$BASE/data/release22_cluster_split.parquet" \
        --out-parquet "$WORK/release22_split_8080.candidate.parquet"
fi

stage VERIFY_DEEP_AND_ORACLE
"$PY" "$CODE/verify_split.py" \
    --split-parquet "$WORK/release22_split_8080.candidate.parquet" \
    --cluster-split "$BASE/data/release22_cluster_split.parquet" \
    --train-oracle "$WORK/r22_train_rfamcap.parquet" \
    --output-json "$WORK/split8080_deep_verify_rebuilt.json"

stage PROBE_COUNT_SMOKE
"$PY" "$CODE/probe_count_smoke.py" \
    --split-parquet "$WORK/release22_split_8080.candidate.parquet" \
    --output-json "$WORK/probe_count_smoke.json"

stage PUBLISH
if [[ -e "$BASE/data/release22_split_8080.parquet" ]]; then
    echo "REFUSE: final target already exists; not overwriting another artifact"
    exit 1
fi
mv "$WORK/release22_split_8080.candidate.parquet" "$BASE/data/release22_split_8080.parquet"
sha256sum "$BASE/data/release22_split_8080.parquet" \
    "$WORK/rnacentral_active.fasta.gz" \
    "$WORK/release22_primary.parquet" \
    "$WORK/release22_dedup.parquet" \
    "$WORK/release22_cluster_8080.parquet" \
    "$WORK/rfam_annotations.tsv.gz" > "$WORK/sha256sums.txt"
stage COMPLETE
