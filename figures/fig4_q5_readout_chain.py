#!/usr/bin/env /usr/bin/python3
# Input SHA-256 (verified at runtime):
# covariation_test.json: 85f2203d74f5162f03347512ff32c7491489adca428248b66522f9956a6d7f25
# covariation_test_650M.json: f5f967cfbc8a56ae47f49189855813973565c0340cf736ecebaaaeb751d2f047
# readout_heads_650M.json: 4ab8b577685526af166569828343e1673f44dac9060720d682a34dfb3bc757df
# readout_heads_v3.json: fb9141c605529e42af13f8e1491eacea92d420fc90328cc37170bb68a2af5168
# v5_readout_head.json: 327faf62a20a21e8457f24888a679a1191e5357f1669c205050d201c262cab9b
# pair_probe_v4.json: 6e0a18a6b2c2e7367d718ccb59f2cc8780bbe823dc8f8bab68b230f76d58ca9d
# pair_probe_baseline.json: 7b69562a41a703ad8cba2ec756615344396ad71ae12b603a6a1b2bd122390458
# s7_trigram_floor.json: 05616cf87f01206a40471bff34b93e3e6c4c791164085110a1b02a5301498b01

import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

OUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/figs_v6")
EVIDENCE = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence")
INPUTS = {
    "cov": (EVIDENCE / "covariation_test.json", "85f2203d74f5162f03347512ff32c7491489adca428248b66522f9956a6d7f25"),
    "cov650": (EVIDENCE / "covariation_test_650M.json", "f5f967cfbc8a56ae47f49189855813973565c0340cf736ecebaaaeb751d2f047"),
    "heads650": (EVIDENCE / "readout_heads_650M.json", "4ab8b577685526af166569828343e1673f44dac9060720d682a34dfb3bc757df"),
    "heads_v3": (EVIDENCE / "readout_heads_v3.json", "fb9141c605529e42af13f8e1491eacea92d420fc90328cc37170bb68a2af5168"),
    "v5": (EVIDENCE / "v5_readout_head.json", "327faf62a20a21e8457f24888a679a1191e5357f1669c205050d201c262cab9b"),
    "pair": (EVIDENCE / "pair_probe_v4.json", "6e0a18a6b2c2e7367d718ccb59f2cc8780bbe823dc8f8bab68b230f76d58ca9d"),
    "pair_base": (EVIDENCE / "pair_probe_baseline.json", "7b69562a41a703ad8cba2ec756615344396ad71ae12b603a6a1b2bd122390458"),
    "trigram": (EVIDENCE / "s7_trigram_floor.json", "05616cf87f01206a40471bff34b93e3e6c4c791164085110a1b02a5301498b01"),
}
BLUE = "#0F4D92"
BLUE2 = "#3775BA"
GREEN = "#42949E"
RED = "#B64342"
GREY = "#767676"
LIGHT = "#CFCECE"
DARK = "#272727"


def load_inputs():
    loaded = {}
    for key, (path, expected) in INPUTS.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"SHA-256 mismatch for {path}: {digest}")
        loaded[key] = json.loads(path.read_text())
    return loaded


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(width=0.8, length=3)


def label_bars(ax, bars, fmt="{:.4f}", dy=0.003, fontsize=8.5):
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + dy,
                fmt.format(bar.get_height()), ha="center", va="bottom", fontsize=fontsize)


