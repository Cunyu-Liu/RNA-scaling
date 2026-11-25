from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow
import torch

from p2_4_common import ARMS, BPRNA, OUT, ROOT, SPLIT, WEIGHTS, sha256, write_json


def file_record(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main():
    validation_path = OUT / "p2_4_validation.json"
    validation = json.loads(validation_path.read_text())
    inputs = []
    for path in sorted((OUT / "code").glob("*")):
        if path.is_file():
            inputs.append(file_record(path))
    for path in sorted((OUT / "prereg").glob("*.md")):
        inputs.append(file_record(path))
    inputs.append(file_record(BPRNA))
    if SPLIT.is_file():
        inputs.append(file_record(SPLIT))
    checkpoint_paths = set()
    for spec in ARMS.values():
        checkpoint_paths.add(WEIGHTS / spec["run"] / "ckpt_nt1900122218_step202784.pt")
    for path in sorted(checkpoint_paths):
        inputs.append(file_record(path))
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"manifest.json", "manifest_sha256.tsv"}:
            continue
        if "code" in path.relative_to(OUT).parts or "prereg" in path.relative_to(OUT).parts:
            continue
        outputs.append({"path": str(path.relative_to(OUT)), "bytes": path.stat().st_size,
                        "sha256": sha256(path)})
    summaries = []
    for arm in ARMS:
        path = OUT / "units" / arm / "unit_summary.json"
        if path.is_file():
            summaries.append(json.loads(path.read_text()))
    blocker = None
    blocker_path = OUT / "p2_4_input_blocker.json"
    if blocker_path.is_file():
        blocker = json.loads(blocker_path.read_text())
    manifest = {
        "task": "X-P24 / P2.4",
        "status": validation["status"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "formal_run_started": bool(summaries),
        "completed_arms": [summary["arm"] for summary in summaries],
        "input_blocker": blocker,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "numpy": np.__version__, "pandas": pd.__version__, "pyarrow": pyarrow.__version__,
        },
        "gpu": {
            "max_project_budget_bytes": 20 * 1024 ** 3,
            "units": [{
                "arm": summary["arm"],
                "max_memory_reserved_bytes": summary["max_memory_reserved_bytes"],
                "forward_batch_reductions": summary["forward_batch_reductions"],
                "cpu_fallback_count": summary["cpu_fallback_count"],
            } for summary in summaries],
        },
        "validation": validation,
        "inputs": inputs,
        "outputs": outputs,
    }
    write_json(OUT / "manifest.json", manifest)
    lines = []
    for record in outputs:
        lines.append(f"{record['sha256']}\t{record['path']}\n")
    (OUT / "manifest_sha256.tsv").write_text("".join(lines))
    print(json.dumps({"status": manifest["status"], "n_inputs": len(inputs),
                      "n_outputs": len(outputs)}))


if __name__ == "__main__":
    main()
