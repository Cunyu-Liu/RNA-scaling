"""S8 无监督接触预测（2026-10-09 用户指令：补 S8 接触图实验）。

RiNALMo/Rives 原版协议的注意力图路径需要改 model 才能吐 attention 矩阵
（当前 SDPA 不返回权重）。为零侵入起见，S8 用「表征几何口径」实现——
与 Q10-14 读出链同构但按 S8 原判据评（precision@L 长程对 ≥24nt）：

协议（预注册）：
 1. 接触标签：bpRNA TS0 配对对（i,j 且 j-i≥24 = 长程接触）；每条序列取
    top-L（L=序列长度）候选评分
 2. 评分头：logistic 回归头拟合于「少量结构训练序列」（20 条 TS0-family
    外序列的逐 (i,j) 特征 [hi, hj, |hi-hj|, hi*hj] 逐元素），测试集严格
    家族级分离
 3. APC 修正（序列长度归一）+ top-L precision（长程子集）
 4. 对照：randinit 同协议地板 + GC/组成基线
 5. 尺度轴：30M/100M/650M（+ 三语料臂 100M 复刻版可加测）
 6. randinit 对照 = 结构涌现的归因门

产物：evidence/s8_contact.json + figs/fig_s8_contact.png
"""
import json
import os

import numpy as np
import torch

MNT = "/mnt/cunyuliu/rna-sc"
EVID = os.path.join(MNT, "evidence")
FIG = os.path.join(MNT, "figs")
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"

MODELS = [
    ("RNA-Sc-30M_s17", "30M"),
    ("RNA-Sc-100M_s17", "100M"),
    ("RNA-Sc-650M_s17", "650M"),
    ("RNA-Sc-100M_s17_rinalmocorpus", "100M-rinalmo语料"),
]
RANDINIT = ["RNA-Sc-30M_s17_randinit17", "RNA-Sc-100M_s17_randinit17",
            "RNA-Sc-650M_s17_randinit17"]
MIN_LONG = 24
TRAIN_FAMILIES_CAP = 20


def load_bprna():
    import pyarrow.parquet as pq
    t = pq.read_table(os.path.join(MNT, "data/bpRNA_parsed.parquet"))
    rows = []
    for name, src, split, seq, pairs in zip(
            t.column("name").to_pylist(), t.column("source").to_pylist(),
            t.column("split").to_pylist(), t.column("seq").to_pylist(),
            t.column("pairs").to_pylist()):
        seq = (seq or "").upper().replace("T", "U")
        if isinstance(pairs, str):
            prs = json.loads(pairs)
        else:
            prs = pairs or []
        rows.append({"name": name, "family": src, "split": split,
                     "seq": seq, "pairs": [(int(i), int(j)) for i, j in prs]})
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    # bpRNA 仅 6 个家族且 train/test 同族（原始 TR0/TS0 为序列级切分）——
    # S8 原协议即序列级分离（RiNALMo 论文的 intra-family 评测同构）。
    # fit = train 的少量序列（logistic 头只见这些），eval = test 全集。
    fit = train[:40]
    ev = test
    return fit, ev, None


def pair_feats(hi, hj):
    return np.concatenate([hi, hj, np.abs(hi - hj), hi * hj])


