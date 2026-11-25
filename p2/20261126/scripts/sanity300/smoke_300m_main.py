import hashlib
import json
import sys
from pathlib import Path

import torch

CODE = Path("/home/cunyuliu/rna-sc-p2/code_git")
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
RUN = BASE / "weights/RNA-Sc-300M_s17"
OUT = BASE / "results/sanity300/gpu_smoke.json"
EXPECTED_SHA256 = "465ca31b2c520c2aa5168a7d57f660c6191d4198ce5811489e7db7ee7edfc443"


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
    checkpoints = sorted(RUN.glob("ckpt_*.pt"))
    assert len(checkpoints) == 1
    path = checkpoints[0]
    actual_hash = sha256(path)
    assert actual_hash == EXPECTED_SHA256
    model, ckpt = load_encoder(str(RUN), ckpt_nt=1900122218)
    assert ckpt["nt"] == 1900122218 and ckpt["step"] == 202784
    assert len(ckpt["model"]) == 197 and "opt" not in ckpt
    device = torch.device("cuda:0")
    model = model.to(device).eval()
    assert next(model.parameters()).is_cuda
    ids = torch.randint(0, 4, (2, 128), dtype=torch.long, device=device)
    torch.cuda.reset_peak_memory_stats(device)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        logits, loss = model(ids)
    torch.cuda.synchronize(device)
    assert logits.is_cuda and logits.shape == (2, 128, 7)
    assert bool(torch.isfinite(logits).all()) and loss is None
    record = {
        "status": "PASS",
        "run": "RNA-Sc-300M_s17",
        "path": str(path),
        "sha256": actual_hash,
        "strict_load": True,
        "model_tensors": len(ckpt["model"]),
        "optimizer_present": False,
        "checkpoint_nt": ckpt["nt"],
        "checkpoint_step": ckpt["step"],
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(device),
        "model_device": str(next(model.parameters()).device),
        "logits_device": str(logits.device),
        "logits_shape": list(logits.shape),
        "logits_dtype": str(logits.dtype),
        "logits_finite": True,
        "peak_memory_allocated_mib": torch.cuda.max_memory_allocated(device) / 2**20,
        "peak_memory_reserved_mib": torch.cuda.max_memory_reserved(device) / 2**20,
        "cpu_fallback_count": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
