"""T4.3.5b b59 臂 random-split Δ 补测（泄漏通道判据，2026-10-08）：

预注册问题：5.9B（全语料 ~3 epoch）预算下，random-split 分数是否随预算
上涨（记忆更多 → 随机切分兑现更多），而 family-split 在 100M 已知下降
（−2.74pp）？两通道若再次背离 → "random 高分 = 记忆兑现"论证链加强。

范围（分层纪律，只做判据需要的）：30M/100M/300M 三个 b59 臂 ×
probe-balanced × random split（family 列已有：0.1942/0.2989/0.3821）。
650M_b59 DONE 后自动补第四格（幂等）。

用法：python -u run_b59_random.py  # 自动选空闲卡，逐臂串行
"""
import json
import os
import subprocess
import time

ROOT = "/home/cunyuliu/rna-sc"
PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
MNT = "/mnt/cunyuliu/rna-sc"
LOG = os.path.join(MNT, "logs", "b59_random_eval.log")

ARMS = ["RNA-Sc-30M_s17_b59", "RNA-Sc-100M_s17_b59",
        "RNA-Sc-300M_s17_b59", "RNA-Sc-650M_s17_b59"]


def arm_probed(arm):
    """主 family probe 已完成 = 该臂可测（权重就绪）。"""
    rd = os.path.join(MNT, "runs", arm, "manifest.json")
    if not os.path.exists(rd):
        return False
    try:
        return json.load(open(rd)).get("status") == "DONE"
    except Exception:
        return False


def pick_gpu():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,memory.free,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True).stdout.strip().splitlines()
    best, best_free = None, 0.0
    for row in out:
        idx, free, util = row.split(",")
        free_gb = float(free) / 1024.0
        try:
            u = float(util.replace("%", "").strip())
        except ValueError:
            u = 0.0
        if u < 60 and free_gb > 6.0 and free_gb > best_free:
            best, best_free = int(idx), free_gb
    return best


def done_models():
    """已写入 eval_matrix_results.jsonl 的 b59×random 行。"""
    out = set()
    res = os.path.join(MNT, "eval", "eval_matrix_results.jsonl")
    if os.path.exists(res):
        for line in open(res):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("split") == "random" and "b59" in str(r.get("model")):
                out.add(r["model"])
    return out


def main():
    print("[b59-random] start", flush=True)
    while True:
        pending = [a for a in ARMS if a not in done_models()]
        if not pending:
            print("[b59-random] all arms done", flush=True)
            return
        runnable = [a for a in pending if arm_probed(a)]
        if not runnable:
            print("[b59-random] waiting for arms DONE (pending: %s)" %
                  pending, flush=True)
            time.sleep(1800)
            continue
        gpu = pick_gpu()
        if gpu is None:
            print("[b59-random] no idle GPU, wait", flush=True)
            time.sleep(600)
            continue
        arm = runnable[0]
        print("[b59-random] running %s on GPU%d" % (arm, gpu), flush=True)
        subprocess.run(
            [PY, "-m", "rna_sc.eval_matrix", "--model", arm,
             "--device", str(gpu), "--n-train", "19200",
             "--n-eval", "4800"],
            cwd=ROOT, stdout=open(LOG, "a"), stderr=subprocess.STDOUT,
            timeout=14400)
        print("[b59-random] %s finished" % arm, flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()
