#!/usr/bin/env python3
# Reproduce Figure 2 for sec43_q3.md with /usr/bin/python3 (Python 3.9).
# Inputs and SHA-256 at authoring time:
# /Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125/p03_baseline_table.csv
#   29a2fceaa9bc3eb0b367f7bb1a6d468ccb7f9351e10ee1246a252b51a403bc0a
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/eval_matrix_v1_delta.json
#   8765ce0429d316e20e3b02d266176b65ed7e2bd5810977aeaca3f455d1801e9f
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/s4x9_leakage_attribution.json
#   0e574ec3de936b274714a0d849fe1f9efe71efa21c258e92d33b44aef585d463
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/classical_baselines.json
#   9206f1913f7916eb8eebd5415b8e5c26ed66a96ac0d53ceb8436238d1e9469ce
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/classical_baselines_extra.json
#   5cd78151a95336edf6ab449ea999eb8ec253239e5ba78f49b1d0cbaf3428e941
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/classical_baselines_extra_s29.json
#   fae90a7f4810ba9d6221c6131a8f559a4f38a7aab457af7df14faef582b986ee
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/classical_baselines_extra_s43.json
#   acd23d17fb724d3405d2bcb13afa6fe720f502229df857bfc287058dea5247b7
# /Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs/evidence/ext_full_layers.json
#   c582f2e710874f00340e173feeaafb3bf1e0cffeaf2ebdde88aa60705fdc810c

import csv
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
EVIDENCE = BACKUP / "eval_evidence_logs" / "evidence"
OUT = ROOT / "figs_v6"

INPUTS = {
    "baseline_table": (ROOT / "对账_P0_20261125" / "p03_baseline_table.csv", "29a2fceaa9bc3eb0b367f7bb1a6d468ccb7f9351e10ee1246a252b51a403bc0a"),
    "delta": (EVIDENCE / "eval_matrix_v1_delta.json", "8765ce0429d316e20e3b02d266176b65ed7e2bd5810977aeaca3f455d1801e9f"),
    "attribution": (EVIDENCE / "s4x9_leakage_attribution.json", "0e574ec3de936b274714a0d849fe1f9efe71efa21c258e92d33b44aef585d463"),
    "kmer": (EVIDENCE / "classical_baselines.json", "9206f1913f7916eb8eebd5415b8e5c26ed66a96ac0d53ceb8436238d1e9469ce"),
    "extra17": (EVIDENCE / "classical_baselines_extra.json", "5cd78151a95336edf6ab449ea999eb8ec253239e5ba78f49b1d0cbaf3428e941"),
    "extra29": (EVIDENCE / "classical_baselines_extra_s29.json", "fae90a7f4810ba9d6221c6131a8f559a4f38a7aab457af7df14faef582b986ee"),
    "extra43": (EVIDENCE / "classical_baselines_extra_s43.json", "acd23d17fb724d3405d2bcb13afa6fe720f502229df857bfc287058dea5247b7"),
    "external": (EVIDENCE / "ext_full_layers.json", "c582f2e710874f00340e173feeaafb3bf1e0cffeaf2ebdde88aa60705fdc810c"),
}

for path, expected_hash in INPUTS.values():
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(f"Input hash mismatch: {path}\nexpected {expected_hash}\nactual   {actual_hash}")

scales = ["1M", "10M", "30M", "100M", "300M", "650M"]
x = np.array([1, 10, 30, 100, 300, 650], dtype=float)
delta_data = json.loads(INPUTS["delta"][0].read_text(encoding="utf-8"))["deltas"]
attribution = json.loads(INPUTS["attribution"][0].read_text(encoding="utf-8"))["table"]
kmer = json.loads(INPUTS["kmer"][0].read_text(encoding="utf-8"))
extra = [json.loads(INPUTS[key][0].read_text(encoding="utf-8")) for key in ("extra17", "extra29", "extra43")]
external = json.loads(INPUTS["external"][0].read_text(encoding="utf-8"))["models"]
with INPUTS["baseline_table"][0].open(encoding="utf-8", newline="") as handle:
    baseline_rows = {row["scale"]: row for row in csv.DictReader(handle)}

