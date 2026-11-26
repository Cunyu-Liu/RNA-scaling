#!/usr/bin/python3
# Input SHA256 (verified 2026-11-25):
# s13b_bell.json: e62de08b33425738f90196a0f72f224704164d405e89556434e38af8f364e328
# s14_rns.json: a910ee7da1d4d5d7237dd4c9872582c1cb05ddb3682fea8ed789f856945e5743
# s14_rns_300m.json: 9c1d24aba4dffb0fd9068da29647e5260d002df201e122786358fd16d591860c
# s14_rns_650m.json: b46487123f78d3b25ffcb459bdaa352f654f1ac13c9d02c2b23b7ea7620cd6de
# s14_timeaxis.json: 8dc4be452cebdd640672cdf316b687322e988c5c7c7a2d53a817e3abed07ece1
# s14_timeaxis_v2.json: 2ae3673ff47a50ea5121c75271425facf7f291939a2aa7ac882337518cdd6021
# s14_rns_ext.json: f24bdefc3310677422f19242f4d647681b7b086d1b1c19f654cde313587703f7
# s14_family_crossval.json: 24fe20837edb76a837dc650bcbb820132c1d278403530eb00ae05b218e5bd1f1

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

EVIDENCE = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence")
OUTPUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/figs_v6")

BLUE = "#0F4D92"
BLUE_2 = "#3775BA"
TEAL = "#42949E"
GREEN = "#8BCF8B"
RED = "#B64342"
RED_LIGHT = "#E9A6A1"
GRAY = "#767676"
LIGHT_GRAY = "#CFCECE"
DARK = "#272727"
GOLD = "#FFD700"


