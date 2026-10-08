"""T4.3.5 预注册判据（2026-10-08 定稿，训练前冻结）。

三个新实验臂的判据全部预注册，防止事后解释：

A. 语料对齐臂（RiNALMo 语料 × 自训架构，100M/300M）
   判据：family-split probe F1 对比同档自训臂（R22 语料）
   - 100M: rinalmocorpus vs 0.3263（R22 主臂）
   - 300M: rinalmocorpus vs 0.3445
   A1 显著超（+2pp）：语料构成因子证实 → slide7 归因升级"受控证据"
   A2 不超/降：架构与配方（RoPE/SwiGLU/训练配方）权重上调
   注意：RiNALMo 语料以 R22 为主体 + 可获取的增补库，为"配方复刻"
   （论文未发布原始语料清单）——判读写明这一点。

B. 预算 × 泄漏通道（b59 臂 random-split Δ）
   判据：random F1(5.9B) − random F1(2B) vs family F1(5.9B) − family F1(2B)
   - 已知 family 通道：30M −5.24 / 100M −2.74 / 300M +3.76
   - B1 random 同向涨（记忆更多→随机切分兑现更多）→ 两通道背离，
     "random 高分=记忆兑现"论证链加强（S9 泄漏三角第四链）
   - B2 random 同向跌（预算红利完全消失）→ 30M 平台期解读改写
   2B 参照值（probe-balanced）：30M 0.6053 / 100M 0.604 / 300M 0.587

C. rfamcap 臂（已在训，D-3 判据沿用）
   结构 F1 显著超主线（+2pp）→ 语料因子证实（Rfam 富集）
"""
import json
import os
import time

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "evidence", "t435_preregistration.json")

spec = {
    "registered": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "before_training": True,
    "arms": {
        "A_corpus_replica": {
            "runs": ["RNA-Sc-100M_s17_rinalmocorpus",
                     "RNA-Sc-300M_s17_rinalmocorpus"],
            "protocol": "RiNALMo Methods 4.3 replica corpus "
                        "(R22 + cached ext fasta, len 16-8192, dedup, "
                        "linclust 0.7/0.8, held-out removed B1), "
                        "2.0B nt iso-token, seed 17, same recipe",
            "judgement": {
                "A1_corpus_confirmed": "family F1 > same-scale R22 arm "
                                       "+ 2pp on either scale",
                "A2_architecture_weighted": "family F1 within ±2pp "
                                            "(corpus replica does not "
                                            "recover RiNALMo gap)"
            },
            "baselines": {"100M_r22": 0.3263, "300M_r22": 0.3445,
                          "rinalmo_giga_651M": 0.2667},
            "caveat": "RiNALMo original corpus manifest not published; "
                      "replica = recipe reproduction (main-db R22 + "
                      "whatever ext fastas cached). Corpus composition "
                      "therefore approximate — reported honestly."
        },
        "B_budget_leakage_channel": {
            "cells": ["30M_b59", "100M_b59", "300M_b59", "650M_b59"],
            "measure": "random-split probe-balanced F1 on b59 arms; "
                       "delta vs 2B random baselines",
            "baselines_random_2B": {"30M": 0.6053, "100M": 0.604,
                                    "300M": 0.587},
            "family_channel_known": {"30M": -5.24, "100M": -2.74,
                                     "300M": +3.76},
            "judgement": {
                "B1_memory_cashing": "random delta positive while "
                                     "family negative (100M) → two-channel "
                                     "divergence, 4th link of leakage "
                                     "triangle",
                "B2_budget_neutral": "random delta ~0 → random-split "
                                     "ceiling is family-overlap bound, "
                                     "not budget-dependent"
            }
        },
        "C_rfamcap": {
            "runs": ["RNA-Sc-100M_s17_rfamcap", "RNA-Sc-30M_s17_rfamcap"],
            "judgement": "structure F1 > mainline +2pp → corpus "
                         "enrichment confirmed (D-3, registered 10-06)"
        }
    },
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(spec, open(OUT, "w"), indent=1, ensure_ascii=False)
print("preregistration written:", OUT)