def main():
    data = load_inputs()
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "axes.linewidth": 0.9,
        "xtick.labelsize": 8.8,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(2, 3, figsize=(14.6, 8.8), facecolor="white")
    fig.subplots_adjust(hspace=0.48, wspace=0.30)
    ax_a, ax_b, ax_c, ax_d, ax_e, ax_f = axes.ravel()

    floor = data["trigram"]["per_set"]
    floor_names = ["bpRNA-TS0", "bpRNA-val", "ArchiveII"]
    floor_values = [floor[name]["trigram_floor"] for name in floor_names]
    style_axis(ax_a)
    bars = ax_a.bar(range(3), floor_values, width=0.62,
                    color=[LIGHT, "#A9A9A9", GREY], edgecolor=DARK, linewidth=0.55)
    label_bars(ax_a, bars, dy=0.004)
    ax_a.set(xticks=range(3), xticklabels=["bpRNA\nTS0", "bpRNA\nval", "ArchiveII"],
             ylim=(0.50, 0.65), ylabel="Paired-position macro-F1")
    ax_a.set_title("a  1 | Model-free composition floor", loc="left", fontweight="bold")
    ax_a.text(0.02, 0.97, "Trigram: left–center–right", transform=ax_a.transAxes,
              va="top", color=GREY, fontsize=8.7)

    cov_scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
    cov_values = [data["cov"][scale]["cov_minus_ctrl"] if scale in data["cov"]
                  else data["cov650"][scale]["cov_minus_ctrl"] for scale in cov_scales]
    style_axis(ax_b)
    ax_b.plot(range(6), cov_values, color=BLUE, lw=2.2, marker="o", ms=5.2)
    ax_b.fill_between(range(6), cov_values, color=BLUE2, alpha=0.10)
    rand_scales = ["30M", "650M"]
    rand_x = [cov_scales.index(scale) for scale in rand_scales]
    rand_values = [data["cov650"][f"{scale}_randinit17"]["cov_minus_ctrl"] for scale in rand_scales]
    ax_b.scatter(rand_x, rand_values, marker="x", s=60, lw=1.8, color=RED, zorder=5,
                 label="Random-init")
    ax_b.annotate(f"{cov_values[0]:.4f}", xy=(0, cov_values[0]), xytext=(0.02, 0.021),
                  arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8), color=DARK)
    ax_b.annotate(f"{cov_values[-1]:.4f}\n({cov_values[-1]/cov_values[3]:.1f}× the 100M value)",
                  xy=(5, cov_values[-1]), xytext=(2.75, 0.083),
                  arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.9), color=BLUE,
                  fontweight="bold")
    ax_b.text(0.05, 0.010, "randinit ≤ 0.0001", color=RED, fontsize=8.5)
    ax_b.set(xticks=range(6), xticklabels=cov_scales, ylim=(-0.003, 0.112),
             ylabel="COV − CTRL (probability difference)")
    ax_b.set_title("b  2 | Forward covariance grows with scale", loc="left", fontweight="bold")
    ax_b.legend(loc="upper left")

    head650 = data["heads650"]["models"]["650M"]
    wall_names = ["linear", "pool16", "attn", "attn_symm"]
    wall_values = [head650[name] for name in wall_names]
    wall_names.append("finetune_top2")
    wall_values.append(data["heads_v3"]["models"]["650M"]["finetune_top2"])
    style_axis(ax_c)
    bars = ax_c.bar(range(5), wall_values, width=0.65,
                    color=[GREY, BLUE2, BLUE2, BLUE, GREEN], edgecolor=DARK, linewidth=0.55)
    bars[-1].set_hatch("//")
    label_bars(ax_c, bars, dy=0.003, fontsize=8.0)
    ax_c.axhspan(0.635, 0.645, color=RED, alpha=0.10, lw=0)
    ax_c.axhline(0.640, color=RED, lw=1.0, ls="--")
    ax_c.text(0.03, 0.95, "readout wall ≈ 0.64", transform=ax_c.transAxes,
              color=RED, ha="left", va="top", fontsize=8.7, fontweight="bold")
    ax_c.set(xticks=range(5), xticklabels=["Linear", "Pool16", "Attn", "Attn\nsymm", "Top-2\nfine-tune"],
             ylim=(0.50, 0.68), ylabel="Paired-position macro-F1 (650M)")
    ax_c.set_title("c  3 | Partner-seeking readouts hit a wall", loc="left", fontweight="bold")
    dp_f1 = data["v5"]["models"]["650M"]["pair_f1_dp"]
    ax_c.text(0.02, 0.025, f"Negative result: PairNet + non-crossing DP\npair F1 = {dp_f1:.3f} (650M)",
              transform=ax_c.transAxes, ha="left", va="bottom", fontsize=8.0, color=DARK,
              bbox=dict(boxstyle="round,pad=0.35", facecolor="#F4F5F6", edgecolor=LIGHT, lw=0.7))

    oracle_scales = ["30M", "100M", "650M"]
    oracle_values = [data["heads_v3"]["models"][scale]["partner_oracle"] for scale in oracle_scales]
    style_axis(ax_d)
    bars = ax_d.bar(range(3), oracle_values, width=0.60, color=[BLUE2, BLUE, GREEN],
                    edgecolor=DARK, linewidth=0.55)
    label_bars(ax_d, bars, fmt="{:.4f}", dy=0.018)
    ax_d.set(xticks=range(3), xticklabels=oracle_scales, ylim=(0, 1.10),
             ylabel="Paired-position macro-F1")
    ax_d.set_title("d  4 | Supplying the partner removes the wall", loc="left", fontweight="bold")
    ax_d.text(0.5, 0.54, "Partner-Oracle\n(partner supplied at inference)", transform=ax_d.transAxes,
              ha="center", va="center", color=DARK, fontsize=9.2,
              bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor=LIGHT, lw=0.8))

    pair_values = [data["pair"]["models"][scale]["auc"] for scale in oracle_scales]
    prior = data["pair_base"]["modes"]["dist_ident"]
    net_values = [value - prior for value in pair_values]
    style_axis(ax_e)
    bars = ax_e.bar(range(3), pair_values, width=0.58, color=[BLUE2, BLUE, GREEN],
                    edgecolor=DARK, linewidth=0.55)
    ax_e.axhline(prior, color=RED, lw=1.5, ls="--", label=f"Model-free prior = {prior:.3f}")
    for i, (bar, value, net) in enumerate(zip(bars, pair_values, net_values)):
        ax_e.text(bar.get_x() + bar.get_width() / 2, value + 0.0015, f"{value:.3f}",
                  ha="center", va="bottom", fontsize=8.7, fontweight="bold")
        ax_e.text(i, prior - 0.003, f"net +{net:.3f}", ha="center", va="top", color=BLUE,
                  fontsize=8.7, fontweight="bold")
    ax_e.set(xticks=range(3), xticklabels=oracle_scales, ylim=(0.90, 0.966),
             ylabel="Candidate-pair AUC")
    ax_e.set_title("e  5 | Pair probe exceeds the matched prior", loc="left", fontweight="bold")
    ax_e.legend(loc="upper left")
    ax_e.text(0.02, 0.02, "Prior: distance + nucleotide identity", transform=ax_e.transAxes,
              color=GREY, fontsize=8.3)

    ax_f.set_axis_off()
    ax_f.text(0.03, 0.93, "Unified interpretation", transform=ax_f.transAxes,
              fontsize=11, fontweight="bold", color=DARK)
    ax_f.text(0.03, 0.73, "Knowledge is present.\nA pairing solver is missing.",
              transform=ax_f.transAxes, fontsize=17, fontweight="bold", color=BLUE,
              va="top", linespacing=1.35)
    chain_labels = ["Composition\nfloor", "Forward\ncovariance", "Readout\nwall", "Partner\nOracle", "Prior-corrected\npair probe"]
    chain_colors = [GREY, BLUE2, RED, GREEN, BLUE]
    for i, (label, color) in enumerate(zip(chain_labels, chain_colors)):
        y = 0.49 - i * 0.095
        ax_f.scatter([0.07], [y], s=60, color=color, transform=ax_f.transAxes, clip_on=False)
        ax_f.text(0.15, y, label, transform=ax_f.transAxes, va="center", fontsize=9.2, color=DARK)
        if i < len(chain_labels) - 1:
            ax_f.add_patch(FancyArrowPatch((0.07, y - 0.027), (0.07, y - 0.068),
                                           transform=ax_f.transAxes, arrowstyle="-|>",
                                           mutation_scale=9, lw=0.8, color=LIGHT))
    ax_f.text(0.98, 0.04, "Oracle is an upper bound,\nnot a deployable predictor.",
              transform=ax_f.transAxes, ha="right", va="bottom", fontsize=8.5, color=GREY)

    fig.suptitle("Q5 | Is structural knowledge absent, or is it inaccessible to standard readouts?",
                 x=0.055, y=0.977, ha="left", fontsize=15, fontweight="bold", color=DARK)
    fig.text(0.055, 0.943,
             "Composition floor → forward covariance → readout wall → Partner-Oracle → prior-corrected pair probe",
             ha="left", fontsize=10.5, color=GREY)
    fig.text(0.055, 0.020,
             "Controlled readout and mutation evidence (E2): pair knowledge is present, but these protocols do not solve structure prediction.  "
             "Raw pair AUC is interpreted only after subtracting the model-free prior.",
             ha="left", fontsize=9.4, color=DARK,
             bbox=dict(boxstyle="round,pad=0.55", facecolor="#F4F5F6", edgecolor=LIGHT, lw=0.8))
    fig.subplots_adjust(left=0.065, right=0.980, bottom=0.120, top=0.865, hspace=0.58, wspace=0.34)
    fig.savefig(OUT / "fig4_q5_readout_chain.png", dpi=300, facecolor="white")
    fig.savefig(OUT / "fig4_q5_readout_chain.pdf", facecolor="white")
    plt.close(fig)

    rows = []

    def add(name, value, source, note):
        rows.append({"论文数字": name, "数值": value, "来源 evidence/账本路径": str(source), "口径备注": note})

    for name, value in zip(floor_names, floor_values):
        add(f"{name} trigram floor", value, INPUTS["trigram"][0], "Model-free left-center-right composition floor; macro-F1")
    for scale, value in zip(cov_scales, cov_values):
        source = INPUTS["cov"][0] if scale in data["cov"] else INPUTS["cov650"][0]
        add(f"{scale} COV minus CTRL", value, source, "Forward paired-probability difference; n=4920")
    for scale, value in zip(rand_scales, rand_values):
        add(f"{scale} random-init COV minus CTRL", value, INPUTS["cov650"][0], "randinit17; n=4920")
    add("650M COV/100M COV ratio", f"{cov_values[-1] / cov_values[3]:.4f}", INPUTS["cov650"][0], "Ratio of COV minus CTRL values")
    for name, value in zip(wall_names, wall_values):
        source = INPUTS["heads_v3"][0] if name == "finetune_top2" else INPUTS["heads650"][0]
        add(f"650M {name} paired-position macro-F1", value, source, "Partner-seeking readout; top-2 fine-tune shown with hatch")
    add("650M PairNet plus non-crossing DP pair F1", dp_f1, INPUTS["v5"][0], "Negative result; pair-level F1, not macro-F1")
    for scale, value in zip(oracle_scales, oracle_values):
        add(f"{scale} Partner-Oracle macro-F1", value, INPUTS["heads_v3"][0], "Partner supplied at inference; upper bound")
    add("Pair-probe model-free dist+identity prior AUC", prior, INPUTS["pair_base"][0], "Distance plus nucleotide-identity baseline")
    for scale, value, net in zip(oracle_scales, pair_values, net_values):
        add(f"{scale} pair-probe AUC", value, INPUTS["pair"][0], "Candidate-pair scoring; v4")
        add(f"{scale} pair-probe net AUC over prior", f"{net:.4f}", INPUTS["pair"][0], "Raw pair AUC minus 0.922 model-free prior")
    with (OUT / "fig4_q5_readout_chain_numbers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["论文数字", "数值", "来源 evidence/账本路径", "口径备注"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote Fig.4 outputs to {OUT}")


if __name__ == "__main__":
    main()
