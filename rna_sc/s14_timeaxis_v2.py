"""S14 time-axis v2: 300M + 650M checkpoints (H8 time axis completion)."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, "/home/cunyuliu/rna-sc")

import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc import s14_rns

OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_timeaxis_v2.json"
RUNS = {"RNA-Sc-300M_s17": (500_000_000, 1_000_000_000, 1_500_000_000,
                            1_900_000_000),
        "RNA-Sc-650M_s17": (500_000_000, 1_000_000_000, 1_500_000_000,
                            1_900_000_000)}
MAX_LEN = 192
ALPHABET = s14_rns.ALPHABET


def ckpt_at(run_dir, nt_target):
    cks = sorted([f for f in os.listdir(run_dir) if f.startswith("ckpt_")],
                 key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    return min(cks, key=lambda f: abs(
        int(f.split("_nt")[1].split("_")[0]) - nt_target))


def embed_one_by_one(model, device, seqs, L_pick):
    model = model.to(device).eval()
    outs = []
    with torch.no_grad():
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s if b in ALPHABET][:MAX_LEN]
            if len(ids) < 2:
                ids = ids + [0]
            x = torch.tensor([ids], device=device, dtype=torch.long)
            _, _, hids = model(x, return_all_hiddens=True)
            outs.append(hids[L_pick][0].float().mean(dim=0).cpu())
    return torch.stack(outs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--n-real", type=int, default=800)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = [s for s in s14_rns.stream_real(args.n_real)]
    rand, _, _ = s14_rns.make_random_pool(real, 3)

    results = {}
    for run, nts in RUNS.items():
        run_dir = "/mnt/cunyuliu/rna-sc/runs/%s" % run
        traj = {}
        for nt_t in nts:
            ck_name = ckpt_at(run_dir, nt_t)
            nt_actual = int(ck_name.split("_nt")[1].split("_")[0])
            model, ck = load_encoder(run_dir, ckpt_nt=nt_actual)
            L = ck["cfg"]["arch"]["n_layers"]
            L_pick = max(0, min(L - 1, int(round(0.75 * (L - 1)))))
            re = embed_one_by_one(model, dev, real, L_pick)
            ae = embed_one_by_one(model, dev, rand, L_pick)
            means, _ = s14_rns.rns_k(re, ae, s14_rns.KS, dev)
            traj["nt_%.1fB" % (nt_actual / 1e9)] = {
                "ckpt": ck_name, "layer": L_pick,
                "RNS": {str(k): round(v, 4) for k, v in means.items()}}
            print("%s nt=%.1fB L%d RNS@10 %.4f" % (
                run, nt_actual / 1e9, L_pick, means[10]), flush=True)
            del model
            torch.cuda.empty_cache()
        results[run] = traj

    out = {"protocol": "one-by-one forward, len cap 192, layer_frac 0.75 "
                       "(matches s14_rns_650m add-on; 10M v1 used batch "
                       "256 - noted)",
           "n_real": len(real), "n_rand": len(rand),
           "results": results,
           "comparison_10M_v1": "10M RNS peak 1.0B vs F1 peak 0.5B "
                                "(two-peak offset); this v2 tests whether "
                                "the offset holds at 300M/650M"}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
