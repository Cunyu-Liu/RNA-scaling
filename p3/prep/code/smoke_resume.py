from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "code_git"))
from rna_sc import config as base_config
from rna_sc.census import count_params
from rna_sc.train import build_model
from p3_train import SmokeInterrupt, find_resume, run
import pyarrow as pa
import pyarrow.parquet as pq


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; resume smoke refused CPU fallback")
    work = args.output.parent / "resume_test_retention"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    parquet = work / "tiny.parquet"
    sequences = []
    for i in range(512):
        seed = torch.Generator().manual_seed(i)
        ids = torch.randint(0, 4, (128,), generator=seed).tolist()
        sequences.append("".join("ACGU"[value] for value in ids))
    pq.write_table(pa.table({
        "split_membership": ["train"] * 384 + ["validation"] * 128,
        "canonical_sequence": sequences,
        "cluster_id": [str(i) for i in range(512)],
        "rna_type": ["synthetic"] * 512,
    }), parquet)
    cfg = base_config.resolve_config("RNA-Sc-1M", 29, "cuda:0", budget_nt=32768)
    cfg = replace(cfg, batch_nt=1024, context_nt=128, warmup_nt=1024,
                  ckpt_nt=16384, val_interval_nt=16384, val_nt=1024)
    expected_params = count_params(build_model(cfg)).total_params

    def spec(name: str) -> dict:
        return {
            "run_id": name, "model_id": "RNA-Sc-1M", "seed": 29,
            "device": 0, "expected_params": expected_params,
            "data_parquet": str(parquet), "out_dir": str(work / name),
            "budget_nt": 32768, "max_final_nt": 32768,
            "retain_ckpt_nt": [16384, 32768],
            "betas": [0.9, 0.95], "weight_decay": 0.1,
            "grad_clip_norm": 1.0, "early_stop_patience": 0,
        }

    continuous_spec = spec("continuous")
    resumed_spec = spec("resumed")
    continuous = run(cfg, continuous_spec)
    interrupted = False
    try:
        run(cfg, resumed_spec, interrupt_after_nt=16384)
    except SmokeInterrupt:
        interrupted = True
    if not interrupted:
        raise RuntimeError("Smoke interruption did not occur")
    checkpoint = find_resume(Path(resumed_spec["out_dir"]))
    if checkpoint is None:
        raise RuntimeError("No valid resume checkpoint")
    resumed = run(cfg, resumed_spec, resume_from=checkpoint)
    continuous_last = continuous["checkpoints"][-1]["path"]
    resumed_last = resumed["checkpoints"][-1]["path"]
    left = torch.load(continuous_last, map_location="cpu", weights_only=False)
    right = torch.load(resumed_last, map_location="cpu", weights_only=False)
    tensor_mismatches = [
        name for name in left["model"]
        if not torch.equal(left["model"][name], right["model"][name])
    ]
    result = {
        "mode": "SYNTHETIC_CUDA_RESUME_SMOKE_ONLY",
        "interruption_observed": interrupted,
        "resume_checkpoint": str(checkpoint),
        "continuous_final_nt": continuous["final_nt"],
        "resumed_final_nt": resumed["final_nt"],
        "continuous_final_step": continuous["final_step"],
        "resumed_final_step": resumed["final_step"],
        "expected_final_step": 32,
        "continuous_validation_nt": [v["nt"] for v in continuous["validations"]],
        "resumed_validation_nt": [v["nt"] for v in resumed["validations"]],
        "continuous_retention_targets": [
            c["retention_target_nt"] for c in continuous["checkpoints"]],
        "resumed_retention_targets": [
            c["retention_target_nt"] for c in resumed["checkpoints"]],
        "resumed_final_checkpoint": resumed["final_checkpoint"],
        "model_tensor_mismatches": tensor_mismatches,
        "resumed_stop_reason": resumed["stop_reason"],
        "cpu_fallback_count": resumed["cpu_fallback_count"],
    }
    result["pass"] = (
        continuous["final_nt"] == resumed["final_nt"] == 32768 and
        continuous["final_step"] == resumed["final_step"] == 32 and
        result["resumed_validation_nt"] == [16384, 32768] and
        result["continuous_retention_targets"] == [16384, 32768] and
        result["resumed_retention_targets"] == [16384, 32768] and
        Path(resumed["final_checkpoint"]).is_file() and
        not tensor_mismatches and resumed["stop_reason"] == "budget" and
        resumed["cpu_fallback_count"] == 0
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