balanced_delta = [delta_data[f"RNA-Sc-{scale}_s17|probe-balanced"]["delta"] for scale in scales]
meanpool_delta = [delta_data[f"RNA-Sc-{scale}_s17|probe-meanpool"]["delta"] for scale in scales]
balanced_family = [delta_data[f"RNA-Sc-{scale}_s17|probe-balanced"]["family"] for scale in scales]
observed_margin = [float(baseline_rows[scale]["delta_lm_minus_strongest_observed"]) for scale in scales]
strict_margin = [float(baseline_rows[scale]["delta_lm_minus_strict_seed_coverage"]) for scale in scales]

cnn_family_values = [row["family"]["onehot_cnn"]["f1_macro"] for row in extra]
cnn_family_mean = statistics.mean(cnn_family_values)
cnn_family_sd = statistics.stdev(cnn_family_values)
logistic_family = kmer["family"]["f1_macro"]
lgbm_family = extra[0]["family"]["kmer_lgbm"]["f1_macro"]
kmer_delta = kmer["delta_random_family"]

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "axes.linewidth": 1.4,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})
colors = {
    "blue": "#0F4D92",
    "blue2": "#3775BA",
    "green": "#42949E",
    "red": "#B64342",
    "pink": "#E9A6A1",
    "gray": "#767676",
    "light_gray": "#CFCECE",
    "violet": "#9A4D8E",
}

fig, axes = plt.subplots(2, 2, figsize=(15.5, 10.5))
ax_a, ax_b, ax_c, ax_d = axes.ravel()

ax_a.axhline(kmer_delta, color=colors["green"], linewidth=9, alpha=0.14, zorder=0)
ax_a.axhline(kmer_delta, color=colors["green"], linestyle="--", linewidth=1.6, label=f"k-mer logistic ({kmer_delta:+.4f})")
ax_a.plot(x, balanced_delta, color=colors["blue"], marker="o", linewidth=2.4, markersize=6, label="Balanced LM")
ax_a.plot(x, meanpool_delta, color=colors["red"], marker="s", linewidth=2.0, markersize=5.5, label="Mean-pool LM")
ax_a.axhline(0, color=colors["gray"], linewidth=0.9)
ax_a.set_xscale("log")
ax_a.set_xticks(x, scales)
ax_a.set_xlabel("Parameters")
ax_a.set_ylabel(r"$\Delta_{split}$ = random $-$ family macro-F1")
ax_a.set_title("a  Family-overlap dividend by readout", loc="left", fontweight="bold")
ax_a.set_ylim(-0.065, 0.49)
ax_a.legend(loc="lower right", fontsize=9)
ax_a.annotate("post-30M plateau", xy=(300, 0.425), xytext=(55, 0.465), arrowprops={"arrowstyle": "->", "color": colors["gray"]}, color=colors["gray"], fontsize=9)

positions = np.arange(10)
ax_b.plot(positions[:6], balanced_family, color=colors["blue"], marker="o", linewidth=2.4, markersize=6, label="RNA-Sc, balanced s17")
ax_b.hlines(logistic_family, -0.4, 5.4, color=colors["green"], linestyle="--", linewidth=1.6, label=f"k-mer logistic ({logistic_family:.4f})")
ax_b.hlines(lgbm_family, -0.4, 5.4, color=colors["red"], linestyle="-.", linewidth=1.6, label=f"k-mer LightGBM s17 ({lgbm_family:.4f})")
ax_b.fill_between([-0.4, 5.4], cnn_family_mean - cnn_family_sd, cnn_family_mean + cnn_family_sd, color=colors["light_gray"], alpha=0.45)
ax_b.hlines(cnn_family_mean, -0.4, 5.4, color=colors["gray"], linestyle=":", linewidth=1.8, label="one-hot CNN, three-seed mean ± SD")
external_names = ["RiNALMo-micro v1(=s17)", "RiNALMo-mega s17", "RiNALMo-giga s17", "RNA-FM-96M s17"]
external_values = [external[name]["best_f1"] for name in external_names]
ax_b.scatter(positions[6:], external_values, marker="D", s=52, facecolor="white", edgecolor=colors["gray"], linewidth=1.6, zorder=4, label="External observational anchors")
ax_b.axvline(5.6, color=colors["light_gray"], linewidth=1.1)
ax_b.text(7.5, 0.315, "unaudited pretraining overlap", ha="center", color=colors["gray"], fontsize=8.5)
ax_b.set_xticks(positions, ["1M", "10M", "30M", "100M", "300M", "650M", "R-micro", "R-mega", "R-giga", "RNA-FM"], rotation=25, ha="right")
ax_b.set_ylabel("Family-held-out macro-F1")
ax_b.set_title("b  Balanced family world and composition floor", loc="left", fontweight="bold")
ax_b.set_ylim(0.04, 0.335)
ax_b.legend(loc="lower right", fontsize=8.2, ncol=2)

