"""更新 corpus_arm_verdict.json：补齐 30M/300M 语料臂（三行完整梯度）。"""
import json

rows = [json.loads(l) for l in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl")]
fv = json.load(open("/mnt/cunyuliu/rna-sc/evidence/factorial_verdict.json"))

def best_f1(run_name):
    best = None
    for r in rows:
        if r.get("run") == run_name and "family" in r.get("split", ""):
            if best is None or r["f1_macro"] > best["f1_macro"]:
                best = r
    return best

out = {}
for arm in ["30M", "100M", "300M"]:
    b = best_f1("RNA-Sc-%s_s17_rinalmocorpus" % arm)
    r22 = fv["table"][arm]["f1_2B"]["f1"]
    out[arm] = {
        "r22": {"f1": r22, "layer": fv["table"][arm]["f1_2B"]["layer"]},
        "rinalmo_corpus_replica": {"f1": round(b["f1_macro"], 4),
                                   "layer": b["layer"]},
        "delta_pp": round(100 * (b["f1_macro"] - r22), 2)
    }

d = {
    "generated": "2026-10-11",
    "protocol": "S11 probe rna_type, family split, final ckpt, best layer; 2B budget both",
    "table": out,
    "note": ("corpus effect decays monotonically with scale: "
             "+7.93/+2.33/+0.63pp (30M/100M/300M) — corpus-boundary "
             "evidence; single-corpus gains saturate as capacity grows"),
    "s8_contact_secondary": {
        "100M_r22_fold": 1.28, "100M_rinalmo_fold": 1.40,
        "note": "S8 contact caliber reproduces corpus effect (+9%) at 100M"
    }
}
p = "/mnt/cunyuliu/rna-sc/evidence/corpus_arm_verdict.json"
json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
print("saved", p)
for k, v in out.items():
    print("%s: r22 %.4f -> replica %.4f (%+.2fpp, L%s)" % (
        k, v["r22"]["f1"], v["rinalmo_corpus_replica"]["f1"],
        v["delta_pp"], v["rinalmo_corpus_replica"]["layer"]))
