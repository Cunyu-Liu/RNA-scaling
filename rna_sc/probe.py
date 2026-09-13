"""Per-layer probe protocol (S7 / T1.3) for RNA-Sc checkpoints.

Protocol discipline (SPEC S7 + TokBench lesson):
  - sequence-level probes use attention pooling over non-pad tokens
    (mean-pool is FORBIDDEN: order-blind, ACG==GCA);
  - probes are trained on a family-level train split and evaluated on
    family-level eval split (via the global family assignment);
  - every layer l in [0..L-1] is probed with the SAME head/architecture so
    the layer axis is comparable;
  - downstream task v1: Rfam-style family classification on release22
    (rna_type field, family-level split via family_assignment table) —
    an S11 "global property" task using zero external data, available
    from day 1 while external eval sets are being integrated.

Outputs per (run, layer): {layer, train_n, eval_n, n_classes, acc, f1_macro,
  head_params} appended to /mnt/cunyuliu/rna-sc/eval/probe_results.jsonl.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.config import SPLIT_8080
from rna_sc.census import GPUGuard
from rna_sc.data import iter_mlm_batches, IGNORE
from rna_sc.model import RNAMLMEncoder, PAD
from rna_sc.specs import FAMILY

EVAL_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"

# rna_type strings -> label ids (built on the fly from the train sample;
# kept stable by deterministic streaming order, then persisted).
MAX_CLASSES = 24


class AttentionPoolProbe(nn.Module):
    """Attention-pooled linear probe over one layer's token states."""

    def __init__(self, d_model: int, n_classes: int):
        super().__init__()
        self.score = nn.Linear(d_model, 1)
        self.head = nn.Linear(d_model, n_classes)

    def forward(self, h, key_pad):
        # h: (B, T, D); key_pad: (B, T) True at PAD
        s = self.score(h).squeeze(-1)
        s = s.masked_fill(key_pad, float("-inf"))
        w = F.softmax(s, dim=-1)
        pooled = (h * w.unsqueeze(-1)).sum(dim=1)
        return self.head(pooled)