ax_c.axhline(0, color=colors["gray"], linewidth=1.0)
ax_c.plot(x, observed_margin, color=colors["blue"], marker="o", linewidth=2.4, markersize=6, label="LM − LightGBM s17 (primary)")
ax_c.plot(x, strict_margin, color=colors["green"], marker="s", markerfacecolor="white", linewidth=1.8, markersize=5.5, label="Strict seed-coverage contrast")
balanced_sensitivity = balanced_family[3] - lgbm_family
ax_c.scatter([100], [balanced_sensitivity], marker="X", s=90, color=colors["red"], zorder=5, label="100M balanced s17 sensitivity")
ax_c.annotate(f"{balanced_sensitivity:+.4f}", xy=(100, balanced_sensitivity), xytext=(115, 0.035), color=colors["red"], fontsize=9, arrowprops={"arrowstyle": "->", "color": colors["red"]})
ax_c.set_xscale("log")
ax_c.set_xticks(x, scales)
ax_c.set_xlabel("Parameters")
ax_c.set_ylabel("LM − classical baseline, family macro-F1")
ax_c.set_title("c  Family-world margin is protocol-dependent", loc="left", fontweight="bold")
ax_c.set_ylim(-0.05, 0.215)
ax_c.legend(loc="upper left", fontsize=8.5)

trained_10 = attribution["RNA-Sc-10M_s17"]["delta"]
trained_100 = attribution["RNA-Sc-100M_s17"]["delta"]
bar_labels = ["Trained LM, 10M", "Randinit, 10M", "Mommatch, 10M", "k-mer logistic / 10M", "Trained LM, 100M", "Randinit, 100M", "k-mer logistic / 100M"]
bar_values = [100.0, 100 * attribution["RNA-Sc-10M_s17_randinit17"]["delta"] / trained_10, 100 * attribution["RNA-Sc-10M_s17_mommatch17"]["delta"] / trained_10, 100 * kmer_delta / trained_10, 100.0, 100 * attribution["RNA-Sc-100M_s17_randinit17"]["delta"] / trained_100, 100 * kmer_delta / trained_100]
bar_colors = [colors["blue"], colors["pink"], colors["violet"], colors["green"], colors["blue"], colors["pink"], colors["green"]]
ypos = np.arange(len(bar_labels))
ax_d.barh(ypos, bar_values, color=bar_colors, edgecolor="#272727", linewidth=0.7, height=0.68)
ax_d.axvline(100, color=colors["gray"], linestyle="--", linewidth=1.0)
for y, value in zip(ypos, bar_values):
    ax_d.text(value + 2, y, f"{value:.1f}%", va="center", fontsize=9)
ax_d.set_yticks(ypos, bar_labels)
ax_d.invert_yaxis()
ax_d.set_xlim(0, 120)
ax_d.set_xlabel("Trained balanced split dividend recovered (%)")
ax_d.set_title("d  S4 × S9 attribution triangle", loc="left", fontweight="bold")
ax_d.text(3, 6.75, "Ratios use each scale's trained dividend; k-mer F1 is shared across scales.", fontsize=8.3, color=colors["gray"])

fig.suptitle("Family overlap is composition-readable; family-held-out gains depend on readout", fontsize=15, fontweight="bold", y=0.995)
fig.tight_layout(pad=2.0, rect=(0, 0, 1, 0.965))
OUT.mkdir(parents=True, exist_ok=True)
png_path = OUT / "fig2_q3_dualworld.png"
pdf_path = OUT / "fig2_q3_dualworld.pdf"
fig.savefig(png_path, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.08)
fig.savefig(pdf_path, facecolor="white", bbox_inches="tight", pad_inches=0.08)
plt.close(fig)
print(f"wrote {png_path}")
print(f"wrote {pdf_path}")
