#!/usr/bin/python3
"""Regenerate Figure 5: corpus- and budget-gated knowledge supply (Q6).

Run: /usr/bin/python3 figs_v6/fig5_q6_supply.py
All source paths are absolute; outputs are PNG (300 dpi) and PDF.

Input SHA-256:
  p02c_factorial_table.csv: 51502cb34d6d3799cba6ef85bb2e9021fbc577a2ffe319fd9a44cc9156e5c0f3
  p02c_structure_budget_matrix.csv: 95bcaa10d94be8362ea8c8937e6cb32d1436767934aaf497a3f0c8f4daaf3642
  p02c_corpus_arm_table.csv: b56d8723cd5bb1f840b98f83671c11456f26e2f2acc0177c83554a7a2f5d235e
  p5rns_b59_verdict.json: 0d9222d8f6e1f8d351e392c59d61adfda617bff2b51e6fb9a2c4205a8019b87b
  probe_results_b59_family.jsonl: 0373b139c4466e8af0cfa40d842a69b507fbe1d356fe8b1eab47e443d69f383f
  random_midpoints_results.jsonl: e8de196c010f49780f9296cb6c3fe19cc2e6ae015dd62649429f352d99795495
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
FACTORIAL = ROOT / "对账_P0_20261125/p02c_factorial_table.csv"
STRUCTURE = ROOT / "对账_P0_20261125/p02c_structure_budget_matrix.csv"
CORPUS = ROOT / "对账_P0_20261125/p02c_corpus_arm_table.csv"
P5RNS = BACKUP / "eval_evidence_logs/evidence/p5rns_b59_verdict.json"
FAMILY_LEDGER = BACKUP / "eval_evidence_logs/eval/probe_results_b59_family.jsonl"
RANDOM_MIDPOINTS = BACKUP / "eval_evidence_logs/eval/random_midpoints_results.jsonl"
OUTPUT = ROOT / "figs_v6"

SCALES = ["30M", "100M", "300M", "650M"]
X = np.arange(len(SCALES))
COLORS = {
    "family": "#4878A8",
    "structure": "#4C956C",
    "random": "#D1495B",
    "replica": "#4878A8",
    "rw1": "#E0A458",
    "rfamcap": "#8E6C8A",
    "rns": "#6C5B7B",
    "ink": "#333333",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 8,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#888888")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(length=3, width=0.7, colors=COLORS["ink"])
    ax.grid(axis="y", color="#999999", alpha=0.18, linestyle=":", linewidth=0.6)
    ax.set_axisbelow(True)


def panel_label(ax, label):
    ax.text(-0.14, 1.04, label, transform=ax.transAxes, fontsize=13,
            fontweight="bold", va="top", color=COLORS["ink"])


factorial = read_csv(FACTORIAL)
structure = read_csv(STRUCTURE)
corpus = read_csv(CORPUS)

family = {
    row["scale"]: float(row["delta_recomputed_pp"])
    for row in factorial
    if row["channel"] == "family" and row["protocol"] == "single_seed_s17_final"
}
random = {
    row["scale"]: float(row["delta_recomputed_pp"])
    for row in factorial
    if row["channel"] == "random"
}
structure_delta = {
    row["scale"]: float(row["budget_delta_recomputed_pp"])
    for row in structure
}

fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.6))
fig.subplots_adjust(left=0.075, right=0.92, bottom=0.09, top=0.91,
                    hspace=0.40, wspace=0.30)

# A: the three downstream/readout channels under the same budget intervention.
ax = axes[0, 0]
for channel, values, marker in [
    ("family", family, "o"),
    ("structure", structure_delta, "^"),
    ("random", random, "s"),
]:
    ax.plot(X, [values[s] for s in SCALES], color=COLORS[channel],
            marker=marker, markersize=6, linewidth=2, label=channel.capitalize())
ax.plot(X[-1], random["650M"], marker="s", markersize=8,
        markerfacecolor="white", markeredgecolor=COLORS["random"],
        markeredgewidth=1.8, linestyle="None")
ax.annotate("historical 5B midpoint;\nterminal not evaluated", (X[-1], random["650M"]),
            xytext=(-68, -35), textcoords="offset points", fontsize=7.5,
            color=COLORS["random"], arrowprops={"arrowstyle": "-", "color": COLORS["random"], "lw": 0.7})
ax.axhline(0, color="#555555", linewidth=0.8)
ax.set_xticks(X, SCALES)
ax.set_ylim(-6.6, 5.4)
ax.set_ylabel("Budget effect (5.9B − 2B), pp")
ax.set_title("Budget response is channel-specific", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="lower right", ncol=3)
panel_label(ax, "A")
style(ax)

# B: controlled corpus interventions; no external-model comparison is included.
ax = axes[0, 1]
series = {
    "replica": ("Recipe replica", "rinalmo_corpus_replica", ["30M", "100M", "300M"], "o"),
    "rw1": ("Family-prior flattening (rw1)", "rw1_reweighting", ["10M", "30M", "100M"], "^"),
    "rfamcap": ("Rfam enrichment (rfamcap)", "rfamcap_family_final_supplement", ["30M", "100M"], "D"),
}
for key, (label, section, scales, marker) in series.items():
    rows = {row["scale"]: row for row in corpus if row["section"] == section}
    # Put 10M at a separate left position while retaining the shared scale order.
    positions = [-0.65 if s == "10M" else SCALES.index(s) for s in scales]
    ax.plot(positions, [float(rows[s]["delta_recomputed_pp"]) for s in scales],
            color=COLORS[key], marker=marker, markersize=6, linewidth=2, label=label)
ax.axhline(0, color="#555555", linewidth=0.8)
ax.annotate("neutral relative to\n10M training-seed SD", (-0.65, 0.15),
            xytext=(-10, 28), textcoords="offset points", ha="center", fontsize=7.5,
            color="#8A642C", arrowprops={"arrowstyle": "-", "color": "#8A642C", "lw": 0.7})
ax.text(0.98, 0.03, "rfamcap: iso-budget terminal", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=7.5, color=COLORS["rfamcap"])
ax.set_xticks([-0.65, 0, 1, 2, 3], ["10M", "30M", "100M", "300M", "650M"])
ax.set_xlim(-1.0, 3.35)
ax.set_ylim(-5.4, 9.0)
ax.set_ylabel("Corpus-arm minus control, pp")
ax.set_title("Corpus levers attenuate or flip with capacity", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper right")
panel_label(ax, "B")
style(ax)

# C: within-run trajectories, using best layer independently at each checkpoint.
ax = axes[1, 0]
family_trajectory = defaultdict(lambda: (-1.0, None))
with FAMILY_LEDGER.open() as handle:
    for line in handle:
        row = json.loads(line)
        run = row.get("run", "")
        is_main = run == "RNA-Sc-30M_s17_b59" or run.startswith("RNA-Sc-30M_s17_b59_ck")
        if not is_main or row.get("n_train", 0) < 20000 or "family" not in row.get("split", ""):
            continue
        nt = row["ckpt_nt"]
        if row["f1_macro"] > family_trajectory[nt][0]:
            family_trajectory[nt] = (row["f1_macro"], row["layer"])
random_trajectory = {}
with RANDOM_MIDPOINTS.open() as handle:
    for line in handle:
        row = json.loads(line)
        if row["run"].startswith("RNA-Sc-30M_s17_b59_"):
            random_trajectory[row["ckpt_nt"]] = row["best_f1_macro"]
random_final = next(row for row in factorial if row["channel"] == "random" and row["scale"] == "30M")
family_terminal = next(row for row in factorial if row["channel"] == "family" and row["scale"] == "30M")
random_trajectory[int(float(family_terminal["ckpt_nt_59b"]))] = float(random_final["f1_59b"])

f_nt = sorted(family_trajectory)
r_nt = sorted(random_trajectory)
ax.plot([nt / 1e9 for nt in f_nt], [family_trajectory[nt][0] for nt in f_nt],
        color=COLORS["family"], marker="o", markersize=4.5, linewidth=2,
        label="Family-held-out")
ax.plot([nt / 1e9 for nt in r_nt], [random_trajectory[nt] for nt in r_nt],
        color=COLORS["random"], marker="s", markersize=5, linewidth=2,
        label="Random split")
ax.annotate("0.3409 at 0.8B", (0.800037752, family_trajectory[800037752][0]),
            xytext=(8, 9), textcoords="offset points", fontsize=7.5, color=COLORS["family"])
ax.annotate("0.1942 at 5.8B", (f_nt[-1] / 1e9, family_trajectory[f_nt[-1]][0]),
            xytext=(-74, -18), textcoords="offset points", fontsize=7.5, color=COLORS["family"])
ax.annotate("0.5721 → 0.6136\n(1B → 5B)", (5e9 / 1e9, random_trajectory[5000000000]),
            xytext=(-88, 12), textcoords="offset points", fontsize=7.5, color=COLORS["random"])
ax.set_xlim(0, 6.15)
ax.set_ylim(0.15, 0.66)
ax.set_xlabel("Pretraining exposure (B nt)")
ax.set_ylabel("30M best-layer macro-F1")
ax.set_title("Random-split memory cashing diverges from family transfer", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper right")
panel_label(ax, "C")
style(ax)

# D: zero-supervision channels reject a shared representation ceiling.
ax = axes[1, 1]
with P5RNS.open() as handle:
    verdict = json.load(handle)
small_scales = ["30M", "100M", "300M"]
small_x = np.arange(len(small_scales))
nonrrna = [verdict["matrix"][s]["nonrRNA_budget_delta"] for s in small_scales]
rrna = [verdict["matrix"][s]["rRNA_budget_delta"] for s in small_scales]
rns = [verdict["matrix"][s]["RNS_budget_delta"] for s in small_scales]
width = 0.32
bars1 = ax.bar(small_x - width / 2, nonrrna, width, color=COLORS["structure"],
               alpha=0.88, label="P5 non-rRNA separation")
bars2 = ax.bar(small_x + width / 2, rrna, width, color="#B8D8C6",
               edgecolor=COLORS["structure"], linewidth=0.7, label="P5 rRNA separation")
ax.set_xticks(small_x, small_scales)
ax.set_ylim(0, 0.43)
ax.set_ylabel("P5 budget change (nats/token)")
ax.set_title("Zero-supervision channels continue to use budget", loc="left", fontweight="bold")
ax_rns = ax.twinx()
ax_rns.plot(small_x, rns, color=COLORS["rns"], marker="o", markersize=6,
            linewidth=2, label="RNS@10 change")
ax_rns.set_ylim(-0.040, 0.005)
ax_rns.set_ylabel("RNS@10 budget change (lower = tighter)", color=COLORS["rns"])
ax_rns.tick_params(axis="y", colors=COLORS["rns"], length=3, width=0.7)
ax_rns.spines["top"].set_visible(False)
ax_rns.spines["right"].set_color(COLORS["rns"])
handles, labels = ax.get_legend_handles_labels()
handles2, labels2 = ax_rns.get_legend_handles_labels()
ax.legend(handles + handles2, labels + labels2, frameon=False, loc="upper left", fontsize=7.5)
panel_label(ax, "D")
style(ax)
ax_rns.set_axisbelow(True)

fig.suptitle("Knowledge supply is gated by corpus composition, budget, scale, and readout channel",
             fontsize=14, fontweight="bold", color=COLORS["ink"], y=0.975)
fig.text(0.075, 0.025,
         "Controlled s17 contrasts. Open marker: demoted historical midpoint; terminal not evaluated (Appendix A). " 
         "Corpus effects are family macro-F1 differences; "
         "P5/RNS use their own zero-supervision units.",
         fontsize=8, color="#555555")

OUTPUT.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT / "fig5_q6_supply.png", dpi=300, bbox_inches="tight")
fig.savefig(OUTPUT / "fig5_q6_supply.pdf", bbox_inches="tight")
plt.close(fig)
print(OUTPUT / "fig5_q6_supply.png")
print(OUTPUT / "fig5_q6_supply.pdf")
