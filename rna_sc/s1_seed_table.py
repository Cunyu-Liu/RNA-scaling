"""S1 three-seed summary table (paper main table generator).

Groups runs by scale family (1M/10M/30M/100M + corpus variants), reports
mean±std of: best_val, probe best F1, best layer (rel depth), band means.
Only counts runs with COMPLETE official probes (final ckpt + 20k).

Usage: python -m rna_sc.s1_seed_table
Output: evidence/s1_seed_table.json + console markdown
"""
from __future__ import annotations

import collections
import json
import math
import re

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
LOGS_GLOB = "/mnt/cunyuliu/rna-sc/logs/RNA-Sc-*.log"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s1_seed_table.json"

DONE_RE = re.compile(
    r"DONE (\S+) \| nt=(\d+) steps=(\d+) best_val=([\d.]+) \| "
    r"(\d+) nt/s peak=(\d+)MB fallback=(\d+)")

FAMILY = {
    "RNA-Sc-1M_s17": "1M",
    "RNA-Sc-10M_s17": "10M",
    "RNA-Sc-30M_s17": "30M",
    "RNA-Sc-100M_s17": "100M",
    "RNA-Sc-100M_s29": "100M",
    "RNA-Sc-100M_s43": "100M",
    "RNA-Sc-30M_s17_c1M": "30M-c1M",
    "RNA-Sc-30M_s17_c1Mcs": "30M-c1Mcs",
    "RNA-Sc-30M_s29_c1Mcs": "30M-c1Mcs",
    "RNA-Sc-30M_s17_c10M": "30M-c10M",
    "RNA-Sc-10M_s17_randinit17": "10M-randinit (control)",
}


def mean_std(v):
    if not v:
        return None, None
    m = sum(v) / len(v)
    s = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5 \
        if len(v) > 1 else 0.0
    return m, s


def scan_done():
    import glob
    out = {}
    for path in glob.glob(LOGS_GLOB):
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = DONE_RE.match(line.strip())
                if m:
                    rid, nt, steps, bv, _, _, fb = m.groups()
                    out[rid] = {"best_val": float(bv), "nt": int(nt),
                                "fallback": int(fb)}
    return out


def official_probes():
    by_run = collections.defaultdict(list)
    with open(PROBE_OUT) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_run[r["run"]].append(r)
    out = {}
    for run, rows in by_run.items():
        elig = [r for r in rows if r.get("n_train", 0) >= 4000
                and r.get("ckpt_nt") is not None]
        if not elig:
            continue
        final_nt = max(r["ckpt_nt"] for r in elig)
        best = {r["layer"]: r for r in elig if r["ckpt_nt"] == final_nt}
        if not best or best.keys() != set(range(max(best) + 1)):
            continue
        layers = sorted(best.values(), key=lambda r: r["layer"])
        L = len(layers)
        bestrow = max(layers, key=lambda r: r["f1_macro"])
        bands = collections.defaultdict(list)
        for r in layers:
            rel = r["layer"] / max(1, L - 1)
            b = "early" if rel <= 0.33 else ("middle" if rel <= 0.66
                                             else "late")
            bands[b].append(r["f1_macro"])
        out[run] = {
            "best_layer": bestrow["layer"], "n_layers": L,
            "best_rel": round(bestrow["layer"] / (L - 1), 3),
            "best_f1": bestrow["f1_macro"],
            "bands": {b: round(sum(v) / len(v), 4) for b, v in
                      bands.items()},
            "final_ckpt_nt": final_nt,
        }
    return out


def main():
    done = scan_done()
    probes = official_probes()
    fam = collections.defaultdict(lambda: {"val": [], "f1": [],
                                           "rel": [], "bandE": [],
                                           "bandM": [], "bandL": [],
                                           "runs": []})
    # done keys are rnasc_* (log DONE lines); probes keys are RNA-Sc-*
    # (run dir names). Bridge: rnasc_1M_s17 -> RNA-Sc-1M_s17
    def to_runname(rid):
        return rid.replace("rnasc_", "RNA-Sc-", 1)
    for rid, famname in FAMILY.items():
        d = done.get(rid) or done.get(rid.replace("RNA-Sc-", "rnasc_", 1))
        p = probes.get(rid) or probes.get(to_runname(rid))
        if d is None or p is None:
            continue
        f = fam[famname]
        f["val"].append(d["best_val"])
        f["f1"].append(p["best_f1"])
        f["rel"].append(p["best_rel"])
        f["bandE"].append(p["bands"].get("early"))
        f["bandM"].append(p["bands"].get("middle"))
        f["bandL"].append(p["bands"].get("late"))
        f["runs"].append(rid)

    table = {}
    print("| family | n | best_val | probe F1 | best rel-depth | "
          "E / M / L band F1 |")
    print("|---|---|---|---|---|---|")
    for famname in sorted(fam, key=lambda x: (len(x), x)):
        f = fam[famname]
        n = len(f["runs"])
        if n == 0:
            continue
        vm, vs = mean_std([x for x in f["val"] if x is not None])
        fm, fs = mean_std([x for x in f["f1"] if x is not None])
        em, es = mean_std([x for x in f["bandE"] if x is not None])
        mm, _ = mean_std([x for x in f["bandM"] if x is not None])
        lm, _ = mean_std([x for x in f["bandL"] if x is not None])
        relm, _ = mean_std([x for x in f["rel"] if x is not None])
        table[famname] = {
            "n_seeds": n, "runs": f["runs"],
            "best_val": [round(vm, 4), round(vs, 4)],
            "probe_best_f1": [round(fm, 4), round(fs, 4)],
            "best_rel_depth": [round(relm, 3), round(es, 3)
                               if False else None],
            "band_early": round(em, 4) if em is not None else None,
            "band_middle": round(mm, 4) if mm is not None else None,
            "band_late": round(lm, 4) if lm is not None else None,
        }
        print("| %s | %d | %.4f±%.4f | %.4f±%.4f | %.3f | %.4f / %.4f / "
              "%.4f |" % (famname, n, vm, vs, fm, fs, relm,
                          em or -1, mm or -1, lm or -1))
    with open(OUT, "w") as fh:
        json.dump(table, fh, indent=2)
    print("saved", OUT)


if __name__ == "__main__":
    main()
