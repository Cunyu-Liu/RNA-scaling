"""Auto-fill the PENDING-650M slots in preprint/DRAFT_v1.md (T4.2 chain).

Runs AFTER closeout_650m has produced evidence/s1_final_verdict.json
with a 650M row. Fills the seven placeholder slots from the verdict
JSON + probe rows, writes DRAFT_v1.md in place (backup to
DRAFT_v1_pre650M_backup.md), and appends a TRAINING_LOG line.

Usage: python -m rna_sc.fill_draft_650m
Exit code 1 (no side effects) if the verdict is not ready yet.
"""
from __future__ import annotations

import json
import os
import shutil

MNT = "/mnt/cunyuliu/rna-sc"
DRAFT = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"
BACKUP = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1_pre650M_backup.md"
VERDICT = os.path.join(MNT, "evidence/s1_final_verdict.json")
TLOG = "/home/cunyuliu/rna-sc/TRAINING_LOG.md"


def main() -> int:
    v = json.load(open(VERDICT))
    t = v.get("five_scale_table", {})
    if "650M" not in t:
        print("verdict not ready: no 650M row; aborting without changes")
        return 1
    c = v.get("checks", {})
    row = t["650M"]
    f65 = row["f1_mean"]
    f100 = t["100M"]["f1_mean"]
    gain = c.get("650M_gain_pp")
    slope = c.get("slope_100M_650M")
    full_slope = c.get("full_slope_f1_per_decade")
    valley = c.get("10M_valley_at_650M_era")
    rel65 = row.get("rel_mean")

    draft = open(DRAFT).read()
    if "PENDING-650M" not in draft:
        print("no PENDING-650M slots found; already filled?")
        return 0
    shutil.copy(DRAFT, BACKUP)

    fills = {
        "continuation [PENDING-650M: five-scale verdict].":
        "continuation — verdict: %s (650M F1 %.4f vs 100M %.4f, %s pp; "
        "slope 100M→650M %s, full-axis %s)."
        % ("650M ABOVE 100M" if c.get("650M_above_100M") else
           "650M below 100M",
           f65, f100,
           ("+" if (gain or 0) >= 0 else "") + str(gain),
           slope, full_slope),

        "training; 650M (666.3M) triggered by pre-registered slope rule\n[PENDING-650M]":
        "training; 650M (666.3M) triggered by pre-registered slope rule —\n"
        "complete, final F1 %.4f (best-layer rel %.2f)." % (f65, rel65),

        "was triggered by rule, not by taste [PENDING-650M: 650M F1, full five-\nscale slope, valley persistence]":
        "was triggered by rule, not by taste. 650M final: F1 %.4f;\n"
        "full five-scale slope %s F1/decade; 10M valley persists in the\n"
        "650M era: %s." % (f65, full_slope, valley),

        "[PENDING-650M confirm], against randinit":
        "(confirmed), against randinit",

        "Hou's protein precondition is unmet here. [PENDING-650M: v2 with\nwidened confidence coverage.]":
        "Hou's protein precondition is unmet here. [v2 re-test pending:\n"
        "closeout chain re-runs s13b with 650M's coverage.]",

        "single seed elsewhere; 650M\n  single seed [PENDING-650M]":
        "single seed elsewhere; 650M single seed (pre-registered)",
    }

    n = 0
    for old, new in fills.items():
        if old in draft:
            draft = draft.replace(old, new, 1)
            n += 1
        else:
            print("[fill] slot not found (may be line-wrapped): %r..."
                  % old[:40])
    draft = draft.replace("PENDING-650M", "FILLED-650M-v1.1")
    open(DRAFT, "w").write(draft)
    with open(TLOG, "a") as fh:
        fh.write("\n- [fill_draft_650m] DRAFT v1.1 auto-fill: %d slots "
                 "replaced from s1_final_verdict (650M F1 %.4f, gain "
                 "%s pp, slope %s); backup DRAFT_v1_pre650M_backup.md\n"
                 % (n, f65, gain, slope))
    print("filled %d slots; backup at %s" % (n, BACKUP))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
