from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "code_git"))
from rna_sc.census import count_params
from rna_sc.train import build_model
from p3_train import load_spec, resolve_frozen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    spec = load_spec(args.config)
    cfg = resolve_frozen(spec)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; smoke aborted without CPU fallback")
    device = cfg.device
    torch.manual_seed(cfg.seed)
    model = build_model(cfg).to(device)
    params = count_params(model).total_params
    if params != spec["expected_params"]:
        raise RuntimeError(f"Parameter mismatch {params}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr,
                                  betas=(0.9, 0.95), weight_decay=0.1)
    ids = torch.randint(0, 4, (16, 1024), device=device)
    targets = torch.full((16, 1024), -100, dtype=torch.long, device=device)
    targets[:, ::7] = ids[:, ::7]
    model.train()
    torch.cuda.reset_peak_memory_stats(device)
    torch.cuda.synchronize(device)
    started = time.time()
    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        logits, loss = model(ids, targets)
    if logits.shape != (16, 1024, 7) or not torch.isfinite(loss):
        raise RuntimeError("Invalid logits or loss")
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    torch.cuda.synchronize(device)
    elapsed = time.time() - started
    checkpoint = args.output.parent / f"{spec['run_id']}.smoke_ckpt.pt"
    torch.save({"model": model.state_dict(), "opt": optimizer.state_dict(),
                "nt": 16384, "step": 1}, checkpoint)
    checkpoint_bytes = checkpoint.stat().st_size
    checkpoint.unlink()
    result = {
        "mode": "CUDA_SMOKE_ONLY_NOT_FORMAL_TRAINING",
        "run_id": spec["run_id"],
        "device": device,
        "gpu_name": torch.cuda.get_device_name(device),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "params": params,
        "input_shape": list(ids.shape),
        "logits_shape": list(logits.shape),
        "loss": float(loss.item()),
        "grad_norm": float(grad_norm),
        "step_seconds": elapsed,
        "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 1024 ** 2,
        "peak_reserved_mib": torch.cuda.max_memory_reserved(device) / 1024 ** 2,
        "checkpoint_bytes": checkpoint_bytes,
        "checkpoint_gib": checkpoint_bytes / 1024 ** 3,
        "estimated_19_checkpoint_gib": 19 * checkpoint_bytes / 1024 ** 3,
        "estimated_4_checkpoint_gib": 4 * checkpoint_bytes / 1024 ** 3,
        "cpu_fallback_count": 0,
        "pass": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
