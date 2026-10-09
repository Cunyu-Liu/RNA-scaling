"""H5-a 增强（2026-10-09 第四轮）：补 100/300/650M 的语料量维度证据。

用户要求"H5 补充 100/300/650M"——诚实可补的是 b59 预算臂（语料量 2B→5.9B
= 语料量轴在大尺度上的受控实验，30M/100M/300M 已出值 + 650M 收口中）。
产出 h5_evidence_v3：三面板——(a) 30M 档语料量曲线（小语料内部比较）
(b) b59 预算效应按尺度（100M/300M/650M 全覆盖！语料量轴的大尺度版）
(c) 多样性轴 rw 三档。每个面板口径独立、数据来源标注。
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"
C_MAIN, C_WARN, C_GOOD, C_GREY = "#2F5C8F", "#B03030", "#1B7A3D", "#8A8A8A"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5, width=0.9, labelsize=9)
    ax.grid(alpha=0.22, ls=":", lw=0.7)
    ax.set_axisbelow(True)


def main():
    c3 = json.load(open(E + "/corpus3.json"))
    h5 = json.load(open(E + "/h5_rw_multiscale.json"))["table"]
    fv = json.load(open(E + "/factorial_verdict.json"))

    fig, axes = plt.subplots(1, 3, figsize=(13.8, 5.0),
                             gridspec_kw={"width_ratios": [1, 1.15, 1]})
    fig.suptitle("H5 · 语料构成三视图（v3：100M/300M/650M 已按预算臂补齐）",
                 fontsize=12, fontweight="bold", x=0.01, ha="left")

    # (a) 数量轴 30M 档（小语料内部）
    ax = axes[0]
    labels_a = ["0.85B\n(c1M)", "0.9B\n(c1Mcs)", "14.1B\n(full)"]
    pts_a = [c3["30M-c1M"]["best_f1"], c3["30M-c1Mcs"]["best_f1"],
             c3["30M-full"]["best_f1"]]
    xpos = np.arange(3)
    ax.bar(xpos, pts_a, width=0.5, color=[C_GOOD, C_GOOD, C_MAIN], alpha=0.9,
           zorder=3, edgecolor="white", linewidth=1.2)
    for x, v in zip(xpos, pts_a):
        ax.text(x, v + 0.004, "%.3f" % v, ha="center", fontsize=10.5,
                fontweight="bold")
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels_a, fontsize=8.5)
    ax.set_ylabel("家族级 probe F1", fontsize=9)
    ax.set_ylim(0, 0.36)
    ax.set_title("(a) 数量轴 · 小尺度内部\n30M 档：小语料 0.316 最优\n(100M/300M 无语料量臂 → 见 b)",
                 fontsize=9.5, loc="left", pad=6, fontweight="bold")
    style_ax(ax)

    # (b) 语料量轴大尺度版（b59 预算臂，含 650M 在训标注）
    ax = axes[1]
    scales = ["30M", "100M", "300M", "650M"]
    deltas = [fv["table"][s].get("budget_delta_pp") for s in scales]
    colors = [C_WARN if (d is not None and d < 0) else C_GOOD for d in deltas]
    xpos = np.arange(4)
    bars = ax.bar(xpos, [d if d is not None else 0 for d in deltas],
                  width=0.5, color=colors, alpha=0.9, zorder=3,
                  edgecolor="white", linewidth=1.2)
    for x, d in zip(xpos, deltas):
        if d is None:
            ax.text(x, 0.3, "在训", ha="center", fontsize=10,
                    fontweight="bold", color=C_GREY, rotation=90)
            continue
        va = "bottom" if d > 0 else "top"
        off = 0.18 if d > 0 else -0.18
        ax.text(x, d + off, "%+.2f" % d, ha="center", va=va, fontsize=11.5,
                fontweight="bold")
    ax.axhline(0, color="#555", lw=1.0)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["30M", "100M", "300M", "650M\n(在训)"],
                       fontsize=10)
    ax.set_ylabel("语料量 2.0B→5.9B 效应（Δpp）", fontsize=9)
    ax.set_ylim(-6.5, 5)
    ax.set_title("(b) 语料量轴 · 大尺度版（100/300/650M）\n"
                 "语料量效应随容量翻正：30M −5.24 → 300M +3.76\n(650M 收口中，自动补第四格)",
                 fontsize=9.5, loc="left", pad=6, fontweight="bold")
    ax.text(0.98, 0.05, "与 fig6 左图同数据源——\n语料量维度的受控证据",
            transform=ax.transAxes, ha="right", fontsize=8, color="#555")
    style_ax(ax)

    # (c) 多样性轴 rw 三档
    ax = axes[2]
    scales_c = ["10M", "30M", "100M"]
    deltas_c = [h5[s]["delta_pp"] for s in scales_c]
    colors_c = ["#C9A227" if d > 0 else C_WARN for d in deltas_c]
    xpos = np.arange(3)
    ax.bar(xpos, deltas_c, width=0.5, color=colors_c, alpha=0.9, zorder=3,
           edgecolor="white", linewidth=1.2)
    for x, d in zip(xpos, deltas_c):
        va = "bottom" if d > 0 else "top"
        off = 0.15 if d > 0 else -0.15
        ax.text(x, d + off, "%+.2f" % d, ha="center", va=va, fontsize=11.5,
                fontweight="bold")
    ax.axhline(0, color="#555", lw=1.0)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["10M\n(受限)", "30M\n(中间)", "100M\n(充足)"],
                       fontsize=9.5)
    ax.set_ylabel("重加权语料 Δpp（展平 vs 原始）", fontsize=9)
    ax.set_ylim(-5.4, 1.5)
    ax.set_title("(c) 多样性轴 · 容量门控翻转\n+0.15 / −0.58 / −4.29\n(300M/650M 无 rw 臂)",
                 fontsize=9.5, loc="left", pad=6, fontweight="bold")
    style_ax(ax)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "h5_evidence_v3.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("h5_v3 saved")


if __name__ == "__main__":
    main()
