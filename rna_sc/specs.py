"""Model specs for the controlled RNA-Sc MLM encoder family (SPEC S1/S2/S3).

Frozen recipe (SPEC 5): single-nucleotide tokenizer, MLM 15%, RNAcentral
ncRNA via the TokBench release22 split, ALiBi positions, identical
optimizer/schedule/budget across all sizes, exposure counted in nt.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSpec:
    model_id: str            # e.g. "RNA-Sc-10M"
    d_model: int
    n_layers: int
    n_heads: int
    d_ff: int
    target_params: int       # nominal total parameter target
    role: str                # "scaling" | "corpus" | "diversity" | "init_ctrl" | "seed_rep"
    note: str = ""
    seeds: tuple = (17,)     # formal seeds; 100M gets (17, 29, 43)


FAMILY = {
    "RNA-Sc-1M": ModelSpec(
        model_id="RNA-Sc-1M", d_model=64, n_layers=18, n_heads=2, d_ff=256,
        target_params=1_000_000, role="scaling",
        note="minimum-size baseline; deep-narrow form matches 2% band"),
    "RNA-Sc-10M": ModelSpec(
        model_id="RNA-Sc-10M", d_model=192, n_layers=20, n_heads=3, d_ff=768,
        target_params=10_000_000, role="scaling",
        note="second point on the scale axis; deep-narrow"),
    "RNA-Sc-30M": ModelSpec(
        model_id="RNA-Sc-30M", d_model=480, n_layers=12, n_heads=8, d_ff=1920,
        target_params=30_000_000, role="scaling",
        note="33.2M total (10.7% over nominal, inside 12% tol); aligned "
             "with RiNALMo-micro 33M"),
    "RNA-Sc-100M": ModelSpec(
        model_id="RNA-Sc-100M", d_model=576, n_layers=23, n_heads=9, d_ff=2304,
        target_params=100_000_000, role="scaling",
        note="flagship ~99.5M; deep-narrow; 3 formal seeds",
        seeds=(17, 29, 43)),
    "RNA-Sc-300M": ModelSpec(
        model_id="RNA-Sc-300M", d_model=1024, n_layers=24, n_heads=16, d_ff=4096,
        target_params=300_000_000, role="scaling",
        note="T1.0.3 anchor tier (修订三): 302.1M (0.7% dev); fills "
             "100M->650M 6.5x log-gap; corpus-optimal anchor "
             "(5.9B/20~295M Chinchilla edge, Claim-14); single seed",
        seeds=(17,)),
    "RNA-Sc-650M": ModelSpec(
        model_id="RNA-Sc-650M", d_model=1408, n_layers=28, n_heads=22, d_ff=5632,
        target_params=650_000_000, role="scaling",
        note="T2.1.3-slope-triggered extension 666.3M (2.5%% dev); deep-narrow; "
             "single-GPU feasible ~20GB fp32; DP optional for speed)",
        seeds=(17,)),
}

# S2 corpus-size axis: 30M model trained on 1M/10M/40M unique train sequences.
CORPUS_AXIS_NSEQ = {"c1M": 1_000_000, "c10M": 10_000_000, "c40M": 40_000_000}

# S3 diversity axis (run after main line lands): dedup-style reweighting.
DIVERSITY_AXIS = {"raw": "train split as-is (power-law clusters)",
                  "reweighted": "cluster-size flattening (deferred)"}
