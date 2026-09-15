"""S1 scaling axis summary: auto-scan DONE runs + probes -> summary table.

Collects:
  - training: run, params, nt budget, best_val, throughput, fallback count
  - probes: per-layer best F1, depth-band means (from probe_results.jsonl)
Emits:
  - evidence/s1_scaling_summary.json
  - console table for TRAINING_LOG

Usage: python -m rna_sc.s1_summary
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

RUNS = "/mnt/cunyuliu/rna-sc/runs"
LOGS = "/mnt/cunyuliu/rna-sc/logs/RNA-Sc-*.log"
PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s1_scaling_summary.json"

DONE_RE = re.compile(
    r"DONE (\S+) \| nt=(\d+) steps=(\d+) best_val=([\d.]+) \| "
    r"(\d+) nt/s peak=(\d+)MB fallback=(\d+)")


def scan_training() -> dict:
    out = {}
    for path in glob.glob(LOGS):
        last = None
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = DONE_RE.match(line.strip())
                if m:
                    last = m
        if last:
            rid, nt, steps, bv, ntps, peak, fb = last.groups()
            out[rid] = {
                "nt_budget": int(nt), "steps": int(steps),
                "best_val": float(bv), "nt_per_s": int(ntps),
                "peak_mem_mb": int(peak), "cpu_fallback": int(fb),
                "status": "done"}
    # running runs: last progress line
    for path in glob.glob(LOGS):
        rid = os.path.basename(path)[len("RNA-Sc-"):-len(".log")]
        key = "rnasc_" + rid.replace("-", "_").replace("RNA_Sc_", "")
        rid_norm = os.path.basename(path)[len("RNA-Sc-"):-len(".log")]
        run_key = "rnasc_" + rid_norm
        if run_key in out:
            continue
        tail = ""
        with open(path, errors="ignore") as fh:
            for line in fh:
                if line.startswith("[rnasc_"):
                    tail = line.strip()
        if tail:
            m = re.match(r"\[(\S+)\] nt=(\d+)M", tail)
            if m:
                out[m.group(1)] = {
                    "nt_seen": int(m.group(2)) * 1_000_000,
                    "status": "running"}
    return out


def scan_probes() -> dict:
    per_run = collections.defaultdict(list)
    if not os.path.exists(PROBE_OUT):
        return {}
    with open(PROBE_OUT) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            per_run[r["run"]].append(r)
    out = {}
    for run, rows in per_run.items():
        # last full probe per run = highest n_train
        rows.sort(key=lambda r: (r.get("n_train", 0), r.get("layer", 0)))
        best = {}
        for r in rows:
            if r.get("n_train", 0) >= 4000:   # official-ish probe scale
                best[r["layer"]] = r
        if not best:
            for r in rows:                     # fall back to small probes
                best.setdefault(r["layer"], r)
        if not best:
            continue
        L = max(best) + 1
        f1s = [best[i]["f1_macro"] for i in range(L) if i in best]
        bands = collections.defaultdict(list)
        for i, r in best.items():
            db = r.get("depth_band") or ("early" if r["layer"] / max(1, r.get("n_layers", 2)-1) <= 0.33 else "middle" if r["layer"] / max(1, r.get("n_layers", 2)-1) <= 0.66 else "late")
            bands[db].append(r["f1_macro"])
        bl = max((i for i in best), key=lambda i: best[i]["f1_macro"])
        out[run] = {
            "n_layers": L,
            "best_layer": bl,
            "best_rel_depth": best[bl].get("rel_depth", "n/a"),
            "best_band": best[bl].get("depth_band", "n/a"),
            "best_f1": best[bl]["f1_macro"],
            "band_mean_f1": {k: round(sum(v) / len(v), 4)
                             for k, v in bands.items()},
            "n_probe_train": best[bl].get("n_train"),
        }
    return out


def main():
    tr = scan_training()
    pr = scan_probes()
    summary = {"training": tr, "probes": pr,
               "note": "S1 axis: model scale 1M/10M/30M/100M (2B nt each) "
                       "+ S2 corpus axis (c1M/c10M/c1Mcs); probes use "
                       "family_validation->family_test, macro-F1"}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(summary, fh, indent=2)
    print("=== S1 scaling summary (auto) ===")
    order = sorted(tr.keys())
    for rid in order:
        t = tr[rid]
        cand = rid.replace("rnasc_", "RNA-Sc-")
        p = pr.get(rid) or pr.get(rid.replace("rnasc_", "")) or pr.get(cand)
        line = "%-24s %-8s nt=%s val=%s" % (
            rid, t["status"],
            f"{t.get('nt_budget', t.get('nt_seen', 0))/1e9:.2f}B",
            t.get("best_val", "-"))
        if p:
            line += " | probe best L%d/%d %s F1=%.4f %s" % (
                p["best_layer"], p["n_layers"] - 1, p["best_band"],
                p["best_f1"], p["band_mean_f1"])
        print(line)
    print("saved", OUT)


if __name__ == "__main__":
    main()
