"""GPU selection by real free memory (torch.cuda.mem_get_info).

nvidia-smi snapshots under-report shared-GPU contention (other users'
processes ramp after launch and caused the first wave's OOM). mem_get_info
reports the allocator-truth at launch time; runs still keep a hard OOM
guard in-process. This module NEVER gates on "GPU busy" — only on real
free memory below the model's need (safety margin included).
"""
from __future__ import annotations

import torch

SAFETY_MARGIN_GB = 1.5


def gpu_free(i: int) -> float:
    free, _total = torch.cuda.mem_get_info(i)
    return free / 1e9


def report() -> list[tuple[int, float]]:
    return [(i, gpu_free(i)) for i in range(torch.cuda.device_count())]


def pick(need_gb: float, exclude: set[int] = frozenset()) -> int:
    """Best free GPU with at least need_gb + margin; raises if none."""
    for i, free in sorted(report(), key=lambda t: -t[1]):
        if i in exclude:
            continue
        if free >= need_gb + SAFETY_MARGIN_GB:
            return i
    raise RuntimeError(
        "no GPU with %.1fGB+free (margin %.1fGB): %s"
        % (need_gb, SAFETY_MARGIN_GB, report()))
