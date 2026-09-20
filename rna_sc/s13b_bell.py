"""S13b structure-version bell curve (H7 MAIN test) — v1.

Hou et al. NCS 2026 transplant to a structure task: is downstream
structure performance mediated by PRETRAINING CONFIDENCE rather than
model size? Family-level scatter: x = per-family confidence (masked
marginal NLL on that family's sequences), y = per-family structure
probe F1. Pool points across scales + randinit (covers the confidence
axis range), then LOWESS + quadratic fit; bell = peak interval above
the lowest-10% interval by >= 0.1 (bootstrap CI).

v1 granularity: bpRNA source families (RFAM/CRW/SRP/tmRNA/SPR/RNP) —
the family axis available in bpRNA_parsed.parquet.

Outputs: evidence/s13b_bell.json + figs/fig_s13b_bell.png

Usage:
  python -m rna_sc.s13b_bell --device 6 [--n-eval-seqs 1500]
"""
from __future__ import annotations

import argparse
import json
import math
import random

import numpy as np
import torch
import pyarrow.parquet as pq

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc.model import RNAMLMEncoder
from rna_sc.data import ALPHABET

BPRNA = "/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s13b_bell.json"
FIG = "/mnt/cunyuliu/rna-sc/figs/fig_s13b_bell"
RUNS = ["RNA-Sc-1M_s17", "RNA-Sc-10M_s17", "RNA-Sc-30M_s17",
        "RNA-Sc-100M_s17", "RNA-Sc-10M_s17_randinit17"]
PAD_ID, MASK_ID, IGNORE = 4, 5, -100


def masked_nll(model, device, seqs, mask_frac=0.15, seed=17):
    """Per-sequence masked-marginal NLL (mean over masked positions).

    Deterministic masking via sequence hash + seed (rna_sc.data style).
    """
    import zlib
    model = model.to(device).eval()
    nlls = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s in seqs:
            ids = [ALPHABET.index(b) for b in s.upper().replace("T", "U")
                   if b in ALPHABET][:256]
            n = len(ids)
            if n < 4:
                continue
            rng = random.Random(zlib.crc32(
                s.upper().encode()) ^ seed)
            idx = list(range(n))
            rng.shuffle(idx)
            n_mask = max(1, int(round(mask_frac * n)))
            sel = sorted(idx[:n_mask])
            inp = list(ids)
            for i in sel:
                inp[i] = MASK_ID
            x = torch.tensor([inp], device=device)
            out = model(x)
            logits = out[0] if isinstance(out, tuple) else out
            logp = torch.log_softmax(logits[0].float(), dim=-1)
            tot = 0.0
            for i in sel:
                tot += float(logp[i, ids[i]])
            nlls.append(-tot / len(sel))
    return nlls


def per_family_tokens(model, device, seqs, pairs, L_pick):
    """Per-token states at layer L_pick, grouped by index order."""
    model = model.to(device).eval()
    out_states, out_labels = [], []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s, prs in zip(seqs, pairs):
            ids = [ALPHABET.index(b) for b in s.upper().replace("T", "U")
                   if b in ALPHABET][:256]
            n = len(ids)
            if n < 4:
                continue
            paired = [0] * n
            for i, j in prs:
                if i <= n and j <= n:
                    paired[i - 1] = 1
                    paired[j - 1] = 1
            x = torch.tensor([ids], device=device)
            _, _, hids = model(x, return_all_hiddens=True)
            out_states.append(hids[L_pick][0, :n].float().cpu())
            out_labels.append(torch.tensor(paired))
    return out_states, out_labels


