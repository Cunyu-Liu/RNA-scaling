"""GPU guard + parameter census (TokBench census.py pattern, adapted).

cpu_fallback_count must stay 0 everywhere: CPU silent degradation stops the
run and preserves evidence (contract rule).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Census:
    total_params: int = 0
    non_embedding_params: int = 0
    embedding_params: int = 0

    def __post_init__(self):
        self.embedding_params = self.total_params - self.non_embedding_params

    def within(self, target: int, tol: float = 0.10) -> bool:
        return abs(self.total_params - target) / target <= tol


_EMBEDDING_MARKERS = ("tok_emb", "lm_head", "cls_emb")


def count_params(model) -> Census:
    total = 0
    non_emb = 0
    for name, p in model.named_parameters():
        n = p.numel()
        total += n
        if not any(m in name for m in _EMBEDDING_MARKERS):
            non_emb += n
    return Census(total_params=total, non_embedding_params=non_emb)


class GPUGuard:
    def __init__(self, device: str):
        self.device = device
        self.cpu_fallback_count = 0

    def check(self) -> str:
        if self.device.startswith("cpu"):
            self.cpu_fallback_count += 1
            raise RuntimeError(
                "CPU fallback denied: neural execution requires CUDA. "
                "fallback_count=%d" % self.cpu_fallback_count)
        return self.device

    def verify_cuda_alive(self):
        import torch
        if not torch.cuda.is_available():
            self.cpu_fallback_count += 1
            raise RuntimeError(
                "CUDA lost mid-run (silent degradation); fallback_count=%d"
                % self.cpu_fallback_count)
