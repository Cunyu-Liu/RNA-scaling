#!/usr/bin/env python3
"""Fig. 1: Q1 controlled scale curve and Q2 learned-weight controls.

Input SHA-256:
  p02a_main_table.csv      e9a8da1753b88de74dab6cc9402a904c5e47c2abf34c12801b55f2d10dfb0b3d
  p02b_s1_seed_recalc.csv  d3b09aec3a5961a934aac9a07913ea5e977ae885062d172f556144be4a586307
  s4_randinit_table.json   def8d392d2d16bf41499a637ca220be4334e76b30d6738eaa0af44c40fda2e11
  s5_mommatch_table.json   20642657b53ebf2119523b7fe194574a125d35da8079d2f2459987b324ad6248
  s1_final_verdict.json    757b78ab77f2609ac294826b287d3bb6885fcb2a82e64de6d4a622800e460018
"""

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence")
MAIN = ROOT / "对账_P0_20261125/p02a_main_table.csv"
RECALC = ROOT / "对账_P0_20261125/p02b_s1_seed_recalc.csv"
RANDINIT = BACKUP / "s4_randinit_table.json"
MOMMATCH = BACKUP / "s5_mommatch_table.json"
VERDICT = BACKUP / "s1_final_verdict.json"
OUT = Path(__file__).resolve().parent / "fig1_q1q2_transfer_controls"
SCALES = ["1M", "10M", "30M", "100M", "300M", "650M"]
PARAMS_M = np.array([1, 10, 30, 100, 300, 650], dtype=float)
EXPECTED_HASHES = {
    MAIN: "e9a8da1753b88de74dab6cc9402a904c5e47c2abf34c12801b55f2d10dfb0b3d",
    RECALC: "d3b09aec3a5961a934aac9a07913ea5e977ae885062d172f556144be4a586307",
    RANDINIT: "def8d392d2d16bf41499a637ca220be4334e76b30d6738eaa0af44c40fda2e11",
    MOMMATCH: "20642657b53ebf2119523b7fe194574a125d35da8079d2f2459987b324ad6248",
    VERDICT: "757b78ab77f2609ac294826b287d3bb6885fcb2a82e64de6d4a622800e460018",
}
CAPTION = (
    "Figure 1 answers Q1 and Q2: does scale improve family-level transfer, and is the remaining gain learned in the weights? "
    "(a) Family-held-out macro-F1 under the mean-pooled linear probe at the final 2.0B-nt checkpoint. "
    "The first four pretrained points are means over training seeds s17/s29/s43 with sample-SD error bars (ddof=1); "
    "300M and 650M are open single-seed points with no uncertainty estimate. Random-initialization and moment-matched controls "
    "are dashed s17 curves. The preregistered 100M-to-650M slope is 0.0293 macro-F1 per decade, below epsilon=0.03. "
    "(b) The best-layer relative depth moves from 0.957 at 300M (L22/24 layers) to 0.296 at 650M (L8/28 layers); both are s17 observations. "
    "The controls exclude architecture and low-order weight statistics as sufficient explanations, but the layer reversal is descriptive "
    "and does not identify its mechanism."
)


def verify_inputs():
    for path, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("SHA-256 mismatch for {}: {}".format(path, actual))


def load_data():
    with MAIN.open(newline="") as handle:
        rows = {row["scale"]: row for row in csv.DictReader(handle)}
    with RECALC.open(newline="") as handle:
        recalc = list(csv.DictReader(handle))
    randinit = json.loads(RANDINIT.read_text())
    mommatch = json.loads(MOMMATCH.read_text())
    verdict = json.loads(VERDICT.read_text())

    mean = np.array([float(rows[s]["family_f1_mean"]) for s in SCALES])
    sample_sd = np.array([
        float(rows[s]["family_f1_std_sample"]) if rows[s]["family_f1_std_sample"] != "NA" else np.nan
        for s in SCALES
    ])
    rand = np.array([randinit[s]["randinit"] for s in SCALES])
    mom = np.array([mommatch[s]["mommatch"] for s in SCALES])
    slope = float(verdict["checks"]["slope_100M_650M"])
    rel_650 = float(verdict["checks"]["layer_migration_endpoint"]["650M"])

    row_300 = next(r for r in recalc if r["scale"] == "300M") if any(r["scale"] == "300M" for r in recalc) else None
    if row_300 is not None:
        raise ValueError("P0 seed-recalculation table unexpectedly contains single-seed 300M")
    rel_300 = int(rows["300M"]["best_layers"]) / (int(randinit["300M"]["n_layers"]) - 1)
    if round(rel_300, 3) != 0.957 or round(rel_650, 3) != 0.296:
        raise ValueError("Best-layer relative-depth check failed")
    if not np.allclose(mean, [0.1650, 0.1535, 0.2651, 0.3394, 0.3445, 0.3632]):
        raise ValueError("Main family-F1 values differ from P0 adjudication")
    if not np.allclose(sample_sd[:4], [0.0131, 0.0173, 0.0162, 0.0147]):
        raise ValueError("Sample-SD values differ from P0 adjudication")
    if round(slope, 4) != 0.0293:
        raise ValueError("Slope differs from P0 adjudication")
    return mean, sample_sd, rand, mom, slope, rel_300, rel_650


