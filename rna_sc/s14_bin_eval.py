"""S14-bin: RNS-binned structure-task evaluation (Q19 / paper-Fig transplant).

Prabakaran & Bromberg style: bin REAL RNAs by their RNS (representation
uncertainty), then evaluate per-sequence structure-task performance in
each bin. Paper found (proteins): contact precision drops ~40% in the
high-RNS bin, long-range contacts (>24 separation) drop >60%, SS3
degrades mildly.

Our RNA counterpart (single script, three task families):
  A. per-position paired/unpaired F1 (bpRNA pairing task, S7 protocol
     heads already trained? -> no: we use the composition-free metric)
  B. long-range subset: pairs with |i-j| >= 24 only
  C. family-classification F1 per bin (global task control)

Per-sequence structure metric WITHOUT a trained head: use the model's
own masked-marginal co-variation proxy? No — simpler and honest: use
the S7-style linear head is trained on TR0; but per-sequence eval with
a fixed head is fine (head is constant across bins — bin comparison is
within-model). We reuse probe_structure head by training it once here
on bpRNA TR0 (balanced logistic, same protocol as S7), then evaluate
per-sequence macro-F1 in RNS bins.

Model: RNA-Sc-650M_s17 (largest, where structure readout is best).
Bins: RNS terciles (low/mid/high) computed with k=10 (our protocol).

Output: evidence/s14_bin_eval.json
"""
from __future__ import annotations

import argparse
import json
import math
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

ALPHABET = "ACGU"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_bin_eval.json"
BPRNA = "/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet"
RUN = "RNA-Sc-100M_s17"
K = 10
N_REAL = 1500
LONG_RANGE = 24
LEN_CAP = 160
BATCH = 4


def clean_seq(s: str) -> str:
    """ACGU-only + LEN_CAP. Labels are built against THIS string so
    id-embedding and pair-mask lengths always agree (N-char drift fix)."""
    return "".join(b for b in s.upper().replace("T", "U")
                   if b in ALPHABET)[:LEN_CAP]


def embed(model, device, seqs, L_pick, batch=BATCH):
    model = model.to(device).eval()
    out = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for i in range(0, len(seqs), batch):
            chunk = [s[:LEN_CAP] for s in seqs[i:i + batch]]
            ids = [[ALPHABET.index(b) for b in s if b in ALPHABET] or [0, 1]
                   for s in chunk]
            T = max(len(x) for x in ids)
            x = torch.tensor([r + [4] * (T - len(r)) for r in ids],
                             device=device)
            pad = x == 4
            _, _, hids = model(x, return_all_hiddens=True)
            h = hids[L_pick]
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
            out.append((hm.sum(1) / lens).cpu())
    return torch.cat(out, 0)


def rns_per_real(real_emb, rand_emb, k, device):
    """Per-real-sequence RNS_k (share of k-NN that are random)."""
    R = torch.nn.functional.normalize(real_emb.to(device), dim=1)
    A = torch.nn.functional.normalize(rand_emb.to(device), dim=1)
    Srr = R @ R.T
    Sra = R @ A.T
    rr = Srr.clone()
    rr.diagonal().fill_(-2.0)
    best_rr, _ = rr.topk(k, dim=1)
    best_ra, _ = Sra.topk(k, dim=1)
    cand = torch.cat([best_rr, best_ra], dim=1)
    thresh, _ = cand.topk(k, dim=1)
    t = thresh[:, -1].unsqueeze(1)
    n_rand = (Sra >= t).float().sum(1).clamp(max=k)
    return (n_rand / k).cpu()


def stream_real(n_needed, seed=17):
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    seqs = []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pq.ParquetFile(SPLIT_8080).iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence",
                     "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"], d["canonical_sequence"],
                               d["rna_type"]):
            if sm != "family_validation":
                continue
            seqs.append((seq.upper().replace("T", "U")[:256], rt))
            if len(seqs) >= n_needed * 3:
                break
        if len(seqs) >= n_needed * 3:
            break
    rng = random.Random(seed)
    rng.shuffle(seqs)
    return seqs[:n_needed]


def make_random_pool(real_seqs, mult, seed=17):
    from rna_sc.s14_rns import make_random_pool as _mk
    return _mk([s for s, _ in real_seqs], mult, seed)