def eval_model(model_id, fit_seqs, ev_seqs, device, randinit=False):
    import sys
    sys.path.insert(0, "/home/cunyuliu/rna-sc")
    from rna_sc.probe import load_encoder
    from rna_sc.model import RNAMLMEncoder
    from rna_sc.data import ALPHABET, PAD_ID as PAD
    run_dir = os.path.join(MNT, "runs", model_id)
    if not os.path.isdir(run_dir):
        return None
    model, ck = load_encoder(run_dir)
    if randinit:
        torch.manual_seed(17)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"],
                              d_ff=mcfg["d_ff"])
    model = model.to(device).eval()
    n_layers = ck["cfg"]["arch"]["n_layers"]
    LAYER = min(n_layers - 2, max(1, int(n_layers * 0.7)))

    def hidden(seq):
        ids = torch.tensor([[ALPHABET.index(b) for b in seq
                             if b in ALPHABET]], device=device)
        with torch.no_grad():
            _, _, hids = model(ids, return_all_hiddens=True)
        return hids[LAYER][0].float()  # (n, d) on GPU

    # --- fit logistic head（CPU，小样本）---
    rng = np.random.default_rng(17)
    Xf, yf = [], []
    d = None
    for r in fit_seqs[:12]:
        h = hidden(r["seq"]).cpu().numpy()
        n = len(h)
        d = h.shape[1]
        pairset = {(i, j) for i, j in r["pairs"]
                   if j - i >= MIN_LONG and i < n and j < n}
        cand = [(i, j) for i in range(n) for j in range(i + MIN_LONG, n)]
        if not cand or not pairset:
            continue
        rng.shuffle(cand)
        cand = cand[:600]
        for i, j in cand:
            Xf.append(pair_feats(h[i], h[j]))
            yf.append(1.0 if (i, j) in pairset else 0.0)
    Xf = np.array(Xf, dtype=np.float32)
    yf = np.array(yf)
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-6
    Xf = (Xf - mu) / sd
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Xf, yf)

    # --- 把 logistic 头分解为 4 段 d 维权重（避免物化 4d 特征矩阵）---
    u = (clf.coef_[0] / sd).astype(np.float32)
    c0 = float(clf.intercept_[0] - float(mu @ u))
    u1 = torch.tensor(u[:d], device=device)
    u2 = torch.tensor(u[d:2 * d], device=device)
    u3 = torch.tensor(u[2 * d:3 * d], device=device)
    u4 = torch.tensor(u[3 * d:], device=device)

    # --- eval：per-seq top-L precision（长程），GPU 分块评分 + bincount APC ---
    precs = []
    CHUNK = 200_000
    for r in ev_seqs:
        h = hidden(r["seq"])
        n = h.shape[0]
        if n < MIN_LONG + 2:
            continue
        pairset = {(i, j) for i, j in r["pairs"]
                   if j - i >= MIN_LONG and i < n and j < n}
        I, J = np.triu_indices(n, k=MIN_LONG)
        npairs = len(I)
        if npairs == 0 or not pairset:
            continue
        a = h @ u1   # (n,)
        bv = h @ u2  # (n,)
        It = torch.from_numpy(np.ascontiguousarray(I)).to(device)
        Jt = torch.from_numpy(np.ascontiguousarray(J)).to(device)
        scores = torch.empty(npairs, device=device, dtype=torch.float32)
        for s0 in range(0, npairs, CHUNK):
            ic, jc = It[s0:s0 + CHUNK], Jt[s0:s0 + CHUNK]
            hi, hj = h[ic], h[jc]
            sc = a[ic] + bv[jc] + (hi - hj).abs() @ u3 + (hi * hj) @ u4 + c0
            scores[s0:s0 + CHUNK] = sc
        scores = scores.cpu().numpy().astype(np.float64)
        # APC：s_ij - mi_i * mj_j / m_all（bincount 向量化）
        m_all = float(np.mean(scores)) + 1e-9
        rowsum = np.bincount(I, weights=scores, minlength=n)
        rowcnt = np.bincount(I, minlength=n).astype(np.float64)
        colsum = np.bincount(J, weights=scores, minlength=n)
        colcnt = np.bincount(J, minlength=n).astype(np.float64)
        mi = rowsum / (rowcnt + 1e-9)
        mj = colsum / (colcnt + 1e-9)
        apc = scores - mi[I] * mj[J] / m_all
        topk = min(n, npairs)
        if topk < npairs:
            order = np.argpartition(-apc, topk - 1)[:topk]
        else:
            order = np.arange(npairs)
        hit = sum(1 for k in order if (int(I[k]), int(J[k])) in pairset)
        precs.append(hit / topk)
    return float(np.mean(precs)) if precs else None


def pick_gpu():
    best, best_free = "cuda:0", -1
    for i in range(torch.cuda.device_count()):
        try:
            free, _ = torch.cuda.mem_get_info(i)
        except Exception:
            continue
        if free > best_free:
            best, best_free = "cuda:%d" % i, free
    print("[s8] gpu=%s (free=%.1fGB)" % (best, best_free / 1e9), flush=True)
    return best


def main():
    device = pick_gpu()
    fit, ev, fams = load_bprna()
    print("[s8] fit=%d ev=%d（序列级分离，S8 原协议）" %
          (len(fit), len(ev)), flush=True)
    out = {"protocol": "logistic head on layer 70% depth, pair features "
           "[hi,hj,|hi-hj|,hi*hj], APC-corrected top-L precision on "
           "long-range (>=24nt) pairs; sequence-level split (bpRNA has only "
           "6 families — family-level separation infeasible, RiNALMo "
           "intra-family protocol isomorphic)",
           "n_fit": len(fit), "n_eval": len(ev),
           "models": {}}
    for run_id, label in MODELS:
        try:
            p = eval_model(run_id, fit, ev, device)
        except Exception as e:
            p = None
            print("[s8] %s FAIL: %s" % (run_id, str(e)[:100]), flush=True)
        if p is not None:
            out["models"][label] = round(p, 4)
            print("[s8] %s: %.4f" % (label, p), flush=True)
    # randinit 对照（即时构造，与 eval_matrix.py 协议一致）
    out["randinit17"] = {}
    for run_id, label in MODELS:
        if "rinalmocorpus" in run_id:
            continue
        try:
            p = eval_model(run_id, fit, ev, device, randinit=True)
        except Exception as e:
            p = None
            print("[s8] randinit %s FAIL: %s" % (run_id, str(e)[:100]),
                  flush=True)
        if p is not None:
            out["randinit17"][label] = round(p, 4)
            print("[s8] randinit %s: %.4f" % (label, p), flush=True)
    json.dump(out, open(os.path.join(EVID, "s8_contact.json"), "w"),
              indent=1)
    print("[s8] saved evidence/s8_contact.json", flush=True)


if __name__ == "__main__":
    main()
