"""S5 moment-matched exclusion table (H3): trained vs moment-matched control.

Reads official probe rows (n_train>=4000, final ckpt) for the trained
runs and their _mommatch{seed} controls from probe_results.jsonl, then
emits the H3 exclusion table (json + markdown).

H3 (good initialization / weight statistics): excluded at a scale iff
trained >> moment-matched. The moment-matched control is a fresh random
encoder whose per-tensor mean/std are matched to the trained weights
(capture BEFORE re-init — see probe.py --moment-matched), so any
remaining gap must come from weight structure, not statistics.

Usage:
  python -m rna_sc.s5_mommatch_table            # default 4 scales s17
"""
from __future__ import annotations

import argparse
import collections
import json

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/s5_mommatch_table.json"
OUT_MD = "/mnt/cunyuliu/rna-sc/evidence/s5_mommatch_table.md"
TRAINED = {"1M": "RNA-Sc-1M_s17",
           "10M": "RNA-Sc-10M_s17",
           "30M": "RNA-Sc-30M_s17",
           "100M": "RNA-Sc-100M_s17"}


def official_best(run_name: str) -> dict | None:
    layers = collections.defaultdict(dict)
    for line in open(PROBE_OUT):
        r = json.loads(line)
        if r["run"] != run_name:
            continue
        if r.get("n_train", 0) < 4000 or r.get("ckpt_nt") is None:
            continue
        layers[r["ckpt_nt"]][r["layer"]] = r
    if not layers:
        return None
    final_nt = max(layers)
    rows = list(layers[final_nt].values())
    L = max(r["layer"] for r in rows) + 1
    if len(rows) != L:
        return None
    best = max(rows, key=lambda r: r["f1_macro"])
    return {"best_f1": best["f1_macro"], "n_layers": L,
            "best_layer": best["layer"], "final_ckpt_nt": final_nt}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", default="1M,10M,30M,100M")
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    out = {}
    for scale in args.scales.split(","):
        t_run = TRAINED.get(scale)
        m_run = "%s_mommatch%d" % (t_run, args.seed)
        t = official_best(t_run)
        m = official_best(m_run)
        if t is None or m is None:
            print("skip %s (trained=%s mommatch=%s)" %
                  (scale, t is not None, m is not None))
            continue
        out[scale] = {"trained": t["best_f1"], "mommatch": m["best_f1"],
                      "delta": round(t["best_f1"] - m["best_f1"], 4),
                      "n_layers": t["n_layers"],
                      "mommatch_best_layer": m["best_layer"]}
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=4)

    lines = ["# T2.2.2 S5 moment-matched exclusion table (H3)", "",
             "Protocol: inc12 deterministic pooled probe; moment-matched = "
             "fresh encoder (seed 17) with per-tensor mean/std matched to "
             "the TRAINED weights (moments captured before re-init).",
             "H3 excluded at a scale iff trained >> moment-matched.",
             "",
             "| scale | trained best F1 | mommatch best F1 | delta |"
             " layers |", "|---|---|---|---|---|"]
    for s, d in out.items():
        lines.append("| %s | %.4f | %.4f | %+.4f | %d |" %
                     (s, d["trained"], d["mommatch"], d["delta"],
                      d["n_layers"]))
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))
    print("saved", OUT_JSON, "and", OUT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
