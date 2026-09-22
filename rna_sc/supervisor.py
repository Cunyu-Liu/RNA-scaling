"""Wave supervisor: schedule runs onto real-free GPUs, relaunch on OOM.

Design (owner rules 2026-09-13):
- GPU choice by torch.cuda.mem_get_info at launch instant, exclude GPUs
  already hosting our runs; ANY GPU with enough real free memory is usable
  (no other gating).
- Queue read from wave.json each cycle: runs can be added live.
- Skips a run whose ledger row is running with a LIVE pid (no duplicates).
- On process death before budget: relaunch with --resume-from latest ckpt
  (up to N attempts). Crashes recorded in ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc import ledger
from rna_sc import gpu_pick

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = "/mnt/cunyuliu/rna-sc/runs"
LOGS = "/mnt/cunyuliu/rna-sc/logs"
WAVE_JSON = "/mnt/cunyuliu/rna-sc/wave.json"

MAX_ATTEMPTS = 5


def default_wave() -> list[dict]:
    return [
        {"model_id": "RNA-Sc-30M", "seed": 17, "corpus_nseq": None,
         "corpus_tag": "full", "need_gb": 4.0},
        {"model_id": "RNA-Sc-10M", "seed": 17, "corpus_nseq": None,
         "corpus_tag": "full", "need_gb": 3.0},
        {"model_id": "RNA-Sc-30M", "seed": 17, "corpus_nseq": 1_000_000,
         "corpus_tag": "c1M", "need_gb": 4.0},
        {"model_id": "RNA-Sc-1M", "seed": 17, "corpus_nseq": None,
         "corpus_tag": "full", "need_gb": 2.0},
    ]


def load_wave() -> list[dict]:
    if os.path.exists(WAVE_JSON):
        try:
            with open(WAVE_JSON) as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            pass
    return default_wave()


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def out_dir_of(model_id, seed, tag) -> str:
    return os.path.join(
        RUNS, "%s_s%s" % (model_id, seed) +
        ("" if tag == "full" else "_" + tag))


def latest_ckpt(out_dir: str) -> str | None:
    if not os.path.isdir(out_dir):
        return None
    cks = [f for f in os.listdir(out_dir) if f.startswith("ckpt_")]
    if not cks:
        return None
    cks.sort(key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    return os.path.join(out_dir, cks[-1])


def _log_missing_done(out_dir: str, mrow: dict) -> bool:
    """Backfill a DONE frame line into the run log if absent (inc10:
    adopted runs that finish while unmanaged lose the log DONE frame that
    watch_all/s1_summary scan)."""
    import glob
    log = os.path.join(LOGS, os.path.basename(out_dir) + ".log")
    if not os.path.exists(log):
        return False
    done_line = "DONE %s |" % (mrow.get("run_id") or
                               os.path.basename(out_dir))
    with open(log, "r+", errors="ignore") as fh:
        for line in fh:
            if line.startswith(done_line):
                return False
        fh.write(
            "DONE %s | nt=%d steps=%d best_val=%.4f | %.0f nt/s "
            "peak=%.0fMB fallback=%d\n" % (
                mrow.get("run_id") or os.path.basename(out_dir),
                mrow.get("final_nt") or 0, mrow.get("final_step") or 0,
                mrow.get("best_val_loss") or 0.0,
                mrow.get("throughput_nt_s") or 0.0,
                mrow.get("peak_vram_mb") or 0.0,
                mrow.get("cpu_fallback_count") or 0))
    return True


def _manifest_done(out_dir: str) -> bool:
    try:
        with open(os.path.join(out_dir, "manifest.json")) as fh:
            return json.load(fh).get("status") == "DONE"
    except (OSError, json.JSONDecodeError):
        return False


def launch_one(item, exclude) -> tuple:
    model_id, seed = item["model_id"], item["seed"]
    tag = item.get("corpus_tag", "full")
    nseq = item.get("corpus_nseq")
    need = item.get("need_gb", 4.0)
    out_dir = out_dir_of(model_id, seed, tag)
    gpu = gpu_pick.pick(need, exclude=exclude)
    log = os.path.join(
        LOGS, "%s_s%s" % (model_id, seed) +
        ("" if tag == "full" else "_" + tag) + ".log")
    rid = ledger.run_id_of(model_id, seed, tag)
    args = [sys.executable, "-m", "rna_sc.train", "--model", model_id,
            "--seed", str(seed), "--device", str(gpu),
            "--out-dir", out_dir]
    if nseq:
        args += ["--corpus-nseq", str(nseq), "--corpus-tag", tag]
    al = item.get("cluster_allowlist")
    if al:
        args += ["--cluster-allowlist", al, "--corpus-tag", tag]
    bnt = item.get("budget_nt")
    if bnt:
        args += ["--budget-nt", str(bnt)]
    ck = latest_ckpt(out_dir)
    if ck:
        args += ["--resume-from", ck]
    with open(log, "a") as lh:
        lh.write("\n=== relaunch %s gpu=%d %s ===\n" % (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), gpu,
            ck or "fresh"))
        proc = subprocess.Popen(args, cwd=ROOT, stdout=lh, stderr=lh,
                                start_new_session=True)
    ledger.upsert({
        "run_id": rid, "model_id": model_id, "seed": seed,
        "corpus_tag": tag, "device": gpu, "out_dir": out_dir,
        "status": "running", "pid": proc.pid,
        "manifest_path": os.path.join(out_dir, "manifest.json"),
        "note": "supervisor launch (inc10: upsert so DONE rows persist)",
    })
    return proc, gpu, out_dir, rid, item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll", type=int, default=120)
    args = ap.parse_args()

    procs = {}          # rid -> (proc, gpu, out_dir, item)
    exclude = set()     # GPUs hosting our runs
    attempts = {}

    if not os.path.exists(WAVE_JSON):
        os.makedirs(os.path.dirname(WAVE_JSON), exist_ok=True)
        with open(WAVE_JSON, "w") as fh:
            json.dump(default_wave(), fh, indent=2)

    while True:
        # 1) adopt runs already alive from earlier waves (e.g. wave1 survivor)
        for row in ledger.summary():
            rid = row["run_id"]
            if rid in procs:
                continue
            if row.get("status") == "running" and pid_alive(row.get("pid")):
                procs[rid] = (None, row.get("device"), row["out_dir"],
                              {"model_id": row["model_id"],
                               "seed": row["seed"],
                               "corpus_tag": row.get("corpus_tag", "full"),
                               "corpus_nseq": None, "need_gb": 4.0})
                exclude.add(row.get("device"))
                print("[sup] adopted live run %s (pid %s)" % (rid, row["pid"]),
                      flush=True)

        # 2) reap dead children AND dead adopted runs
        for rid in list(procs):
            proc, gpu, out_dir, item = procs[rid]
            if proc is None:
                # adopted run: check ledger pid liveness each cycle.
                # IMPORTANT: a run whose manifest says DONE has finished
                # normally — do NOT relaunch it (early bug: treated as dead).
                row = ledger.by_run_id(rid) or {}
                if row.get("status") == "done":
                    del procs[rid]
                    exclude.discard(gpu)
                    continue
                if row.get("status") == "running" and \
                        not pid_alive(row.get("pid")):
                    if _manifest_done(out_dir):
                        ledger.update(rid, "done")
                        print("[sup] adopted run %s manifest DONE" % rid,
                              flush=True)
                        mrow = json.load(
                            open(os.path.join(out_dir, "manifest.json")))
                        if _log_missing_done(out_dir, mrow):
                            print("[sup] %s DONE frame backfilled to log "
                                  "(watch_all parity)" % rid, flush=True)
                        del procs[rid]
                        exclude.discard(gpu)
                        continue
                    del procs[rid]
                    exclude.discard(gpu)
                    ledger.update(rid, "pending",
                                  note="adopted proc died; relaunch queued")
                    print("[sup] adopted run %s died -> pending" % rid,
                          flush=True)
                continue
            rc = proc.poll()
            if rc is None:
                continue
            del procs[rid]
            exclude.discard(gpu)
            if rc == 0:
                ledger.update(rid, "done")
                print("[sup] %s DONE" % rid, flush=True)
            else:
                att = attempts.get(rid, 0) + 1
                attempts[rid] = att
                ck = latest_ckpt(out_dir)
                ledger.update(rid, "failed", attempts=att,
                              note="rc=%s last_ck=%s" % (rc, ck))
                print("[sup] %s rc=%s (attempt %d/%d) ck=%s" % (
                    rid, rc, att, MAX_ATTEMPTS, ck), flush=True)
                if att < MAX_ATTEMPTS:
                    time.sleep(30)  # let foreign memory pressure settle
                    ledger.update(rid, "pending")

        # 3) launch from wave.json queue
        for item in load_wave():
            model_id, seed = item["model_id"], item["seed"]
            tag = item.get("corpus_tag", "full")
            rid = ledger.run_id_of(model_id, seed, tag)
            if rid in procs:
                continue
            row = ledger.by_run_id(rid)
            if row and row.get("status") == "done":
                continue
            if row and row.get("status") == "running" and pid_alive(row.get("pid")):
                continue
            try:
                proc, gpu, out_dir, rid2, it = launch_one(item, exclude)
            except RuntimeError as e:
                print("[sup] waiting: %s" % e, flush=True)
                break
            exclude.add(gpu)
            procs[rid2] = (proc, gpu, out_dir, it)
            print("[sup] launched %s on GPU%d" % (rid2, gpu), flush=True)

        # 4) exit when wave.json fully done
        wave = load_wave()
        pending = [it for it in wave
                   if (ledger.by_run_id(ledger.run_id_of(
                       it["model_id"], it["seed"],
                       it.get("corpus_tag", "full"))) or {}).get("status")
                   != "done"]
        if not pending and all(p is None for p, *_ in procs.values()):
            print("[sup] wave complete", flush=True)
            return
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
