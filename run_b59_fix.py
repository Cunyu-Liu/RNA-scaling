"""b59 补测 3.0B/5.0B 中点（修正 ckpt nt 数值）。"""
import os
import subprocess
import time

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
LOG = "/home/cunyuliu/rna-sc/logs/b59_midpoints_eval.log"

# 3.0B ≈ ckpt_nt3000177442; 5.0B ≈ ckpt_nt5000262199
PLAN = {
    "RNA-Sc-30M_s17_b59": [3000177442, 5000262199],
    "RNA-Sc-100M_s17_b59": [3000177442, 5000262199],
    "RNA-Sc-300M_s17_b59": [3000177442, 5000262199],
    "RNA-Sc-650M_s17_b59": [3000177442, 5000262199],
}

t0 = time.time()
with open(LOG, "a") as lf:
    lf.write("\n[%s] b59 fix batch (3.0/5.0B) start\n" % time.ctime())
    for run_id, cks in PLAN.items():
        run_dir = os.path.join("/mnt/cunyuliu/rna-sc/runs", run_id)
        for ck_nt in cks:
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
            except subprocess.TimeoutExpired:
                lf.write("TIMEOUT %s %d\n" % (run_id, ck_nt))
            lf.flush()
    lf.write("[%s] fix batch done, %.1f min\n" % (time.ctime(),
                                                  (time.time() - t0) / 60))
print("fix batch done")
