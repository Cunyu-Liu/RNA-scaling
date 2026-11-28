from __future__ import annotations
# P2.13 — Q5 self-family COV-CTRL multi-seed (650M/100M + randinit17).
# Reuses the verified P2.3 COV implementation (run_p2_3_cov.py) as a module.
# Condition-generation seeds {17,29,43,61,79}; seed17 must reproduce the original anchor.
import sys, json, time, hashlib, platform, importlib.metadata
from pathlib import Path
import numpy as np
import torch

ROOT = Path("/home/cunyuliu/rna-sc-p2")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code_git"))
import run_p2_3_cov as C
from rna_sc.probe import load_encoder
from rna_sc.model import RNAMLMEncoder

BASE = C.BASE
OUT = BASE / "results" / "P2_13" / "cov_multiseed"
LOGS = BASE / "logs"
SEEDS = [17, 29, 43, 61, 79]
SELF = {
    "650M": (BASE / "weights" / "RNA-Sc-650M_s17", 0.09572),
    "100M": (BASE / "weights" / "RNA-Sc-100M_s17", 0.0203),
}
TOL = 5e-4


def set_seed_paths(seed):
    OUT.mkdir(parents=True, exist_ok=True)
    C.SEED = seed
    C.OUT = OUT
    C.CONDITIONS = OUT / f"conditions_seed{seed}.jsonl"
    C.FREEZE_META = OUT / f"freeze_seed{seed}.json"


def self_adapter(run, mode, device="cuda:0"):
    model, ck = load_encoder(str(run))
    arch = ck["cfg"]["arch"]
    if mode == "randinit17":
        torch.manual_seed(17)
        model = RNAMLMEncoder(d_model=arch["d_model"], n_layers=arch["n_layers"],
                              n_heads=arch["n_heads"], d_ff=arch["d_ff"])
    ad = C.RNAScAdapter(model, device)
    return ad, {"run_dir": str(run), "checkpoint_nt": ck["nt"], "mode": mode}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    assert torch.cuda.is_available(), "CUDA unavailable; refusing CPU fallback"
    recs = []
    for seed in SEEDS:
        set_seed_paths(seed)
        C.freeze_conditions()
        meta, conds = C.load_frozen()
        for scale, (run, anchor) in SELF.items():
            for mode in ("trained", "randinit17"):
                ad, info = self_adapter(run, mode)
                ids = ad.encode_ids(conds[0]["ids"])
                sm = ad.smoke(ids, conds[0]["j"], ad.vocab)
                C.write_json(LOGS / f"P2_13_{scale}_{mode}_seed{seed}_smoke.json", sm)
                pc = OUT / f"per_condition_{scale}_{mode}_seed{seed}.jsonl"
                res = C.evaluate_model(ad, f"rnasc{scale}", mode, conds, pc)
                res.update(info)
                res["seed"] = seed
                res["smoke"] = sm
                C.write_json(OUT / f"{scale}_{mode}_seed{seed}.json", res)
                recs.append({"scale": scale, "mode": mode, "seed": seed,
                             "cov_minus_ctrl": res["cov_minus_ctrl"], "n": res["cov"]["n"]})
                print("SELF_DONE", scale, mode, seed, res["cov_minus_ctrl"], flush=True)
                del ad
                torch.cuda.empty_cache()
    summ = {}
    for scale in SELF:
        tr = [r["cov_minus_ctrl"] for r in recs if r["scale"] == scale and r["mode"] == "trained"]
        ri = [r["cov_minus_ctrl"] for r in recs if r["scale"] == scale and r["mode"] == "randinit17"]
        s17 = [r["cov_minus_ctrl"] for r in recs if r["scale"] == scale and r["mode"] == "trained" and r["seed"] == 17][0]
        anchor = SELF[scale][1]
        summ[scale] = {
            "trained_mean": float(np.mean(tr)), "trained_sd": float(np.std(tr, ddof=1)),
            "sign_positive_frac": float(np.mean([x > 0 for x in tr])),
            "randinit_mean": float(np.mean(ri)), "randinit_max": float(np.max(ri)),
            "per_seed_trained": {str(s): v for s, v in zip(SEEDS, tr)},
            "anchor_seed17": anchor, "seed17_value": s17,
            "anchor_abs_diff": abs(s17 - anchor), "anchor_pass": abs(s17 - anchor) < TOL,
        }
        assert summ[scale]["anchor_pass"], (scale, s17, anchor)
    manifest = {
        "task": "P2.13 self-family COV multi-seed", "seeds": SEEDS,
        "created_unix": time.time(), "script_sha256": C.sha256_file(__file__),
        "bpRNA_sha256": C.sha256_file(C.DATA),
        "weights": {s: {"path": str(r),
                        "ckpt": max((f.name for f in r.iterdir() if f.name.startswith("ckpt_")),
                                    key=lambda f: int(f.split("_nt")[1].split("_")[0])),
                        "sha256": C.sha256_file(max((f for f in r.iterdir() if f.name.startswith("ckpt_")),
                                                    key=lambda f: int(f.name.split("_nt")[1].split("_")[0])))}
                    for s, (r, _) in SELF.items()},
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "torch": torch.__version__, "cuda": torch.cuda.get_device_name(0)},
    }
    C.write_json(OUT / "summary.json", {"seeds": SEEDS, "models": summ, "records": recs, "manifest": manifest})
    print("P2_13_SUMMARY", json.dumps(summ, indent=1), flush=True)
    print("P2_13_ALL_DONE", flush=True)


if __name__ == "__main__":
    main()