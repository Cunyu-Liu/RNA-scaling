# -*- coding: utf-8 -*-
"""P2.9 线性擦除因果：擦除可线性读出的结构(配对)方向→MLM 损失升幅 vs 随机方向。
借鉴 Hallee&Gleghorn DEPTH。多深度 INLP 擦除，比较可读深度 vs 擦除致损深度。
用法: python p2_9_erasure.py --run-dir <weights/RNA-Sc-650M_s17> --tag 650M
"""
import argparse, json, os, random
import numpy as np
import torch
import torch.nn.functional as F
import pyarrow.parquet as pq
from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

ALPHABET="ACGU"; PAD=4; MASK=5; IGNORE=-100
BPRNA="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/bpRNA_parsed.parquet"
OUTROOT="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/P2_9"
CTX=256

def encode(s):
    return [ALPHABET.index(b) for b in s.upper().replace("T","U") if b in ALPHABET][:CTX]

def get_resid(model, dev, seqs, L):
    cap={}
    h=model.blocks[L].register_forward_hook(lambda m,i,o: cap.__setitem__('r', o.detach()))
    states=[]; labs=[]
    model.eval()
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s,pr in seqs:
            ids=encode(s); n=len(ids)
            if n<4: continue
            x=torch.tensor([ids],device=dev); model(x)
            states.append(cap['r'][0,1:1+n,:].float().cpu())
            p=[0]*n
            for i,j in pr:
                if i<=n and j<=n: p[i-1]=1; p[j-1]=1
            labs.extend(p)
    h.remove()
    return torch.cat(states,0), torch.tensor(labs,dtype=torch.long)

def inlp_directions(X, y, dev, max_iter=12):
    """iteratively train linear paired probe, collect unit directions until chance."""
    dirs=[]; Xc=X.clone().to(dev)
    for it in range(max_iter):
        d=Xc.shape[1]
        W=torch.zeros(d,2,device=dev,requires_grad=True)
        npos=float((y==1).sum()); nneg=float(len(y)-npos)
        w=torch.tensor([1.0,max(1.0,nneg/max(1.0,npos))],device=dev)
        opt=torch.optim.AdamW([W],lr=1e-3,weight_decay=0.01)
        yt=y.to(dev)
        for ep in range(15):
            perm=torch.randperm(len(Xc),device=dev)
            for i in range(0,len(Xc),8192):
                idx=perm[i:i+8192]
                loss=F.cross_entropy(Xc[idx]@W, yt[idx], weight=w)
                opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
        with torch.no_grad():
            logit=(Xc@W)[:,1]
            # AUC via rank
            order=logit.argsort(); ranks=torch.empty_like(order,dtype=torch.float); ranks[order]=torch.arange(len(order),device=dev,dtype=torch.float)
            pos=ranks[yt==1]; auc=(pos.sum()-len(pos)*(len(pos)-1)/2)/(len(pos)*(len(yt)-len(pos)))
            auc=float(auc)
        wdir=W[:,1]-W[:,0]; wdir=(wdir/wdir.norm()).detach()
        dirs.append(wdir)
        if auc<0.55: break
        Xc=(Xc-(Xc@wdir).unsqueeze(-1)*wdir.unsqueeze(0)).detach()
    return dirs, auc

def proj_matrix(dirs, D, dev):
    M=torch.eye(D,device=dev)
    for w in dirs:
        M=M-(M@w).unsqueeze(-1)*w.unsqueeze(0)  # M = M (I - w w^T)
    return M

def random_proj(rank, D, dev, seed):
    g=torch.Generator(device=dev).manual_seed(seed)
    A=torch.randn(D,rank,device=dev,generator=g)
    Q,_=torch.linalg.qr(A)
    return torch.eye(D,device=dev)-Q@Q.T

def mlm_loss(model, dev, seqs, L, M, mask_seed=17):
    """forward with hook at L applying M; masked CE loss."""
    def hook(m,i,o):
        return o @ M.to(o.dtype)
    h=model.blocks[L].register_forward_hook(hook) if M is not None else None
    g=torch.Generator(device=dev).manual_seed(mask_seed)
    tot=0.0; cnt=0
    model.eval()
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for s,pr in seqs:
            ids=encode(s); n=len(ids)
            if n<8: continue
            x=torch.tensor([ids],device=dev)
            tgt=torch.full((1,n),IGNORE,device=dev,dtype=torch.long)
            mask=torch.rand(1,n,generator=g,device=dev)<0.15
            xm=x.clone(); xm[mask]=MASK
            tgt[mask]=x[mask]
            logits,loss=model(xm,targets=tgt)
            tot+=float(loss)*int(mask.sum()); cnt+=int(mask.sum())
    if h: h.remove()
    return tot/max(1,cnt)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True); ap.add_argument("--tag",required=True)
    ap.add_argument("--device",type=int,default=0)
    args=ap.parse_args()
    dev=f"cuda:{args.device}"; GPUGuard(dev).check()
    tab=pq.read_table(BPRNA).to_pydict()
    idx=[i for i,sp in enumerate(tab["split"]) if sp=="train"]
    rng=random.Random(17); rng.shuffle(idx)
    probe_seqs=[(tab["seq"][i],tab["pairs"][i]) for i in idx[:2000]]
    eval_seqs=[(tab["seq"][i],tab["pairs"][i]) for i in idx[2000:2600]]
    model,ck=load_encoder(args.run_dir); model=model.to(dev)
    arch=ck["cfg"]["arch"]; D=arch["d_model"]; NL=arch["n_layers"]
    depths={"rel0.3":round(0.3*(NL-1)),"rel0.5":round(0.5*(NL-1)),"rel0.7":round(0.7*(NL-1)),"rel0.9":round(0.9*(NL-1))}
    os.makedirs(f"{OUTROOT}/{args.tag}",exist_ok=True)
    out={"tag":args.tag,"depths":{}}
    base_loss=None
    for name,L in depths.items():
        X,y=get_resid(model,dev,probe_seqs,L)
        dirs,auc=inlp_directions(X,y,dev)
        rank=len(dirs)
        M=proj_matrix(dirs,D,dev)
        Mr=random_proj(rank,D,dev,17)
        lb=mlm_loss(model,dev,eval_seqs,L,None)
        le=mlm_loss(model,dev,eval_seqs,L,M)
        lr=mlm_loss(model,dev,eval_seqs,L,Mr)
        rec={"layer":L,"rank":rank,"final_probe_auc":round(auc,4),
             "loss_base":round(lb,5),"loss_erasure":round(le,5),"loss_random":round(lr,5),
             "delta_erasure":round(le-lb,5),"delta_random":round(lr-lb,5),
             "extra_over_random":round((le-lb)-(lr-lb),5)}
        out["depths"][name]=rec
        print(f"[{args.tag}] {name} L{L} rank{rank} auc{auc:.3f} base{lb:.4f} eras{le:.4f} rand{lr:.4f} extra{rec['extra_over_random']:.4f}",flush=True)
    with open(f"{OUTROOT}/{args.tag}/summary.json","w") as f: json.dump(out,f,indent=2)
    print("SAVED",f"{OUTROOT}/{args.tag}/summary.json",flush=True)

if __name__=="__main__":
    main()