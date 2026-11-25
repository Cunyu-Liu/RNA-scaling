import hashlib
import json
import os
import sys
from pathlib import Path

import torch

CODE = Path("/home/cunyuliu/rna-sc-p2/code_git")
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
WEIGHTS = BASE / "weights"
OUT = BASE / "results" / "upload_main"
EXPECTED = {
    "RNA-Sc-30M_s17": (1900121822, 202784, 101),
    "RNA-Sc-100M_s17": (1900122218, 202784, 189),
    "RNA-Sc-650M_s17": (1900122218, 202784, 229),
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    sys.path.insert(0, str(CODE))
    from rna_sc.probe import load_encoder

    local_hashes = {}
    with (OUT / "weight_source_strip_sha256.tsv").open() as handle:
        next(handle)
        for line in handle:
            run, filename, _, _, _, stripped_hash = line.rstrip("\n").split("\t")
            local_hashes[(run, filename)] = stripped_hash
    remote_records = json.loads((OUT / "remote_strip_verification.json").read_text())
    expected_hashes = {(row["run"], Path(row["target_path"]).name): row["target_sha256"]
                       for row in remote_records}

    device = torch.device("cuda:0")
    records = []
    for run, (expected_nt, expected_step, expected_tensors) in EXPECTED.items():
        run_dir = WEIGHTS / run
        checkpoints = sorted(run_dir.glob("ckpt_*.pt"))
        assert len(checkpoints) == 1, checkpoints
        path = checkpoints[0]
        actual_hash = sha256(path)
        assert actual_hash == expected_hashes[(run, path.name)]
        model, ckpt = load_encoder(str(run_dir), ckpt_nt=expected_nt)
        assert ckpt["nt"] == expected_nt and ckpt["step"] == expected_step
        assert len(ckpt["model"]) == expected_tensors
        assert "opt" not in ckpt
        model = model.to(device).eval()
        assert next(model.parameters()).device.type == "cuda"
        ids = torch.randint(0, 4, (2, 128), dtype=torch.long, device=device)
        torch.cuda.reset_peak_memory_stats(device)
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
            logits, loss = model(ids)
        torch.cuda.synchronize(device)
        assert logits.device.type == "cuda"
        assert logits.shape == (2, 128, 7)
        assert bool(torch.isfinite(logits).all())
        assert loss is None
        record = {
            "status": "PASS",
            "run": run,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": actual_hash,
            "sha256_matches_remote_strip_record": True,
            "local_torch28_container_sha256": local_hashes[(run, path.name)],
            "container_matches_local_torch28": actual_hash == local_hashes[(run, path.name)],
            "source_and_tensor_bitwise_verified": True,
            "strict_load": True,
            "model_tensors": len(ckpt["model"]),
            "optimizer_present": False,
            "ckpt_nt": ckpt["nt"],
            "step": ckpt["step"],
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(device),
            "model_device": str(next(model.parameters()).device),
            "logits_device": str(logits.device),
            "logits_shape": list(logits.shape),
            "logits_dtype": str(logits.dtype),
            "logits_finite": True,
            "peak_memory_allocated_mib": round(
                torch.cuda.max_memory_allocated(device) / 2**20, 2),
            "peak_memory_reserved_mib": round(
                torch.cuda.max_memory_reserved(device) / 2**20, 2),
        }
        records.append(record)
        (OUT / f"{run}_gpu_smoke.json").write_text(
            json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2), flush=True)
        del model, ckpt, logits, ids
        torch.cuda.empty_cache()
    summary = {
        "status": "PASS",
        "runs_passed": len(records),
        "runs_expected": len(EXPECTED),
        "cuda_fallback_count": 0,
        "records": records,
    }
    (OUT / "weight_verification.json").write_text(
        json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
