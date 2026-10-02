"""b59 5.9B factorial closeout chain v2 (2026-10-02, fixes arm_done)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

PY = "/home/cunyuliu/miniconda3/envs/toktokenbench/bin/python"
ROOT = "/home/cunyuliu/rna-sc"
MNT = "/mnt/cunyuliu/rna-sc"
TLOG = os.path.join(ROOT, "TRAINING_LOG.md")

ARMS = ["RNA-Sc-30M_s17_b59", "RNA-Sc-100M_s17_b59",
        "RNA-Sc-300M_s17_b59", "RNA-Sc-650M_s17_b59"]
# rw1 follow-on arm (H5 replication at 10M; probe when done too)
EXTRA = ["RNA-Sc-10M_s17_rw1"]
DONE_MARK = os.path.join(MNT, "logs", "closeout_b59_done.json")
LOG = os.path.join(MNT, "logs", "closeout_b59.log")


def arm_done(arm: str) -> bool:
    """True when the arm's TRAIN PROCESS is gone AND its manifest says
    DONE (b59 manifests only write the status field at completion).
    While training, the key is absent -> False. Robust to relaunch
    headers: DONE line + manifest double-check; no early-exit bug."""
    rd = os.path.join(MNT, "runs", arm)
    try:
        m = json.load(open(os.path.join(rd, "manifest.json")))
    except (OSError, json.JSONDecodeError):
        return False
    if m.get("status") != "DONE":
        return False
    nt = m.get("final_nt") or 0
    budget = m.get("nt_budget") or 0
    if budget and nt < budget - 200_000_000:
        return False
    return True


def _final_rows(arm: str) -> list[dict]:
    p = os.path.join(MNT, "eval", "probe_results.jsonl")
    rows = []
    if not os.path.exists(p):
        return rows
    with open(p) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("run") == arm:
                rows.append(r)
    return rows


def arm_probed(arm: str) -> bool:
    rows = _final_rows(arm)
    elig = [r for r in rows if r.get("n_train", 0) >= 4000
            and r.get("ckpt_nt") is not None]
    if not elig:
        return False
    final_nt = max(r["ckpt_nt"] for r in elig)
    layers = {r["layer"] for r in elig if r["ckpt_nt"] == final_nt}
    if not layers or layers != set(range(max(layers) + 1)):
        return False
    try:
        m = json.load(open(os.path.join(MNT, "runs", arm, "manifest.json")))
        mnt = m.get("final_nt") or 0
    except (OSError, json.JSONDecodeError):
        mnt = 0
    if mnt and final_nt < mnt - 100_000_000:
        return False
    return True


def _have_randinit(arm: str) -> bool:
    """True if a randinit17 control run row exists for this arm.
    Uses parsed-json matching (not string formatting, which breaks on
    json.dump spacing differences)."""
    rand_name = "%s_randinit17" % arm
    for r in _final_rows(arm):
        if r.get("run") == rand_name:
            return True
    return False


def run_probe(arm: str, device: int) -> None:
    log = os.path.join(MNT, "logs", "probe_%s_auto_b59.log" % arm)
    rows = _final_rows(arm)
    if not rows:
        with open(log, "a") as lf:
            subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                            os.path.join(MNT, "runs", arm), "--device",
                            str(device)], cwd=ROOT, stdout=lf, stderr=lf,
                           timeout=14400)
    # randinit control (idempotent, parsed-json check)
    if not _have_randinit(arm):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--random-init", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass


def factorial_verdict(device: int) -> None:
    log = os.path.join(MNT, "logs", "closeout_b59_verdict.log")
    with open(log, "a") as lf:
        subprocess.run([PY, "-m", "rna_sc.factorial_verdict",
                        "--device", str(device)],
                       cwd=ROOT, stdout=lf, stderr=lf, timeout=7200)
    with open(TLOG, "a") as fh:
        fh.write("\n- [closeout-b59] 3x2 factorial verdict refreshed "
                 "(evidence/factorial_verdict.json; Claim-14 test)\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--timeout-h", type=float, default=600.0)
    args = ap.parse_args()
    t0 = time.time()
    print("[closeout-b59] v2 start; arms:", ARMS, flush=True)
    handled = set()
    while time.time() - t0 < args.timeout_h * 3600:
        for a in ARMS + EXTRA:
            if a in handled:
                continue
            if arm_done(a):
                try:
                    run_probe(a, args.device)
                except subprocess.TimeoutExpired:
                    print("[closeout-b59] %s probe TIMEOUT" % a, flush=True)
                else:
                    handled.add(a)
                    print("[closeout-b59] %s probed" % a, flush=True)
        if all(arm_done(a) and arm_probed(a) for a in ARMS):
            factorial_verdict(args.device)
            json.dump(
                {"finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "arms": ARMS},
                open(DONE_MARK, "w"))
            print("[closeout-b59] ALL ARMS PROBED + verdict done", flush=True)
            return 0
        time.sleep(600)
    print("[closeout-b59] TIMEOUT", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
