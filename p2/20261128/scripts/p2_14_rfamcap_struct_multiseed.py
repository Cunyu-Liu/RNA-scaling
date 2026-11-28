from __future__ import annotations
# P2.14 Part B — rfamcap structure probe multi-seed (30M/100M rfamcap vs main).
# Reuses probe_structure_p2_1 collect_token_states/run_one_layer. sample_seed 17 frozen;
# probe seeds {17,29,43,61,79} (head seed = probe_seed + layer). paired-F1 best-layer.
import sys, json, time, random, shutil
from pathlib import Path
import numpy as np
import torch
import pyarrow.parquet as pq
ROOT = Path("/home/cunyuliu/rna-sc-p2")
sys.path.insert(0, str(ROOT / "code_git"))
import rna_sc.probe_structure_p2_1 as M
from rna_sc.probe import load_encoder
from rna_sc.census import GPUGuard
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
OUT = BASE / "results" / "P2_14" / "rfamcap_struct_multiseed"
BPRNA = BASE / "data" / "bpRNA_parsed.parquet"
SEEDS = [17, 29, 43, 61, 79]
MODELS = {"30M_rfamcap": BASE / "weights" / "RNA-Sc-30M_s17_rfamcap",
          "30M_main": BASE / "weights" / "RNA-Sc-30M_s17",
          "100M_rfamcap": BASE / "weights" / "RNA-Sc-100M_s17_rfamcap",
          "100M_main": BASE / "weights" / "RNA-Sc-100M_s17"}


def sample():
    table = pq.read_table(BPRNA).to_pydict()
    by = {"train": [], "test": []}
    for i, sp in enumerate(table["split"]):
        if sp in by:
            by[sp].append(i)
    rng = random.Random(17)
    ti = rng.sample(by["train"], min(8000, len(by["train"])))
    ei = rng.sample(by["test"], min(1305, len(by["test"])))
    return ([table["seq"][i] for i in ti], [table["pairs"][i] for i in ti],
            [table["seq"][i] for i in ei], [table["pairs"][i] for i in ei])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda:0"
    g = GPUGuard(dev); g.check()
    assert torch.cuda.is_available(), "CUDA unavailable; refusing CPU fallback"
    tr_seqs, tr_pairs, ev_seqs, ev_pairs = sample()
    results = {}
    for name, run in MODELS.items():
        model, ck = load_encoder(str(run))
        L = int(ck["cfg"]["arch"]["n_layers"])
        cache = OUT / "cache" / name
        if cache.exists():
            shutil.rmtree(cache)
        xt, yt = M.collect_token_states(model, dev, tr_seqs, tr_pairs, L, cache / "train", "train")
        xe, ye = M.collect_token_states(model, dev, ev_seqs, ev_pairs, L, cache / "eval", "eval")
        g.verify_cuda_alive()
        per_seed = {}
        for ps in SEEDS:
            best = None
            for li in range(L):
                met, _ = M.run_one_layer(xt[li], yt, xe[li], ye, dev, seed=ps + li,
                                         probe_batch_size=512, epochs=6)
                f1 = met["f1_paired_legacy_unrounded"]
                if best is None or f1 > best["f1"]:
                    best = {"layer": li, "f1": round(f1, 4),
                            "f1_macro": round(met["f1_macro_unrounded"], 6)}
            per_seed[str(ps)] = best
            print("STRUCT", name, ps, best, flush=True)
        results[name] = {"n_layers": L, "checkpoint_nt": ck["nt"], "per_seed": per_seed}
        del xt, xe, model
        torch.cuda.empty_cache()
        shutil.rmtree(cache)
    paired = {}
    for scale in ["30M", "100M"]:
        diffs = []
        for ps in SEEDS:
            rf = results[f"{scale}_rfamcap"]["per_seed"][str(ps)]["f1"]
            mn = results[f"{scale}_main"]["per_seed"][str(ps)]["f1"]
            diffs.append((rf - mn) * 100)
        paired[scale] = {"mean_pp": round(float(np.mean(diffs)), 3),
                         "sd_pp": round(float(np.std(diffs, ddof=1)), 3),
                         "sign_positive_frac": float(np.mean([d > 0 for d in diffs])),
                         "per_seed_pp": {str(s): round(d, 3) for s, d in zip(SEEDS, diffs)}}
    json.dump({"models": results, "paired_rfamcap_minus_main": paired,
               "note": "randinit floors from P2.1 (30M 0.5794 / 100M 0.5875); sample_seed 17 frozen",
               "created_unix": time.time()}, open(OUT / "summary.json", "w"), indent=2)
    print("P2_14_STRUCT_SUMMARY", json.dumps(paired, indent=1), flush=True)
    print("P2_14_STRUCT_DONE", flush=True)


if __name__ == "__main__":
    main()