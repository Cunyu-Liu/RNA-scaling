from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import zipfile

import torch

CODE_ROOT = Path(__file__).resolve().parents[1] / "code_git"
import sys
sys.path.insert(0, str(CODE_ROOT))

from rna_sc import config as base_config
from rna_sc import train as base_train
from rna_sc.census import GPUGuard, count_params
from rna_sc.data import iter_mlm_batches, count_valid_nt


class SmokeInterrupt(RuntimeError):
    pass


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as handle:
        json.dump(value, handle, indent=2, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def load_spec(path: str | Path) -> dict:
    with Path(path).open() as handle:
        return json.load(handle)


RETENTION_TARGETS_NT = [500_000_000, 1_000_000_000, 1_500_000_000, 1_900_122_218]


def validate_retention_targets(targets: list[int], budget_nt: int) -> list[int]:
    if (not targets or any(not isinstance(value, int) or value <= 0 for value in targets)
            or targets != sorted(set(targets)) or targets[-1] != budget_nt):
        raise RuntimeError(f"Invalid retained checkpoint targets: {targets!r}")
    return targets


def due_retention_target(cumulative_nt: int, checkpoints: list[dict],
                         targets: list[int]) -> int | None:
    saved = {int(checkpoint["retention_target_nt"]) for checkpoint in checkpoints}
    due = [target for target in targets if cumulative_nt >= target and target not in saved]
    if len(due) > 1:
        raise RuntimeError(f"Multiple retention targets crossed at once: {due}")
    return due[0] if due else None


def resolve_frozen(spec: dict):
    device = "cuda:%d" % spec["device"]
    cfg = base_config.resolve_config(
        spec["model_id"], spec["seed"], device,
        budget_nt=spec["schedule_budget_nt"])
    expected = {
        "budget_nt": spec["schedule_budget_nt"],
        "batch_nt": spec["batch_nt"],
        "context_nt": spec["context_nt"],
        "lr": spec["lr"],
        "warmup_nt": spec["warmup_nt"],
        "ckpt_nt": spec["ckpt_nt"],
        "val_interval_nt": spec["val_interval_nt"],
        "val_nt": spec["val_nt"],
        "val_split": spec["val_split"],
        "mlm_p": spec["mlm_p"],
    }
    for key, value in expected.items():
        actual = getattr(cfg, key)
        if actual != value:
            raise RuntimeError(f"Frozen config mismatch {key}: {actual!r} != {value!r}")
    if spec["early_stop_patience"] != 0:
        raise RuntimeError("P3.1 forbids early stopping")
    validate_retention_targets(spec["retain_ckpt_nt"], spec["budget_nt"])
    if spec["retain_ckpt_nt"] != RETENTION_TARGETS_NT:
        raise RuntimeError(
            f"P3.1 retention amendment requires {RETENTION_TARGETS_NT}: "
            f"{spec['retain_ckpt_nt']!r}")
    if spec["max_final_nt"] != spec["budget_nt"]:
        raise RuntimeError("P3.1 requires exact iso-budget final_nt with no overshoot allowance")
    return cfg


def valid_checkpoint(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def find_resume(out_dir: Path) -> Path | None:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    with manifest_path.open() as handle:
        manifest = json.load(handle)
    for checkpoint in reversed(manifest.get("checkpoints", [])):
        path = Path(checkpoint["path"])
        if path.parent != out_dir:
            raise RuntimeError(f"Checkpoint outside run directory: {path}")
        if valid_checkpoint(path):
            return path
    return None


def save_checkpoint(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".pt.tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def run(cfg, spec: dict, resume_from: Path | None = None,
        interrupt_after_nt: int | None = None) -> dict:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; refusing CPU fallback")
    dev = cfg.device
    guard = GPUGuard(dev)
    guard.check()
    base_config.SPLIT_8080 = spec["data_parquet"]
    base_train.SPLIT_8080 = spec["data_parquet"]
    out_dir = Path(spec["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    retention_targets = validate_retention_targets(
        spec["retain_ckpt_nt"], spec["budget_nt"])

    old_manifest = None
    if resume_from is not None:
        if not manifest_path.is_file():
            raise RuntimeError("Resume requires the previous manifest")
        with manifest_path.open() as handle:
            old_manifest = json.load(handle)
        if old_manifest.get("retention_targets_nt") != retention_targets:
            raise RuntimeError("Cannot resume with a different checkpoint retention policy")
    elif manifest_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing run: {out_dir}")

    torch.manual_seed(cfg.seed)
    model = base_train.build_model(cfg).to(dev)
    pc = count_params(model)
    if pc.total_params != spec["expected_params"]:
        raise RuntimeError(f"Parameter mismatch: {pc.total_params}")
    opt = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, betas=tuple(spec["betas"]),
        weight_decay=spec["weight_decay"])

    cumulative_nt = 0
    step = 0
    replay_target_nt = None
    replayed_nt = 0
    last_val_nt = 0
    best_val = float("inf")
    best_ck = None
    elapsed_before = 0.0
    previous_peak = 0.0
    if old_manifest is not None:
        best_val = old_manifest.get("best_val_loss", float("inf"))
        best_ck = old_manifest.get("best_checkpoint")
        elapsed_before = old_manifest.get("elapsed_seconds", 0.0)
        previous_peak = old_manifest.get("peak_vram_mb", 0.0)
    if resume_from is not None:
        payload = torch.load(resume_from, map_location=dev, weights_only=False)
        model.load_state_dict(payload["model"])
        opt.load_state_dict(payload["opt"])
        cumulative_nt = int(payload["nt"])
        step = int(payload["step"])
        replay_target_nt = cumulative_nt
        last_val_nt = cumulative_nt
        print(f"[resume-fixed] {resume_from} nt={cumulative_nt} step={step}; "
              "data replay does not increment nt or optimizer steps", flush=True)

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(dev)
    if old_manifest is None:
        manifest = {
            "project": "rna-sc",
            "run_id": spec["run_id"],
            "model_id": spec["model_id"],
            "role": cfg.spec.role,
            "seed": spec["seed"],
            "device": dev,
            "config": cfg.to_dict(),
            "params": pc.total_params,
            "non_embedding_params": pc.non_embedding_params,
            "retention_targets_nt": retention_targets,
            "iso_budget_nt": spec["budget_nt"],
            "schedule_budget_nt": cfg.budget_nt,
            "checkpoints": [],
            "validations": [],
            "resume_events": [],
            "start_utc": utcnow(),
        }
    else:
        manifest = old_manifest
        manifest["device"] = dev
        manifest["config"] = cfg.to_dict()
    manifest["status"] = "RUNNING"
    manifest["early_stop_patience"] = None
    if resume_from is not None:
        manifest.setdefault("resume_events", []).append({
            "utc": utcnow(), "path": str(resume_from),
            "nt": cumulative_nt, "step": step,
        })
    atomic_json(manifest_path, manifest)

    done = False
    while not done:
        gen = iter_mlm_batches(
            spec["data_parquet"], "train", cfg.seed, cfg.context_nt,
            cfg.batch_nt, corpus_nseq=None)
        for batch in gen:
            if cumulative_nt >= spec["budget_nt"]:
                done = True
                break
            valid_nt = count_valid_nt(batch)
            if replay_target_nt is not None and replayed_nt < replay_target_nt:
                replayed_nt += valid_nt
                if replayed_nt > replay_target_nt:
                    raise RuntimeError(
                        f"Data replay overshot checkpoint: {replayed_nt} > {replay_target_nt}")
                continue
            ids = base_train._t(batch, "ids", dev)
            tgt = base_train._t(batch, "targets", dev)
            for group in opt.param_groups:
                group["lr"] = base_train.lr_at(cumulative_nt, cfg)
            model.train()
            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                _, loss = model(ids, tgt)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), spec["grad_clip_norm"])
            opt.step()
            cumulative_nt += valid_nt
            step += 1
            if step % 200 == 0:
                print(f"[{spec['run_id']}] nt={cumulative_nt / 1e6:.0f}M "
                      f"step={step} loss={float(loss.item()):.4f} "
                      f"lr={opt.param_groups[0]['lr']:.2e}", flush=True)
            if (cumulative_nt >= spec["budget_nt"] or
                    (cfg.val_interval_nt and
                     cumulative_nt - last_val_nt >= cfg.val_interval_nt)):
                last_val_nt = cumulative_nt
                validation = base_train.validate(cfg, model, dev)
                if validation["cpu_fallback_count"] != 0:
                    raise RuntimeError("CPU fallback during validation")
                manifest["validations"].append({
                    "nt": cumulative_nt, "step": step, **validation})
                retention_target = due_retention_target(
                    cumulative_nt, manifest["checkpoints"], retention_targets)
                if retention_target is not None:
                    ck_path = out_dir / f"ckpt_nt{cumulative_nt:09d}_step{step:06d}.pt"
                    save_checkpoint(ck_path, {
                        "model": model.state_dict(), "opt": opt.state_dict(),
                        "nt": cumulative_nt, "step": step,
                        "val_loss": validation["val_loss"], "run_id": spec["run_id"],
                        "model_id": spec["model_id"], "seed": spec["seed"],
                        "retention_target_nt": retention_target,
                        "cfg": cfg.to_dict(),
                    })
                    manifest["checkpoints"].append({
                        "nt": cumulative_nt, "step": step,
                        "retention_target_nt": retention_target,
                        "val_loss": validation["val_loss"], "path": str(ck_path),
                    })
                    if validation["val_loss"] < best_val:
                        best_val = validation["val_loss"]
                        best_ck = str(ck_path)
                    print(f"[{spec['run_id']}] RETAINED_CKPT "
                          f"target_nt={retention_target} actual_nt={cumulative_nt} "
                          f"path={ck_path}", flush=True)
                print(f"[{spec['run_id']}] VAL nt={cumulative_nt} step={step} "
                      f"val={validation['val_loss']:.4f} best={best_val:.4f}; "
                      "early_stop=DISABLED", flush=True)
                manifest.update({
                    "best_val_loss": best_val,
                    "best_checkpoint": best_ck,
                    "elapsed_seconds": elapsed_before + time.time() - t0,
                    "status": "RUNNING",
                })
                atomic_json(manifest_path, manifest)
                if interrupt_after_nt is not None and cumulative_nt >= interrupt_after_nt:
                    manifest["status"] = "INTERRUPTED_SMOKE"
                    atomic_json(manifest_path, manifest)
                    raise SmokeInterrupt(f"Intentional smoke interruption at {cumulative_nt}")
        done = True

    if replay_target_nt is not None and replayed_nt != replay_target_nt:
        raise RuntimeError(f"Replay incomplete: {replayed_nt} != {replay_target_nt}")
    if not spec["budget_nt"] <= cumulative_nt <= spec["max_final_nt"]:
        raise RuntimeError(f"Budget endpoint violation: final_nt={cumulative_nt}")
    guard.verify_cuda_alive()
    retained_targets = [
        checkpoint["retention_target_nt"] for checkpoint in manifest["checkpoints"]]
    if retained_targets != retention_targets:
        raise RuntimeError(
            f"Retained checkpoint set incomplete: {retained_targets} != {retention_targets}")
    final_checkpoint = manifest["checkpoints"][-1]
    if final_checkpoint["nt"] != cumulative_nt or not valid_checkpoint(
            Path(final_checkpoint["path"])):
        raise RuntimeError("Final retained checkpoint is missing or does not match final_nt")
    elapsed = elapsed_before + time.time() - t0
    peak = max(previous_peak, torch.cuda.max_memory_allocated(dev) / (1024 ** 2))
    manifest.update({
        "final_nt": cumulative_nt,
        "final_checkpoint": final_checkpoint["path"],
        "final_step": step,
        "best_val_loss": best_val if best_val != float("inf") else None,
        "best_checkpoint": best_ck,
        "throughput_nt_s": cumulative_nt / max(1e-9, elapsed),
        "peak_vram_mb": peak,
        "wall_seconds": elapsed,
        "elapsed_seconds": elapsed,
        "cpu_fallback_count": guard.cpu_fallback_count,
        "end_utc": utcnow(),
        "status": "DONE",
        "stop_reason": "budget",
        "early_stop_patience": None,
        "cosine_truncated": False,
    })
    atomic_json(manifest_path, manifest)
    print(f"DONE {spec['run_id']} | nt={cumulative_nt} steps={step} "
          f"best_val={best_val:.4f} | {manifest['throughput_nt_s']:.0f} nt/s "
          f"peak={peak:.0f}MB fallback={guard.cpu_fallback_count}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume-latest", action="store_true")
    args = parser.parse_args()
    spec = load_spec(args.config)
    cfg = resolve_frozen(spec)
    out_dir = Path(spec["out_dir"])
    resume = find_resume(out_dir) if args.resume_latest else None
    manifest_path = out_dir / "manifest.json"
    if args.resume_latest and manifest_path.is_file():
        with manifest_path.open() as handle:
            old = json.load(handle)
        if old.get("status") == "DONE":
            if old.get("stop_reason") != "budget":
                raise RuntimeError("Completed run has non-budget stop reason")
            print(f"ALREADY_DONE {spec['run_id']} final_nt={old.get('final_nt')}")
            return
        if resume is None:
            archived = out_dir / f"manifest.before_restart_{int(time.time())}.json"
            os.replace(manifest_path, archived)
            print(f"NO_VALID_CHECKPOINT; restarting same deterministic run; "
                  f"old_manifest={archived}", flush=True)
    run(cfg, spec, resume_from=resume)


if __name__ == "__main__":
    main()
