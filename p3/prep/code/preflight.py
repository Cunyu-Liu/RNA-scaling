from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import torch

from p3_train import load_spec, resolve_frozen

HOME = Path("/home/cunyuliu/rna-sc-p2")
EXPECTED_SOURCE_SHA256 = {
    "train.py": "4ef53be57ed2c4b996d9a01d7c7d21d06018a2ad32771e8004e8798515fbc6ef",
    "config.py": "e1fef7c37cd1ec2d79f95c872a773859bd517a6a3914e981f7d0557bc10295e6",
    "data.py": "e6355986132944437de73e65b07a55d2360b6674e14ad055c704a62f16e4eafa",
    "specs.py": "6773c6adb54bae6d04ae7fad5b62472ecc2e5299d39e662a7a8376beea309833",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    parser.add_argument("--skip-resource-checks", action="store_true")
    args = parser.parse_args()
    spec = load_spec(args.config)
    cfg = resolve_frozen(spec)
    checks = {}
    for name, expected in EXPECTED_SOURCE_SHA256.items():
        actual = file_sha256(HOME / "code_git/rna_sc" / name)
        checks[f"source_{name}"] = actual == expected
    checks["cuda_available"] = torch.cuda.is_available()
    if torch.cuda.is_available():
        checks["cuda_device_valid"] = spec["device"] < torch.cuda.device_count()
    else:
        checks["cuda_device_valid"] = False
    if not args.skip_resource_checks:
        query = subprocess.check_output([
            "nvidia-smi", f"--id={spec['device']}",
            "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits",
        ], text=True).strip()
        total, used = [int(value) for value in query.split(",")]
        free = total - used
        disk = shutil.disk_usage(Path(spec["out_dir"]).parent)
        checks["free_vram"] = free >= spec["required_free_vram_mib"]
        checks["free_disk"] = disk.free // (1024 ** 2) >= spec["required_free_disk_mib"]
    result = {
        "run_id": spec["run_id"],
        "retain_ckpt_nt": spec["retain_ckpt_nt"],
        "iso_budget_nt": spec["budget_nt"],
        "schedule_budget_nt": spec["schedule_budget_nt"],
        "retained_checkpoint_count": len(spec["retain_ckpt_nt"]),
        "resolved_config": cfg.to_dict(),
        "checks": checks,
        "pass": all(checks.values()),
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text)
    print(text, end="")
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
