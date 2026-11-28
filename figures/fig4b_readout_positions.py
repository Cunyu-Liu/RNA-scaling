#!/usr/bin/env /usr/bin/python3
# Fig.4b — Readout-position panel (Q5, P2.8 data).
# Question: Does reading a different intra-block position unlock pretrained pairing knowledge?
# Answer: Absolute readability shifts with position; pretrained-specific net gain does not —
#         the wall is not a readout-position artifact.
# Input SHA-256 (verified at runtime):
# 650M_summary.json: a7e6b904eec5fb4b5d39a4e294516fd41a4babc3d009168c91c054b465a83700
# 100M_summary.json: 1005fc34c328ec27709c6f74288fc59817d08517bd90d06405cde10a7ce21293
# 650M_randinit17_summary.json: ef08293d829a2c7aa2c6d21136508438391d75e556d911c8ebb473a3f8d19ccd
# 100M_randinit17_summary.json: 07bde572e70e508c9f696ac7413d8f74aa7c062026fa1e23a9b307bbb3837b36
# Caliber: per-token paired-position F1 (non-saturated), linear heads trained to convergence;
#          trivial floor ~0.54; NOT a direct pair-level reproduction of the ~0.64 wall.

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/figs_v6")
P2_8 = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/补证_P2_20261125/results/P2_8")
INPUTS = {
    "650M": (P2_8 / "650M_summary.json", "a7e6b904eec5fb4b5d39a4e294516fd41a4babc3d009168c91c054b465a83700"),
    "100M": (P2_8 / "100M_summary.json", "1005fc34c328ec27709c6f74288fc59817d08517bd90d06405cde10a7ce21293"),
    "650M_ri": (P2_8 / "650M_randinit17_summary.json", "ef08293d829a2c7aa2c6d21136508438391d75e556d911c8ebb473a3f8d19ccd"),
    "100M_ri": (P2_8 / "100M_randinit17_summary.json", "07bde572e70e508c9f696ac7413d8f74aa7c062026fa1e23a9b307bbb3837b36"),
}
BLUE = "#0F4D92"
BLUE2 = "#3775BA"
GREEN = "#42949E"
RED = "#B64342"
GREY = "#767676"
LIGHT = "#CFCECE"
DARK = "#272727"

POSITIONS = ["resid_post", "attn_query", "attn_key", "ffn_up"]
POS_LABEL = {"resid_post": "resid_post", "attn_query": "attn_query",
             "attn_key": "attn_key", "ffn_up": "ffn_up"}


def load_inputs():
    loaded = {}
    for key, (path, expected) in INPUTS.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"SHA-256 mismatch for {path}: {digest}")
        loaded[key] = json.loads(path.read_text())
    return loaded


