"""S12 x S7 linkage: per-family decoupling index vs probe-layer behavior.

Question (H6): do high-DI families (sequence-divergent, structure-conserved)
show different probe-layer dependence than low-DI families?

Analysis:
  1. Load probe_results.jsonl rows (with per_class_f1) for a given run.
  2. Load s12_family_identity.json + s12_decoupling_index.json.
  3. For each family with DI: track per-layer F1; compute
     argmax-layer and early-vs-late F1 gap.
  4. Correlate (Spearman) DI vs layer-of-best-F1 and vs late-minus-early.

Usage:
  python -m rna_sc.s12_linkage --run RNA-Sc-100M_s17
"""
from __future__ import annotations

import argparse
import json
import math
import os

PROBE_OUT = "/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl"
IDENT = "/mnt/cunyuliu/rna-sc/evidence/s12_family_identity.json"
DEC = "/mnt/cunyuliu/rna-sc/evidence/s12_decoupling_index.json"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s12_linkage.json"

MAX_CLASSES = 24


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) *
                    sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--source", default="rna_type")
    args = ap.parse_args()

    rows = []
    with open(PROBE_OUT) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("run") == args.run and "per_class_f1" in r:
                rows.append(r)
    if not rows:
        print("no probe rows with per_class_f1 for run %s" % args.run)
        return
    rows.sort(key=lambda r: r["layer"])
    L = len(rows)

    with open(DEC) as fh:
        dec = json.load(fh)["families"]
    with open(IDENT) as fh:
        ident = json.load(fh)["families"]

    # probe classes are rna_type names; DI keys are RF accessions.
    # Aggregate accessions -> their dominant rna_type (acc2type.json).
    ACC2TYPE = "/mnt/cunyuliu/rna-sc/evidence/acc2type.json"
    acc2type = {}
    if os.path.exists(ACC2TYPE):
        acc2type = json.load(open(ACC2TYPE))
    di_by_type = {}
    for acc, d in dec.items():
        t = acc2type.get(acc)
        if t is None:
            continue
        di_by_type.setdefault(t, []).append(
            (d["decoupling_index"], d.get("mean_pairwise_identity"),
             d.get("mean_cm_bits")))
    type_di = {t: sum(x[0] for x in v) / len(v)
               for t, v in di_by_type.items() if v}
    print("types with DI: %d (%s)" % (
        len(type_di), sorted(type_di.keys())))

    di, best_layer, late_early = [], [], []
    per_fam = {}
    for fam, d in type_di.items():
        f1s = []
        for r in rows:
            v = r["per_class_f1"].get(fam)
            if v is None:
                f1s = None
                break
            f1s.append(v)
        if f1s is None:
            continue
        bl = max(range(L), key=lambda i: f1s[i])
        le = (sum(f1s[math.ceil(2 * L / 3):]) / max(1, L - math.ceil(2 * L / 3))) - \
             (sum(f1s[:math.ceil(L / 3)]) / max(1, math.ceil(L / 3)))
        di.append(d)
        best_layer.append(bl / max(1, L - 1))
        late_early.append(round(le, 4))
        src = di_by_type[fam]
        per_fam[fam] = {"DI": round(d, 4),
                        "n_accessions": len(src),
                        "identity": round(sum(x[1] for x in src) / len(src), 3)
                        if src[0][1] is not None else None,
                        "cm_bits": round(sum(x[2] for x in src) / len(src), 1)
                        if src[0][2] is not None else None,
                        "best_rel_layer": round(bl / max(1, L - 1), 3),
                        "late_minus_early": round(le, 4),
                        "per_layer_f1": f1s}

    rho_layer = spearman(di, best_layer)
    rho_le = spearman(di, late_early)
    out = {
        "run": args.run, "n_families": len(di),
        "spearman_DI_vs_bestlayer": rho_layer,
        "spearman_DI_vs_lateMinusEarly": rho_le,
        "interpretation": {
            "rho_layer>0": "high-DI families peak deeper — structure-conserved "
                           "sequence-divergent families rely on later layers",
            "rho_layer<0": "high-DI families peak earlier",
        },
        "families": per_fam,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps({k: out[k] for k in
                      ("run", "n_families", "spearman_DI_vs_bestlayer",
                       "spearman_DI_vs_lateMinusEarly")}, indent=2))
    print("saved", OUT)


if __name__ == "__main__":
    main()
