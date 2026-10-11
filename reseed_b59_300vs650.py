"""650M@5.9B vs 300M@5.9B 复测 v4：INNER 独立文件版。

修改：子任务改为运行磁盘上的 reseed_inner.py（避免 -c 字符串行号/
转义歧义）；层窗口修正为模型实际层内（300M 24 层 → L19-23，
650M 28 层 → L23-27）。
"""
import json
import os
import subprocess

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
EVID = "/mnt/cunyuliu/rna-sc/evidence"

OUT = {}
for seed in [29, 43, 61]:
    for run_id, layers in [("RNA-Sc-300M_s17_b59", range(19, 24)),
                           ("RNA-Sc-650M_s17_b59", range(23, 28))]:
        for L in layers:
            cmd = [PY, "/home/cunyuliu/rna-sc/reseed_inner.py",
                   run_id, str(L), str(seed)]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True,
                                     timeout=3600, cwd=ROOT)
                line = [l for l in res.stdout.split("\n")
                        if l.strip().startswith("{")]
                if line:
                    r = json.loads(line[-1])
                    if "error" in r:
                        print("[reseed] OOB %s L%s" % (run_id, L),
                              flush=True)
                        continue
                    OUT.setdefault(run_id, {}).setdefault(
                        str(seed), {})[str(L)] = r["f1_macro"]
                    print("[reseed] %s seed=%s L%s F1=%.4f" %
                          (run_id, seed, L, r["f1_macro"]), flush=True)
                else:
                    print("[reseed] FAIL %s s%s L%s: %s" %
                          (run_id, seed, L, res.stderr[-300:]), flush=True)
            except subprocess.TimeoutExpired:
                print("[reseed] TIMEOUT %s s%s L%s" % (run_id, seed, L),
                      flush=True)

json.dump(OUT, open(os.path.join(EVID, "b59_reseed_300vs650.json"), "w"),
          indent=1)
print("[reseed] saved", flush=True)
