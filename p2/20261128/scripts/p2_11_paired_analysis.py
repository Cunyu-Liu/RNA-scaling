import json, numpy as np, sys
R="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/P2_11"
def load(t): return json.load(open(f"{R}/{t}/summary.json"))
out={}
for scale in ["650M","300M"]:
    a=load(f"{scale}_2B"); b=load(f"{scale}_59B")
    # pair by (data_seed, probe_seed)
    ma={(r["data_seed"],r["probe_seed"]):r["f1"] for r in a["records"]}
    mb={(r["data_seed"],r["probe_seed"]):r["f1"] for r in b["records"]}
    keys=sorted(set(ma)&set(mb))
    diffs=[mb[k]-ma[k] for k in keys]
    diffs_pp=[d*100 for d in diffs]
    out[scale]={
        "n_pairs":len(keys),
        "f1_2B_mean":a["mean_f1"],"f1_2B_sd":a["sd_f1"],
        "f1_59B_mean":b["mean_f1"],"f1_59B_sd":b["sd_f1"],
        "budget_effect_pp_mean":round(float(np.mean(diffs_pp)),3),
        "budget_effect_pp_sd":round(float(np.std(diffs_pp,ddof=1)),3),
        "budget_effect_pp_sem":round(float(np.std(diffs_pp,ddof=1)/np.sqrt(len(diffs_pp))),3),
        "sign_positive_frac":round(float(np.mean([d>0 for d in diffs])),3),
        "per_pair_pp":[round(d,3) for d in diffs_pp],
    }
print(json.dumps(out,indent=2,ensure_ascii=False))
json.dump(out,open(f"{R}/budget_effect_paired.json","w"),indent=2,ensure_ascii=False)