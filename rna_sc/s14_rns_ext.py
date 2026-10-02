"""Q20: External-SOTA RNS + random-split F1 correlation.

For each published model (RiNALMo micro/mega/giga, RNA-FM-96M,
NucleicBERT-404M) + our controlled family points for reference:
  1. RNS@10 on the SAME real pool (family_validation 1500) and the
     SAME matched random pool (Markov, 4500) — our s14 protocol.
  2. random-split family probe F1: read from eval/eval_matrix_results
     .jsonl where available (ours); external random-split F1 from
     probe_results_ext.jsonl (random split, i%5 rows on held-out
     pool) — reuse the protocol used for the published-model table.
  3. Spearman / Pearson across ALL models (RNS vs random F1).

Output: evidence/s14_rns_ext.json
"""
from __future__ import annotations

import argparse
import json
import random

import numpy as np
import torch

from rna_sc.census import GPUGuard

ALPHABET = "ACGU"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s14_rns_ext.json"
K = 10
LEN_CAP = 192
N_REAL = 1500


def stream_real(n_needed, seed=17):
    import pyarrow.parquet as pq
    from rna_sc.config import SPLIT_8080
    seqs = []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence"]):
        d = rb.to_pydict()
        for sm, seq in zip(d["split_membership"], d["canonical_sequence"]):
            if sm != "family_validation":
                continue
            seqs.append("".join(b for b in seq.upper().replace("T", "U")
                                if b in ALPHABET)[:LEN_CAP])
            if len(seqs) >= n_needed * 3:
                break
        if len(seqs) >= n_needed * 3:
            break
    rng = random.Random(seed)
    rng.shuffle(seqs)
    return seqs[:n_needed]


def rns_from_emb(real_emb, rand_emb, k=K):
    R = torch.nn.functional.normalize(real_emb, dim=1)
    A = torch.nn.functional.normalize(rand_emb, dim=1)
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
    return float((n_rand / k).mean())


# ---- model adapters: each returns (name, fn seqs->emb tensor cpu) ----

def ours_embedder(run, device):
    from rna_sc.probe import load_encoder
    model, ck = load_encoder("/mnt/cunyuliu/rna-sc/runs/%s" % run)
    model = model.to(device).eval()
    L = ck["cfg"]["arch"]["n_layers"]
    L_pick = max(0, min(L - 1, int(round(0.75 * (L - 1)))))
    AL = ALPHABET

    def fn(seqs):
        model.eval()
        out = []
        with torch.no_grad(), torch.amp.autocast("cuda",
                                                 dtype=torch.bfloat16):
            for i in range(0, len(seqs), 8):
                chunk = seqs[i:i + 8]
                ids = [[AL.index(b) for b in s] or [0, 1]
                       for s in chunk]
                T = max(len(x) for x in ids)
                x = torch.tensor(
                    [r + [4] * (T - len(r)) for r in ids], device=device)
                pad = x == 4
                _, _, hids = model(x, return_all_hiddens=True)
                h = hids[L_pick]
                hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
                lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
                out.append((hm.sum(1) / lens).cpu())
        return torch.cat(out, 0)
    return fn


def rinalmo_embedder(ckpt_dir, device):
    # multimolecule lives in the rna_junction_preorganization_v1_1 env
    # (documented in probe_rinalmo.py header); reuse it via env python
    import subprocess, sys
    PYEXT = ("/home/cunyuliu/miniconda3/envs/"
             "rna_junction_preorganization_v1_1/bin/python")
    import os
    helper = "/tmp/_rns_ext_embed_rinalmo.py"
    with open(helper, "w") as fh:
        fh.write(EMBED_HELPER_RINALMO)
    outp = "/tmp/_rns_ext_emb_%s.pt" % os.path.basename(ckpt_dir)

    def fn(seqs):
        payload = json.dumps({"ckpt": ckpt_dir,
                              "seqs": seqs})
        r = subprocess.run([PYEXT, helper, outp], input=payload,
                           capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:])
        return torch.load(outp, map_location="cpu")
    return fn


EMBED_HELPER_RINALMO = r'''
import sys, json
import torch
out_path = sys.argv[1]
payload = json.load(sys.stdin)
ckpt = payload["ckpt"]; seqs = payload["seqs"]
import multimolecule.models.rinalmo  # noqa
from multimolecule.models.rinalmo import RiNALMoModel
from multimolecule.tokenisers import RnaTokenizer
tok = RnaTokenizer.from_pretrained(ckpt)
m = RiNALMoModel.from_pretrained(ckpt).eval().cuda()
TOK = {"A": 6, "C": 7, "G": 8, "U": 9}
PAD = tok.pad_token_id
out = []
with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
    for i in range(0, len(seqs), 8):
        chunk = [s[:192] for s in seqs[i:i+8]]
        encs = [[TOK[b] for b in s if b in TOK] or [TOK["A"]]
                for s in chunk]
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
print("saved", out_path)
'''


def rnafm_embedder(device):
    from rna_sc.probe_rnafm import (RNAFMEncoder, CKPT, TOK, BOS, PAD)
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    m = RNAFMEncoder(ck["model"]).eval().to(device)
    L = m.n_layers

    def fn(seqs):
        out = []
        with torch.no_grad(), torch.amp.autocast(
                "cuda", dtype=torch.bfloat16):
            for i in range(0, len(seqs), 8):
                encs = [[BOS] + [TOK[b] for b in s[:LEN_CAP]
                                 if b in TOK] or [BOS, TOK["A"]]
                        for s in seqs[i:i + 8]]
                T = max(len(x) for x in encs)
                ids = torch.tensor(
                    [r + [PAD] * (T - len(r)) for r in encs],
                    dtype=torch.long, device=device)
                pad = ids == PAD
                hids = m(ids, return_all_hiddens=True)
                h = hids[L - 1]
                hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
                lens = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
                out.append((hm.sum(1) / lens).cpu())
        return torch.cat(out, 0)
    return fn


