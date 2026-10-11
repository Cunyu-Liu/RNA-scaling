"""300M/650M 涌现时间线补充：逐 ckpt probe。

对 300M/650M 主臂跑 --ckpt-nt 时间线（与 1M-100M 的 _ck 行同管线，
20k/4k family split，全层扫描——probe 不支持层窗口）。
300M: 6 ckpt；650M: 3 ckpt（1.2/1.6/1.9B，控算力）。
GPU 用空闲卡（6 已被 s8 占）。
"""
import os
import subprocess

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"

PLAN = {
    "RNA-Sc-300M_s17": [400021893, 800041855, 1200074751,
                        1600097397, 1800104724, 1900122218],
    "RNA-Sc-650M_s17": [1200074751, 1600097397, 1900122218],
}

for run_id, cks in PLAN.items():
    run_dir = os.path.join("/mnt/cunyuliu/rna-sc/runs", run_id)
    for ck_nt in cks:
        out = subprocess.run(
            [PY, "-m", "rna_sc.probe", "--run-dir", run_dir,
             "--ckpt-nt", str(ck_nt), "--device", "7"],
            cwd=ROOT, capture_output=True, text=True, timeout=14400)
        print("[s6-ext] %s ck=%d rc=%s" % (run_id, ck_nt, out.returncode),
              flush=True)
        if out.returncode != 0:
            print(out.stderr[-300:], flush=True)
print("[s6-ext] done", flush=True)