def main():
    d = load_inputs()
    scales = ["650M", "100M"]
    # absolute F1 and net gain tables
    abs_tr = {s: [d[s]["positions"][p]["f1"] for p in POSITIONS] for s in scales}
    abs_ri = {s: [d[s + "_ri"]["positions"][p]["f1"] for p in POSITIONS] for s in scales}
    net = {s: [round(abs_tr[s][i] - abs_ri[s][i], 4) for i in range(len(POSITIONS))] for s in scales}
    rot = {s: d[s]["positions"]["resid_rot17"]["f1"] for s in scales}

    # cross-check against contract reference values (3rd verification)
    ref_net = {"650M": [0.0206, 0.0086, -0.0280, -0.0681],
               "100M": [-0.0291, -0.0076, 0.0624, 0.0096]}
    for s in scales:
        for i, p in enumerate(POSITIONS):
            assert abs(net[s][i] - ref_net[s][i]) < 5e-5, (s, p, net[s][i], ref_net[s][i])
    assert abs(rot["650M"] - 0.5478) < 1e-9 and abs(rot["100M"] - 0.4815) < 1e-9

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.6, 4.6),
                                   gridspec_kw={"width_ratios": [1.35, 1.0]})

    # ---- panel a: absolute position F1, trained vs randinit grey ----
    npos = len(POSITIONS)
    group_gap = 1.0
    bar_w = 0.38
    xticks, xlabels = [], []
    for gi, s in enumerate(scales):
        base = gi * (npos + group_gap)
        x = np.arange(npos) + base
        axa.bar(x - bar_w / 2, abs_tr[s], bar_w, color=BLUE if s == "650M" else BLUE2,
                label="trained" if gi == 0 else None, zorder=3)
        axa.bar(x + bar_w / 2, abs_ri[s], bar_w, color=LIGHT,
                label="randinit17" if gi == 0 else None, zorder=3)
        # rotation control marker on resid_post
        axa.scatter([base - bar_w / 2], [rot[s]], marker="D", s=42, color=GREY,
                    zorder=5, label="resid_rot17 (rotation ctrl)" if gi == 0 else None)
        for i, p in enumerate(POSITIONS):
            xticks.append(base + i)
            xlabels.append(POS_LABEL[p])
        axa.text(base + (npos - 1) / 2, 0.70, s, ha="center", va="bottom",
                 fontsize=11, fontweight="bold", color=DARK)
    axa.axhline(0.54, color=GREY, lw=0.9, ls="--", zorder=1)
    axa.text(npos + group_gap + npos - 0.4, 0.545, "trivial floor ~0.54",
             ha="right", va="bottom", fontsize=8, color=GREY)
    axa.set_xticks(xticks)
    axa.set_xticklabels(xlabels, rotation=20, ha="right")
    axa.set_ylim(0.40, 0.72)
    axa.set_ylabel("per-token paired-position F1 (absolute)")
    axa.set_title("a  Absolute readability by readout position", loc="left", fontsize=11)
    axa.legend(frameon=False, loc="upper right", fontsize=8.5)

    # ---- panel b: pretrained-specific net gain (trained - randinit) ----
    xticks_b, xlabels_b = [], []
    for gi, s in enumerate(scales):
        base = gi * (npos + group_gap)
        x = np.arange(npos) + base
        colors = [GREEN if v >= 0 else RED for v in net[s]]
        axb.bar(x, net[s], 0.62, color=colors, zorder=3)
        for xi, v in zip(x, net[s]):
            axb.text(xi, v + (0.004 if v >= 0 else -0.004), f"{v:+.3f}",
                     ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=DARK)
        for i, p in enumerate(POSITIONS):
            xticks_b.append(base + i)
            xlabels_b.append(POS_LABEL[p])
        axb.text(base + (npos - 1) / 2, 0.085, s, ha="center", va="bottom",
                 fontsize=11, fontweight="bold", color=DARK)
    axb.axhline(0, color=DARK, lw=1.0, zorder=2)
    axb.set_xticks(xticks_b)
    axb.set_xticklabels(xlabels_b, rotation=20, ha="right")
    axb.set_ylim(-0.09, 0.10)
    axb.set_ylabel("pretrained-specific net gain (trained − randinit)")
    axb.set_title("b  Net gain does not follow absolute readability", loc="left", fontsize=11)
    from matplotlib.patches import Patch
    axb.legend(handles=[Patch(color=GREEN, label="net gain ≥ 0"),
                        Patch(color=RED, label="net gain < 0")],
               frameon=False, loc="lower right", fontsize=8.5)

    fig.suptitle("Does reading a different intra-block position unlock pretrained pairing knowledge?",
                 fontsize=12, fontweight="bold", x=0.01, ha="left", y=1.02)
    fig.text(0.01, -0.04,
             "Absolute readability shifts with position; pretrained-specific net gain does not — the wall is not a readout-position artifact. "
             "Per-token caliber (trivial floor ~0.54); not a direct pair-level reproduction. P2.8, s17, 650M L15 / 100M L22.",
             fontsize=8.5, color=GREY, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig4b_readout_positions.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig4b_readout_positions.pdf", bbox_inches="tight")
    plt.close(fig)
    print("FIG4B_OK")
    print(json.dumps({"abs_trained": abs_tr, "abs_randinit": abs_ri,
                      "net_gain": net, "resid_rot17": rot}, indent=2))


if __name__ == "__main__":
    main()