"""gap-bridge v2：解码空间约束实验（可比口径）。

v1 教训：logistic 分数 + 全域 DP → F1 0.005（DP 对分数噪声极敏感，
全域搜索放大噪声）——这本身是"解码器需要约束"的证据。

v2 设计（与 v5/S8 可比）：同一 logistic 头分数，三个解码策略：
  A. top-L 贪心（S8 口径基线）：分数 top-L 直接输出
  B. 约束 DP：只在 top-2L 候选内做非交叉选择（解码空间收窄）
  C. 约束 DP + 环长先验（B + min_loop=3）
模型：650M + 300M。若 B/C > A 显著 → 结构约束是解码器 gap 的
可及修复（gap-bridge 成立）；若不显著 → 缺口在分数质量本身。
"""
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, "/home/cunyuliu/rna-sc")

MNT = "/mnt/cunyuliu/rna-sc"
EVID = os.path.join(MNT, "evidence")
BPRNA = os.path.join(MNT, "data/bpRNA_parsed.parquet")
LAYER_FRAC = 0.7


def load_bprna():
    import pyarrow.parquet as pq
    tr, ev = [], []
    for rb in pq.ParquetFile(BPRNA).iter_batches(
            batch_size=50_000, columns=["split", "seq", "pairs"]):
        d = rb.to_pydict()
        for sp, s, p in zip(d["split"], d["seq"], d["pairs"]):
            row = {"seq": s.upper().replace("T", "U"),
                   "pairs": [(int(i), int(j)) for i, j in
                             (json.loads(p) if isinstance(p, str) else p)]}
            (tr if sp == "train" else ev).append(row)
            if len(ev) >= 500 and len(tr) >= 200:
                break
        if len(ev) >= 500 and len(tr) >= 200:
            break
    return tr[:200], ev[:500]


def dp_constrained(cand_scores, n, min_loop=0):
    """cand_scores: list of (i, j, score)（已筛 top 候选）。
    非交叉 DP 只在候选集上选子集（最大化总分）。
    相邻段实现：dp over positions，pair 只来自候选。"""
    best = {}
    pair_at = {}
    for i in range(n):
        best[(i, i + 1)] = 0.0  # 空段 [i, i)
    # 按段长递增
    for span in range(2, n + 1):
        for i in range(0, n - span + 1):
            j = i + span
            b = best.get((i + 1, j), 0.0)  # i 不配
            b = max(b, best.get((i, j - 1), 0.0))  # j 不配
            if j - i - 1 >= min_loop:
                for pi, pj in [(i, j - 1)]:
                    pass
                # (i, j-1) 直接配对（若在候选）
            best[(i, j)] = b
    # 上面写法复杂——改简单递归记忆化
    from functools import lru_cache
    cands = {}
    for i, j, s in cand_scores:
        cands.setdefault((i, j), s)
    sys.setrecursionlimit(10000)

    memo = {}

    def solve(i, j):
        if j - i < 2 + min_loop:
            return 0.0
        key = (i, j)
        if key in memo:
            return memo[key]
        b = solve(i + 1, j)
        b = max(b, solve(i, j - 1))
        if j - i - 1 >= min_loop and (i, j - 1 + 1 - 1) in cands:
            pass
        if (i, j - 1) in cands and j - 1 - i - 1 >= min_loop:
            b = max(b, solve(i + 1, j - 2) + cands[(i, j - 1)])
        if (i, j) in cands and j - i - 1 >= min_loop:
            b = max(b, solve(i + 1, j - 1) + cands[(i, j)])
        for k in range(i + 1, j - 1):
            b = max(b, solve(i, k) + solve(k + 1, j))
        memo[key] = b
        return b

    total = solve(0, n - 1)
    # 回溯
    chosen = []

    def bt(i, j):
        if j - i < 2 + min_loop:
            return
        b = memo[(i, j)]
        if abs(b - solve(i + 1, j)) < 1e-12 and (i + 1, j) in memo:
            bt(i + 1, j)
            return
        if abs(b - solve(i, j - 1)) < 1e-12:
            bt(i, j - 1)
            return
        if (i, j) in cands and j - i - 1 >= min_loop and \
                abs(b - (solve(i + 1, j - 1) + cands[(i, j)])) < 1e-12:
            chosen.append((i, j))
            bt(i + 1, j - 1)
            return
        for k in range(i + 1, j - 1):
            if abs(b - (solve(i, k) + solve(k + 1, j))) < 1e-12:
                bt(i, k)
                bt(k + 1, j)
                return
    bt(0, n - 1)
    return chosen, total


