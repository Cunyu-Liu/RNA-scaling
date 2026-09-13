"""Train status monitor: reads manifests, reconciles ledger, writes report.

Usage (server cron or from anywhere via ssh):
  python -m rna_sc.status            # one-shot report
  python -m rna_sc.status --watch    # continuous, refresh every 300s
"""
from __future__ import annotations

import argparse
import datetime
import json
import os

RUNS_ROOT = "/mnt/cunyuliu/rna-sc/runs"
STATUS_JSON = "/mnt/cunyuliu/rna-sc/status.json"
STATUS_MD = "/mnt/cunyuliu/rna-sc/status.md"


def collect() -> list[dict]:
    rows = []
    if not os.path.isdir(RUNS_ROOT):
        return rows
    for name in sorted(os.listdir(RUNS_ROOT)):
        mp = os.path.join(RUNS_ROOT, name, "manifest.json")
        if not os.path.exists(mp):
            rows.append({"run": name, "status": "no-manifest-yet"})
            continue
        try:
            with open(mp) as fh:
                m = json.load(fh)
        except json.JSONDecodeError:
            rows.append({"run": name, "status": "manifest-corrupt"})
            continue
        cfg = m.get("config", {})
        budget = cfg.get("budget_nt") or 0
        fin = m.get("final_nt")
        # live progress: last checkpoint / validation entry
        last_val = m["validations"][-1] if m.get("validations") else None
        cur_nt = fin if fin is not None else (last_val or {}).get("nt", 0)
        rows.append({
            "run": name,
            "status": m.get("status", "RUNNING"),
            "model_id": m.get("model_id"),
            "seed": m.get("seed"),
            "corpus_tag": cfg.get("corpus_tag"),
            "device": m.get("device"),
            "nt_done": cur_nt,
            "nt_budget": budget,
            "progress_pct": round(100.0 * cur_nt / max(1, budget), 2),
            "best_val_loss": m.get("best_val_loss"),
            "last_val": (last_val or {}).get("val_loss"),
            "n_checkpoints": len(m.get("checkpoints", [])),
            "throughput_nt_s": m.get("throughput_nt_s"),
            "peak_vram_mb": m.get("peak_vram_mb"),
            "cpu_fallback_count": m.get("cpu_fallback_count"),
            "updated_utc": m.get("end_utc"),
        })
    return rows


def render(rows: list[dict]) -> str:
    lines = ["# RNA-Sc Training Status",
             "",
             "generated: %s" % datetime.datetime.now().isoformat(timespec="seconds"),
             ""]
    for r in rows:
        if r.get("status") == "no-manifest-yet":
            lines.append("- **%s**: waiting for first manifest (starting)" % r["run"])
            continue
        if r.get("status") == "manifest-corrupt":
            lines.append("- **%s**: manifest corrupt (investigate!)" % r["run"])
            continue
        lines.append(
            "- **%s** [%s] %s seed=%s corpus=%s gpu=%s | nt %.0fM/%.0fM (%.1f%%) "
            "| best_val=%s | ckpts=%s | thr=%.0f nt/s | fallback=%s" % (
                r["run"], r["status"], r.get("model_id"), r.get("seed"),
                r.get("corpus_tag"), (r.get("device") or "?").replace("cuda:", "GPU"),
                (r.get("nt_done") or 0) / 1e6, (r.get("nt_budget") or 0) / 1e6,
                r.get("progress_pct") or 0,
                ("%.4f" % r["best_val_loss"]) if r.get("best_val_loss") else "-",
                r.get("n_checkpoints"),
                r.get("throughput_nt_s") or 0,
                r.get("cpu_fallback_count")))
    running = [r for r in rows if r.get("status") not in ("DONE", "no-manifest-yet")]
    lines += ["", "_%d run(s) not DONE._" % len(running)]
    return "\n".join(lines) + "\n"


def write_outputs(rows: list[dict]):
    os.makedirs(os.path.dirname(STATUS_JSON), exist_ok=True)
    with open(STATUS_JSON, "w") as fh:
        json.dump({"generated": datetime.datetime.now().isoformat(),
                   "rows": rows}, fh, indent=2)
    with open(STATUS_MD, "w") as fh:
        fh.write(render(rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=300)
    args = ap.parse_args()
    if not args.watch:
        rows = collect()
        write_outputs(rows)
        print(render(rows))
        return
    while True:
        rows = collect()
        write_outputs(rows)
        print(render(rows))
        import time
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
