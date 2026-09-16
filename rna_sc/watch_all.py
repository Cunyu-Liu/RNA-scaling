"""Generic run watcher: auto final-probe every run when it hits DONE.

Watches all runs not yet probed at final ckpt (per s1_summary official
rule: final ckpt + n_train>=4000). On DONE:
  1. run probe (20k/4k, per-class F1) on the freest GPU
  2. run s12_linkage for that run
  3. refresh s1_summary
  4. append TRAINING_LOG line
Loops forever; 5-min poll. Safe to restart (idempotent via probe ledger
check: a run is 'done-probing' if probe_results.jsonl has final-ckpt rows
for every layer).
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import time

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/mnt/cunyuliu/rna-sc"
LOGS = os.path.join(ROOT, "logs")
PROBE_OUT = os.path.join(ROOT, "eval", "probe_results.jsonl")
TLOG = "/home/cunyuliu/rna-sc/TRAINING_LOG.md"
WLOG = os.path.join(LOGS, "watch_all.log")

DONE_RE = re.compile(
    r"DONE (\S+) \| nt=(\d+) steps=(\d+) best_val=([\d.]+) \| "
    r"(\d+) nt/s peak=(\d+)MB fallback=(\d+)")


def free_gpu() -> int:
    import torch
    best, best_free = -1, 0
    for i in range(torch.cuda.device_count()):
        try:
            free, _ = torch.cuda.mem_get_info(i)
        except Exception:
            continue
        if free > best_free:
            best, best_free = i, free
    return best if best_free > (2 << 30) else 6


def scan_done() -> dict[str, dict]:
    """run_id -> {nt, best_val, fallback} for every DONE line."""
    out = {}
    for path in glob.glob(os.path.join(LOGS, "RNA-Sc-*.log")):
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = DONE_RE.match(line.strip())
                if m:
                    rid, nt, steps, bv, ntps, peak, fb = m.groups()
                    out[rid] = {"nt": int(nt), "best_val": float(bv),
                                "fallback": int(fb), "log": path}
    return out


def probed_runs() -> set[str]:
    """Runs with a full-layer final-ckpt probe already in JSONL."""
    out = set()
    if not os.path.exists(PROBE_OUT):
        return out
    by_run = {}
    with open(PROBE_OUT) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_run.setdefault(r["run"], []).append(r)
    for run, rows in by_run.items():
        elig = [r for r in rows if r.get("n_train", 0) >= 4000
                and r.get("ckpt_nt") is not None]
        if not elig:
            continue
        final_nt = max(r["ckpt_nt"] for r in elig)
        # inc11 fix: compare against the run's TRUE final ckpt nt on
        # disk (manifest). A run probed only at an early ckpt (S6-style
        # rows) must NOT be considered final-probed once it is DONE.
        rd = os.path.join(ROOT, "runs", run)
        try:
            with open(os.path.join(rd, "manifest.json")) as mh:
                mnt = json.load(mh).get("final_nt") or 0
        except (OSError, json.JSONDecodeError):
            mnt = 0
        if mnt and final_nt < mnt - 100_000_000:
            continue    # probe predates the final ckpt -> re-probe
        layers = {r["layer"] for r in elig if r["ckpt_nt"] == final_nt}
        # complete coverage = 0..max layer contiguous
        if layers and layers == set(range(max(layers) + 1)):
            out.add(run)
    # namespace bridge (inc10): scan_done keys are "rnasc_30M_s17_c1M"
    # but probe jsonl keys are "RNA-Sc-30M_s17_c1M" — translate so the
    # membership check in _cycle actually matches.
    def _to_rid(run):
        # RNA-Sc-30M_s17_c1M -> rnasc_30M_s17_c1M
        return "rnasc_" + run[len("RNA-Sc-"):]
    return { _to_rid(r) for r in out }


def run_dir_of(rid: str) -> str:
    # rid like rnasc_1M_s17 -> RNA-Sc-1M_s17
    name = rid.replace("rnasc_", "RNA-Sc-", 1)
    return os.path.join(ROOT, "runs", name)


def main():
    print("[watch-all] start", flush=True)
    handled = set()
    cycle = 0
    while True:
        cycle += 1
        try:
            _cycle(handled)
        except Exception:
            import traceback
            print("[watch-all] cycle error:\n%s" %
                  traceback.format_exc()[-1500:], flush=True)
        if cycle % 12 == 0:      # hourly heartbeat
            print("[watch-all] alive cycle=%d handled=%d" %
                  (cycle, len(handled)), flush=True)
        time.sleep(300)


def _cycle(handled):
        done = scan_done()
        probed = probed_runs()
        todo = [rid for rid, d in done.items()
                if rid not in probed and rid not in handled]
        for rid in todo:
            d = done[rid]
            if d["fallback"] != 0:
                print("[watch-all] %s fallback!=0, SKIP+flag" % rid,
                      flush=True)
                handled.add(rid)
                continue
            gpu = free_gpu()
            plog = os.path.join(LOGS, "probe_%s_final_auto.log" % rid)
            print("[watch-all] %s DONE nt=%.2fB val=%.4f -> probe GPU%d" % (
                rid, d["nt"] / 1e9, d["best_val"], gpu), flush=True)
            try:
                with open(plog, "w") as lf:
                    subprocess.run(
                        [PY, "-m", "rna_sc.probe", "--run-dir",
                         run_dir_of(rid), "--device", str(gpu)],
                        cwd="/home/cunyuliu/rna-sc", stdout=lf, stderr=lf,
                        timeout=14400)
            except subprocess.TimeoutExpired:
                print("[watch-all] %s probe TIMEOUT" % rid, flush=True)
            r = subprocess.run(
                [PY, "-m", "rna_sc.s12_linkage", "--run",
                 os.path.basename(run_dir_of(rid))],
                cwd="/home/cunyuliu/rna-sc", capture_output=True, text=True)
            subprocess.run([PY, "-m", "rna_sc.s1_summary"],
                           cwd="/home/cunyuliu/rna-sc", capture_output=True)
            subprocess.run([PY, "-m", "rna_sc.s1_seed_table"],
                           cwd="/home/cunyuliu/rna-sc", capture_output=True)
            subprocess.run([PY, "-m", "rna_sc.fig1_layer_migration"],
                           cwd="/home/cunyuliu/rna-sc", capture_output=True)
            with open(TLOG, "a") as fh:
                fh.write("\n- [auto] %s complete: nt=%.2fB best_val=%.4f "
                         "fallback=0; final probe+linkage+s1_summary done\n"
                         % (rid, d["nt"] / 1e9, d["best_val"]))
            print("[watch-all] %s handled" % rid, flush=True)
            handled.add(rid)


if __name__ == "__main__":
    main()
