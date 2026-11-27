# -*- coding: utf-8 -*-
"""P2.8 结构读出位置实验：resid_post vs attn_query/attn_key/ffn_up。
借鉴 Hallee&Gleghorn READOUT。固定残差流结构最佳层，比较读出位置。
per-token 配对分类（位置 F1，非饱和），线性头训到收敛，randinit+随机旋转对照。
用法: python p2_8_readout_positions.py --run-dir <weights/RNA-Sc-650M_s17> --layer 15 --tag 650M [--randinit 17]
"""
import argparse, json, os, random, math
import numpy as np
import torch
import pyarrow.parquet as pq
from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder
from rna_sc.model import RNAMLMEncoder

ALPHABET = "ACGU"; PAD = 4
BPRNA = "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/bpRNA_parsed.parquet"
OUTROOT = "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/P2_8"
CTX = 256

def seq_lens(seqs):
    out = []
    for s in seqs:
        ids = [ALPHABET.index(b) for b in s.upper().replace("T","U") if b in ALPHABET][:CTX]
        out.append(len(ids) if len(ids) >= 4 else 0)
    return out

def paired_labels(seqs, pairs_list):
    labs = []
    for s, pairs in zip(seqs, pairs_list):
        ids = [ALPHABET.index(b) for b in s.upper().replace("T","U") if b in ALPHABET][:CTX]
        n = len(ids)
        if n < 4: continue
        p = [0]*n
        for i,j in pairs:
            if i <= n and j <= n:
                p[i-1] = 1; p[j-1] = 1
        labs.extend(p)
    return np.array(labs, dtype=np.int64)

def collect(model, dev, seqs, pairs_list, L, dims, tag, split):
    """hooks capture resid/q/k/ffn at layer L; write float16 memmap per position."""
    cap = {}
    h1 = model.blocks[L].attn.qkv.register_forward_hook(lambda m,i,o: cap.__setitem__('qkv', o.detach()))
    h2 = model.blocks[L].mlp[0].register_forward_hook(lambda m,i,o: cap.__setitem__('ffn', o.detach()))
    h3 = model.blocks[L].register_forward_hook(lambda m,i,o: cap.__setitem__('resid', o.detach()))
    lens = seq_lens(seqs); total = sum(lens)
    os.makedirs(f"{OUTROOT}/{tag}", exist_ok=True)
    # cache: skip collection if all position files complete
    paths = {p: f"{OUTROOT}/{tag}/{split}_{p}.f16" for p in dims}
    if all(os.path.exists(paths[p]) and os.path.getsize(paths[p]) == total*d*2 for p,d in dims.items()):
        print(f"[{tag}/{split}] cache hit, skip collection ({total} tokens)", flush=True)
        return total
    mm = {p: np.memmap(paths[p], dtype=np.float16, mode='w+', shape=(total, d))
          for p,d in dims.items()}
    off = 0
    model.eval()
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s, n in zip(seqs, lens):
            if n == 0: continue
            ids = [ALPHABET.index(b) for b in s.upper().replace("T","U") if b in ALPHABET][:CTX]
            x = torch.tensor([ids], device=dev)
            model(x)
            qkv = cap['qkv'][0,1:1+n,:].float()      # drop CLS
            q,k,_ = qkv.chunk(3, dim=-1)
            resid = cap['resid'][0,1:1+n,:].float()
            ffn = cap['ffn'][0,1:1+n,:].float()
            mm['resid_post'][off:off+n] = resid.cpu().numpy().astype(np.float16)
            mm['attn_query'][off:off+n] = q.cpu().numpy().astype(np.float16)
            mm['attn_key'][off:off+n] = k.cpu().numpy().astype(np.float16)
            mm['ffn_up'][off:off+n] = ffn.cpu().numpy().astype(np.float16)
            off += n
    for p in mm: mm[p].flush()
    h1.remove(); h2.remove(); h3.remove()
    return total

