"""300M/650M 涌现时间线补充：逐 ckpt probe（v2：650M 换 GPU7→3）。

s6 v1 的 650M 在 GPU7 OOM。改 GPU3（32GB 空闲较大）。
300M 6 ckpt 已全部完成（rc=0），本版只跑 650M 3 ckpt。
"""
import os
import subprocess

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"

PLAN = {
    "RNA-Sc-650M_s17": [1200074751, 1600097397, 1900122218],
}

for run_id, cks in PLAN.items():
    run_dir = os.path.join("/mnt/cunyuliu/rna-sc/runs", run_id)
    for ck_nt in cks:
        out = subprocess.run(
            [PY, "-m", "rna_sc.probe", "--run-dir", run_dir,
             "--ckpt-nt", str(ck_nt), "--device", "3"],
            cwd=ROOT, capture_output=True, text=True, timeout=14400)
        print("[s6-ext] %s ck=%d rc=%s" % (run_id, ck_nt, out.returncode),
              flush=True)
        if out.returncode != 0:
            print(out.stderr[-300:], flush=True)
print("[s6-ext] done", flush=True)
