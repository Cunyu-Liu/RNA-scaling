from __future__ import annotations

import hashlib
import json
import math
import os
import random
from pathlib import Path

import numpy as np
import torch

ALPHABET = "ACGU"
K = 10
N_REAL = 1500
RAND_MULT = 3
LONG_RANGE = 24
LEN_CAP = 160
BATCH = 4
SEED = 17
BOOTSTRAP_N = 2000
EXPECTED_SPLIT_COUNTS = {
    "family_test": 7082895,
    "family_validation": 7525752,
    "test": 108979,
    "train": 14130321,
    "validation": 164280,
}
EXPECTED_SPLIT_ROWS = 29012227
ROOT = Path(os.environ.get(
    "RNA_SC_P2_ROOT", "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2"))
OUT = ROOT / "results" / "P2_4"
BPRNA = ROOT / "data" / "bpRNA_parsed.parquet"
SPLIT = ROOT / "data" / "release22_split_8080.parquet"
WEIGHTS = ROOT / "weights"
ARMS = {
    "100M": {"run": "RNA-Sc-100M_s17", "layers": 23, "layer": 16,
             "randinit": False},
    "650M": {"run": "RNA-Sc-650M_s17", "layers": 28, "layer": 20,
             "randinit": False},
    "randinit": {"run": "RNA-Sc-100M_s17", "layers": 23, "layer": 16,
                 "randinit": True},
}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                              allow_nan=False) + "\n")
    tmp.replace(path)


def clean_seq(seq: str) -> str:
    return "".join(b for b in seq.upper().replace("T", "U")
                   if b in ALPHABET)[:LEN_CAP]


def pair_mask(pairs, length: int) -> torch.Tensor:
    mask = torch.zeros(length, dtype=torch.long)
    for pair in pairs or []:
        i, j = pair
        i0, j0 = i - 1, j - 1
        if 0 <= i0 < length and 0 <= j0 < length:
            mask[i0] = 1
            mask[j0] = 1
    return mask


def long_range_mask(pairs, length: int) -> torch.Tensor:
    mask = torch.zeros(length, dtype=torch.bool)
    for pair in pairs or []:
        i, j = pair
        i0, j0 = i - 1, j - 1
        if (0 <= i0 < length and 0 <= j0 < length
                and abs(i0 - j0) >= LONG_RANGE):
            mask[i0] = True
            mask[j0] = True
    return mask


def paired_f1(truth: torch.Tensor, pred: torch.Tensor) -> float:
    tp = ((pred == 1) & (truth == 1)).sum().item()
    fp = ((pred == 1) & (truth == 0)).sum().item()
    fn = ((pred == 0) & (truth == 1)).sum().item()
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return float(2 * precision * recall / max(1e-9, precision + recall))


def coordinate_validation() -> dict:
    cases = {
        "one_based_1_4_marks_0_3": pair_mask([[1, 4]], 4).tolist() == [1, 0, 0, 1],
        "zero_is_invalid_one_based": pair_mask([[0, 3]], 4).tolist() == [0, 0, 0, 0],
        "out_of_cap_excluded": pair_mask([[2, 5]], 4).tolist() == [0, 0, 0, 0],
        "long_range_1_25_marks_0_24": long_range_mask([[1, 25]], 25).tolist()
        == [True] + [False] * 23 + [True],
        "short_range_1_24_excluded": not long_range_mask([[1, 24]], 24).any().item(),
    }
    assert all(cases.values()), cases
    return {"passed": True, "cases": cases, "rule": "i0=i-1; j0=j-1"}


def stream_real(n_needed: int = N_REAL, seed: int = SEED,
                split_path: str | Path = SPLIT):
    import pyarrow.parquet as pq
    seqs = []
    pf = pq.ParquetFile(split_path)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence", "rna_type"]):
        d = rb.to_pydict()
        for membership, seq, rna_type in zip(
                d["split_membership"], d["canonical_sequence"], d["rna_type"]):
            if membership != "family_validation":
                continue
            seqs.append((seq.upper().replace("T", "U")[:256], rna_type))
            if len(seqs) >= n_needed * 3:
                break
        if len(seqs) >= n_needed * 3:
            break
    rng = random.Random(seed)
    rng.shuffle(seqs)
    return seqs[:n_needed]


def make_random_pool(real_seqs, mult: int = RAND_MULT, seed: int = SEED):
    rng = random.Random(seed)
    mono = {b: 0 for b in ALPHABET}
    di = {}
    total = 0
    for seq in real_seqs:
        for b in seq:
            if b in ALPHABET:
                mono[b] += 1
                total += 1
        for a, b in zip(seq, seq[1:]):
            if a in ALPHABET and b in ALPHABET:
                di[a + b] = di.get(a + b, 0) + 1
    p_mono = {b: mono[b] / max(1, total) for b in ALPHABET}
    total_di = sum(di.values())
    p_di = {key: value / max(1, total_di) for key, value in di.items()}
    out = []
    lengths = [len(seq) for seq in real_seqs]
    for _ in range(mult * len(real_seqs)):
        length = lengths[rng.randrange(len(lengths))]
        cur = rng.choices(ALPHABET, weights=[p_mono[b] for b in ALPHABET])[0]
        seq = [cur]
        for _ in range(length - 1):
            weights = [max(1e-6, p_di.get(cur + b, 0.0)) for b in ALPHABET]
            cur = rng.choices(ALPHABET, weights=weights)[0]
            seq.append(cur)
        out.append("".join(seq))
    return out, p_mono, p_di


def mono_freq(seqs) -> dict:
    counts = {b: 0 for b in ALPHABET}
    total = 0
    for seq in seqs:
        for b in seq:
            if b in ALPHABET:
                counts[b] += 1
                total += 1
    return {b: counts[b] / max(1, total) for b in ALPHABET}


def di_freq(seqs) -> dict:
    counts = {a + b: 0 for a in ALPHABET for b in ALPHABET}
    total = 0
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            if a in ALPHABET and b in ALPHABET:
                counts[a + b] += 1
                total += 1
    return {key: value / max(1, total) for key, value in counts.items()}


def ks_check(real_lengths, random_lengths) -> tuple[float, float]:
    a = np.sort(np.asarray(real_lengths, dtype=float))
    b = np.sort(np.asarray(random_lengths, dtype=float))
    all_values = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, all_values, side="right") / len(a)
    cdf_b = np.searchsorted(b, all_values, side="right") / len(b)
    d = float(np.max(np.abs(cdf_a - cdf_b)))
    n_eff = len(a) * len(b) / (len(a) + len(b))
    lam = (math.sqrt(n_eff) + 0.12 + 0.11 / math.sqrt(n_eff)) * d
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam)
                for k in range(1, 51))
    return round(d, 4), round(min(1.0, max(0.0, p)), 4)


def average_rank(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        sorted_ranks[start:end] = (start + 1 + end) / 2.0
        start = end
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = sorted_ranks
    return ranks


def residual_on_length(values, length_ranks) -> np.ndarray:
    design = np.column_stack([np.ones(len(values)), length_ranks])
    beta = np.linalg.lstsq(design, values, rcond=None)[0]
    return values - design @ beta