def style():
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 9.5,
        "axes.labelsize": 10.5,
        "axes.titlesize": 11,
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 8.4,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


def main():
    verify_inputs()
    mean, sample_sd, rand, mom, slope, rel_300, rel_650 = load_data()
    style()
    blue = "#0F4D92"
    red = "#B64342"
    teal = "#42949E"
    gray = "#4D4D4D"
    x = np.log10(PARAMS_M)

    fig = plt.figure(figsize=(10.8, 4.25))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.75, 1.0], wspace=0.28)
    ax = fig.add_subplot(grid[0, 0])
    bx = fig.add_subplot(grid[0, 1])

    ax.plot(x, mean, color=blue, lw=2.0, zorder=2)
    ax.errorbar(
        x[:4], mean[:4], yerr=sample_sd[:4], fmt="o", ms=6.2,
        color=blue, ecolor=blue, elinewidth=1.2, capsize=3.5,
        markerfacecolor=blue, markeredgecolor="white", markeredgewidth=0.7,
        zorder=4,
    )
    ax.plot(
        x[4:], mean[4:], linestyle="none", marker="o", ms=7.0,
        markerfacecolor="white", markeredgecolor=blue, markeredgewidth=1.6,
        zorder=4,
    )
    ax.plot(x, rand, "--v", color=red, lw=1.6, ms=5.0, label="Random init (s17)", zorder=3)
    ax.plot(x, mom, "--s", color=teal, lw=1.6, ms=4.8, label="Moment-matched (s17)", zorder=3)
    ax.annotate(
        "100M → 650M slope = {:.4f}\n< preregistered ε = 0.03".format(slope),
        xy=(x[5], mean[5]), xytext=(2.90, 0.405),
        arrowprops=dict(arrowstyle="->", color=gray, lw=0.9),
        fontsize=9.0, color=gray, ha="right", va="center",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(SCALES)
    ax.set_xlim(-0.14, 2.96)
    ax.set_ylim(0.075, 0.422)
    ax.set_yticks(np.arange(0.10, 0.41, 0.05))
    ax.set_xlabel("Parameters (log scale)")
    ax.set_ylabel("Family-held-out macro-F1")
    ax.set_title("Bounded scale gains survive both weight controls", pad=8)
    handles = [
        Line2D([0], [0], color=blue, lw=2.0, label="Pretrained family curve"),
        Line2D([0], [0], color=red, lw=1.6, ls="--", marker="v", ms=5, label="Random init (s17)"),
        Line2D([0], [0], color=teal, lw=1.6, ls="--", marker="s", ms=5, label="Moment-matched (s17)"),
        Line2D([0], [0], color=blue, marker="o", ms=6, lw=0, label="3 training seeds: mean ± sample SD"),
        Line2D([0], [0], color=blue, marker="o", ms=6, lw=0, markerfacecolor="white", markeredgewidth=1.4, label="Single training seed"),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.94), handletextpad=0.6, borderaxespad=0)

    y = np.array([1.0, 0.0])
    depths = np.array([rel_300, rel_650])
    bx.plot(depths, y, color="#CFCECE", lw=4.0, solid_capstyle="round", zorder=1)
    bx.scatter(depths, y, s=105, facecolors="white", edgecolors=blue, linewidths=1.8, zorder=3)
    bx.annotate("0.957\nL22 / 24 layers", (rel_300, 1), xytext=(0, 17), textcoords="offset points", ha="center", fontsize=9.2, color=blue)
    bx.annotate("0.296\nL8 / 28 layers", (rel_650, 0), xytext=(0, 18), textcoords="offset points", ha="center", fontsize=9.2, color=blue)
    bx.set_yticks(y)
    bx.set_yticklabels(["300M", "650M"])
    bx.set_ylim(-0.42, 1.48)
    bx.set_xlim(-0.04, 1.06)
    bx.set_xticks(np.arange(0, 1.01, 0.25))
    bx.set_xlabel("Best-layer relative depth")
    bx.set_title("Best-layer readout returns shallow\nat 650M (both s17)", pad=8)
    bx.text(0.5, -0.25, "Lbest / (number of layers − 1)", transform=bx.transAxes, ha="center", va="top", fontsize=8.5, color=gray)

    ax.text(-0.13, 1.03, "a", transform=ax.transAxes, fontsize=14, fontweight="bold", va="top")
    bx.text(-0.18, 1.03, "b", transform=bx.transAxes, fontsize=14, fontweight="bold", va="top")
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.19, top=0.86)
    fig.savefig(str(OUT) + ".png", dpi=300, facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print(CAPTION)
    print("Saved {}.png and {}.pdf".format(OUT, OUT))


if __name__ == "__main__":
    main()
