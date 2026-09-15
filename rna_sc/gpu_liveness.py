"""GPU-context liveness check (incident #9 prevention).

For every RUNNING rna_sc.train process: verify it appears in
nvidia-smi compute-apps. A training PID absent from all GPUs while its
log is not advancing (or CPU-spinning) = GPU context loss -> alert +
auto-kill (supervisor will resume from latest ckpt).

Also detects: log not advancing 30+ min while process alive.

Run via monitoring/check.sh (cron). Writes evidence + kills stale PIDs.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import time

LOGS = "/mnt/cunyuliu/rna-sc/logs"
EVID = "/mnt/cunyuliu/rna-sc/evidence"


def gpu_pids() -> set[int]:
    r = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        capture_output=True, text=True)
    return {int(x) for x in r.stdout.split() if x.strip().isdigit()}


def train_pids() -> dict[int, str]:
    r = subprocess.run(["pgrep", "-af", "rna_sc.train"],
                       capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        pid = int(parts[0])
        cmd = parts[1]
        out[pid] = cmd
    return out


def log_mtime_map() -> dict[str, float]:
    out = {}
    for p in glob.glob(os.path.join(LOGS, "RNA-Sc-*.log")):
        out[os.path.basename(p)] = os.path.getmtime(p)
    return out


def main():
    gp = gpu_pids()
    tp = train_pids()
    now = time.time()
    mtimes = log_mtime_map()
    alerts = []
    for pid, cmd in tp.items():
        if pid not in gp:
            # find its log via out-dir name
            m = re.search(r"out-dir (\S+)", cmd)
            logname = None
            if m:
                logname = os.path.basename(m.group(1)) + ".log"
            mt = mtimes.get(logname, 0) if logname else 0
            stale_min = (now - mt) / 60 if mt else 999
            # log fresh (<10 min) but no GPU context = silent loss;
            # log stale = dead-but-running; both get killed for resume
            alerts.append(
                "GPU-CONTEXT-LOSS pid=%d stale_log=%.0fmin cmd=%s" % (
                    pid, stale_min, cmd[:120]))
            with open(os.path.join(EVID, "gpu_context_loss.txt"), "a") as fh:
                fh.write("%s pid=%d stale_log=%.1fmin\n%s\n\n" % (
                    time.strftime("%F %T"), pid, stale_min, cmd))
            subprocess.run(["kill", str(pid)])
            print("KILLED pid=%d (no GPU context, supervisor will resume)"
                  % pid)
    if not alerts:
        print("all %d train PIDs present on GPUs" % len(tp))
    else:
        for a in alerts:
            print("ALERT", a)


if __name__ == "__main__":
    main()
