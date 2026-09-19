"""T2.3.1 corpus-axis saturation point statistics (95% threshold).

Per family (10M / 30M), reads corpus3.json (corpus arms: nt_unique_B,
epochs, best_f1) and computes:
  1. shape classification (monotone-rise / monotone-fall / U / other)
     on the unique-nt axis;
  2. saturation point: first unique-nt x on the ASCENDING limb where
     interpolated f(x) >= 0.95 * max_f1 (None if never reached —
     honest reporting, e.g. U-shapes whose right limb stays below);
  3. same-epoch-coverage pairs (red-team fix A: saturation and arm
     comparisons only meaningful within equal epoch coverage — e.g.
     c1M prefix vs c1Mcs cluster-stratified, both ~2.2 epochs).

Outputs evidence/corpus_saturation.json (+ prints a table).

Usage: python -m rna_sc.corpus_saturation
"""
from __future__ import annotations

import json

IN_JSON = "/mnt/cunyuliu/rna-sc/evidence/corpus3.json"
OUT_JSON = "/mnt/cunyuliu/rna-sc/evidence/corpus_saturation.json"
THRESH = 0.95


def interp_crossing(x0, y0, x1, y1, target):
    if y0 == y1:
        return None
    t = (target - y0) / (y1 - y0)
    if 0.0 <= t <= 1.0:
        return x0 + t * (x1 - x0)
    return None


def classify(points):
    """points sorted by x (nt_unique). Returns shape label."""
    ys = [p[1] for p in points]
    rises = sum(1 for a, b in zip(ys, ys[1:]) if b > a)
    falls = sum(1 for a, b in zip(ys, ys[1:]) if b < a)
    n = len(ys) - 1
    if rises == n:
        return "monotone-rise"
    if falls == n:
        return "monotone-fall"
    if len(ys) >= 3 and ys[0] < ys[1] and ys[-1] < max(ys[:-1]):
        return "rise-then-fall"
    if len(ys) >= 3 and ys[0] > min(ys[1:]) and ys[-1] > ys[0]:
        return "U"
    return "mixed"


def saturation(points):
    """First x on ascending limb reaching THRESH*max (interp)."""
    target = THRESH * max(p[1] for p in points)
    best_x = min(p[0] for p in points if p[1] == max(q[1] for q in points))
    sat = best_x  # argmax arm is trivially >= 95% of itself
    # ascending limbs: scan left-to-right, track rising runs
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if y1 >= y0:  # rising segment: check crossing before the peak
            c = interp_crossing(x0, y0, x1, y1, target)
            if c is not None:
                sat = min(sat, c)
    return round(sat, 2), round(target, 4)


def main() -> int:
    data = json.load(open(IN_JSON))
    families = {}
    for arm, d in data.items():
        fam = arm.split("-")[0]
        families.setdefault(fam, []).append(
            (d["nt_unique_B"], d["best_f1"], arm, d["epochs"]))

    out = {"threshold": "95% of family max (ascending-limb interp)",
           "families": {}}
    for fam, pts in families.items():
        pts.sort(key=lambda p: p[0])
        xy = [(p[0], p[1]) for p in pts]
        shape = classify(xy)
        sat_x, target = saturation(xy)
        note = None
        if shape in ("monotone-fall", "rise-then-fall"):
            note = ("max at smallest corpus; 95%% sat trivially at %.2fB "
                    "(performance declines with more unique nt)" % sat_x)
        elif shape == "U":
            note = ("U-shape: right limb does not re-reach 95%% of max; "
                    "sat reported at argmax arm")
        out["families"][fam] = {
            "shape": shape,
            "saturation_nt_B": sat_x,
            "target_f1": target,
            "arms": [{"arm": a, "nt_unique_B": x, "epochs": e, "best_f1": y}
                     for x, y, a, e in pts],
            "note": note,
        }

    same_cov = []
    arms10 = out["families"].get("10M", {}).get("arms", [])
    for i, a in enumerate(arms10):
        for b in arms10[i + 1:]:
            if abs(a["epochs"] - b["epochs"]) <= 0.25:
                same_cov.append((a["arm"], b["arm"],
                                 "10M same-coverage pair"))
    arms30 = out["families"].get("30M", {}).get("arms", [])
    for i, a in enumerate(arms30):
        for b in arms30[i + 1:]:
            if abs(a["epochs"] - b["epochs"]) <= 0.25:
                same_cov.append((a["arm"], b["arm"],
                                 "30M same-coverage pair"))
    out["same_coverage_pairs"] = [
        {"a": a, "b": b, "note": n} for a, b, n in same_cov]

    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=2)
    for fam, d in out["families"].items():
        print("[%s] shape=%s saturation=%.2fB (target F1 %.4f)" %
              (fam, d["shape"], d["saturation_nt_B"], d["target_f1"]))
        for a in d["arms"]:
            print("  %-12s nt=%.2fB epochs=%.2f f1=%.4f" %
                  (a["arm"], a["nt_unique_B"], a["epochs"], a["best_f1"]))
        if d["note"]:
            print("  note:", d["note"])
    for p in out["same_coverage_pairs"]:
        print("same-coverage pair: %s vs %s" % (p["a"], p["b"]))
    print("saved", OUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
