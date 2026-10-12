"""COV 前向共变 300M 补测（用户需求：图 d 缺 300M）。

复用 /tmp/covariation_test.py 的完整协议（mask-j + mutate-partner-i
+ unpaired-k 对照），仅改 RUNS 只跑 300M，输出合并进
covariation_test.json（不覆盖，update 键）。
"""
import json
import random
import sys

sys.path.insert(0, "/home/cunyuliu/rna-sc")

import torch
import pyarrow.parquet as pq

from rna_sc.probe import load_encoder

BPRNA = "/mnt/cunyuliu/rna-sc/data/bpRNA_parsed.parquet"
ALPHABET = "ACGU"
MASK = 5
COMP = {0: 3, 3: 0, 1: 2, 2: 1}
OUT = "/mnt/cunyuliu/rna-sc/evidence/covariation_test.json"
RUN = "/mnt/cunyuliu/rna-sc/runs/RNA-Sc-300M_s17"


def load_test():
    seqs, pairs_list = [], []
    pf = pq.ParquetFile(BPRNA)
    for rb in pf.iter_batches(batch_size=50_000,
                              columns=["seq", "pairs", "split"]):
        d = rb.to_pydict()
        for s, p, sp in zip(d["seq"], d["pairs"], d["split"]):
            if sp == "test":
                seqs.append(s)
                pairs_list.append(p)
    return seqs, pairs_list


def encode(seq):
    return [ALPHABET.index(b) for b in seq.upper().replace("T", "U")
            if b in ALPHABET][:256]


def build_conditions(ids, pairs, rng, max_pairs=20):
    n = len(ids)
    valid = [(i - 1, j - 1) for i, j in pairs if i <= n and j <= n]
    paired_pos = set()
    for i, j in valid:
        paired_pos.add(i)
        paired_pos.add(j)
    unpaired = [p for p in range(n) if p not in paired_pos]
    rng.shuffle(valid)
    valid = valid[:max_pairs]
    conds = []
    for i, j in valid:
        xi = ids[i]
        if xi not in COMP:
            continue
        far = [k for k in unpaired if abs(k - i) > 5 and abs(k - j) > 5]
        k = rng.choice(far) if far else None
        muts = [b for b in range(4) if b != xi]
        conds.append({"i": i, "j": j, "k": k, "xi": xi, "muts": muts,
                      "ids": list(ids)})
    return conds


def run_model_batch(model, dev, rows, read_pos):
    T = max(len(r) for r in rows)
    ids = torch.tensor([r + [4] * (T - len(r)) for r in rows],
                       dtype=torch.long, device=dev)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        out = model(ids, return_all_hiddens=False)
        logits = out[0]
    probs = torch.softmax(logits.float(), dim=-1)
    out = []
    for bi, rp in zip(range(len(rows)), read_pos):
        out.append(probs[bi, rp, :4].cpu())
    return torch.stack(out)


def evaluate_model(model, dev, seqs, pairs_list, n_seq=100, seed=17):
    rng = random.Random(seed)
    idx = rng.sample(range(len(seqs)), n_seq)
    stats = {"cov": [], "ctrl": [], "old_drop": []}
    for si in idx:
        ids = encode(seqs[si])
        if len(ids) < 20:
            continue
        conds = build_conditions(ids, pairs_list[si], rng)
        for c in conds:
            base = list(c["ids"])
            rows, reads = [], []
            orig = list(base)
            orig[c["j"]] = MASK
            rows.append(orig)
            reads.append(c["j"])
            for m in c["muts"]:
                mut = list(base)
                mut[c["i"]] = m
                mut[c["j"]] = MASK
                rows.append(mut)
                reads.append(c["j"])
            if c["k"] is not None:
                orig_k = list(base)
                orig_k[c["k"]] = MASK
                rows.append(orig_k)
                reads.append(c["k"])
                for m in c["muts"]:
                    mut_k = list(base)
                    mut_k[c["i"]] = m
                    mut_k[c["k"]] = MASK
                    rows.append(mut_k)
                    reads.append(c["k"])
            P = run_model_batch(model, dev, rows, reads)
            # cov: 读 j 位
            p_orig = P[0]
            for bi, m in enumerate(c["muts"]):
                p_mut = P[1 + bi]
                stats["cov"].append(float(p_mut[COMP[m]] -
                                          p_orig[COMP[m]]))
            if c["k"] is not None:
                ko = 1 + len(c["muts"])
                pk_orig = P[ko]
                for bi, m in enumerate(c["muts"]):
                    pk_mut = P[ko + 1 + bi]
                    stats["ctrl"].append(float(pk_mut[COMP[m]] -
                                                pk_orig[COMP[m]]))
                for bi, m in enumerate(c["muts"]):
                    p_mut = P[1 + bi]
                    stats["old_drop"].append(float(p_mut[m] - p_orig[m]))
    import numpy as np
    return {"cov": {"mean": float(np.mean(stats["cov"])),
                    "n": len(stats["cov"])},
            "ctrl": {"mean": float(np.mean(stats["ctrl"])),
                     "n": len(stats["ctrl"])},
            "old_drop": {"mean": float(np.mean(stats["old_drop"])),
                         "n": len(stats["old_drop"])},
            "cov_minus_ctrl": float(np.mean(stats["cov"]) -
                                    np.mean(stats["ctrl"]))}


def main():
    dev = "cuda:6"
    seqs, pairs_list = load_test()
    print("[cov300] test seqs:", len(seqs), flush=True)
    model, ck = load_encoder(RUN)
    model = model.to(dev).eval()
    r = evaluate_model(model, dev, seqs, pairs_list, 100)
    print("[cov300] 300M cov=%.5f ctrl=%.5f COV-CTRL=%+.5f" % (
        r["cov"]["mean"], r["ctrl"]["mean"], r["cov_minus_ctrl"]),
        flush=True)
    results = json.load(open(OUT))
    results["300M"] = r
    json.dump(results, open(OUT, "w"), indent=2)
    print("[cov300] merged into covariation_test.json", flush=True)


if __name__ == "__main__":
    main()
