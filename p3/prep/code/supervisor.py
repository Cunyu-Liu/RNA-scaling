from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
LOGS = BASE / "logs/p3_1"
QUEUES = {
    "server1": ["RNA-Sc-300M_s29", "RNA-Sc-650M_s29"],
    "server2": ["RNA-Sc-300M_s43", "RNA-Sc-650M_s43"],
}


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def manifest_update(run_dir: Path, log) -> None:
    path = run_dir / "manifest.json"
    if not path.is_file():
        return
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    validations = manifest.get("validations", [])
    if not validations:
        return
    best = min(item["val_loss"] for item in validations)
    non_improving = 0
    for item in reversed(validations):
        if item["val_loss"] <= best:
            break
        non_improving += 1
    if non_improving >= 3:
        print(f"{utcnow()} VAL_PLATEAU_OBSERVED run={manifest['run_id']} "
              f"consecutive_non_improving={non_improving}; "
              f"NO_EARLY_STOP; continue_to={manifest.get('iso_budget_nt', manifest['config']['budget_nt'])}nt", flush=True)
    latest = validations[-1]
    print(f"{utcnow()} PROGRESS run={manifest['run_id']} nt={latest['nt']} "
          f"step={latest['step']} val={latest['val_loss']:.6f} "
          f"best={best:.6f}", flush=True)


def completed(spec: dict) -> dict:
    manifest = json.loads((Path(spec["out_dir"]) / "manifest.json").read_text())
    if manifest.get("status") != "DONE":
        raise RuntimeError("Run is not DONE")
    if manifest.get("stop_reason") != "budget":
        raise RuntimeError("Run stopped for a non-budget reason")
    if not spec["budget_nt"] <= manifest.get("final_nt", 0) <= spec["max_final_nt"]:
        raise RuntimeError("Run final_nt violates the iso-token endpoint")
    if manifest.get("cpu_fallback_count") != 0:
        raise RuntimeError("CPU fallback count is nonzero")
    if manifest.get("early_stop_patience") is not None:
        raise RuntimeError("Early stop was not disabled")
    checkpoints = manifest.get("checkpoints", [])
    targets = [item.get("retention_target_nt") for item in checkpoints]
    if targets != spec["retain_ckpt_nt"]:
        raise RuntimeError(f"Retained checkpoint targets do not match policy: {targets}")
    if checkpoints[-1]["nt"] != manifest["final_nt"]:
        raise RuntimeError("Final checkpoint does not match final_nt")
    if not (Path(spec["out_dir"]) / "manifest.json").is_file():
        raise RuntimeError("Final manifest missing")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=sorted(QUEUES), required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--max-attempts", type=int, default=20)
    args = parser.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    lock_path = LOGS / f"{args.server}.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"Another P3.1 supervisor holds {lock_path}")
        status_path = LOGS / f"{args.server}_status.json"
        status = {"server": args.server, "state": "STARTING", "utc": utcnow()}
        write_json(status_path, status)
        for run_id in QUEUES[args.server]:
            config = HERE / "configs" / f"{run_id}.json"
            spec = json.loads(config.read_text())
            run_log = LOGS / f"{run_id}.log"
            gate_receipt = LOGS / f"{run_id}_data_gate.json"
            preflight_receipt = LOGS / f"{run_id}_preflight.json"
            for attempt in range(1, args.max_attempts + 1):
                status.update({"state": "PREFLIGHT", "run_id": run_id,
                               "attempt": attempt, "utc": utcnow()})
                write_json(status_path, status)
                with run_log.open("a") as log:
                    subprocess.run([
                        args.python, str(HERE / "data_gate.py"),
                        "--data-parquet", spec["data_parquet"],
                        "--output", str(gate_receipt),
                    ], stdout=log, stderr=subprocess.STDOUT, check=True)
                    subprocess.run([
                        args.python, str(HERE / "preflight.py"),
                        "--config", str(config), "--output", str(preflight_receipt),
                    ], stdout=log, stderr=subprocess.STDOUT, check=True)
                    print(f"{utcnow()} LAUNCH_ATTEMPT run={run_id} attempt={attempt}", flush=True)
                    process = subprocess.Popen([
                        args.python, str(HERE / "p3_train.py"),
                        "--config", str(config), "--resume-latest",
                    ], stdout=log, stderr=subprocess.STDOUT)
                    while process.poll() is None:
                        time.sleep(120)
                        manifest_update(Path(spec["out_dir"]), log)
                    returncode = process.wait()
                if returncode == 0:
                    final = completed(spec)
                    status.update({"state": "RUN_DONE", "run_id": run_id,
                                   "final_nt": final["final_nt"], "utc": utcnow()})
                    write_json(status_path, status)
                    break
                log_text = run_log.read_text(errors="replace")[-200_000:]
                if "CUDA out of memory" in log_text:
                    status.update({"state": "BLOCKED_OOM_NO_BATCH_RESIZE",
                                   "run_id": run_id, "utc": utcnow()})
                    write_json(status_path, status)
                    raise SystemExit(1)
                cuda_check = subprocess.run([
                    args.python, "-c", "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)"
                ]).returncode
                if cuda_check != 0:
                    status.update({"state": "BLOCKED_CUDA_UNAVAILABLE",
                                   "run_id": run_id, "utc": utcnow()})
                    write_json(status_path, status)
                    raise SystemExit(1)
                status.update({"state": "RETRY_FROM_CHECKPOINT", "run_id": run_id,
                               "attempt": attempt, "returncode": returncode,
                               "utc": utcnow()})
                write_json(status_path, status)
                time.sleep(60)
            else:
                status.update({"state": "BLOCKED_ATTEMPTS_EXHAUSTED",
                               "run_id": run_id, "utc": utcnow()})
                write_json(status_path, status)
                raise SystemExit(1)
        status.update({"state": "QUEUE_DONE", "utc": utcnow()})
        write_json(status_path, status)


if __name__ == "__main__":
    main()
