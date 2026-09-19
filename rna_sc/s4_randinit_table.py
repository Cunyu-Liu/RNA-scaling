"""S4 randinit exclusion table (H2): trained vs random-init probe F1.

Reads official probe rows (n_train>=4000, final ckpt) from
probe_results.jsonl for both the trained run and its randinit control
(run name suffix _randinit{seed}), then emits the four-scale exclusion
table (json + markdown) with delta = trained - randinit.

H2 (inductive bias / over-parameterization) is excluded at a scale iff
trained >> randinit. This module exists so the table is regenerable
from the jsonl alone (reproducibility: the 2026-09-16 first version was
produced by an ad-hoc inline script that never entered the repo).

Usage:
  python -m rna_sc.s4_randinit_table            # default 4 scales s17
  python -m rna_sc.s4_randinit_table --scales 1M,10M
"""
from __future__ import annotations

import argparse
import collections
import json

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/s4_randinit_table.json"
OUT_MD = "/mnt/cunyuliu/rna-sc/evidence/s4_randinit_table.md"
TRAINED = {"1M": "RNA-Sc-1M_s17",
           "10M": "RNA-Sc-10M_s17",
           "30M": "RNA-Sc-30M_s17",
           "100M": "RNA-Sc-100M_s17"}


def official_best(run_name: str) -> dict | None:
    """Best-layer macro-F1 of the final-ckpt official rows of a run."""
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
    ap.add_argument("--randinit-seed", type=int, default=17)
    args = ap.parse_args()

    out = {}
    for scale in args.scales.split(","):
        t_run = TRAINED.get(scale)
        r_run = "%s_randinit%d" % (t_run, args.randinit_seed)
        t = official_best(t_run)
        r = official_best(r_run)
        if t is None or r is None:
            print("skip %s (trained=%s randinit=%s)" %
                  (scale, t is not None, r is not None))
            continue
        out[scale] = {"trained": t["best_f1"], "randinit": r["best_f1"],
                      "delta": round(t["best_f1"] - r["best_f1"], 4),
                      "n_layers": t["n_layers"],
                      "trained_best_layer": t["best_layer"],
                      "randinit_best_layer": r["best_layer"]}
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=4)

    lines = ["# T2.2.1 S4 randinit exclusion table (H2)", "",
             "Protocol: inc12 deterministic pooled probe (per-layer seed "
             "17+layer_idx), n_train=20000, n_eval=4000, family split;",
             "randinit = torch.manual_seed(17) fresh encoder, same "
             "architecture. H2 excluded at a scale iff trained >> randinit.",
             "",
             "| scale | trained best F1 | randinit best F1 | delta |"
             " layers |", "|---|---|---|---|---|"]
    for s, d in out.items():
        lines.append("| %s | %.4f | %.4f | %+.4f | %d |" %
                     (s, d["trained"], d["randinit"], d["delta"],
                      d["n_layers"]))
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))
    print("saved", OUT_JSON, "and", OUT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
