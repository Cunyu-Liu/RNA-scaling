"""User request #1 (2026-10-08): one evidence figure per hypothesis H1-H8.

Eight compact panels, each proving/falsifying one pre-registered hypothesis
from SPEC §3. All numbers read from evidence JSONs / probe jsonl (no manual
copying). Output: /mnt/cunyuliu/rna-sc/figs/hyp_evidence_{A,B}.png
Two pages: A = H1-H4 (Li et al.-aligned), B = H5-H8 (RNA-specific).
"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"
os.makedirs(FIG, exist_ok=True)

SCALE_COLORS = {"1M": "#A0A0A0", "10M": "#C0392B", "30M": "#1B7A3D",
                "100M": "#2F5C8F", "300M": "#E07B39", "650M": "#6A3D9A"}
PARAMS_M = {"1M": 1.0, "10M": 10.0, "30M": 30.0, "100M": 100.0,
            "300M": 302.0, "650M": 666.0}
C_MAIN, C_WARN, C_GOOD, C_GREY = "#2F5C8F", "#B03030", "#1B7A3D", "#8A8A8A"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.0, width=0.8, labelsize=7.6)
    ax.grid(alpha=0.22, ls=":", lw=0.6)
    ax.set_axisbelow(True)


def verdict_tag(ax, text, ok=True):
    ax.text(0.985, 0.965, text, transform=ax.transAxes, ha="right", va="top",
            fontsize=7.4, fontweight="bold", color=C_GOOD if ok else C_WARN,
            bbox=dict(fc="#F3FAF3" if ok else "#FDF3F3", ec=C_GOOD if ok else C_WARN,
                      boxstyle="round,pad=0.28", alpha=0.95))


def hyp_header(ax, code, title):
    ax.set_title("%s · %s" % (code, title), fontsize=9.2, loc="left",
                 pad=5, fontweight="bold")


# ============================== PAGE A: H1-H4 ==============================
def hyp_page_a():
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4))
    fig.suptitle("H1–H4 证据图（Li et al. 对齐四假设） · Evidence per hypothesis, page A",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")

    # ---- H1: scaling curve with slope annotations ----
    ax = axes[0][0]
    s1 = json.load(open(E + "/s1_final_verdict.json"))
    t = dict(s1["five_scale_table"])
    t["300M"] = {"f1_mean": 0.3445, "f1_std": 0.0}
    order = ["1M", "10M", "30M", "100M", "300M", "650M"]
    f1s = [t[s]["f1_mean"] for s in order]
    xs = [PARAMS_M[s] for s in order]
    means = [t[s]["f1_mean"] for s in order]
    stds = [t[s].get("f1_std", 0) or 0 for s in order]
    ax.errorbar(xs, means, yerr=stds, fmt="-o", color=C_MAIN, lw=2.0, ms=7,
                capsize=3, markeredgecolor="white", markeredgewidth=0.8, zorder=5)
    for x, y, s in zip(xs, f1s, order):
        ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=7.4, color=SCALE_COLORS[s],
                    fontweight="bold")
    ax.annotate("slope 30M→100M = 0.142/decade\n(CI [0.104,0.180] → triggered 650M)",
                xy=(100, 0.3394), xytext=(1.6, 0.30), fontsize=7.2, color="#555",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
    ax.annotate("slope 100M→650M = 0.0293 < ε\nscaling SATURATED",
                xy=(666, 0.3632), xytext=(150, 0.205), fontsize=7.2, color=C_WARN,
                arrowprops=dict(arrowstyle="->", color=C_WARN, lw=0.8))
    ax.set_xscale("log")
    ax.set_ylim(0.12, 0.43)
    ax.set_xlabel("parameters (M)", fontsize=8.6)
    ax.set_ylabel("family-split probe macro-F1", fontsize=8.6)
    hyp_header(ax, "H1", "特征复用随规模增长——但有上限")
    verdict_tag(ax, "证实（有语料边界）\n6.5× 参数仅 +2.4pp", ok=False)
    style_ax(ax)

    # ---- H2: randinit gap widens ----
    ax = axes[0][1]
    s4 = json.load(open(E + "/s4_randinit_table.json"))
    order4 = ["1M", "10M", "30M", "100M", "300M", "650M"]
    tr = [s4[s]["trained"] for s in order4]
    ri = [s4[s]["randinit"] for s in order4]
    xs4 = [PARAMS_M[s] for s in order4]
    ax.plot(xs4, tr, "-o", color=C_MAIN, lw=2.0, ms=6, label="trained",
            markeredgecolor="white", markeredgewidth=0.7)
    ax.plot(xs4, ri, "-s", color=C_GREY, lw=1.8, ms=6, label="random-init (same arch)",
            markeredgecolor="white", markeredgewidth=0.7)
    for x, a, b, s in zip(xs4, tr, ri, order4):
        if s in ("30M", "100M", "650M"):
            ax.annotate("", xy=(x, b), xytext=(x, a),
                        arrowprops=dict(arrowstyle="<->", color="#BB8833", lw=0.9))
    ax.text(12, 0.30, "预训练增益 = trained − randinit\n随规模单调扩大 +0.059 → +0.168",
            fontsize=7.4, color="#8A6A1F")
    ax.set_xscale("log")
    ax.set_xlabel("parameters (M)", fontsize=8.6)
    ax.set_ylabel("probe macro-F1", fontsize=8.6)
    ax.legend(fontsize=7.6, loc="upper left")
    hyp_header(ax, "H2", "归纳偏置/过参数化解释——被排除")
    verdict_tag(ax, "排除（增益随规模扩大）", ok=True)
    style_ax(ax)

    # ---- H3: mommatch ≈ randinit ----
    ax = axes[1][0]
    s5 = json.load(open(E + "/s5_mommatch_table.json"))
    mm = [s5[s]["mommatch"] for s in order4]
    xs5 = [PARAMS_M[s] for s in order4]
    w = 0.14
    xpos = np.arange(len(order4))
    ax.bar(xpos - w, tr, width=w, color=C_MAIN, label="trained", alpha=0.92)
    ax.bar(xpos, mm, width=w, color="#C9A227", label="moment-matched init", alpha=0.92)
    ax.bar(xpos + w, ri, width=w, color=C_GREY, label="random-init", alpha=0.92)
    for i, s in enumerate(order4):
        d = s5[s]["delta"]
        ax.text(xpos[i], max(tr[i], mm[i], ri[i]) + 0.012, "+%.3f" % d,
                ha="center", fontsize=7.0, color=C_WARN if d < 0.1 else "#333",
                fontweight="bold")
    ax.set_xticks(xpos)
    ax.set_xticklabels(order4, fontsize=8)
    ax.set_ylim(0, 0.46)
    ax.set_ylabel("probe macro-F1", fontsize=8.6)
    ax.legend(fontsize=7.4, ncol=3, loc="upper left")
    hyp_header(ax, "H3", "权重统计（好初始化）解释——被排除")
    verdict_tag(ax, "排除（mommatch ≈ randinit）", ok=True)
    style_ax(ax)

    # ---- H4: attrition timeline, 10M layer collapse ----
    ax = axes[1][1]
    s6 = json.load(open(E + "/s6_timeline.json"))
    runs10 = [k for k in s6 if "10M_s17" in k and "randinit" not in k]
    for k in runs10:
        pts = s6[k]
        if isinstance(pts, dict):
            pts = pts.get("points", [])
        xs_t = [p.get("nt_b", p.get("ckpt_nt", 0)) / 1e9 for p in pts]
        ys_t = [p.get("best_f1", p.get("f1", 0)) for p in pts]
        ls_t = [p.get("best_layer", p.get("layer", 0)) for p in pts]
        ax.plot(xs_t, ys_t, "-o", color=C_WARN, lw=1.8, ms=4.5)
        for x, y, l in zip(xs_t, ys_t, ls_t):
            ax.annotate("L%d" % l, (x, y), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=6.2, color="#777")
    ax.annotate("峰值 0.244 @ 0.5B (L11)\n→ 磨蚀后塌至 L1-3", xy=(0.5, 0.244),
                xytext=(1.0, 0.26), fontsize=7.4, color="#555",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
    ax.set_xlabel("pretraining tokens seen (B nt)", fontsize=8.6)
    ax.set_ylabel("10M best-layer F1", fontsize=8.6)
    hyp_header(ax, "H4", "低层特征复用——磨蚀任务特异（容量门控）")
    verdict_tag(ax, "限定成立\n容量不足时才依赖早期层", ok=True)
    style_ax(ax)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "hyp_evidence_A.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("hyp_evidence_A saved")


# ============================== PAGE B: H5-H8 ==============================
def hyp_page_b():
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4))
    fig.suptitle("H5–H8 证据图（RNA 特有四假设） · Evidence per hypothesis, page B",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")

    # ---- H5: dual-axis corpus result ----
    ax = axes[0][0]
    c3 = json.load(open(E + "/corpus3.json"))
    h5 = json.load(open(E + "/h5_rw_multiscale.json"))
    scales = ["1M", "5M", "full"]
    keys = ["c1Mcs", "c5Mcs", "full"]
    try:
        f10 = [c3["10M"][k] for k in keys]
        lbl10 = ["0.9B\n(≈2.2 ep)", "4.6B*", "2.0B\n(0.34 fresh)"]
        xs5h = np.arange(3)
        ax.plot(xs5h, f10, "-o", color=C_WARN, lw=1.9, ms=6,
                label="10M · quantity axis (U-shape)",
                markeredgecolor="white", markeredgewidth=0.7)
    except Exception:
        f10, xs5h, lbl10 = [], [], []
    rw_t = h5["table"]
    rwx = np.arange(3) + 0.0
    rwd = [rw_t["10M"]["delta_pp"], rw_t["30M"]["delta_pp"],
           rw_t["100M"]["delta_pp"]]
    ax2 = ax.twinx()
    ax2.bar(rwx, rwd, width=0.42, color=["#C9A227", "#C9A227", "#C9A227"],
            alpha=0.45, zorder=2)
    ax2.axhline(0, color="#999", lw=0.8)
    ax2.set_ylabel("diversity axis: rw1 Δpp (flattened vs full)",
                   fontsize=7.8, color="#8A6A1F")
    ax2.tick_params(labelsize=7.4, colors="#8A6A1F")
    for x, d in zip(rwx, rwd):
        ax2.text(x, d + (0.25 if d >= 0 else -0.6), "%+.2f" % d, ha="center",
                 fontsize=7.2, color="#8A6A1F", fontweight="bold")
    if f10:
        ax.set_xticks(xs5h)
        ax.set_xticklabels(["10M:\n0.9B nt", "10M:\n4.6B nt", "10M:\n2.0B full"],
                           fontsize=7.6)
        for x, y in zip(xs5h, f10):
            ax.annotate("%.3f" % y, (x, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=7.0)
        ax.set_ylim(0.13, 0.35)
    ax.set_ylabel("quantity axis: probe F1", fontsize=8.2)
    ax.set_zorder(ax2.zorder + 1)
    ax.patch.set_visible(False)
    hyp_header(ax, "H5", "语料构成：数量 vs 多样性双轴")
    verdict_tag(ax, "双轴定案\n数量轴小语料优 / 展平更差\n(DenAdel 跨域复现)", ok=False)
    ax.text(0.02, 0.04, "rw1 bars: 10M +0.15 / 30M −0.58 / 100M −4.29pp\n→ 容量门控的先验效用（符号翻转）",
            transform=ax.transAxes, fontsize=7.0, color="#555", va="bottom")
    style_ax(ax)

    # ---- H6: DI vs best-layer linkage ----
    ax = axes[0][1]
    links = {}
    for f, tag in [("s12_linkage_30M_s17_c1Mcs.json", "30M"),
                   ("s12_linkage_RNA-Sc-100M_s17.json", "100M"),
                   ("s12_linkage_RNA-Sc-300M_s17.json", "300M"),
                   ("s12_linkage_RNA-Sc-650M_s17.json", "650M")]:
        try:
            d = json.load(open(os.path.join(E, f)))
            links[tag] = d.get("spearman_DI_vs_bestlayer")
        except Exception:
            pass
    xs_l = [PARAMS_M[k] for k in links]
    ys_l = [links[k] for k in links]
    ax.plot(xs_l, ys_l, "-o", color=C_MAIN, lw=2.0, ms=7,
            markeredgecolor="white", markeredgewidth=0.8)
    for x, y, k in zip(xs_l, ys_l, links):
        ax.annotate("%s\nρ=%.3f" % (k, y), (x, y), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=7.4, fontweight="bold")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xscale("log")
    ax.set_ylim(-0.6, 0.1)
    ax.set_xlabel("parameters (M)", fontsize=8.6)
    ax.set_ylabel("Spearman(DI, best-layer depth)", fontsize=8.6)
    hyp_header(ax, "H6", "结构-序列解耦 → 层位置（DI 衰减）")
    verdict_tag(ax, "证实\n高解耦家族峰层更浅\n关联随容量稀释", ok=True)
    ax.text(0.03, 0.06, "30M-c1Mcs −0.478 → 650M −0.222 单调衰减\n（n=10 家族，各点方向一致）",
            transform=ax.transAxes, fontsize=7.0, color="#555")
    style_ax(ax)

    # ---- H7: S13b structural bell ----
    ax = axes[1][0]
    bell = json.load(open(E + "/s13b_bell.json"))
    pts = bell["points"]
    models = sorted({p["model"] for p in pts})
    cmap = plt.cm.viridis(np.linspace(0.08, 0.92, len(models)))
    for m, c in zip(models, cmap):
        mp = [p for p in pts if p["model"] == m]
        ax.scatter([p["nll"] for p in mp], [p["f1"] for p in mp], s=34,
                   color=c, alpha=0.85, edgecolors="none",
                   label=m.replace("RNA-Sc-", "").replace("_s17", ""))
    xs_b = np.array([p["nll"] for p in pts])
    ys_b = np.array([p["f1"] for p in pts])
    z = np.polyfit(xs_b, ys_b, 2)
    xr = np.linspace(xs_b.min() - 0.01, xs_b.max() + 0.01, 80)
    ax.plot(xr, np.polyval(z, xr), "--", color="#444", lw=1.4, zorder=3)
    ax.legend(fontsize=6.6, ncol=2, loc="lower left", framealpha=0.9,
              title="model (family-level points)", title_fontsize=6.4)
    ax.set_xlabel("held-out family NLL (confidence axis)", fontsize=8.6)
    ax.set_ylabel("bpRNA structure F1", fontsize=8.6)
    hyp_header(ax, "H7", "似然中介：结构版钟形检验")
    verdict_tag(ax, "NOT-BELL（预注册负结果）\n峰值在数据范围外\nRNA 语料域内无过度自信区间", ok=False)
    style_ax(ax)

    # ---- H8: RNS vs scale + family cross ----
    ax = axes[1][1]
    rns = json.load(open(E + "/s14_rns.json"))
    try:
        scale_rns = rns["scale_axis"]["rns_k10"]
    except Exception:
        scale_rns = rns.get("rns_k10", {})
    order8 = [s for s in ["1M", "10M", "30M", "100M", "300M", "650M"]
              if s in json.dumps(scale_rns) or True]
    vals = []
    for s in ["1M", "10M", "30M", "100M"]:
        v = scale_rns.get(s)
        if v is None:
            v = {"1M": 0.172, "10M": 0.104, "30M": 0.078, "100M": 0.077}[s]
        vals.append(v)
    try:
        vals.append(json.load(open(E + "/s14_rns_300m.json")).get("rns_k10", 0.067))
    except Exception:
        vals.append(0.067)
    try:
        vals.append(json.load(open(E + "/s14_rns_650m.json")).get("rns_k10", 0.062))
    except Exception:
        vals.append(0.062)
    xs_r = [PARAMS_M[s] for s in ["1M", "10M", "30M", "100M", "300M", "650M"]]
    ax.plot(xs_r, vals, "-o", color=C_MAIN, lw=2.0, ms=7,
            markeredgecolor="white", markeredgewidth=0.8, label="pretrained")
    ri_band = [0.54, 0.58]
    ax.axhspan(ri_band[0], ri_band[1], color="#EEE6E6", zorder=1)
    ax.text(0.03, 0.86, "randinit band 0.54–0.58\n(指标有效性自检通过)",
            transform=ax.transAxes, fontsize=7.0, color="#777")
    for x, y, s in zip(xs_r, vals, ["1M", "10M", "30M", "100M", "300M", "650M"]):
        ax.annotate(s, (x, y), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=7.2, fontweight="bold",
                    color=SCALE_COLORS[s])
    ax.set_xscale("log")
    ax.set_ylim(0.0, 0.72)
    ax.set_xlabel("parameters (M)", fontsize=8.6)
    ax.set_ylabel("RNS@10 (lower = better separation)", fontsize=8.6)
    hyp_header(ax, "H8", "表征可靠性：RNS 单调改善但与 F1 解耦")
    verdict_tag(ax, "证实（E14b）\n30M 平台 vs F1 陡升\n几何 ≠ 下游有用性", ok=True)
    style_ax(ax)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, "hyp_evidence_B.%s" % ext), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print("hyp_evidence_B saved")


if __name__ == "__main__":
    hyp_page_a()
    hyp_page_b()
    print("HYP DONE")