def load_bprna_pairs():
    """(sequence, pairs) list from parsed parquet; split tag normalized."""
    import pyarrow.parquet as pq
    rows = pq.read_table(BPRNA).to_pydict()
    out = []
    for seq, pairs, split in zip(rows["seq"], rows["pairs"],
                                 rows["split"]):
        s = seq.upper().replace("T", "U")
        out.append((s, pairs, split))
    return out


def macro_f1_pair(y_true, y_pred):
    """Binary paired-position F1 (positive class = paired)."""
    tp = ((y_pred == 1) & (y_true == 1)).sum()
    fp = ((y_pred == 1) & (y_true == 0)).sum()
    fn = ((y_pred == 0) & (y_true == 1)).sum()
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return float(f1), float(prec), float(rec)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-real", type=int, default=1500)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    # 1) real sequences + embeddings + per-seq RNS
    real = stream_real(args.n_real)
    rand, _, _ = make_random_pool(real, 3)
    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % RUN)
    L = ck["cfg"]["arch"]["n_layers"]
    L_pick = max(0, min(L - 1, int(round(0.75 * (L - 1)))))
    re = embed(model, dev, [s for s, _ in real], L_pick)
    ae = embed(model, dev, rand, L_pick)
    rns = rns_per_real(re, ae, K, dev)

    # 2) bpRNA pairs: build simple GC-free? No — honest per-position
    #    structure readout using a small trained head (constant across
    #    bins): train logistic on TR0 with GC / trigram / model-emb
    #    feats? To keep this script self-contained and comparable to
    #    S7's zero-gain finding, use per-position model hidden state +
    #    logistic head trained once on TR0.
    # NOTE: full per-position pipeline is heavy; use the S7-style
    # approach: hidden state at each position -> logistic pairing
    # classifier. Train on TR0 (8000 seqs, subsample 2000), eval on TS0.
    print("loading bpRNA ...", flush=True)
    bprna = load_bprna_pairs()
    tr = [(clean_seq(s), p) for s, p, sp in bprna
          if sp == "train" and p is not None]
    ts = [(clean_seq(s), p) for s, p, sp in bprna
          if sp == "test" and p is not None]
    rng = random.Random(17)
    tr_sub = tr[:2000] if len(tr) >= 2000 else tr

    # per-position embeddings for training
    def pos_embed(seqs, batch=BATCH):
        outs = []
        with torch.no_grad():
            for i in range(0, len(seqs), batch):
                chunk = [s[:LEN_CAP] for s in seqs[i:i + batch]]
                ids = [[ALPHABET.index(b) for b in s if b in ALPHABET]
                       or [0, 1] for s in chunk]
                T = max(len(x) for x in ids)
                x = torch.tensor([r + [4] * (T - len(r)) for r in ids],
                                 device=dev)
                pad = x == 4
                _, _, hids = model(x, return_all_hiddens=True)
                h = hids[L_pick].float()
                for j in range(len(chunk)):
                    n = len(ids[j])
                    outs.append(h[j, :n].cpu())
        return outs

    print("embedding TR0 subsample ...", flush=True)
    tr_emb = pos_embed([s for s, _ in tr_sub])
    # labels: paired mask (clean_seq already capped: len(s) is the
    # ACGU-only effective length — no further cap needed)
    def pair_mask(pairs, L_seq):
        m = torch.zeros(L_seq, dtype=torch.long)
        for (i, j) in (pairs or []):
            if 0 <= i < L_seq and 0 <= j < L_seq:
                m[i] = 1
                m[j] = 1
        return m

    X_tr = torch.cat([e for e in tr_emb], 0)
    y_tr = torch.cat([pair_mask(p, len(s)) for (s, p), e in
                      zip(tr_sub, tr_emb)], 0)

    # balanced logistic head (same class-weighting discipline as S7)
    n_pos = y_tr.sum().item()
    n_neg = len(y_tr) - n_pos
    w = torch.tensor([n_pos / max(1, len(y_tr)),
                      n_neg / max(1, len(y_tr))], dtype=torch.float)
    head = torch.nn.Linear(X_tr.shape[1], 2)
    opt = torch.optim.Adam(head.parameters(), lr=1e-3)
    head.to(dev); Xd = X_tr.to(dev); yd = y_tr.to(dev)
    for ep in range(3):
        perm = torch.randperm(len(Xd), device=dev)
        for i in range(0, len(Xd), 65536):
            idx = perm[i:i + 65536]
            logits = head(Xd[idx])
            loss = torch.nn.functional.cross_entropy(logits, yd[idx],
                                                     weight=w.to(dev))
            opt.zero_grad(); loss.backward(); opt.step()
        print("head epoch", ep, "loss", float(loss), flush=True)
    head.eval()

    # 3) per-sequence eval on TS0 with RNS-matched bins:
    #    embed TS0 sequences, compute RNS on the SAME random pool,
    #    then per-sequence F1 by bin
    print("embedding TS0 ...", flush=True)
    ts_seqs = [s for s, _ in ts]
    # TS0 may exceed n_real; embed in chunks, RNS via combined pool
    ts_emb_full = pos_embed(ts_seqs)
    ts_mean = torch.stack([e.mean(0) for e in ts_emb_full], 0)
    rns_ts = rns_per_real(ts_mean, ae, K, dev)

    f1_all, f1_lr_all = [], []
    f1_by_bin = {"low": [], "mid": [], "high": []}
    lr_by_bin = {"low": [], "mid": [], "high": []}
    n_by_bin = {"low": 0, "mid": 0, "high": 0}
    qs = torch.quantile(rns_ts, torch.tensor([1 / 3, 2 / 3]))

    with torch.no_grad():
        for si, ((s, pairs), emb) in enumerate(zip(ts, ts_emb_full)):
            if pairs is None or len(s) == 0:
                continue
            logits = head(emb.to(dev))
            pred = logits.argmax(-1).cpu()
            truth = pair_mask(pairs, len(s))
            assert len(pred) == len(truth), \
                "pred/truth length mismatch (embed vs pair_mask cap)"
            # all-position F1 (positive=paired)
            f1, _, _ = macro_f1_pair(truth, pred)
            # long-range subset: positions in pairs with |i-j|>=24
            # (within the cleaned/capped sequence)
            lr_pos = set()
            for (i, j) in pairs:
                if abs(i - j) >= LONG_RANGE and i < len(s) and j < len(s):
                    lr_pos.add(i); lr_pos.add(j)
            if lr_pos:
                mask = torch.zeros(len(s), dtype=torch.bool)
                for p in lr_pos:
                    mask[p] = True
                f1l, _, _ = macro_f1_pair(truth[mask], pred[mask])
                f1_lr_all.append(f1l)
            f1_all.append(f1)
            r = float(rns_ts[si])
            b = "low" if r <= qs[0] else ("mid" if r <= qs[1] else "high")
            f1_by_bin[b].append(f1)
            if lr_pos:
                lr_by_bin[b].append(f1l)
            n_by_bin[b] += 1

    def mstat(v):
        v = [x for x in v if not math.isnan(x)]
        if not v:
            return None
        v_a = np.array(v)
        return {"mean": round(float(v_a.mean()), 4),
                "n": len(v),
                "std": round(float(v_a.std()), 4)}

    res = {
        "run": RUN, "k": K, "layer_frac": 0.75,
        "bins": "RNS terciles on TS0 (same random pool)",
        "bin_edges": [round(float(qs[0]), 4), round(float(qs[1]), 4)],
        "overall_pair_f1": mstat(f1_all),
        "overall_longrange_f1": mstat(f1_lr_all),
        "pair_f1_by_bin": {b: mstat(v) for b, v in f1_by_bin.items()},
        "longrange_f1_by_bin": {b: mstat(v) for b, v in lr_by_bin.items()},
    }
    # relative drop high vs low bin
    lo = res["pair_f1_by_bin"]["low"]; hi = res["pair_f1_by_bin"]["high"]
    lol = res["longrange_f1_by_bin"]["low"]
    hil = res["longrange_f1_by_bin"]["high"]
    if lo and hi and lo["mean"] > 0:
        res["pair_drop_high_vs_low_pct"] = round(
            100 * (lo["mean"] - hi["mean"]) / lo["mean"], 1)
    if lol and hil and lol["mean"] > 0:
        res["longrange_drop_high_vs_low_pct"] = round(
            100 * (lol["mean"] - hil["mean"]) / lol["mean"], 1)
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
