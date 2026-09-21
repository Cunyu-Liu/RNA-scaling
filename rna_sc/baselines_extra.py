"""T1.2.5 remaining classical baselines (Q4; completes baselines_kmer.py).

  1. k-mer(1-6) + LightGBM (CPU, deterministic=True/force_row_wise)
  2. one-hot CNN (GPU: conv1d stack + masked global max-pool)
  3. random-emb + attention-pool head (GPU: frozen random embeddings,
     trained head; probe.py head family, order-blind minus)

Splits/sample sizes EXACTLY match baselines_kmer.py for table parity:
  family: family_validation(20000) -> family_test(4000)
  random: i%5 rule on family_validation pool (24000)

Output: evidence/classical_baselines_extra.json (+ stdout table).

Usage: python -m rna_sc.baselines_extra --device 6
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.census import GPUGuard

SPLIT_8080 = "/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet"
OUT = "/mnt/cunyuliu/rna-sc/evidence/classical_baselines_extra.json"
ALPHABET = "ACGU"
KMAX = 6
N_FEATS = sum(4 ** k for k in range(1, KMAX + 1))
VOCAB = 5
PAD_ID = 4
MAXLEN = 256
SEED = 17


def kmer_index(kmer: str) -> int:
    v = 0
    for ch in kmer:
        v = v * 4 + ALPHABET.index(ch)
    return v


def offset_for_k(k: int) -> int:
    return sum(4 ** j for j in range(1, k))


def seq_to_feats(seq: str) -> np.ndarray:
    x = np.zeros(N_FEATS, dtype=np.float32)
    canon = seq.upper().replace("T", "U")
    L = len(canon)
    for k in range(1, KMAX + 1):
        off = offset_for_k(k)
        denom = max(1, L - k + 1)
        for i in range(L - k + 1):
            km = canon[i:i + k]
            if all(c in ALPHABET for c in km):
                x[off + kmer_index(km)] += 1.0 / denom
    return x


def seq_to_ids(seq: str) -> list:
    canon = seq.upper().replace("T", "U")
    return [ALPHABET.index(b) for b in canon if b in ALPHABET][:MAXLEN]


def collect_rows(split: str, n_seq: int):
    seqs, ys = [], []
    pf = pq.ParquetFile(SPLIT_8080)
    for rb in pf.iter_batches(
            batch_size=50_000,
            columns=["split_membership", "canonical_sequence", "rna_type"]):
        d = rb.to_pydict()
        for sm, seq, rt in zip(d["split_membership"],
                               d["canonical_sequence"], d["rna_type"]):
            if sm != split:
                continue
            seqs.append(seq[:MAXLEN])
            ys.append(rt)
            if len(ys) >= n_seq:
                return seqs, ys
    return seqs, ys


def macro_f1(y_true, y_pred, n_classes):
    from collections import Counter
    ct = Counter(zip(y_true, y_pred))
    per = []
    for c in range(n_classes):
        tp = ct[(c, c)]
        fp = sum(v for (t, p), v in ct.items() if p == c and t != c)
        fn = sum(v for (t, p), v in ct.items() if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per.append(f1)
    return float(np.mean(per)), per


def run_lgbm(Xtr, ytr, Xev, yev, n_classes, seed=SEED):
    import lightgbm as lgb
    clf = lgb.LGBMClassifier(
        n_estimators=400, learning_rate=0.1, num_leaves=63,
        min_child_samples=20, class_weight="balanced",
        random_state=seed, deterministic=True, force_row_wise=True,
        n_jobs=4, verbosity=-1)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xev)
    acc = float((pred == yev).mean())
    f1, _ = macro_f1(list(yev), list(pred), n_classes)
    return acc, f1


def pad_batch(list_ids, device):
    import torch
    B = len(list_ids)
    T = max(len(x) for x in list_ids)
    ids = torch.full((B, T), PAD_ID, dtype=torch.long)
    mask = torch.zeros(B, T, dtype=torch.bool)
    for b, x in enumerate(list_ids):
        ids[b, :len(x)] = torch.tensor(x, dtype=torch.long)
        mask[b, :len(x)] = True
    return ids.to(device), mask.to(device)


def train_neural(make_model, tr_ids, ytr, ev_ids, yev, n_classes,
                 device, guard, epochs=10, lr=1e-3, batch=64):
    import torch
    import torch.nn as nn

    torch.manual_seed(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    model = make_model(n_classes).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.01)

    counts = np.bincount(np.asarray(ytr), minlength=n_classes)
    w = np.minimum(10.0, len(ytr) / (n_classes * np.maximum(counts, 1)))
    crit = nn.CrossEntropyLoss(
        weight=torch.tensor(w, dtype=torch.float32, device=device))

    ytr_arr = np.asarray(ytr)
    for ep in range(epochs):
        guard.verify_cuda_alive()
        model.train()
        perm = np.random.RandomState(SEED * 1000 + ep).permutation(len(tr_ids))
        for i in range(0, len(perm), batch):
            idx = perm[i:i + batch]
            ids, mask = pad_batch([tr_ids[j] for j in idx], device)
            yb = torch.tensor(ytr_arr[idx], dtype=torch.long, device=device)
            logits = model(ids, mask)
            loss = crit(logits, yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(ev_ids), 256):
            ids, mask = pad_batch(ev_ids[i:i + 256], device)
            preds.extend(model(ids, mask).argmax(dim=-1).cpu().tolist())
    yev_arr = np.asarray(yev)
    acc = float((np.asarray(preds) == yev_arr).mean())
    f1, _ = macro_f1(list(yev_arr), preds, n_classes)
    return acc, f1


class OneHotCNN:
    def new(self, n_classes):
        import torch
        import torch.nn as nn
        import torch.nn.functional as F

        class _M(nn.Module):
            def __init__(self):
                super().__init__()
                self.c1 = nn.Conv1d(4, 64, 7, padding=3)
                self.c2 = nn.Conv1d(64, 128, 7, padding=3)
                self.head = nn.Linear(128, n_classes)

            def forward(self, ids, mask):
                oh5 = F.one_hot(ids, VOCAB)
                xoh = oh5[..., :4].permute(0, 2, 1).float()
                h = F.relu(self.c1(xoh))
                h = F.max_pool1d(h, 2)
                h = F.relu(self.c2(h))
                m1 = mask[:, ::2]
                m2 = mask[:, 1::2]
                if m2.shape[1] < m1.shape[1]:
                    m2 = F.pad(m2, (0, 1))
                m = m1 | m2
                if m.shape[1] < h.shape[2]:
                    m = F.pad(m, (0, h.shape[2] - m.shape[1]))
                else:
                    m = m[:, :h.shape[2]]
                h = h.masked_fill(~m.unsqueeze(1), float("-inf"))
                pooled = h.max(dim=2).values
                return self.head(pooled)

        return _M()


class RandEmbHead:
    def new(self, n_classes):
        import torch
        import torch.nn as nn
        import torch.nn.functional as F

        class _M(nn.Module):
            def __init__(self, d=64):
                super().__init__()
                self.emb = nn.Embedding(VOCAB, d)
                torch.manual_seed(SEED + 1)
                nn.init.normal_(self.emb.weight, std=0.02)
                self.emb.weight.requires_grad_(False)
                self.score = nn.Linear(d, 1)
                self.head = nn.Linear(d, n_classes)

            def forward(self, ids, mask):
                h = self.emb(ids)
                s = self.score(h).squeeze(-1)
                s = s.masked_fill(~mask, float("-inf"))
                w = F.softmax(s, dim=-1)
                pooled = (h * w.unsqueeze(-1)).sum(dim=1)
                return self.head(pooled)

        return _M()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--skip-lgbm", action="store_true")
    ap.add_argument("--skip-neural", action="store_true")
    args = ap.parse_args()

    dev = "cuda:%d" % args.device
    guard = GPUGuard(dev)
    guard.check()

    out = {
        "seed": SEED,
        "n_train": args.n_train,
        "n_eval": args.n_eval,
        "epochs": args.epochs,
        "protocol": ("family: family_validation->family_test; "
                     "random: i%5 on family_validation pool "
                     "(baselines_kmer parity)"),
    }

    tr_seqs, y_tr = collect_rows("family_validation", args.n_train)
    ev_seqs, y_ev = collect_rows("family_test", args.n_eval)
    classes = sorted(set(y_tr))
    cls_map = {c: i for i, c in enumerate(classes)}
    keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
    ev_seqs = [ev_seqs[i] for i in keep_ev]
    y_ev_fam = [cls_map[y_ev[i]] for i in keep_ev]
    y_tr_fam = [cls_map[c] for c in y_tr]
    nc = len(classes)
    print("[data] family: train=%d eval=%d classes=%d"
          % (len(y_tr_fam), len(y_ev_fam), nc))

    results_fam = {}

    if not args.skip_lgbm:
        Xtr = np.stack([seq_to_feats(s) for s in tr_seqs])
        Xev = np.stack([seq_to_feats(s) for s in ev_seqs])
        acc, f1 = run_lgbm(Xtr, np.asarray(y_tr_fam), Xev,
                           np.asarray(y_ev_fam), nc)
        results_fam["kmer_lgbm"] = {
            "acc": round(acc, 4), "f1_macro": round(f1, 4),
            "baseline": "kmer1-6+LightGBM(balanced,400trees)"}
        print("[family] lgbm  acc=%.4f f1=%.4f" % (acc, f1))

    if not args.skip_neural:
        tr_ids = [seq_to_ids(s) for s in tr_seqs]
        ev_ids = [seq_to_ids(s) for s in ev_seqs]
        for tag, factory in (("onehot_cnn", OneHotCNN()),
                             ("randemb_head", RandEmbHead())):
            acc, f1 = train_neural(
                factory.new, tr_ids, y_tr_fam, ev_ids, y_ev_fam, nc,
                dev, guard, epochs=args.epochs)
            results_fam[tag] = {
                "acc": round(acc, 4), "f1_macro": round(f1, 4),
                "baseline": "%s(seed17, %d ep)" % (tag, args.epochs)}
            print("[family] %-11s acc=%.4f f1=%.4f" % (tag, acc, f1))

    out["family"] = results_fam

    n_all = args.n_train + args.n_eval
    all_seqs, y_all = collect_rows("family_validation", n_all)
    y_all_i = [cls_map[c] for c in y_all if c in cls_map]
    assert len(y_all_i) == n_all, "class drift in random pool"
    idx_ev = [i for i in range(n_all) if i % 5 == 0]
    idx_tr = [i for i in range(n_all) if i % 5 != 0]
    results_rand = {}

    if not args.skip_lgbm:
        Xtr2 = np.stack([seq_to_feats(all_seqs[i]) for i in idx_tr])
        Xev2 = np.stack([seq_to_feats(all_seqs[i]) for i in idx_ev])
        acc, f1 = run_lgbm(Xtr2, np.asarray([y_all_i[i] for i in idx_tr]),
                           Xev2, np.asarray([y_all_i[i] for i in idx_ev]), nc)
        results_rand["kmer_lgbm"] = {
            "acc": round(acc, 4), "f1_macro": round(f1, 4),
            "baseline": "kmer1-6+LightGBM(balanced,400trees)"}
        print("[random] lgbm  acc=%.4f f1=%.4f" % (acc, f1))

    if not args.skip_neural:
        all_ids = [seq_to_ids(s) for s in all_seqs]
        tr_ids2 = [all_ids[i] for i in idx_tr]
        ev_ids2 = [all_ids[i] for i in idx_ev]
        ytr2 = [y_all_i[i] for i in idx_tr]
        yev2 = [y_all_i[i] for i in idx_ev]
        for tag, factory in (("onehot_cnn", OneHotCNN()),
                             ("randemb_head", RandEmbHead())):
            acc, f1 = train_neural(
                factory.new, tr_ids2, ytr2, ev_ids2, yev2, nc,
                dev, guard, epochs=args.epochs)
            results_rand[tag] = {
                "acc": round(acc, 4), "f1_macro": round(f1, 4),
                "baseline": "%s(seed17, %d ep)" % (tag, args.epochs)}
            print("[random] %-11s acc=%.4f f1=%.4f" % (tag, acc, f1))

    out["random"] = results_rand

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
