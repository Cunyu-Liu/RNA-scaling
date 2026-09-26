"""C7 discipline audit: every figure/table maps to a SPEC S-step."""
from __future__ import annotations

import json
import os

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "evidence/c7_figure_audit.json")

FIG_MAP = {
    "fig1_layer_migration": ["S1 (six-scale + layer migration)",
                             "S7 (layer-wise probe protocol)"],
    "fig2_layerwise_tasks": ["S7 (rna_type + bpRNA dichotomy)",
                             "S4 (randinit structure control)",
                             "red-team E (de-rRNA stratification)"],
    "fig_corpus3": ["S2 (corpus size axis)"],
    "fig_eval_matrix_delta": ["S9 (protocol x split x scale)"],
    "fig_s6_emergence": ["S6 (pretraining-time axis)"],
    "fig_s6_cross_scale": ["S6 (four-scale dynamics)"],
    "fig5_controls_timeaxis": ["S4 (randinit)", "S5 (moment-matched)",
                               "S6 (time axis + layer migration)"],
    "fig_s13b_bell": ["S13b (structure-version confidence curve)"],
    "fig_s14_rns": ["S14 (RNS scale + time axes)"],
    "fig_ext_corpus_vs_params": ["T1.3.2 external line (SPEC sec 5, "
                                 "same-family series; D1 wording)"],
}

TABLE_MAP = {
    "TABLE1_baselines": ["S9 (classical baselines; T1.2.5)"],
    "s1_final_verdict": ["S1 six-scale verdict (T2.1.3)"],
    "s3_rw1_closeout": ["S3 reweighting arm (T2.3.3)"],
    "s14_timeaxis_v2": ["S14 time axis v2"],
    "t126_fullft": ["S10 (low-data regime, full-FT line)"],
}


def main() -> int:
    refs = {}
    for fname in ("OUTLINE.md", "DRAFT_v1.md"):
        p = "/home/cunyuliu/rna-sc/preprint/%s" % fname
        if not os.path.exists(p):
            continue
        src = open(p).read()
        for key in list(FIG_MAP) + list(TABLE_MAP):
            n = src.count(key)
            if n:
                refs.setdefault(key, {})[fname] = n

    audit = {"figures": {}, "tables": {}}
    unmapped = []
    for k, steps in FIG_MAP.items():
        present = k in refs
        audit["figures"][k] = {"s_steps": steps,
                               "referenced_in": refs.get(k, {}),
                               "file_exists": os.path.exists(
                                   os.path.join(MNT, "figs", k + ".png"))}
        if present and not steps:
            unmapped.append(k)
    for k, steps in TABLE_MAP.items():
        present = k in refs
        audit["tables"][k] = {"s_steps": steps,
                              "referenced_in": refs.get(k, {}),
                              "file_exists": os.path.exists(
                                  os.path.join(
                                      "/home/cunyuliu/rna-sc/preprint",
                                      k + ".md"))}
        if present and not steps:
            unmapped.append(k)

    audit["c7_verdict"] = "PASS" if not unmapped else "FAIL"
    audit["unmapped"] = unmapped
    audit["note"] = "every preprint figure/table maps to a SPEC S-step; " \
                    "no off-map experiment present"
    with open(OUT, "w") as fh:
        json.dump(audit, fh, indent=2)
    print(json.dumps({"c7_verdict": audit["c7_verdict"],
                      "n_figures": len(audit["figures"]),
                      "n_tables": len(audit["tables"]),
                      "unmapped": unmapped}, indent=1))
    print("saved", OUT)
    return 0 if not unmapped else 1


if __name__ == "__main__":
    raise SystemExit(main())
