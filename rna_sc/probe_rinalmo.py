"""T1.3.2 external model probe #2: RiNALMo micro (36M, multimolecule).

Second line-1 external model under the SAME pooled-linear probe protocol
as probe_rnafm.py (RNA-FM), making layer behavior comparable across
external pretraining recipes (RiNALMo lineage: 36M non-coding RNA corpus,
rotary, 28-vocab n-mer).

Checkpoint: /mnt/cunyuliu/rna-sc/ext/rinalmo (multimolecule rinalmo-micro,
d=480, 12 layers, 20 heads, rotary; downloaded via hf-mirror 2026-09-22).

Tokenizer: library RnaTokenizer verified at runtime — A=6 C=7 G=8 U=9,
cls=1 eos=2 pad=0 (verified by tokenizing ACGU through the library
tokenizer and asserting the mapping before any probing; abort on drift).

Protocol (EXACT parity with probe_rnafm.py):
  - family_validation (20000) -> family_test (4000), context 256
  - per-layer post-block states (hidden_states[1..L], HF convention)
  - mean-pool over non-pad tokens (pooled-linear external protocol)
  - linear probe, class-balanced weights, inc12-style layer seed 17+li
  - rows appended to eval/probe_results_ext.jsonl (run RiNALMo-micro-36M)

RUN WITH the rna_junction_preorganization_v1_1 env (multimolecule there):
  /home/cunyuliu/miniconda3/envs/rna_junction_preorganization_v1_1/bin/
    python -m rna_sc.probe_rinalmo --device 3
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.census import GPUGuard

CKPT_DIR = "/mnt/cunyuliu/rna-sc/ext/rinalmo"
OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
RUN_NAME = "RiNALMo-micro-36M"
ALPHABET = "ACGU"
CLS, EOS, PAD = 1, 2, 0
TOK = {"A": 6, "C": 7, "G": 8, "U": 9}


def load_model():
    import multimolecule.models.rinalmo  # noqa: F401 (registers AutoConfig)
    from multimolecule.models.rinalmo import RiNALMoModel
    from multimolecule.tokenisers import RnaTokenizer

    tok = RnaTokenizer.from_pretrained(CKPT_DIR)
    probe_ids = tok("".join(ALPHABET), add_special_tokens=False)[
        "input_ids"]
    assert list(probe_ids) == [TOK[c] for c in ALPHABET], (
        "tokenizer drift: ACGU -> %s (expected %s)"
        % (probe_ids, [TOK[c] for c in ALPHABET]))
    full = tok("".join(ALPHABET))["input_ids"]
    assert full[0] == CLS and full[-1] == EOS, (
        "special-token drift: %s" % full)
    print("[tokenizer] verified ACGU->%s, cls=%d eos=%d pad=%d"
          % (probe_ids, full[0], full[-1], tok.pad_token_id))
    assert tok.pad_token_id == PAD

    m = RiNALMoModel.from_pretrained(CKPT_DIR)
    m.eval()
    return m, m.config.num_hidden_layers


def collect_states(model, device, split, n_seq, L, context_nt=256,
                   batch_nt=8192):
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    model = model.to(device).eval()
    states = [[] for _ in range(L)]
    labels = []
    rows = []
    cur_max = 0
    n = 0

    def _enc(seq):
        s = seq.upper().replace("T", "U")
        return [TOK[b] for b in s if b in TOK]

    def flush():
        nonlocal rows
        if not rows:
            return
        T = max(len(r[0]) for r in rows)
        ids = torch.tensor(
            [r[0] + [PAD] * (T - len(r[0])) for r in rows],
            dtype=torch.long, device=device)
        am = (ids != PAD)
        with torch.amp.autocast("cuda", dtype=torch.bfloat16):
            out = model(ids, attention_mask=am, output_hidden_states=True)
        hids = out.hidden_states  # tuple: (emb, block1..blockL)
        lengths = am.sum(-1).clamp(min=1).float().unsqueeze(-1)
        for li in range(L):
            h = hids[li + 1]
            hm = h.float().masked_fill(~am.unsqueeze(-1), 0.0)
            pooled = hm.sum(dim=1) / lengths
            states[li].append(pooled.cpu())
        labels.extend(r[1] for r in rows)
        rows = []

    pf = pq.ParquetFile(SPLIT_8080)
    with torch.no_grad():
        for rb in pf.iter_batches(
                batch_size=50_000,
                columns=["split_membership", "canonical_sequence",
                         "rna_type"]):
            d = rb.to_pydict()
            for sm, seq, rt in zip(d["split_membership"],
                                   d["canonical_sequence"], d["rna_type"]):
                if sm != split:
                    continue
                ids = [CLS] + _enc(seq[:context_nt])
                if len(ids) < 3:
                    continue
                Lx = len(ids)
                if rows and (len(rows) + 1) * max(cur_max, Lx) > batch_nt:
                    flush()
                    cur_max = 0
                rows.append((ids, rt))
                cur_max = max(cur_max, Lx)
                n += 1
                if n >= n_seq:
                    flush()
                    X = [torch.cat(s, dim=0) for s in states]
                    return X, labels[:len(X[0])]
        flush()
    X = [torch.cat(s, dim=0) for s in states]
    return X, labels[:len(X[0])]


def probe_one_layer(X_tr, y_tr, X_ev, y_ev, n_classes, device, layer_seed,
                    epochs=8):
    import torch.nn.functional as F
    torch.manual_seed(layer_seed)
    d = X_tr.shape[1]
    W = torch.zeros(d, n_classes, device=device, requires_grad=True)
    Xtr, Xev = X_tr.to(device).float(), X_ev.to(device).float()
    ytr = torch.tensor(y_tr, device=device)
    yev = torch.tensor(y_ev, device=device)
    freq = collections.Counter(y_tr)
    n = len(y_tr)
    weights = torch.tensor(
        [min(10.0, n / max(1, freq[c])) for c in range(n_classes)],
        dtype=torch.float32, device=device)
    opt = torch.optim.AdamW([W], lr=1e-3, weight_decay=0.01)
    for _ in range(epochs):
        perm = torch.randperm(len(Xtr), device=device)
        for i in range(0, len(Xtr), 256):
            idx = perm[i:i + 256]
            loss = F.cross_entropy(Xtr[idx] @ W, ytr[idx], weight=weights)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    with torch.no_grad():
        pred = (Xev @ W).argmax(-1)
        acc = float((pred == yev).float().mean())
        tp = collections.Counter(zip(y_ev, pred.tolist()))
        f1s = []
        for c in range(n_classes):
            ctp = tp[(c, c)]
            cfp = sum(v for (t, p), v in tp.items() if p == c and t != c)
            cfn = sum(v for (t, p), v in tp.items() if t == c and p != c)
            prec = ctp / (ctp + cfp) if ctp + cfp else 0.0
            rec = ctp / (ctp + cfn) if ctp + cfn else 0.0
            f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return acc, sum(f1s) / n_classes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=3)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    model, L = load_model()
    print("RiNALMo loaded: %d layers (d=%s)" % (L, model.config.hidden_size))

    X_tr, y_tr = collect_states(model, dev, "family_validation",
                                args.n_train, L)
    X_ev, y_ev = collect_states(model, dev, "family_test", args.n_eval, L)
    print("collected: train=%d eval=%d" % (len(y_tr), len(y_ev)))
    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    y_tri = [cls_map[c] for c in y_tr]
    keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
    y_evi = [cls_map[y_ev[i]] for i in keep_ev]

    best = None
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for li in range(L):
        acc, f1 = probe_one_layer(
            X_tr[li], y_tri, X_ev[li][keep_ev], y_evi, len(classes),
            dev, layer_seed=17 + li)
        rec = {"run": RUN_NAME, "layer": li,
               "rel_depth": round(li / (L - 1), 3),
               "depth_band": ("early" if li / (L - 1) <= 0.33 else
                              ("middle" if li / (L - 1) <= 0.66
                               else "late")),
               "n_layers": L, "ckpt_nt": None,
               "n_classes": len(classes),
               "n_train": len(y_tri), "n_eval": len(y_evi),
               "acc": round(acc, 4), "f1_macro": round(f1, 4),
               "task": "rna_type classification (S11)",
               "split": "family_validation->family_test",
               "protocol": "probe-balanced (class-weighted, inc12 seed)"}
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print("layer %d (rel %.2f) acc=%.4f f1=%.4f" %
              (li, li / (L - 1), acc, f1))
        if best is None or f1 > best["f1_macro"]:
            best = rec
    print("BEST:", json.dumps(best))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
