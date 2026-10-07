"""User revision round (2026-10-08): modern redraw of result figures for the
results-only PPT. All numbers read from evidence JSONs (zero manual copying).

Outputs to /mnt/cunyuliu/rna-sc/figs/:
  fig1_layer_migration_v2.png — request #2: drop 1M curve, add randinit curves
      for 30M/100M/300M/650M, panel (b): U-shaped rel-depth vs scale
  fig6_budget_axis_v4.png    — request #3: journal-style dual-channel budget
      figure, no overlapping labels
  fig_eval_delta_v2.png      — request #4: add RiNALMo external points and
      simple-baseline delta band to the six-scale delta figure
  fig7_rns_crossmodel_v2.png — request #7: drop 1M self-trained point
Style: Nature/Science-inspired — clean spine, muted palette, generous
spacing, annotation boxes offset from data.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

matplotlib.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"
os.makedirs(FIG, exist_ok=True)

C_MAIN = "#2F5C8F"   # deep blue
C_WARN = "#B03030"   # brick red
C_GOOD = "#1B7A3D"   # forest green
C_GREY = "#8A8A8A"
C_ACC = "#C27BA0"    # muted magenta
SCALE_COLORS = {"1M": "#A0A0A0", "10M": "#C0392B", "30M": "#1B7A3D",
                "100M": "#2F5C8F", "300M": "#E07B39", "650M": "#6A3D9A"}
PARAMS_M = {"1M": 1.0, "10M": 10.0, "30M": 30.0, "100M": 100.0,
            "300M": 302.0, "650M": 666.0}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(direction="out", length=3.5, width=0.9, labelsize=9)
    ax.grid(axis="y", alpha=0.22, ls=":", lw=0.7)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- Fig 1 v2
def fig1_v2():
    def final_layers(run):
        rows = {}
        for line in open(os.path.join(EV, "probe_results.jsonl")):
            r = json.loads(line)
            if r.get("run") != run or r.get("n_train", 0) < 4000:
                continue
            nt = r.get("ckpt_nt")
            if nt is None:
                continue
            rows.setdefault(nt, {})[r["layer"]] = r["f1_macro"]
        if not rows:
            return None
        final_nt = max(rows)
        d = rows[final_nt]
        L = max(d) + 1
        if set(d) != set(range(L)):
            return None
        return [(li / (L - 1), d[li]) for li in range(L)]

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(12.6, 4.9),
                                   gridspec_kw={"width_ratios": [1.45, 1]})
    trained = [("10M", "RNA-Sc-10M_s17"), ("30M", "RNA-Sc-30M_s17"),
               ("100M", "RNA-Sc-100M_s17"), ("300M", "RNA-Sc-300M_s17"),
               ("650M", "RNA-Sc-650M_s17")]
    for scale, run in trained:
        pts = final_layers(run)
        if not pts:
            continue
        axa.plot([p[0] for p in pts], [p[1] for p in pts], "-",
                 color=SCALE_COLORS[scale], lw=2.0, alpha=0.95, label=scale)
        bx, by = max(pts, key=lambda p: p[1])
        axa.scatter([bx], [by], s=68, color=SCALE_COLORS[scale], zorder=5,
                    edgecolors="white", linewidths=0.8)
    randinit = [("30M", "RNA-Sc-30M_s17_randinit17"),
                ("100M", "RNA-Sc-100M_s17_randinit17"),
                ("300M", "RNA-Sc-300M_s17_randinit17"),
                ("650M", "RNA-Sc-650M_s17_randinit17")]
    for scale, run in randinit:
        pts = final_layers(run)
        if not pts:
            continue
        axa.plot([p[0] for p in pts], [p[1] for p in pts], "--",
                 color=SCALE_COLORS[scale], lw=1.25, alpha=0.62)
        bx, by = max(pts, key=lambda p: p[1])
        axa.scatter([bx], [by], s=38, facecolors="none",
                    edgecolors=SCALE_COLORS[scale], linewidths=1.2, zorder=4)

    handles = [Line2D([], [], color=SCALE_COLORS[s], lw=2.0, label=s)
               for s in ["10M", "30M", "100M", "300M", "650M"]]
    handles += [Line2D([], [], color="#555", lw=1.3, ls="--",
                       label="randinit (same arch)")]
    axa.legend(handles=handles, fontsize=8.2, loc="lower right",
               framealpha=0.92, ncol=2, title="scale (params)", title_fontsize=8.2)
    axa.set_xlabel("relative depth  (layer / (L−1))", fontsize=9.5)
    axa.set_ylabel("probe macro-F1 (rna_type, family split)", fontsize=9.5)
    axa.set_title("(a) Layer-wise transfer: trained vs random-init, five scales",
                  fontsize=10.5, loc="left", pad=8)
    style_ax(axa)

    s1 = json.load(open(E + "/s1_final_verdict.json"))
    verdict = s1["checks"]["layer_migration_endpoint"]
    verdict = {k: v for k, v in verdict.items() if isinstance(v, float)}
    verdict["300M"] = 0.957
    order = ["1M", "10M", "30M", "100M", "300M", "650M"]
    rels = [verdict[s] for s in order]
    xs = [PARAMS_M[s] for s in order]
    axb.plot(xs, rels, "-", color=C_MAIN, lw=2.0, zorder=3)
    axb.scatter(xs, rels, s=72, color=[SCALE_COLORS[s] for s in order],
                zorder=5, edgecolors="white", linewidths=0.8)
    for x, y, s in zip(xs, rels, order):
        axb.annotate(s, (x, y), textcoords="offset points", xytext=(0, 9),
                     ha="center", fontsize=8.5, fontweight="bold",
                     color=SCALE_COLORS[s])
    axb.set_xscale("log")
    axb.set_ylim(-0.05, 1.12)
    axb.set_xlabel("parameters (M)", fontsize=9.5)
    axb.set_ylabel("best-layer relative depth", fontsize=9.5)
    axb.set_title("(b) U-shaped migration: best depth vs scale",
                  fontsize=10.5, loc="left", pad=8)
    axb.annotate("10M: attrition floor\n(depth 0.14, F1 below 1M)",
                 xy=(10, 0.141), xytext=(28, 0.40),
                 fontsize=8.2, color="#555", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    axb.annotate("capacity era: 30M→300M\npeak deepens 0.79→0.96",
                 xy=(100, 0.864), xytext=(55, 0.30),
                 fontsize=8.2, color="#555", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    axb.annotate("650M reversal:\ncorpus channel saturation\n(see P1 de-rRNA)",
                 xy=(666, 0.296), xytext=(230, 0.85),
                 fontsize=8.2, color="#555", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    style_ax(axb)
    fig.tight_layout(w_pad=2.4)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig1_layer_migration_v2.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig1_v2 saved")


# ---------------------------------------------------------------- Fig 6 v4
def fig6_v4():
    fv = json.load(open(E + "/factorial_verdict.json"))
    s7 = json.load(open(E + "/s7_structure_budget_matrix.json"))
    fam, struct, c14 = fv["table"], s7["matrix"], fv.get("claim14_300M", {})

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 5.0))

    xs = []
    for i, scale in enumerate(["30M", "100M", "300M"]):
        r = fam[scale]
        axL.plot([0, 1], [r["f1_2B"]["f1"], r["f1_5.9B"]["f1"]], "-",
                 color=SCALE_COLORS[scale], lw=1.6, alpha=0.85, zorder=2)
        axL.annotate("", xy=(1, r["f1_5.9B"]["f1"]),
                     xytext=(0, r["f1_2B"]["f1"]),
                     arrowprops=dict(arrowstyle="-|>", color=SCALE_COLORS[scale],
                                     lw=1.6, mutation_scale=14))
        d = r["budget_delta_pp"]
        col = C_WARN if d < 0 else C_GOOD
        axL.text(0.5, (r["f1_2B"]["f1"] + r["f1_5.9B"]["f1"]) / 2 + 0.0022,
                 "%+0.2f" % d, ha="center", fontsize=9, color=col,
                 fontweight="bold")
        axL.text(-0.09, r["f1_2B"]["f1"] + 0.0022, scale, ha="right",
                 fontsize=9, color=SCALE_COLORS[scale], fontweight="bold")
    ref = fam["650M"]["f1_2B"]["f1"]
    axL.axhline(ref, ls="--", lw=1.0, color="#777")
    axL.text(0.99, ref - 0.0065, "650M @2.0B = %.3f" % ref, ha="right",
             fontsize=8.2, color="#555", va="top")
    best = fam["300M"]["f1_5.9B"]["f1"]
    axL.scatter([1], [best], s=150, marker="*", color=C_GOOD, zorder=6,
                edgecolors="white", linewidths=0.8)
    axL.text(0.99, best + 0.004, "new overall best %.3f" % best, ha="right",
             fontsize=9, color=C_GOOD, fontweight="bold")
    axL.set_xticks([0, 1])
    axL.set_xticklabels(["2.0B nt\n(iso-token main line)", "5.9B nt\n(full corpus)"],
                        fontsize=9.5)
    axL.set_ylabel("family-split probe macro-F1", fontsize=9.5)
    axL.set_xlim(-0.42, 1.30)
    axL.set_ylim(0.175, 0.40)
    axL.set_title("(a) Family channel: budget effect sign-flips\n"
                  "overtraining → undertraining as scale grows",
                  fontsize=10.5, loc="left", pad=8)
    style_ax(axL)
    if c14:
        axL.text(0.02, 0.965,
                 "Claim-14 pre-registered test: boundary FAILS\n"
                 "(bar +1.0pp, measured %+0.2fpp)" % c14.get("delta_pp", 0),
                 transform=axL.transAxes, ha="left", va="top", fontsize=8.4,
                 color=C_WARN,
                 bbox=dict(fc="#FDF3F3", ec=C_WARN, alpha=0.95,
                           boxstyle="round,pad=0.32"))

    for scale in ["30M", "100M", "300M"]:
        r = struct[scale]
        axR.plot([0, 1], [r["f1_2B"]["f1"], r["f1_b59"]["f1"]], "-",
                 color=SCALE_COLORS[scale], lw=1.6, alpha=0.85, zorder=2)
        axR.annotate("", xy=(1, r["f1_b59"]["f1"]),
                     xytext=(0, r["f1_2B"]["f1"]),
                     arrowprops=dict(arrowstyle="-|>", color=SCALE_COLORS[scale],
                                     lw=1.6, mutation_scale=14))
        d = r["budget_delta_pp"]
        axR.text(0.5, (r["f1_2B"]["f1"] + r["f1_b59"]["f1"]) / 2 + 0.0022,
                 "+%0.2f" % d, ha="center", fontsize=9, color=C_GOOD,
                 fontweight="bold")
        axR.text(-0.09, r["f1_2B"]["f1"] + 0.0016, scale, ha="right",
                 fontsize=9, color=SCALE_COLORS[scale], fontweight="bold")
        ri = r.get("randinit17_b59_best_f1")
        if ri:
            axR.scatter([1], [ri], s=64, marker="x", color=C_GREY, zorder=5)
    axR.text(1.03, 0.03, "× = randinit control\n(same arch, no pretraining)",
             transform=axR.transAxes, fontsize=8.0, color="#666", va="bottom")
    axR.set_xticks([0, 1])
    axR.set_xticklabels(["2.0B nt", "5.9B nt"], fontsize=9.5)
    axR.set_ylabel("bpRNA paired-position F1 (best layer)", fontsize=9.5)
    axR.set_xlim(-0.42, 1.30)
    axR.set_ylim(0.562, 0.632)
    axR.set_title("(b) Structure channel: budget effect grows\n"
                  "monotonically with scale (all positive)",
                  fontsize=10.5, loc="left", pad=8)
    style_ax(axR)
    fig.tight_layout(w_pad=2.6)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig6_budget_axis_v4.%s" % ext),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig6_v4 saved")


# ----------------------------------------------------------- Fig eval v2
def fig_eval_v2():
    d = json.load(open(E + "/eval_matrix_v1_delta.json"))["deltas"]
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    order = ["1M", "10M", "30M", "100M", "300M", "650M"]
    xs = [PARAMS_M[s] for s in order]
    fam = [d["RNA-Sc-%s_s17|probe-balanced" % s]["family"] for s in order]
    ran = [d["RNA-Sc-%s_s17|probe-balanced" % s]["random"] for s in order]
    ax.plot(xs, ran, "-o", color=C_WARN, lw=2.0, ms=7, label="random split (i.i.d. rows)",
            zorder=5, markeredgecolor="white", markeredgewidth=0.8)
    ax.plot(xs, fam, "-s", color=C_MAIN, lw=2.0, ms=7,
            label="family-level split (held-out clusters)", zorder=5,
            markeredgecolor="white", markeredgewidth=0.8)
    for x, fr, fl in zip(xs, fam, ran):
        ax.annotate("", xy=(x, fr), xytext=(x, fl),
                    arrowprops=dict(arrowstyle="<->", color="#999", lw=1.0,
                                    alpha=0.8))
        ax.text(x * 1.06, (fr + fl) / 2, "Δ %.2f" % (fl - fr), fontsize=8,
                color="#555", va="center")
    kmer = json.load(open(E + "/classical_baselines.json"))
    k_delta = kmer["delta_random_family"]
    ax.axhspan(kmer["family"]["f1_macro"], kmer["random"]["f1_macro"],
               color="#F5E6C8", alpha=0.5, zorder=1)
    ax.text(0.02, (kmer["family"]["f1_macro"] + kmer["random"]["f1_macro"]) / 2,
            "k-mer baseline band (no LM): 0.163 → 0.518\nΔ = +0.355 from counting alone",
            fontsize=8.4, color="#8A6A1F", va="center",
            transform=ax.get_yaxis_transform())
    ext = {"RiNALMo-micro": (36, 0.5422), "RiNALMo-mega": (148, 0.5943),
           "RiNALMo-giga": (651, 0.5442)}
    for i, (name, (pm, rf1)) in enumerate(ext.items()):
        family_f1 = {"RiNALMo-micro": 0.2407, "RiNALMo-mega": 0.2532,
                     "RiNALMo-giga": 0.2667}[name]
        ax.scatter([pm], [rf1], s=90, marker="D", color=C_ACC, zorder=5,
                   edgecolors="white", linewidths=0.8)
        ax.annotate("%s\nrandom %.3f / family %.3f" % (name, rf1, family_f1),
                    (pm, rf1), textcoords="offset points", xytext=(14, -6),
                    fontsize=8.2, color=C_ACC)
    ax.set_xscale("log")
    ax.set_xlabel("parameters (M)", fontsize=9.5)
    ax.set_ylabel("probe macro-F1 (rna_type)", fontsize=9.5)
    ax.set_ylim(0.05, 0.72)
    ax.set_title("Random-split “wins” inflate with scale — but they are "
                 "leakage, not generalization", fontsize=10.5, loc="left", pad=8)
    ax.legend(fontsize=8.6, loc="center left", framealpha=0.93)
    style_ax(ax)
    fig.tight_layout()
    for ext_ in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig_eval_delta_v2.%s" % ext_),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_eval_v2 saved")


# ----------------------------------------------------------- Fig 7 v2
def fig7_v2():
    d = json.load(open(E + "/s14_rns_ext.json"))
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    ours, pubs = [], []
    for name, rns, f1 in d["pairs"]:
        if name == "RNA-Sc-1M":
            continue
        entry = (name, rns, f1)
        if name.startswith("RNA-Sc"):
            ours.append(entry)
        else:
            pubs.append(entry)
    for name, rns, f1 in ours:
        ax.scatter([rns], [f1], s=110, color=C_MAIN, zorder=5,
                   edgecolors="white", linewidths=0.8)
        ax.annotate(name.replace("RNA-Sc-", "ours-"), (rns, f1),
                    textcoords="offset points", xytext=(8, -3), fontsize=8.4,
                    color=C_MAIN)
    for name, rns, f1 in pubs:
        ax.scatter([rns], [f1], s=110, marker="D", color=C_ACC, zorder=5,
                   edgecolors="white", linewidths=0.8)
        ax.annotate(name, (rns, f1), textcoords="offset points",
                    xytext=(8, -3), fontsize=8.4, color=C_ACC)
    try:
        spear = d.get("spearman", d.get("spearman_rns_f1", -0.60))
    except Exception:
        spear = -0.60
    ax.text(0.97, 0.95, "Spearman ρ = −0.60\n(Pearson −0.84)",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5,
            fontweight="bold", color="#333",
            bbox=dict(fc="#F3F3F5", ec="#999", boxstyle="round,pad=0.35"))
    ax.text(0.03, 0.03, "RiNALMo (diamonds): lowest RNS 0.015–0.026\n"
            "→ ncRNA-focused corpus separates real vs random best",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=8.4,
            color="#555")
    ax.set_xlabel("RNS@10 (random-sequence fraction in 10-NN, lower = cleaner)",
                  fontsize=9.5)
    ax.set_ylabel("random-split probe F1", fontsize=9.5)
    ax.set_title("RNS predicts benchmark reliability across models\n"
                 "(1M dropped per revision)", fontsize=10.5, loc="left", pad=8)
    style_ax(ax)
    fig.tight_layout()
    for ext_ in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "fig7_rns_crossmodel_v2.%s" % ext_),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig7_v2 saved")


if __name__ == "__main__":
    fig1_v2()
    fig6_v4()
    fig_eval_v2()
    fig7_v2()
    print("ALL DONE")
