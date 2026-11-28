from __future__ import annotations
# P2.14 Part A — external COV multi-seed (RiNALMo micro/mega/giga + NucleicBERT).
# Runs on server1 original P2.3 environment (venv with multimolecule). Observational anchors.
import sys, json, time
from pathlib import Path
import numpy as np
import torch
ROOT = Path("/home/cunyuliu/rna-sc-p2")
sys.path.insert(0, str(ROOT / "p2_3"))
sys.path.insert(0, str(ROOT / "code_git"))
import run_p2_3_cov as C
BASE = C.BASE
OUT = BASE / "results" / "P2_14" / "ext_cov_multiseed"
SEEDS = [17, 29, 43, 61, 79]
EXT = ["rinalmo_micro", "rinalmo_mega", "rinalmo_giga", "nucleicbert"]
ANCHOR = {"rinalmo_micro": 0.1134, "rinalmo_mega": 0.1998, "rinalmo_giga": 0.2477, "nucleicbert": 0.0108}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert torch.cuda.is_available(), "CUDA unavailable; refusing CPU fallback"
    recs = []
    for seed in SEEDS:
        so = OUT / f"seed{seed}"
        so.mkdir(parents=True, exist_ok=True)
        C.SEED = seed
        C.OUT = so
        C.CONDITIONS = so / "conditions.jsonl"
        C.FREEZE_META = so / "freeze.json"
        C.freeze_conditions()
        for mk in EXT:
            C.run_external(mk)
            pair = json.load(open(so / f"p2_3_{mk}_pair.json"))
            assert pair["status"] == "COMPLETE", (mk, seed, pair["status"])
            t = pair["arms"]["trained"]["cov_minus_ctrl"]
            ri = pair["arms"]["randinit17"]["cov_minus_ctrl"]
            recs.append({"model": mk, "seed": seed, "trained": t, "randinit": ri,
                         "net": pair["trained_minus_randinit"]})
            print("EXT_DONE", mk, seed, t, flush=True)
    summ = {}
    for mk in EXT:
        tr = [r["trained"] for r in recs if r["model"] == mk]
        net = [r["net"] for r in recs if r["model"] == mk]
        s17 = [r["trained"] for r in recs if r["model"] == mk and r["seed"] == 17][0]
        summ[mk] = {"trained_mean": float(np.mean(tr)), "trained_sd": float(np.std(tr, ddof=1)),
                    "sign_positive_frac": float(np.mean([x > 0 for x in tr])),
                    "net_mean": float(np.mean(net)),
                    "per_seed": {str(s): v for s, v in zip(SEEDS, tr)},
                    "anchor": ANCHOR[mk], "seed17_value": s17,
                    "anchor_abs_diff": abs(s17 - ANCHOR[mk]), "anchor_pass": abs(s17 - ANCHOR[mk]) < 5e-4,
                    "scope": "observational_anchor"}
    C.write_json(OUT / "summary.json", {"seeds": SEEDS, "models": summ, "records": recs,
                                        "created_unix": time.time()})
    print("P2_14_EXT_SUMMARY", json.dumps(summ, indent=1), flush=True)
    print("P2_14_EXT_DONE", flush=True)


if __name__ == "__main__":
    main()