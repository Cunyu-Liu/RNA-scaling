"""Q20b: random-split family probe for external models.

Same protocol as our eval_matrix random rows: held-out pool rows i%5
as eval, rest as train (i is a row counter, deterministic), balanced
linear head, best layer. Reuses each model's own encoder helpers.

Output: appends rows to eval/eval_matrix_results.jsonl with
model names "RiNALMo-micro/mega/giga", "RNA-FM-96M".
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch

from rna_sc.census import GPUGuard

ALPHABET = "ACGU"
LEN_CAP = 256
OUT = "/mnt/cunyuliu/rna-sc/eval/eval_matrix_results.jsonl"


def stream_pool(n=24000):
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    rows = []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence",
                     "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm not in ("family_validation", "family_test", "val",
                          "test"):
                continue
            s = "".join(b for b in seq.upper().replace("T", "U")
                        if b in ALPHABET)[:LEN_CAP]
            if len(s) < 16:
                continue
            rows.append((s, rt))
            if len(rows) >= n:
                break
        if len(rows) >= n:
            break
    # deterministic i%5 random split (our v1 protocol)
    tr = [(s, rt) for i, (s, rt) in enumerate(rows) if i % 5 != 0]
    ev = [(s, rt) for i, (s, rt) in enumerate(rows) if i % 5 == 0]
    return tr, ev


def balanced_probe(X_tr, y_tr, X_ev, y_ev, n_classes, device, seed):
    torch.manual_seed(seed)
    d = X_tr.shape[1]
    W = torch.zeros(d, n_classes, device=device, requires_grad=True)
    freq = torch.bincount(y_tr, minlength=n_classes).float()
    w = torch.tensor([min(10.0, len(y_tr) / max(1, freq[c].item()))
                      for c in range(n_classes)], device=device)
    opt = torch.optim.Adam([W], lr=0.05)
    Xd, yd = X_tr.to(device), y_tr.to(device)
    for ep in range(300):
        logits = Xd @ W
        loss = torch.nn.functional.cross_entropy(logits, yd, weight=w)
        opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        logits = X_ev.to(device) @ W
        pred = logits.argmax(-1).cpu()
    tp = ((pred == y_ev) & (y_ev >= 0)).sum().item()
    acc = tp / max(1, len(y_ev))
    f1s = []
    for c in range(n_classes):
        ctp = ((pred == c) & (y_ev == c)).sum().item()
        cfp = ((pred == c) & (y_ev != c)).sum().item()
        cfn = ((pred != c) & (y_ev == c)).sum().item()
        prec = ctp / max(1, ctp + cfp)
        rec = ctp / max(1, ctp + cfn)
        f1s.append(2 * prec * rec / max(1e-9, prec + rec))
    return acc, float(np.mean(f1s))


def embed_ours(run, device, seqs):
    from rna_sc.probe import load_encoder
    m, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % run)
    m = m.to(device).eval()
    L = ck["cfg"]["arch"]["n_layers"]
    out = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for i in range(0, len(seqs), 8):
            ids = [[ALPHABET.index(b) for b in s] for s in seqs[i:i+8]]
            T = max(len(x) for x in ids)
            x = torch.tensor([r + [4]*(T-len(r)) for r in ids],
                             device=device)
            pad = x == 4
            _, _, hids = m(x, return_all_hiddens=True)
            h = hids[L-1]
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
            out.append((hm.sum(1)/lens).cpu())
    return torch.cat(out, 0)


def embed_rinalmo(ckpt, seqs):
    import subprocess
    PYEXT = ("/home/cunyuliu/miniconda3/envs/"
             "rna_junction_preorganization_v1_1/bin/python")
    helper = "/tmp/_rand_embed_rinalmo.py"
    with open(helper, "w") as fh:
        fh.write(RINALMO_HELPER)
    outp = "/tmp/_rand_emb.pt"
    r = subprocess.run([PYEXT, helper, outp],
                       input=json.dumps({"ckpt": ckpt, "seqs": seqs}),
                       capture_output=True, text=True, timeout=7200)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])
    return torch.load(outp, map_location="cpu")


RINALMO_HELPER = r'''
import sys, json, torch
out_path = sys.argv[1]
p = json.load(sys.stdin)
import multimolecule.models.rinalmo  # noqa
from multimolecule.models.rinalmo import RiNALMoModel
from multimolecule.tokenisers import RnaTokenizer
tok = RnaTokenizer.from_pretrained(p["ckpt"])
m = RiNALMoModel.from_pretrained(p["ckpt"]).eval().cuda()
TOK = {"A": 6, "C": 7, "G": 8, "U": 9}
PAD = tok.pad_token_id
out = []
with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
    for i in range(0, len(p["seqs"]), 8):
        chunk = [s[:192] for s in p["seqs"][i:i+8]]
        encs = [[TOK[b] for b in s if b in TOK] or [TOK["A"]] for s in chunk]
        T = max(len(x) for x in encs)
        ids = torch.tensor([r + [PAD]*(T-len(r)) for r in encs],
                           dtype=torch.long, device="cuda")
        am = (ids != PAD)
        o = m(ids, attention_mask=am, output_hidden_states=True)
        h = o.hidden_states[-1]
        hm = h.float().masked_fill(~am.unsqueeze(-1), 0.0)
        lens = am.sum(-1).clamp(min=1).float().unsqueeze(-1)
        out.append((hm.sum(1)/lens).cpu())
torch.save(torch.cat(out, 0), out_path)
'''


def embed_rnafm(seqs, device):
    from rna_sc.probe_rnafm import RNAFMEncoder, CKPT, TOK, BOS, PAD
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    m = RNAFMEncoder(ck["model"]).eval().to(device)
    out = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for i in range(0, len(seqs), 8):
            encs = [[BOS] + [TOK[b] for b in s[:192] if b in TOK]
                    or [BOS, TOK["A"]] for s in seqs[i:i+8]]
            T = max(len(x) for x in encs)
            ids = torch.tensor([r + [PAD]*(T-len(r)) for r in encs],
                               dtype=torch.long, device=device)
            pad = ids == PAD
            hids = m(ids, return_all_hiddens=True)
            h = hids[-1]
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
            out.append((hm.sum(1)/lens).cpu())
    return torch.cat(out, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    tr, ev = stream_pool()
    classes = sorted({rt for _, rt in tr + ev})
    cmap = {c: i for i, c in enumerate(classes)}
    y_tr = torch.tensor([cmap[rt] for _, rt in tr])
    y_ev = torch.tensor([cmap[rt] for _, rt in ev])

    jobs = [
        ("RiNALMo-micro", lambda: embed_rinalmo(
            "/mnt/cunyuliu/rna-sc/ext/rinalmo",
            [s for s, _ in tr] + [s for s, _ in ev])),
        ("RiNALMo-mega", lambda: embed_rinalmo(
            "/mnt/cunyuliu/rna-sc/ext/rinalmo-mega",
            [s for s, _ in tr] + [s for s, _ in ev])),
        ("RiNALMo-giga", lambda: embed_rinalmo(
            "/mnt/cunyuliu/rna-sc/ext/rinalmo-giga",
            [s for s, _ in tr] + [s for s, _ in ev])),
        ("RNA-FM-96M", lambda: torch.cat([
            embed_rnafm([s for s, _ in tr], dev),
            embed_rnafm([s for s, _ in ev], dev)], 0)),
    ]
    for name, fn in jobs:
        try:
            emb = fn()
            n_tr = len(tr)
            X_tr, X_ev = emb[:n_tr], emb[n_tr:]
            acc, f1 = balanced_probe(X_tr, y_tr, X_ev, y_ev,
                                     len(classes), dev, seed=17)
            rec = {"model": name, "protocol": "probe-balanced",
                   "split": "random", "best_layer": None,
                   "n_layers": None, "n_train": n_tr,
                   "n_eval": len(ev), "best_acc": round(acc, 4),
                   "best_f1_macro": round(f1, 4)}
            with open(OUT, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(name, "random F1 =", round(f1, 4), flush=True)
            del emb
            torch.cuda.empty_cache()
        except Exception as e:
            print(name, "FAILED", str(e)[:200], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
