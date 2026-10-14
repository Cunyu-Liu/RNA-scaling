"""b59 (5.9B) 中间 ckpt probe 批次：补时间轴过程点。

每尺度 7 个中间点（0.4/0.8/1.2/1.6/2.0/3.0/5.0B），加已有 5.8B 终点
= 8 点/尺度。全层扫描、family split、probe-balanced、20k/4k——
与 s6_cross_scale 同管线。GPU 用 2（19GB 占用，40GB 卡有空余）。
"""
import os
import subprocess
import sys
import time

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
LOG = "/home/cunyuliu/rna-sc/logs/b59_midpoints_eval.log"

PLAN = {
    "RNA-Sc-30M_s17_b59": [400021893, 800041855, 1200074751,
                           1600097397, 2000136751, 300014117, 500024610],
    "RNA-Sc-100M_s17_b59": [400021893, 800041855, 1200074751,
                            1600097397, 2000136751, 300014117, 500024610],
    "RNA-Sc-300M_s17_b59": [400021893, 800041855, 1200074751,
                            1600097397, 2000136751, 300014117, 500024610],
    "RNA-Sc-650M_s17_b59": [400021893, 800041855, 1200074751,
                            1600097397, 2000136751, 300014117, 500024610],
}

t0 = time.time()
n_done = 0
with open(LOG, "a") as lf:
    lf.write("\n[%s] b59 midpoints batch start\n" % time.ctime())
    for run_id, cks in PLAN.items():
        run_dir = os.path.join("/mnt/cunyuliu/rna-sc/runs", run_id)
        for ck_nt in cks:
            # 已探过则跳过（idempotent）
            already = False
            for line in open("/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"):
                if '"%s_ck%d"' % (run_id, ck_nt) in line.replace(" ", "")[:120]:
                    pass
            lf.write("[%s] %s ck=%d start\n" % (time.ctime(), run_id, ck_nt))
            lf.flush()
            try:
                out = subprocess.run(
                    [PY, "-m", "rna_sc.probe", "--run-dir", run_dir,
                     "--ckpt-nt", str(ck_nt), "--device", "2"],
                    cwd=ROOT, capture_output=True, text=True, timeout=14400)
                lf.write("[%s] %s ck=%d rc=%s\n" % (
                    time.ctime(), run_id, ck_nt, out.returncode))
                if out.returncode != 0:
                    lf.write(out.stderr[-300:] + "\n")
                else:
                    n_done += 1
            except subprocess.TimeoutExpired:
                lf.write("[%s] %s ck=%d TIMEOUT\n" % (time.ctime(), run_id, ck_nt))
            lf.flush()
    lf.write("[%s] batch done: %d ok, %.1f min\n" % (time.ctime(), n_done,
                                                     (time.time() - t0) / 60))
print("done", n_done)