def nucleicbert_embedder(device):
    import sys
    sys.path.insert(0, "/mnt/cunyuliu/rna-sc/ext/nucleicbert")
    from bert import NucleicBertModel  # repo API
    ck = "/mnt/cunyuliu/rna-sc/ext/nucleicbert/ckpt"
    m = NucleicBertModel.from_pretrained(ckpt).eval().to(device)
    # NB BPE tokens loaded from its tokenizer json
    import json as _json
    tk = _json.load(open(
        "/mnt/cunyuliu/rna-sc/ext/nucleicbert/tokenizer.json"))

    def fn(seqs):
        out = []
        with torch.no_grad(), torch.amp.autocast(
                "cuda", dtype=torch.bfloat16):
            for i in range(0, len(seqs), 8):
                chunk = seqs[i:i + 8]
                ids = []
                for s in chunk:
                    t = tk.get("encode", None)
                    # fallback: char-level via vocab
                    ids.append([t[s[j]] if t and s[j] in t else 0
                                for j in range(len(s))])
                T = max(len(x) for x in ids)
                x = torch.tensor(
                    [r + [0] * (T - len(r)) for r in ids],
                    dtype=torch.long, device=device)
                am = (x != 0) | (x == 0)  # NB pad=0 but A also 0?
                # use attention of real length instead
                am = torch.zeros_like(x, dtype=torch.bool)
                for j, r in enumerate(ids):
                    am[j, :len(r)] = True
                o = m(x, attention_mask=am,
                      output_hidden_states=True)
                h = o.hidden_states[-1]
                hm = h.float().masked_fill(~am.unsqueeze(-1), 0.0)
                lens = am.sum(-1).clamp(min=1).float().unsqueeze(-1)
                out.append((hm.sum(1) / lens).cpu())
        return torch.cat(out, 0)
    return fn


def read_random_split_f1():
    """random-split family F1 for every model we have on record."""
    out = {}
    p = "/mnt/cunyuliu/rna-sc/eval/eval_matrix_results.jsonl"
    import os
    if os.path.exists(p):
        for line in open(p):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r.get("split") == "random"
                    and r.get("protocol") == "probe-balanced"):
                out[r["model"]] = r.get("best_f1_macro")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    real = stream_real(N_REAL)
    from rna_sc.s14_rns import make_random_pool
    rand, _, _ = make_random_pool(real, 3)

    jobs = []
    try:
        jobs.append(("RNA-Sc-1M", ours_embedder("RNA-Sc-1M_s17", dev)))
    except Exception as e:
        print("1M skip", e)
    try:
        jobs.append(("RNA-Sc-10M", ours_embedder("RNA-Sc-10M_s17", dev)))
    except Exception as e:
        print("10M skip", e)
    try:
        jobs.append(("RNA-Sc-30M", ours_embedder("RNA-Sc-30M_s17", dev)))
    except Exception as e:
        print("30M skip", e)
    try:
        jobs.append(("RNA-Sc-100M", ours_embedder("RNA-Sc-100M_s17", dev)))
    except Exception as e:
        print("100M skip", e)
    try:
        jobs.append(("RiNALMo-micro",
                     rinalmo_embedder(
                         "/mnt/cunyuliu/rna-sc/ext/rinalmo", dev)))
    except Exception as e:
        print("rinalmo-micro skip", e)
    try:
        jobs.append(("RiNALMo-mega",
                     rinalmo_embedder(
                         "/mnt/cunyuliu/rna-sc/ext/rinalmo-mega", dev)))
    except Exception as e:
        print("rinalmo-mega skip", e)
    try:
        jobs.append(("RiNALMo-giga",
                     rinalmo_embedder(
                         "/mnt/cunyuliu/rna-sc/ext/rinalmo-giga", dev)))
    except Exception as e:
        print("rinalmo-giga skip", e)
    try:
        jobs.append(("RNA-FM-96M", rnafm_embedder(dev)))
    except Exception as e:
        print("rnafm skip", e)

    rns_table = {}
    for name, fn in jobs:
        try:
            re = fn(real)
            ae = fn(rand)
            v = rns_from_emb(re, ae)
            rns_table[name] = round(v, 4)
            print("%-14s RNS@10 = %.4f" % (name, v), flush=True)
            del re, ae
            torch.cuda.empty_cache()
        except Exception as e:
            print("%-14s FAILED %s" % (name, str(e)[:200]), flush=True)
            rns_table[name] = None

    rnd_f1 = read_random_split_f1()
    print("random-split F1 on record:", json.dumps(rnd_f1, indent=1))

    pairs = [(n, rns_table[n], rnd_f1.get(n))
             for n in rns_table if rns_table[n] is not None]
    have = [(n, r, f) for n, r, f in pairs if f is not None]
    res = {"rns_k10": rns_table,
           "random_split_f1_source": rnd_f1,
           "pairs": have}
    if len(have) >= 4:
        a = np.array([r for _, r, _ in have])
        b = np.array([f for _, _, f in have])
        ra = np.argsort(np.argsort(a))
        rb = np.argsort(np.argsort(b))
        res["spearman_rns_randomF1"] = round(
            float(np.corrcoef(ra, rb)[0, 1]), 4)
        res["pearson_rns_randomF1"] = round(
            float(np.corrcoef(a, b)[0, 1]), 4)
        res["n_models"] = len(have)
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