def probe(Xtr_path, ytr, Xev_path, yev, dim, dev, seed=17, max_epochs=40):
    torch.manual_seed(seed)
    Xtr = torch.tensor(np.asarray(np.memmap(Xtr_path, dtype=np.float16, mode='r', shape=(len(ytr), dim))), dtype=torch.float32)
    Xev = torch.tensor(np.asarray(np.memmap(Xev_path, dtype=np.float16, mode='r', shape=(len(yev), dim))), dtype=torch.float32)
    on_gpu = dim <= 2000
    Xtr_d = Xtr.to(dev) if on_gpu else Xtr
    Xev_d = Xev.to(dev) if on_gpu else Xev
    W = torch.zeros(dim, 2, device=dev, requires_grad=True)
    npos = float((ytr==1).sum()); nneg = float(len(ytr)-npos)
    w = torch.tensor([1.0, max(1.0, nneg/max(1.0,npos))], device=dev)
    opt = torch.optim.AdamW([W], lr=1e-3, weight_decay=0.01)
    ytr_t = torch.tensor(ytr, device=dev)
    plateau = 0; best_loss = 1e9
    for ep in range(max_epochs):
        perm = torch.randperm(len(ytr), device=dev)
        tot = 0.0; nb = 0
        for i in range(0, len(ytr), 8192):
            idx = perm[i:i+8192]
            xb = Xtr_d[idx] if on_gpu else Xtr_d[idx.cpu().numpy()].to(dev)
            loss = torch.nn.functional.cross_entropy(xb @ W, ytr_t[idx], weight=w)
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
            tot += float(loss.detach()); nb += 1
        tl = tot/nb
        if tl < best_loss - 1e-4:
            best_loss = tl; plateau = 0
        else:
            plateau += 1
        if plateau >= 4: break
    preds = []
    with torch.no_grad():
        for i in range(0, len(yev), 16384):
            xe = Xev_d[i:i+16384] if on_gpu else Xev_d[i:i+16384].to(dev)
            preds.append((xe @ W).argmax(-1).cpu().numpy())
    pred = np.concatenate(preds)
    del Xtr, Xev, Xtr_d, Xev_d
    tp = int(((pred==1)&(yev==1)).sum()); fp = int(((pred==1)&(yev==0)).sum()); fn = int(((pred==0)&(yev==1)).sum())
    f1 = 2*tp/(2*tp+fp+fn) if (2*tp+fp+fn) else 0.0
    prec = tp/(tp+fp) if (tp+fp) else 0.0; rec = tp/(tp+fn) if (tp+fn) else 0.0
    acc = float((pred==yev).mean())
    return dict(f1=round(f1,4), precision=round(prec,4), recall=round(rec,4), acc=round(acc,4),
                epochs=ep+1, final_train_loss=round(tl,5))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--randinit", type=int, default=None)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--rotate", type=int, default=None, help="random rotation seed for resid control")
    args = ap.parse_args()
    dev = f"cuda:{args.device}"; GPUGuard(dev).check()
    tab = pq.read_table(BPRNA).to_pydict()
    by = {"train":[], "test":[]}
    for i,sp in enumerate(tab["split"]):
        if sp in by: by[sp].append(i)
    rng = random.Random(17)
    tr = rng.sample(by["train"], min(8000, len(by["train"])))
    ev = rng.sample(by["test"], min(1500, len(by["test"])))
    tr_seqs=[tab["seq"][i] for i in tr]; tr_pairs=[tab["pairs"][i] for i in tr]
    ev_seqs=[tab["seq"][i] for i in ev]; ev_pairs=[tab["pairs"][i] for i in ev]
    ytr = paired_labels(tr_seqs, tr_pairs); yev = paired_labels(ev_seqs, ev_pairs)
    model, ck = load_encoder(args.run_dir)
    arch = ck["cfg"]["arch"]
    if args.randinit is not None:
        torch.manual_seed(args.randinit)
        model = RNAMLMEncoder(d_model=arch["d_model"], n_layers=arch["n_layers"],
                              n_heads=arch["n_heads"], d_ff=arch["d_ff"])
    model = model.to(dev)
    D = arch["d_model"]; FF = arch["d_ff"]
    dims = {"resid_post":D, "attn_query":D, "attn_key":D, "ffn_up":FF}
    ntr = collect(model, dev, tr_seqs, tr_pairs, args.layer, dims, args.tag, "train")
    nev = collect(model, dev, ev_seqs, ev_pairs, args.layer, dims, args.tag, "eval")
    assert ntr == len(ytr) and nev == len(yev), (ntr, len(ytr), nev, len(yev))
    results = {}
    for p,d in dims.items():
        r = probe(f"{OUTROOT}/{args.tag}/train_{p}.f16", ytr, f"{OUTROOT}/{args.tag}/eval_{p}.f16", yev, d, dev)
        results[p] = r
        print(f"[{args.tag}] {p}: F1={r['f1']} acc={r['acc']} epochs={r['epochs']}", flush=True)
    # random rotation control on resid_post
    if args.rotate is not None:
        g = torch.Generator().manual_seed(args.rotate)
        R = torch.linalg.qr(torch.randn(D, D, generator=g))[0].numpy().astype(np.float16)
        for split,y in [("train",ytr),("eval",yev)]:
            src = np.memmap(f"{OUTROOT}/{args.tag}/{split}_resid_post.f16", dtype=np.float16, mode='r', shape=(len(y),D))
            dst = np.memmap(f"{OUTROOT}/{args.tag}/{split}_rot{args.rotate}.f16", dtype=np.float16, mode='w+', shape=(len(y),D))
            for i in range(0, len(y), 20000):
                dst[i:i+20000] = (np.asarray(src[i:i+20000]).astype(np.float32) @ R.astype(np.float32)).astype(np.float16)
            dst.flush()
        r = probe(f"{OUTROOT}/{args.tag}/train_rot{args.rotate}.f16", ytr, f"{OUTROOT}/{args.tag}/eval_rot{args.rotate}.f16", yev, D, dev)
        results[f"resid_rot{args.rotate}"] = r
        print(f"[{args.tag}] resid_rot{args.rotate}: F1={r['f1']}", flush=True)
    out = {"tag":args.tag, "layer":args.layer, "randinit":args.randinit,
           "n_train_tokens":int(ntr), "n_eval_tokens":int(nev),
           "paired_rate_train":round(float(ytr.mean()),4), "paired_rate_eval":round(float(yev.mean()),4),
           "positions":results}
    with open(f"{OUTROOT}/{args.tag}/summary.json","w") as f: json.dump(out,f,indent=2)
    print("SAVED", f"{OUTROOT}/{args.tag}/summary.json", flush=True)

if __name__ == "__main__":
    main()