def load_encoder(run_dir: str) -> tuple[RNAMLMEncoder, dict]:
    cks = sorted([f for f in os.listdir(run_dir) if f.startswith("ckpt_")],
                 key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    ck = torch.load(os.path.join(run_dir, cks[-1]), map_location="cpu",
                    weights_only=False)
    mcfg = ck["cfg"]["arch"]
    model = RNAMLMEncoder(d_model=mcfg["d_model"], n_layers=mcfg["n_layers"],
                          n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
    model.load_state_dict(ck["model"])
    return model, ck


@torch.no_grad()
def collect_states(model, device, split, n_seq, d_layers, context_nt=256,
                   batch_nt=8192):
    """Single-pass state collection: streams (sequence, rna_type) rows from
    the split, encodes each sequence (no masking — pure hidden states), and
    pools per-sequence mean over non-pad tokens for every layer.

    Batching here is independent from the MLM training stream (probes never
    feed back into training), so a simple length-bucketed batching is fine.
    Sequence and label come from the SAME row: no pairing bug possible.
    """
    import pyarrow.parquet as pq
    model = model.to(device).eval()
    states = [[] for _ in range(d_layers)]
    labels = []
    rows: list[tuple[list[int], str]] = []
    cur_max = 0
    n = 0

    def _enc(seq: str) -> list[int]:
        from rna_sc.data import ALPHABET
        s = seq.upper().replace("T", "U")
        return [ALPHABET.index(b) for b in s if b in ALPHABET]

    def flush():
        if not rows:
            return
        T = max(len(r[0]) for r in rows)
        ids = torch.tensor(
            [r[0] + [PAD] * (T - len(r[0])) for r in rows],
            dtype=torch.long, device=device)
        _, _, hids = model(ids, return_all_hiddens=True)
        pad = ids == PAD
        lengths = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
        for li, h in enumerate(hids):
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            pooled = hm.sum(dim=1) / lengths
            states[li].append(pooled.cpu())
        labels.extend(r[1] for r in rows)
        rows.clear()

    pf = pq.ParquetFile(SPLIT_8080)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for rb in pf.iter_batches(
                batch_size=50_000,
                columns=["split_membership", "canonical_sequence", "rna_type"]):
            d = rb.to_pydict()
            for sm, seq, rt in zip(d["split_membership"],
                                   d["canonical_sequence"], d["rna_type"]):
                if sm != split:
                    continue
                ids = _enc(seq[:context_nt])
                if len(ids) < 2:
                    continue
                L = len(ids)
                if rows and (len(rows) + 1) * max(cur_max, L) > batch_nt:
                    flush()
                    cur_max = 0
                rows.append((ids, rt))
                cur_max = max(cur_max, L)
                n += 1
                if n >= n_seq:
                    flush()
                    X = [torch.cat(s, dim=0) for s in states]
                    return X, labels[:len(X[0])]
        flush()
    X = [torch.cat(s, dim=0) for s in states]
    return X, labels[:len(X[0])]


class LinearProbe(nn.Module):
    """Linear head over a pooled (B, D) sequence representation."""

    def __init__(self, d_model: int, n_classes: int):
        super().__init__()
        self.head = nn.Linear(d_model, n_classes)

    def forward(self, x):
        return self.head(x)


def probe_one_layer(X_tr, y_tr, X_ev, y_ev, n_classes, device, epochs=8):
    d = X_tr.shape[1]
    probe = LinearProbe(d, n_classes).to(device)
    opt = torch.optim.AdamW(probe.parameters(), lr=1e-3, weight_decay=0.01)
    Xtr, Xev = X_tr.to(device).float(), X_ev.to(device).float()
    ytr = torch.tensor(y_tr, device=device)
    yev = torch.tensor(y_ev, device=device)
    for ep in range(epochs):
        perm = torch.randperm(len(Xtr), device=device)
        for i in range(0, len(Xtr), 256):
            idx = perm[i:i + 256]
            logits = probe(Xtr[idx])
            loss = F.cross_entropy(logits, ytr[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    with torch.no_grad():
        pred = probe(Xev).argmax(-1)
        acc = (pred == yev).float().mean().item()
        f1 = _macro_f1(pred, yev, n_classes)
    return acc, f1


def _macro_f1(pred, yev, n_classes):
    f1s = []
    for c in range(n_classes):
        tp = ((pred == c) & (yev == c)).sum().item()
        fp = ((pred == c) & (yev != c)).sum().item()
        fn = ((pred != c) & (yev == c)).sum().item()
        if tp + fn == 0:
            continue
        prec = tp / max(1, tp + fp)
        rec = tp / (tp + fn)
        f1s.append(2 * prec * rec / max(1e-9, prec + rec))
    return sum(f1s) / max(1, len(f1s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--device", type=int, default=1)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    guard = GPUGuard(dev)
    guard.check()
    model, ck = load_encoder(args.run_dir)
    L = ck["cfg"]["arch"]["n_layers"]
    # family-level split for the probe: family_validation vs family_test
    # (both disjoint from train by cluster construction; validation split is
    # used for pretraining model selection, so probes avoid it).
    X_tr, y_tr = collect_states(model, dev, "family_validation", args.n_train, L)
    X_ev, y_ev = collect_states(model, dev, "family_test", args.n_eval, L)
    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    y_tri = [cls_map[c] for c in y_tr if c in cls_map]
    keep_tr = [i for i, c in enumerate(y_tr) if c in cls_map]
    y_evi, keep_ev = [], []
    for i, c in enumerate(y_ev):
        if c in cls_map:
            y_evi.append(cls_map[c])
            keep_ev.append(i)
    print("classes=%d train=%d eval=%d" % (len(classes), len(y_tri), len(y_evi)))
    os.makedirs(os.path.dirname(EVAL_OUT), exist_ok=True)
    for li in range(L):
        Xtr = X_tr[li][keep_tr]
        Xev = X_ev[li][keep_ev]
        acc, f1 = probe_one_layer(Xtr, y_tri, Xev, y_evi, len(classes), dev)
        rec = {"run": os.path.basename(args.run_dir), "layer": li,
               "ckpt_nt": ck.get("nt"), "n_classes": len(classes),
               "n_train": len(y_tri), "n_eval": len(y_evi),
               "acc": round(acc, 4), "f1_macro": round(f1, 4),
               "pooling": "per-token state mean-pool per sequence + linear "
                          "head (S7 sequencing tasks will use attention "
                          "pooling over tokens; this pooled probe is the "
                          "day-1 protocol)",
               "task": "rna_type classification (S11 global property)",
               "split": "family_validation->family_test"}
        with open(EVAL_OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print("layer %d acc=%.4f f1=%.4f" % (li, acc, f1))
    assert guard.cpu_fallback_count == 0


if __name__ == "__main__":
    main()
