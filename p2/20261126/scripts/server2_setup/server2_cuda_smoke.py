import json
import os
import sys

import torch

CODE = "/home/cunyuliu/rna-sc-p2/code_git"
RUN = "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/weights/RNA-Sc-650M_s17"
OUT = "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/server2_setup/cuda_smoke.json"

if not torch.cuda.is_available():
    raise RuntimeError("CUDA unavailable; refusing CPU fallback")

sys.path.insert(0, CODE)
from rna_sc.probe import load_encoder

device = torch.device("cuda:0")
model, ckpt = load_encoder(RUN)
model = model.to(device).eval()
assert next(model.parameters()).device.type == "cuda"
allocated_after_load = torch.cuda.memory_allocated(device)
torch.cuda.reset_peak_memory_stats(device)
ids = torch.randint(0, 4, (2, 128), dtype=torch.long, device=device)
with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
    logits, loss = model(ids)
torch.cuda.synchronize(device)
assert logits.device.type == "cuda"
assert logits.shape == (2, 128, 7)
assert bool(torch.isfinite(logits).all())
assert loss is None
result = {
    "status": "PASS",
    "torch": torch.__version__,
    "torch_cuda_build": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "device_name": torch.cuda.get_device_name(device),
    "device_capability": list(torch.cuda.get_device_capability(device)),
    "run": os.path.basename(RUN),
    "ckpt_nt": ckpt["nt"],
    "model_tensors": len(ckpt["model"]),
    "optimizer_present": "opt" in ckpt,
    "model_device": str(next(model.parameters()).device),
    "logits_device": str(logits.device),
    "input_shape": list(ids.shape),
    "logits_shape": list(logits.shape),
    "logits_dtype": str(logits.dtype),
    "logits_finite": True,
    "memory_allocated_after_load_mib": round(allocated_after_load / 2**20, 2),
    "memory_allocated_after_forward_mib": round(torch.cuda.memory_allocated(device) / 2**20, 2),
    "memory_reserved_after_forward_mib": round(torch.cuda.memory_reserved(device) / 2**20, 2),
    "peak_memory_allocated_mib": round(torch.cuda.max_memory_allocated(device) / 2**20, 2),
    "peak_memory_reserved_mib": round(torch.cuda.max_memory_reserved(device) / 2**20, 2),
}
with open(OUT, "w") as handle:
    json.dump(result, handle, indent=2)
print(json.dumps(result, indent=2))