def load(name):
    with (EVIDENCE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.tick_params(width=1.0, labelsize=8)


def panel_label(ax, label, title):
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", pad=8)
    ax.text(-0.16, 1.08, label, transform=ax.transAxes, fontsize=13,
            fontweight="bold", va="top", ha="left")


def main():
    rns = load("s14_rns.json")
    rns300 = load("s14_rns_300m.json")
    rns650 = load("s14_rns_650m.json")
    time10 = load("s14_timeaxis.json")
    time_large = load("s14_timeaxis_v2.json")
    ext = load("s14_rns_ext.json")
    family = load("s14_family_crossval.json")
    bell = load("s13b_bell.json")

    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 9,
        "axes.linewidth": 1.2,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.4))

    ax = axes[0, 0]
    names = [f"RNA-Sc-{scale}_s17" for scale in ["1M", "10M", "30M", "100M"]]
    values = [rns["results"][name]["RNS"]["10"] for name in names]
    values += [rns300["RNS"]["10"], rns650["RNS"]["10"]]
    params = np.array([1, 10, 30, 100, 300, 650])
    ax.plot(params, values, color=BLUE, marker="o", markersize=6, linewidth=2.2)
    for x, y in zip(params, values):
        ax.annotate(f"{y:.3f}", (x, y), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=7.5, color=DARK)
    ax.axvspan(30, 100, color=GOLD, alpha=0.20, lw=0)
    ax.text(55, 0.16, "local shoulder", ha="center", fontsize=8, color=DARK)
    ax.text(0.04, 0.05, "Randinit: 0.544–0.580", transform=ax.transAxes,
            fontsize=8, color=GRAY)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.045, 0.72)
    ax.set_xticks(params)
    ax.set_xticklabels(["1M", "10M", "30M", "100M", "300M", "650M"])
    ax.set_xlabel("Parameters (log scale)")
    ax.set_ylabel("RNS@10 (log scale; lower is tighter)")
    panel_label(ax, "a", "Scale axis: monotone decrease")
    style_axis(ax)

    ax = axes[0, 1]
    exposures = np.array([0.5, 1.0, 1.5, 1.9])
    keys = ["nt_0.5B", "nt_1.0B", "nt_1.5B", "nt_1.9B"]
    series = [
        ("10M", time10["results"], BLUE, "o"),
        ("300M", time_large["results"]["RNA-Sc-300M_s17"], TEAL, "s"),
        ("650M", time_large["results"]["RNA-Sc-650M_s17"], RED, "^"),
    ]
    for label, data, color, marker in series:
        vals = [data[key]["RNS"]["10"] for key in keys]
        ax.plot(exposures, vals, label=label, color=color, marker=marker,
                markersize=5, linewidth=2.0)
    ax.axvline(0.5, color=GRAY, linestyle="--", linewidth=1.2)
    ax.axvline(1.0, color=GOLD, linestyle=":", linewidth=2.0)
    ax.text(0.48, 0.151, "10M F1 max", rotation=90, ha="right", va="top",
            fontsize=7.5, color=GRAY)
    ax.text(1.03, 0.151, "10M RNS max", rotation=90, ha="left", va="top",
            fontsize=7.5, color=DARK)
    ax.set_xlim(0.38, 2.02)
    ax.set_ylim(0.055, 0.155)
    ax.set_xticks(exposures)
    ax.set_xlabel("Pretraining exposure (B nt)")
    ax.set_ylabel("RNS@10")
    ax.legend(loc="lower left", ncol=3, fontsize=8)
    panel_label(ax, "b", "Time axis: offset and capacity dependence")
    style_axis(ax)

    ax = axes[0, 2]
    for name, x, y in ext["pairs"]:
        is_self = name.startswith("RNA-Sc")
        ax.scatter(x, y, s=58, marker="o" if is_self else "D",
                   color=BLUE if is_self else RED, edgecolor="white",
                   linewidth=0.7, zorder=3)
        short = name.replace("RNA-Sc-", "").replace("RiNALMo-", "R-").replace("RNA-FM-96M", "RNA-FM")
        ax.annotate(short, (x, y), xytext=(5, 4), textcoords="offset points", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("RNS@10 (log scale)")
    ax.set_ylabel("Random-split family macro-F1")
    ax.set_ylim(0.04, 0.69)
    ax.text(0.04, 0.95, "Spearman ρ = −0.60 (n = 8)", transform=ax.transAxes,
            va="top", fontsize=9, fontweight="bold")
    ax.text(0.04, 0.87, "External points: observational anchors", transform=ax.transAxes,
            va="top", fontsize=7.5, color=GRAY)
    ax.scatter([], [], marker="o", color=BLUE, label="Controlled family")
    ax.scatter([], [], marker="D", color=RED, label="External models")
    ax.legend(loc="lower left", fontsize=8)
    panel_label(ax, "c", "Cross-model axis: model-level association")
    style_axis(ax)

    ax = axes[1, 0]
    for fam, row in family["families"].items():
        ax.scatter(row["rns_30M"], row["probe_f1"], s=58, color=BLUE_2,
                   edgecolor="white", linewidth=0.7, zorder=3)
        ax.annotate(fam, (row["rns_30M"], row["probe_f1"]), xytext=(5, 4),
                    textcoords="offset points", fontsize=7.5)
    ax.set_xlim(-0.02, 0.68)
    ax.set_ylim(-0.06, 1.06)
    ax.set_xlabel("Family RNS@10 at 30M")
    ax.set_ylabel("Family probe macro-F1")
    ax.text(0.04, 0.95, "Spearman ρ = −0.19", transform=ax.transAxes,
            va="top", fontsize=9, fontweight="bold")
    ax.text(0.04, 0.87, "Weak within-model relation", transform=ax.transAxes,
            va="top", fontsize=8, color=GRAY)
    panel_label(ax, "d", "Family axis: organization ≠ usefulness")
    style_axis(ax)

    ax = axes[1, 1]
    ax.text(0.5, 0.62, "WITHDRAWN", transform=ax.transAxes,
            ha="center", va="center", fontsize=14, fontweight="bold", color=RED)
    ax.text(0.5, 0.43,
            "Pair-index misalignment + unseeded heads\n"
            "No bin-direction or axis-dependent claim\n"
            "Historical values: Appendix A only",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=9, color=DARK, linespacing=1.6)
    ax.set_xticks([])
    ax.set_yticks([])
    panel_label(ax, "e", "Sequence bins: historical analysis withdrawn")
    style_axis(ax)

    ax = axes[1, 2]
    trained = [p for p in bell["points"] if "randinit" not in p["model"]]
    model_order = ["1M", "10M", "30M", "100M", "300M", "650M"]
    colors = [BLUE, BLUE_2, TEAL, GREEN, GRAY, RED]
    for scale, color in zip(model_order, colors):
        pts = [p for p in trained if f"-{scale}_" in p["model"]]
        ax.scatter([p["nll"] for p in pts], [p["f1"] for p in pts], s=32,
                   color=color, edgecolor="white", linewidth=0.5, label=scale, zorder=3)
    nll = np.array([p["nll"] for p in trained])
    coeffs = bell["bell_test"]["quad_coeffs"]
    vertex = bell["bell_test"]["peak_x_nll"]
    x_obs = np.linspace(nll.min(), nll.max(), 200)
    x_extra = np.linspace(nll.max(), vertex, 100)
    ax.plot(x_obs, np.polyval(coeffs, x_obs), color=RED, linewidth=1.8,
            label="Quadratic fit")
    ax.plot(x_extra, np.polyval(coeffs, x_extra), color=RED, linewidth=1.8,
            linestyle="--", label="Extrapolation")
    ax.axvline(vertex, color=RED, linestyle=":", linewidth=1.5)
    ax.text(vertex - 0.012, 0.37, "vertex 1.7201", rotation=90, ha="right",
            fontsize=7.5, color=RED)
    ax.set_xlim(0.98, 1.79)
    ax.set_ylim(0.32, 0.75)
    ax.set_xlabel("Masked NLL")
    ax.set_ylabel("Structure macro-F1")
    ax.text(0.03, 0.05,
            "NOT-BELL (pre-registered)\nv1: n = 30; vertex 1.745 outside data\nv2: n = 36; vertex outside [1.025, 1.3872]",
            transform=ax.transAxes, fontsize=7.5, va="bottom",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "#F6CFCB", "edgecolor": RED_LIGHT})
    ax.legend(loc="upper left", ncol=4, fontsize=7, columnspacing=0.9, handletextpad=0.4)
    panel_label(ax, "f", "Confidence axis: fitted peak outside data")
    style_axis(ax)

    fig.suptitle("Representation organization and confidence do not substitute for downstream evaluation",
                 fontsize=14, fontweight="bold", y=0.995)
    fig.text(0.5, 0.005,
             "RNS: lower = tighter real-pool organization  |  Sequence-bin result withdrawn; mechanism unresolved  |  Both S13b versions: NOT-BELL",
             ha="center", fontsize=9, color=DARK)
    fig.tight_layout(rect=[0.015, 0.03, 0.995, 0.97], h_pad=3.0, w_pad=2.5)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig6_crosscut.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUTPUT / "fig6_crosscut.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUTPUT / "fig6_crosscut.png")
    print(OUTPUT / "fig6_crosscut.pdf")


if __name__ == "__main__":
    main()