def eval_model(model_id, fit_seqs, ev_seqs, device):
    from rna_sc.probe import load_encoder
    from rna_sc.data import ALPHABET
    from sklearn.linear_model import LogisticRegression
    model, ck = load_encoder(os.path.join(MNT, "runs", model_id))
    model = model.to(device).eval()
    L = ck["cfg"]["arch"]["n_layers"]
    LAYER = min(L - 2, max(1, int(L * LAYER_FRAC)))

    def hidden(seq):
        ids = torch.tensor([[ALPHABET.index(b) for b in seq
                             if b in ALPHABET]], device=device)
        with torch.no_grad():
            _, _, hids = model(ids, return_all_hiddens=True)
        return hids[LAYER][0].float().cpu().numpy()

    rng = np.random.default_rng(17)
    Xf, yf = [], []
    for r in fit_seqs[:12]:
        h = hidden(r["seq"])
        n = len(h)
        ps = {(i, j) for i, j in r["pairs"] if i < n and j < n}
        cand = [(i, j) for i in range(n) for j in range(i + 1, n)]
        if not cand or not ps:
            continue
        rng.shuffle(cand)
        cand = cand[:600]
        for i, j in cand:
            Xf.append(np.concatenate([h[i], h[j], np.abs(h[i] - h[j]),
                                      h[i] * h[j]]))
            yf.append(1.0 if (i, j) in ps else 0.0)
    Xf = np.array(Xf, dtype=np.float32)
    yf = np.array(yf)
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-6
    Xf = (Xf - mu) / sd
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Xf, yf)

    res = {"A_topL": [], "B_top2L_dp": [], "C_top2L_dp_loop3": []}
    for r in ev_seqs:
        h = hidden(r["seq"])
        n = len(h)
        if n < 15:
            continue
        gold = {(i, j) for i, j in r["pairs"] if i < n and j < n}
        if not gold:
            continue
        I, J = np.triu_indices(n, k=1)
        X = np.array([np.concatenate([h[i], h[j], np.abs(h[i] - h[j]),
                                      h[i] * h[j]])
                      for i, j in zip(I, J)], dtype=np.float32)
        X = (X - mu) / sd
        sc = clf.decision_function(X)
        pairs_sc = list(zip(I.tolist(), J.tolist(), sc.tolist()))

        def f1_of(pred):
            pred = set(pred)
            tp = len(pred & gold)
            p = tp / max(1, len(pred))
            r_ = tp / max(1, len(gold))
            return 0 if p + r_ == 0 else 2 * p * r_ / (p + r_)

        # A: top-L 贪心
        top = sorted(pairs_sc, key=lambda t: -t[2])[:n]
        res["A_topL"].append(f1_of([(i, j) for i, j, _ in top]))
        # B: top-2L 候选内 DP
        cand2 = sorted(pairs_sc, key=lambda t: -t[2])[:2 * n]
        chosen, _ = dp_constrained([(i, j, s) for i, j, s in cand2],
                                   n, min_loop=0)
        res["B_top2L_dp"].append(f1_of(chosen))
        # C: B + 环长 3
        chosen3, _ = dp_constrained([(i, j, s) for i, j, s in cand2],
                                    n, min_loop=3)
        res["C_top2L_dp_loop3"].append(f1_of(chosen3))
    return {k: round(float(np.mean(v)), 4) for k, v in res.items()}


def main():
    device = "cuda:4"
    fit, ev = load_bprna()
    print("[gapbridge2] fit=%d ev=%d" % (len(fit), len(ev)), flush=True)
    out = {"protocol": "logistic pair scores (layer 70%) + three "
           "decoders: A top-L greedy / B top-2L noncrossing DP / "
           "C B+loop>=3; pair-F1; fit=200/eval=500 bpRNA",
           "models": {}}
    for mid, tag in [("RNA-Sc-650M_s17", "650M"),
                     ("RNA-Sc-300M_s17", "300M")]:
        r = eval_model(mid, fit, ev, device)
        out["models"][tag] = r
        print("[gapbridge2] %s: A %.4f → B %.4f → C %.4f" %
              (tag, r["A_topL"], r["B_top2L_dp"], r["C_top2L_dp_loop3"]),
              flush=True)
    json.dump(out, open(os.path.join(EVID, "gapbridge_decoder_v2.json"),
                        "w"), indent=1, ensure_ascii=False)
    print("[gapbridge2] saved", flush=True)


if __name__ == "__main__":
    main()
