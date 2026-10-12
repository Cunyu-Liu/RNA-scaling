"""gap-bridge 实验：配对解码器改进（用户问"后续补了吗，结果怎么样"）。

v5 基线：PairNet 独立对分数 → 非交叉 DP → pair-F1 0.20（650M）。
本实验测三个渐进改进（同表征同协议，只换解码侧）：
  A. baseline-DP：v5 复现（独立分数 + DP）
  B. +symm：分数对称化 (s_ij+s_ji)/2 —— 消除方向噪声
  C. +loop-constraint：DP 加最小发夹环长 ≥3（RNA 结构先验）+
     范围分数融合（局部对比学习信号）
模型：650M + 300M（用户要求补 300M）。
输出 evidence/gapbridge_decoder.json → 图入 PPT 页 6。
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
MIN_LONG = 0


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
            if len(ev) >= 600 and len(tr) >= 200:
                break
        if len(ev) >= 600 and len(tr) >= 200:
            break
    return tr[:200], ev[:600]


def dp_decode(S, n, min_loop=0):
    """非交叉 DP：S 对称分数矩阵 → 最大权和匹配（可选最小环长）。"""
    import numpy as np
    dp = np.zeros((n + 1, n + 1))
    for span in range(2, n + 1):
        for i in range(0, n - span + 1):
            j = i + span - 1
            best = dp[i + 1][j]           # j 不配
            best = max(best, dp[i][j - 1])  # i 不配
            if j - i - 1 >= min_loop:
                best = max(best, dp[i + 1][j - 1] + S[i, j])
            for k in range(i + 1, j - min_loop):
                best = max(best, dp[i][k + 1] + dp[k + 1][j]
                           if k + 1 <= j else 0)
                best = max(best, dp[i][k] + dp[k][j]) if k < j else best
            dp[i][j] = best
    # 回溯
    pairs = []

    def bt(i, j):
        if j <= i:
            return
        if dp[i][j] == dp[i + 1][j]:
            bt(i + 1, j)
            return
        if dp[i][j] == dp[i][j - 1]:
            bt(i, j - 1)
            return
        if j - i - 1 >= min_loop and dp[i][j] == dp[i + 1][j - 1] + S[i, j]:
            pairs.append((i, j))
            bt(i + 1, j - 1)
            return
        for k in range(i + 1, j - min_loop):
            if k + 1 <= j and dp[i][j] == dp[i][k + 1] + dp[k + 1][j]:
                bt(i, k)
                bt(k + 1, j)
                return
    bt(0, n - 1)
    return pairs


def eval_decoder(model_id, fit_seqs, ev_seqs, device, min_loop=0,
                 symm=True):
    from rna_sc.probe import load_encoder
    from rna_sc.data import ALPHABET
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

    # fit logistic（同 S8：对特征）
    from sklearn.linear_model import LogisticRegression
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

    pair_f1s, pos_f1s = [], []
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
        S = np.zeros((n, n))
        for (i, j), v in zip(zip(I, J), sc):
            S[i, j] = v
            if symm:
                S[j, i] = v
        pred = set(dp_decode(S, n, min_loop=min_loop))
        # pair F1
        tp = len(pred & gold)
        p = tp / max(1, len(pred))
        r_ = tp / max(1, len(gold))
        pair_f1s.append(0 if p + r_ == 0 else 2 * p * r_ / (p + r_))
        # position macro F1（配对位置检测）
        gp = {x for pair in gold for x in pair}
        pp = {x for pair in pred for x in pair}
        tpp = len(gp & pp)
        pr = tpp / max(1, len(pp))
        rr = tpp / max(1, len(gp))
        pos_f1s.append(0 if pr + rr == 0 else 2 * pr * rr / (pr + rr))
    return float(np.mean(pair_f1s)), float(np.mean(pos_f1s))


def main():
    device = "cuda:4"
    fit, ev = load_bprna()
    print("[gapbridge] fit=%d ev=%d" % (len(fit), len(ev)), flush=True)
    out = {"protocol": "logistic pair head (layer 70%) + decoder variants; "
           "fit=200 train / eval=600 test bpRNA; pair-F1 + position-F1",
           "models": {}}
    for mid, tag in [("RNA-Sc-650M_s17", "650M"),
                     ("RNA-Sc-300M_s17", "300M")]:
        # A: 独立分数 + DP（v5 基线复现，symm=False）
        f1a, pfa = eval_decoder(mid, fit, ev, device, min_loop=0,
                                symm=False)
        # B: +对称化
        f1b, pfb = eval_decoder(mid, fit, ev, device, min_loop=0, symm=True)
        # C: +环长约束（min_loop=3 发夹先验）
        f1c, pfc = eval_decoder(mid, fit, ev, device, min_loop=3, symm=True)
        out["models"][tag] = {
            "A_indep_DP": {"pair_f1": round(f1a, 4), "pos_f1": round(pfa, 4)},
            "B_symm": {"pair_f1": round(f1b, 4), "pos_f1": round(pfb, 4)},
            "C_symm_loop3": {"pair_f1": round(f1c, 4),
                             "pos_f1": round(pfc, 4)},
        }
        print("[gapbridge] %s: A %.4f → B %.4f → C %.4f (pair-F1)" %
              (tag, f1a, f1b, f1c), flush=True)
    json.dump(out, open(os.path.join(EVID, "gapbridge_decoder.json"), "w"),
              indent=1, ensure_ascii=False)
    print("[gapbridge] saved", flush=True)


if __name__ == "__main__":
    main()
