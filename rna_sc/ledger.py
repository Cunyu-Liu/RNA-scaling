"""Run registry ledger (Z5): tracks every RNA-Sc run, prevents duplicates.

JSON-lines ledger at /mnt/cunyuliu/rna-sc/ledger.jsonl:
  {"run_id", "model_id", "seed", "corpus_tag", "device", "out_dir",
   "status" ("pending"|"running"|"done"|"failed"), "manifest_path",
   "updated_utc", "final_nt", "best_val_loss", "note"}

Ledger discipline (TokBench closure-ledger pattern):
  - `claim` refuses to start a run_id that is already running/done;
  - every launch/completion/failure updates exactly one line (by run_id).

2026-09-14 race fix: ALL read-modify-write cycles now hold an exclusive
flock on ledger.lock. Previously, the monitoring cron's `ledger sync` and
the supervisor's `update` could interleave (read A, read A, write B, write
A'), silently dropping rows — which caused duplicate 100M launches.
"""
from __future__ import annotations

import contextlib
import datetime
import fcntl
import json
import os
import sys

LEDGER = "/mnt/cunyuliu/rna-sc/ledger.jsonl"
LOCK = "/mnt/cunyuliu/rna-sc/ledger.lock"


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


@contextlib.contextmanager
def _locked():
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LOCK, "a") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    rows = []
    with open(LEDGER) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _write(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, LEDGER)


def run_id_of(model_id: str, seed: int, corpus_tag: str = "full") -> str:
    tag = corpus_tag if corpus_tag != "full" else ""
    return "rnasc_%s_s%s%s" % (model_id.split("-")[-1], seed, tag)


def claim(model_id: str, seed: int, device: int, out_dir: str,
          corpus_tag: str = "full", note: str = "") -> dict:
    rid = run_id_of(model_id, seed, corpus_tag)
    with _locked():
        rows = _load()
        for r in rows:
            if r["run_id"] == rid and r.get("status") in ("running", "done"):
                return {"claimed": False, "reason": "already %s" % r["status"],
                        "row": r}
        row = {"run_id": rid, "model_id": model_id, "seed": seed,
               "corpus_tag": corpus_tag, "device": device, "out_dir": out_dir,
               "status": "pending", "manifest_path":
                   os.path.join(out_dir, "manifest.json"),
               "updated_utc": _now(), "note": note}
        rows.append(row)
        _write(rows)
    return {"claimed": True, "row": row}


def update(run_id: str, status: str, **fields) -> dict | None:
    out = None
    with _locked():
        rows = _load()
        for r in rows:
            if r["run_id"] == run_id:
                r["status"] = status
                r["updated_utc"] = _now()
                r.update(fields)
                out = r
        _write(rows)
    return out


def upsert(row: dict) -> dict:
    """Insert or replace a row by run_id (recovery tool)."""
    with _locked():
        rows = _load()
        rows = [r for r in rows if r["run_id"] != row["run_id"]]
        rows.append(row)
        _write(rows)
    return row


def sync_from_manifests() -> dict:
    """Reconcile ledger with on-disk manifests (for monitoring)."""
    with _locked():
        rows = _load()
        n_synced, n_stale = 0, 0
        for r in rows:
            mp = r.get("manifest_path")
            if mp and os.path.exists(mp):
                try:
                    with open(mp) as fh:
                        m = json.load(fh)
                    changed = False
                    if r.get("final_nt") != m.get("final_nt") and m.get("final_nt"):
                        r["final_nt"] = m.get("final_nt")
                        changed = True
                    if m.get("best_val_loss") is not None and \
                            r.get("best_val_loss") != m.get("best_val_loss"):
                        r["best_val_loss"] = m.get("best_val_loss")
                        changed = True
                    if m.get("status") == "DONE" and r.get("status") != "done":
                        r["status"] = "done"
                        changed = True
                    n_synced += changed
                except (OSError, json.JSONDecodeError):
                    n_stale += 1
        _write(rows)
    return {"rows": len(rows), "synced_changes": n_synced, "stale": n_stale}


def by_run_id(run_id: str) -> dict | None:
    for r in _load():
        if r["run_id"] == run_id:
            return r
    return None


def reset(run_id: str) -> dict | None:
    """Set a failed/pending row back to launchable (supervisor relaunch)."""
    rows = _load()
    out = None
    for r in rows:
        if r["run_id"] == run_id and r.get("status") in ("pending", "failed"):
            r["status"] = "pending"
            r["updated_utc"] = _now()
            out = r
    _write(rows)
    return out


def summary() -> list[dict]:
    return _load()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for r in summary():
            print(json.dumps(r))
    elif len(sys.argv) > 1 and sys.argv[1] == "sync":
        print(json.dumps(sync_from_manifests()))
    else:
        print("usage: python -m rna_sc.ledger [list|sync]")
