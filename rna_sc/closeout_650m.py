"""650M closeout chain + evidence v2 expansion (Day 12, 2026-09-22).

Chain A (runs automatically after 650M DONE):
  1. wait for watch_all to finish the final probe (all layers, final ckpt)
  2. s1_final_verdict (five-scale table incl. 650M + pre-registered checks)
  3. s13b_bell v2 with 650M appended (max-confidence coverage point)
  4. TRAINING_LOG entry

Chain B (650M-side evidence, run on a free GPU while chain A probes):
  - s14_rns_650m: single-run RNS point for RNA-Sc-650M_s17 (no JSONL
    overwrite; merges into a v2 side file)

Usage:
  python -m rna_sc.closeout_650m --device 7            # full chain
  python -m rna_sc.closeout_650m --device 7 --only-rns # just chain B
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
MNT = "/mnt/cunyuliu/rna-sc"
RUN = "RNA-Sc-650M_s17"
TLOG = os.path.join(ROOT, "TRAINING_LOG.md")
VERDICT = os.path.join(MNT, "evidence", "s1_final_verdict.json")


def sh(args, log_name):
    log = os.path.join(MNT, "logs", log_name)
    print("[closeout] %s -> %s" % (" ".join(args), log), flush=True)
    with open(log, "a") as lf:
        subprocess.run(args, cwd=ROOT, stdout=lf, stderr=lf, timeout=21600)


def probe_done() -> bool:
    """650M final-ckpt probe complete: full contiguous layer coverage
    at the run's true final ckpt nt (mirror of watch_all.probed_runs)."""
    p = os.path.join(MNT, "eval", "probe_results.jsonl")
    if not os.path.exists(p):
        return False
    rows = []
    with open(p) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("run") == RUN and r.get("n_train", 0) >= 4000 \
                    and r.get("ckpt_nt") is not None:
                rows.append(r)
    if not rows:
        return False
    final_nt = max(r["ckpt_nt"] for r in rows)
    try:
        with open(os.path.join(MNT, "runs", RUN, "manifest.json")) as mh:
            mnt = json.load(mh).get("final_nt") or 0
    except (OSError, json.JSONDecodeError):
        mnt = 0
    if mnt and final_nt < mnt - 100_000_000:
        return False
    layers = {r["layer"] for r in rows if r["ckpt_nt"] == final_nt}
    return bool(layers) and layers == set(range(max(layers) + 1))


def verdict_has_650m() -> bool:
    try:
        with open(VERDICT) as fh:
            return "650M" in json.load(fh).get("five_scale_table", {})
    except (OSError, json.JSONDecodeError):
        return False


def wait_probe(timeout_s=6 * 3600) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if probe_done():
            return True
        time.sleep(300)
    return probe_done()


def chain_a(device: int):
    print("[closeout] chain A: waiting for 650M final probe", flush=True)
    ok = wait_probe()
    print("[closeout] 650M final probe complete=%s" % ok, flush=True)
    if not ok:
        with open(TLOG, "a") as fh:
            fh.write("\n- [closeout][WARN] 650M probe not complete after "
                     "6h wait; verdict deferred\n")
        return
    sh([PY, "-m", "rna_sc.s1_final_verdict"], "closeout_verdict.log")
    if not verdict_has_650m():
        print("[closeout][WARN] verdict still missing 650M", flush=True)
        return
    with open(VERDICT) as fh:
        v = json.load(fh)
    with open(TLOG, "a") as fh:
        fh.write("\n- [closeout] 650M five-scale verdict done: %s\n"
                 % json.dumps(v.get("checks", {})))
    sh([PY, "-m", "rna_sc.s13b_bell", "--device", str(device)],
       "s13b_bell_v2_650m.log")
    with open(TLOG, "a") as fh:
        fh.write("- [closeout] s13b_bell v2 (with 650M coverage point) "
                 "done; evidence/s13b_bell.json refreshed\n")
    sh([PY, "-m", "rna_sc.fill_draft_650m"], "fill_draft_650m.log")
    with open(TLOG, "a") as fh:
        fh.write("- [closeout] DRAFT v1.1 auto-fill attempted "
                 "(fill_draft_650m)\n")


def chain_b(device: int):
    sh([PY, "-m", "rna_sc.s14_rns_650m", "--device", str(device)],
       "s14_rns_650m.log")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=7)
    ap.add_argument("--only-rns", action="store_true")
    args = ap.parse_args()
    if args.only_rns:
        chain_b(args.device)
        return 0
    chain_b(args.device)
    chain_a(args.device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
