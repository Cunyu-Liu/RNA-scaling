"""T1.3.2 external model probe #4: NucleicBERT (404M, KIT-MBS, Nat MI 2026).

Fourth line-1 external model under the SAME pooled-linear protocol as
probe_rnafm.py / probe_rinalmo.py — adds a third corpus recipe contrast:
MARS ncRNA subset (~30M seqs) vs RNAcentral general (RNA-FM) vs ncRNA
36M (RiNALMo). Param count 404M (32 layers, d=1024, 32 heads, BPE 25).

Checkpoint: /mnt/cunyuliu/rna-sc/ext/nucleicbert_repo/pretrained.pt
(Zenodo 10.5281/zenodo.16989562, 1.6GB)
Tokenizer: PreTrainedTokenizerFast(tokenizer_file=noncoding_seqs.json)
  verified ids: a=6 c=8 g=11 u=20, [PAD]=0 [CLS]=3 [SEP]=4.

Protocol (EXACT parity with probe_rnafm.py):
  - family_validation (20000) -> family_test (4000), context 256
  - per-layer post-block states (embeddings_list[1..L]; index 0 = embedding)
  - mean-pool over non-pad tokens (pooled-linear external protocol)
  - balanced linear probe, layer seed 17+li, 8 epochs
  - rows appended to eval/probe_results_ext.jsonl (run NucleicBERT-404M)

Run: python -m rna_sc.probe_nucleicbert --device N
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

REPO = "/mnt/cunyuliu/rna-sc/ext/nucleicbert_repo"
CKPT = os.path.join(REPO, "pretrained.pt")
TOK_FILE = os.path.join(REPO, "nucleicbert", "tokenizers", "noncoding_seqs.json")
OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results_ext.jsonl"
RUN_NAME = "NucleicBERT-404M"
ALPHABET = "ACGU"

# verified from noncoding_seqs.json model.vocab (2026-09-27)
TOK = {"a": 6, "c": 8, "g": 11, "u": 20}
PAD, CLS, SEP = 0, 3, 4
MAXLEN = 1024  # NB_CONFIG max_length


def load_model(ckpt=CKPT, random_init=None, moment_matched=None):
    """random_init / moment_matched: H2/H3 decomposition controls (S4/S5
    protocol parity with rna_sc.probe). random_init replaces all weights
    with seeded init; moment_matched re-inits then matches per-tensor
    mean/std to the TRAINED model (captures weight statistics, destroys
    learned structure)."""
    sys.path.insert(0, REPO)
    from nucleicbert.models.bert import BERT, NB_CONFIG
    model = BERT(**NB_CONFIG)
    if random_init is None and moment_matched is None:
        sd = torch.load(ckpt, map_location="cpu")
        if isinstance(sd, dict) and "state_dict" in sd:
            sd = sd["state_dict"]
        model.load_state_dict(sd)
    else:
        torch.manual_seed(random_init if random_init is not None
                          else moment_matched)
        if moment_matched is not None:
            trained = BERT(**NB_CONFIG)
            tsd = torch.load(ckpt, map_location="cpu")
            if isinstance(tsd, dict) and "state_dict" in tsd:
                tsd = tsd["state_dict"]
            trained.load_state_dict(tsd)
            trained_sd = {k: v.clone() for k, v in trained.state_dict().items()
                          if v.is_floating_point()}
            with torch.no_grad():
                new_sd = model.state_dict()
                n_matched = 0
                for k, v in new_sd.items():
                    if not v.is_floating_point() or v.numel() < 2:
                        continue
                    t = trained_sd[k]
                    tm, ts = t.mean(), t.std()
                    vm, vs = v.mean(), v.std()
                    if ts > 0 and vs > 0:
                        v.copy_((v - vm) / vs * ts + tm)
                        n_matched += 1
                model.load_state_dict(new_sd)
                print("moment-matched %d tensors to trained moments"
                      % n_matched)
    model.eval()
    return model, NB_CONFIG["num_hidden_layers"]


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
        s = seq.upper().replace("T", "U").lower()
        return [TOK[b] for b in s if b in TOK]

    def flush():
        nonlocal rows
        if not rows:
            return
        T = max(len(r[0]) for r in rows)
        ids = torch.tensor(
            [r[0] + [PAD] * (T - len(r[0])) for r in rows],
            dtype=torch.long, device=device)
        # BERT.forward(input_ids, output_attentions=True) -> (mlm, attn, emb)
        _, _, emb_list = model(ids, output_attentions=True)
        # emb_list: list of (B,1,T,d) — [embedding, block1..blockL]
        pad = ids == PAD
        lengths = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
        for li in range(L):
            h = emb_list[li + 1].squeeze(1)  # skip embedding layer
            hm = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            pooled = hm.sum(dim=1) / lengths
            states[li].append(pooled.cpu())
        labels.extend(r[1] for r in rows)
        rows = []

    pf = pq.ParquetFile(SPLIT_8080)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for rb in pf.iter_batches(
                batch_size=50_000,
                columns=["split_membership", "canonical_sequence",
                         "rna_type"]):
            d = rb.to_pydict()
            for sm, seq, rt in zip(d["split_membership"],
                                   d["canonical_sequence"], d["rna_type"]):
                if sm != split:
                    continue
                ids = [CLS] + _enc(seq[:context_nt]) + [SEP]
                if len(ids) < 3:
                    continue
                Lx = min(len(ids), MAXLEN)
                ids = ids[:Lx]
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
                    epochs=8, class_names=None):
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
    per_class = {}
    for c in range(n_classes):
        name = class_names[c] if class_names else str(c)
        per_class[name] = round(f1s[c], 4)
    return acc, sum(f1s) / n_classes, per_class


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    ap.add_argument("--probe-seed", type=int, default=17)
    ap.add_argument("--random-init", type=int, default=None,
                    help="H2 control: seeded random init (S4 parity)")
    ap.add_argument("--moment-matched", type=int, default=None,
                    help="H3 control: moment-matched re-init (S5 parity)")
    args = ap.parse_args()
    dev = "cuda:%d" % args.device
    GPUGuard(dev).check()

    run_name = RUN_NAME
    if args.random_init is not None:
        run_name = "%s_randinit%d" % (RUN_NAME, args.random_init)
    elif args.moment_matched is not None:
        run_name = "%s_mommatch%d" % (RUN_NAME, args.moment_matched)
    print("model mode: random-init=%s moment-matched=%s -> run %s"
          % (args.random_init, args.moment_matched, run_name))

    model, L = load_model(random_init=args.random_init,
                          moment_matched=args.moment_matched)
    print("NucleicBERT loaded: %d layers" % L)

    X_tr, y_tr = collect_states(model, dev, "family_validation",
                                args.n_train, L)
    X_ev, y_ev = collect_states(model, dev, "family_test", args.n_eval, L)
    print("collected train=%d eval=%d" % (len(y_tr), len(y_ev)))

    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    y_tri = [cls_map[c] for c in y_tr if c in cls_map]
    keep_tr = [i for i, c in enumerate(y_tr) if c in cls_map]
    y_evi, keep_ev = [], []
    for i, c in enumerate(y_ev):
        if c in cls_map:
            y_evi.append(cls_map[c])
            keep_ev.append(i)
    print("classes=%d" % len(classes))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows_out = []
    for li in range(L):
        Xtr = X_tr[li][keep_tr]
        Xev = X_ev[li][keep_ev]
        acc, f1, per_class = probe_one_layer(
            Xtr, y_tri, Xev, y_evi, len(classes), dev,
            layer_seed=args.probe_seed + li, class_names=classes)
        rec = {"run": run_name, "layer": li,
               "rel_depth": round(li / max(1, L - 1), 3),
               "n_layers": L, "acc": round(acc, 4),
               "f1_macro": round(f1, 4), "per_class_f1": per_class,
               "pooling": "per-token state mean-pool + balanced linear head "
                          "(external pooled-linear protocol, parity with "
                          "probe_rnafm/probe_rinalmo)",
               "task": "rna_type classification (S11 global property)",
               "split": "family_validation->family_test"}
        rows_out.append(rec)
        print("layer %d (rel=%.2f) acc=%.4f f1=%.4f"
              % (li, li / max(1, L - 1), acc, f1))
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    best = max(rows_out, key=lambda r: r["f1_macro"])
    print("BEST L%d rel=%.3f f1=%.4f"
          % (best["layer"], best["rel_depth"], best["f1_macro"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
