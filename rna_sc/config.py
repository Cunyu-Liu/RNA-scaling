"""Run-config resolution for RNA-Sc training (frozen recipe, SPEC S1)."""
from __future__ import annotations

from dataclasses import dataclass

from .specs import FAMILY, ModelSpec

SPLIT_8080 = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"

CONTEXT_NT = 1024
DROPOUT = 0.0
BUDGET_NT = 2_000_000_000          # 2.0B valid nt for every model (single recipe)
BATCH_NT = 16_384                  # effective valid nt per optimizer step
BASE_LR = 3e-4                     # matched to TokBench 100M scale base LR
WARMUP_NT_FRAC = 0.005
CKPT_NT = 100_000_000              # S6 pretraining-time axis: ckpt every 100M nt
VAL_INTERVAL_NT = 100_000_000
VAL_NT = 4_000_000
VAL_SPLIT = "validation"
MLM_P = 0.15
SEED_TUNE = 17

SCALE_LR_FACTOR = {                # smaller models get the 2.0x factor TokBench
    "RNA-Sc-1M": 2.0,              # selected by validation (3.4 analogue)
    "RNA-Sc-10M": 2.0,
    "RNA-Sc-30M": 2.0,
    "RNA-Sc-100M": 1.0,
}


@dataclass(frozen=True)
class RNAMLMConfig:
    run_id: str
    spec: ModelSpec
    seed: int
    device: str
    budget_nt: int = BUDGET_NT
    batch_nt: int = BATCH_NT
    context_nt: int = CONTEXT_NT
    lr: float = BASE_LR
    warmup_nt: int = int(WARMUP_NT_FRAC * BUDGET_NT)
    ckpt_nt: int = CKPT_NT
    val_interval_nt: int = VAL_INTERVAL_NT
    val_nt: int = VAL_NT
    val_split: str = VAL_SPLIT
    mlm_p: float = MLM_P
    # S2 corpus-size axis: cap on unique train sequences (None = full train).
    corpus_nseq: int | None = None
    corpus_tag: str = "full"
    # S3 diversity axis (deferred; placeholder for reweighting).
    diversity_mode: str = "raw"
    smoke_nt: int | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "model_id": self.spec.model_id,
            "role": self.spec.role,
            "seed": self.seed,
            "device": self.device,
            "arch": {
                "d_model": self.spec.d_model,
                "n_layers": self.spec.n_layers,
                "n_heads": self.spec.n_heads,
                "d_ff": self.spec.d_ff,
                "target_params": self.spec.target_params,
                "positions": "ALiBi",
                "tokenizer": "single-nucleotide ACGU",
                "objective": "MLM 15% (80/10/10)",
            },
            "budget_nt": self.budget_nt,
            "batch_nt": self.batch_nt,
            "context_nt": self.context_nt,
            "lr": self.lr,
            "warmup_nt": self.warmup_nt,
            "ckpt_nt": self.ckpt_nt,
            "val_interval_nt": self.val_interval_nt,
            "val_nt": self.val_nt,
            "val_split": self.val_split,
            "mlm_p": self.mlm_p,
            "corpus_nseq": self.corpus_nseq,
            "corpus_tag": self.corpus_tag,
            "diversity_mode": self.diversity_mode,
            "smoke_nt": self.smoke_nt,
        }


def resolve_config(model_id: str, seed: int, device: str,
                   corpus_nseq: int | None = None,
                   corpus_tag: str = "full",
                   budget_nt: int | None = None,
                   smoke_nt: int | None = None) -> RNAMLMConfig:
    spec = FAMILY[model_id]
    lr = BASE_LR * SCALE_LR_FACTOR.get(model_id, 1.0)
    tag = corpus_tag if corpus_nseq is not None else "full"
    run_id = "rnasc_%s_s%s%s" % (spec.model_id.split("-")[-1], seed,
                                 "" if tag == "full" else "_" + tag)
    budget = budget_nt or BUDGET_NT
    return RNAMLMConfig(
        run_id=run_id, spec=spec, seed=seed, device=device,
        budget_nt=budget, lr=lr,
        warmup_nt=int(WARMUP_NT_FRAC * budget),
        corpus_nseq=corpus_nseq, corpus_tag=tag,
        smoke_nt=smoke_nt)
