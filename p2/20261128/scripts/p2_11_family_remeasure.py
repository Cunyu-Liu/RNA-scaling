# -*- coding: utf-8 -*-
"""P2.11-rna_type 家族预算效应多种子重测（恢复版 split）。
650M/300M × 2B/5.9B × 探针种子{17,29,43,61,79} × 数据子样{17,29}。
复用 probe.py collect_states/probe_one_layer（mean-pool，best-layer macro-F1）。
用法: python p2_11_family_remeasure.py --tag 650M_2B --run-dir <weights/RNA-Sc-650M_s17>
"""
import argparse, json, os, random
import numpy as np
import torch
import rna_sc.probe as P
from rna_sc.probe import load_encoder
from rna_sc.census import GPUGuard

RECOVERED="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/release22_split_8080_recovered.parquet"
OUTROOT="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/P2_11"
P.SPLIT_8080 = RECOVERED
import rna_sc.config as C
C.SPLIT_8080 = RECOVERED

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True); ap.add_argument("--tag",required=True)
    ap.add_argument("--device",type=int,default=0)
    ap.add_argument("--n-val-pool",type=int,default=30000)
    ap.add_argument("--n-test-pool",type=int,default=6000)
    args=ap.parse_args()
    dev=f"cuda:{args.device}"; GPUGuard(dev).check()
    model,ck=load_encoder(args.run_dir); model=model.to(dev)
    L=ck["cfg"]["arch"]["n_layers"]
    # collect mean-pooled states once (large pool)
    Xv,yv_raw=P.collect_states(model,dev,"family_validation",args.n_val_pool,L)
    Xt,yt_raw=P.collect_states(model,dev,"family_test",args.n_test_pool,L)
    classes=sorted(set(yv_raw)|set(yt_raw)); cmap={c:i for i,c in enumerate(classes)}
    yv=np.array([cmap[c] for c in yv_raw]); yt=np.array([cmap[c] for c in yt_raw])
    nc=len(classes)
    print(f"[{args.tag}] pool val={len(yv)} test={len(yt)} classes={nc} layers={L}",flush=True)
    os.makedirs(f"{OUTROOT}/{args.tag}",exist_ok=True)
    recs=[]
    for data_seed in [17,29]:
        rv=random.Random(data_seed); rt=random.Random(data_seed+1000)
        iv=rv.sample(range(len(yv)),20000); it=rt.sample(range(len(yt)),4000)
        yv_s=yv[iv]; yt_s=yt[it]
        for probe_seed in [17,29,43,61,79]:
            best=None
            for li in range(L):
                Xtr=Xv[li][iv]; Xev=Xt[li][it]
                acc,f1=P.probe_one_layer(Xtr,yv_s.tolist(),Xev,yt_s.tolist(),nc,dev,epochs=8,layer_seed=probe_seed+li)
                if best is None or f1>best["f1"]:
                    best={"layer":li,"f1":round(f1,4),"acc":round(acc,4),"rel":round(li/(L-1),3)}
            rec={"data_seed":data_seed,"probe_seed":probe_seed,**best}
            recs.append(rec)
            print(f"[{args.tag}] data{data_seed} probe{probe_seed} bestF1={best['f1']}@L{best['layer']}",flush=True)
    out={"tag":args.tag,"run_dir":args.run_dir,"n_classes":nc,"records":recs,
         "mean_f1":round(float(np.mean([r["f1"] for r in recs])),4),
         "sd_f1":round(float(np.std([r["f1"] for r in recs],ddof=1)),4)}
    json.dump(out,open(f"{OUTROOT}/{args.tag}/summary.json","w"),indent=2)
    print(f"[{args.tag}] MEAN F1={out['mean_f1']} SD={out['sd_f1']} (n={len(recs)})",flush=True)

if __name__=="__main__":
    main()