def train_head(X, y, device, seed, epochs=6):
    torch.manual_seed(seed)
    d = X.shape[1]
    W = torch.zeros(d, 2, device=device, requires_grad=True)
    Xd, yd = X.to(device).float(), y.to(device)
    npos = float((yd == 1).sum())
    nneg = float(len(yd) - npos)
    w = torch.tensor([1.0, max(1.0, nneg / max(1.0, npos))],
                     device=device)
    opt = torch.optim.AdamW([W], lr=1e-3, weight_decay=0.01)
    for _ in range(epochs):
        perm = torch.randperm(len(Xd), device=device)
        for i in range(0, len(Xd), 512):
            idx = perm[i:i + 512]
            loss = torch.nn.functional.cross_entropy(
                Xd[idx] @ W, yd[idx], weight=w)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    return W


def f1_of(pred, y):
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    return (2 * tp / (2 * tp + fp + fn)
            if (2 * tp + fp + fn) else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train-seqs", type=int, default=8000)
    ap.add_argument("--n-eval-seqs", type=int, default=1500)
    ap.add_argument("--layer-frac", type=float, default=0.6,
                    help="structure-probe layer (best layers are "
                         "mid-early; 0.6 covers 10M best 0.68/30M "
                         "0.27 mid)")
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    tab = pq.read_table(BPRNA).to_pydict()
    tr_idx = [i for i, sp in enumerate(tab["split"]) if sp == "train"]
    ev_idx = [i for i, sp in enumerate(tab["split"]) if sp == "test"]
    rng = random.Random(17)
    tr_idx = rng.sample(tr_idx, min(args.n_train_seqs, len(tr_idx)))
    ev_idx = rng.sample(ev_idx, min(args.n_eval_seqs, len(ev_idx)))
    tr_seqs = [tab["seq"][i] for i in tr_idx]
    tr_pairs = [tab["pairs"][i] for i in tr_idx]
    ev_src = {}
    ev_seqs_all, ev_pairs_all, ev_srcs_all = [], [], []
    for i in ev_idx:
        ev_seqs_all.append(tab["seq"][i])
        ev_pairs_all.append(tab["pairs"][i])
        ev_srcs_all.append(tab["source"][i])

    points = []
    for run in RUNS:
        base = run.replace("_randinit17", "")
        ri = run.endswith("_randinit17")
        model, ck = load_encoder(
            "/mnt/cunyuliu/rna-sc/runs/%s" % base)
        L = ck["cfg"]["arch"]["n_layers"]
        if ri:
            torch.manual_seed(17)
            mcfg = ck["cfg"]["arch"]
            model = RNAMLMEncoder(d_model=mcfg["d_model"],
                                  n_layers=mcfg["n_layers"],
                                  n_heads=mcfg["n_heads"],
                                  d_ff=mcfg["d_ff"])
        L_pick = max(0, min(L - 1, int(round(args.layer_frac * (L - 1)))))

        tr_states, tr_labels = per_family_tokens(
            model, dev, tr_seqs, tr_pairs, L_pick)
        Xtr = torch.cat(tr_states)
        ytr = torch.cat(tr_labels)
        W = train_head(Xtr, ytr, dev, seed=17 + L_pick)

        ev_states, ev_labels = per_family_tokens(
            model, dev, ev_seqs_all, ev_pairs_all, L_pick)
        # per-source F1 + per-source NLL
        by_src = {}
        for s_st, s_lb, src, seq in zip(ev_states, ev_labels,
                                        ev_srcs_all, ev_seqs_all):
            by_src.setdefault(src, []).append((s_st, s_lb, seq))
        nll_by_src = {}
        for src, items in by_src.items():
            Xs = torch.cat([it[0] for it in items])
            ys = torch.cat([it[1] for it in items])
            with torch.no_grad():
                pred = (Xs.to(dev).float() @ W).argmax(-1).cpu()
            f1 = f1_of(pred, ys)
            seqs = [it[2] for it in items]
            nl = masked_nll(model, dev, seqs)
            nll_by_src[src] = {
                "f1": round(f1, 4),
                "nll": round(float(np.mean(nl)), 4),
                "n_seqs": len(items)}
            points.append({"model": run, "source": src,
                           "nll": round(float(np.mean(nl)), 4),
                           "f1": round(f1, 4)})
            print("%-26s %-6s nll=%.4f f1=%.4f (n=%d)" % (
                run, src, float(np.mean(nl)), f1, len(items)))
        del model
        torch.cuda.empty_cache()

    # bell test on pooled scatter
    xs = np.array([p["nll"] for p in points])
    ys = np.array([p["f1"] for p in points])
    out = {"points": points, "n_points": len(points)}

    # quadratic fit + peak
    if len(points) >= 6:
        c2, c1, c0 = np.polyfit(xs, ys, 2)
        peak_x = -c1 / (2 * c2) if c2 != 0 else float(xs.mean())
        lo10 = float(np.quantile(xs, 0.10))
        hi10 = float(np.quantile(xs, 0.90))
        # peak-interval performance vs lowest-10% interval
        mask_peak = (xs >= peak_x - (hi10 - lo10) * 0.1) & \
                    (xs <= peak_x + (hi10 - lo10) * 0.1)
        mask_low = xs <= lo10
        peak_perf = float(ys[mask_peak].mean()) if mask_peak.sum() else None
        low_perf = float(ys[mask_low].mean()) if mask_low.sum() else None
        gap = (peak_perf - low_perf) if (peak_perf is not None and
                                         low_perf is not None) else None
        # bootstrap CI for gap
        rng = random.Random(17)
        boots = []
        idxs = list(range(len(xs)))
        for _ in range(1000):
            b = [rng.choice(idxs) for _ in idxs]
            bx = xs[b]
            by = ys[b]
            try:
                bc2, bc1, _ = np.polyfit(bx, by, 2)
                bp = -bc1 / (2 * bc2) if bc2 != 0 else float(bx.mean())
                m_pk = (bx >= bp - (hi10 - lo10) * 0.1) & \
                       (bx <= bp + (hi10 - lo10) * 0.1)
                m_lo = bx <= float(np.quantile(bx, 0.10))
                if m_pk.sum() and m_lo.sum():
                    boots.append(by[m_pk].mean() - by[m_lo].mean())
            except Exception:  # noqa: BLE001
                pass
        boots.sort()
        ci = [round(boots[int(0.025 * len(boots))], 4),
              round(boots[int(0.975 * len(boots))], 4)] if boots else None
        out["bell_test"] = {
            "quad_coeffs": [round(v, 6) for v in (c2, c1, c0)],
            "peak_x_nll": round(float(peak_x), 4),
            "peak_interval_f1": round(peak_perf, 4) if peak_perf else None,
            "lowest10_f1": round(low_perf, 4) if low_perf else None,
            "gap": round(gap, 4) if gap is not None else None,
            "gap_boot_ci95": ci,
            "criterion": "bell iff gap >= 0.1 and CI excludes 0",
            "verdict": ("BELL" if (gap is not None and gap >= 0.1 and
                                   ci and ci[0] > 0) else
                        "NOT-BELL (v1: monotone or flat)")}

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    print(json.dumps(out.get("bell_test", {}), indent=2))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5.4, 3.8))
        for run in RUNS:
            px = [p["nll"] for p in points if p["model"] == run]
            py = [p["f1"] for p in points if p["model"] == run]
            ax.scatter(px, py, s=26, label=run.replace("RNA-Sc-", ""))
        if len(points) >= 6:
            xr = np.linspace(xs.min(), xs.max(), 100)
            ax.plot(xr, np.polyval((c2, c1, c0), xr), "k--", lw=1,
                    label="quad fit")
        ax.set_xlabel("family NLL (masked marginal, lower=more confident)")
        ax.set_ylabel("family structure F1 (bpRNA paired-position)")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig("%s.%s" % (FIG, ext), dpi=200,
                        bbox_inches="tight")
        print("saved", FIG + ".{png,pdf}")
    except Exception as e:  # noqa: BLE001
        print("plot skipped:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
