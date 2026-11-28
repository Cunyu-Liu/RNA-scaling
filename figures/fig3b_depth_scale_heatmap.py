#!/usr/bin/env /usr/bin/python3
# Fig.3b — Depth x scale heatmap of family signal (Q4).
# Question: Where does family signal become readable, and how does that depth shift with scale?
# Input SHA-256 (verified at runtime):
# probe_results.jsonl: a9bc5f93232ed51d094e66634e2609794e1221af6667d20beafc5a778e0e0315
# s1_final_verdict.json: 757b78ab77f2609ac294826b287d3bb6885fcb2a82e64de6d4a622800e460018
# Caliber: rna_type family per-layer macro-F1, final ckpt (max ckpt_nt).
#   1M/10M/30M/100M = mean across seeds {s17,s29,s43}; 300M/650M = single-seed s17 (hollow marker).
#   Best-layer marker = rel_mean from s1_final_verdict five_scale_table (mean rel_depth of per-seed best layer).

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
OUT = ROOT / "figs_v6"
B = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/eval_evidence_logs")
INPUTS = {
    "probe": (B / "eval" / "probe_results.jsonl", "a9bc5f93232ed51d094e66634e2609794e1221af6667d20beafc5a778e0e0315"),
    "verdict": (B / "evidence" / "s1_final_verdict.json", "757b78ab77f2609ac294826b287d3bb6885fcb2a82e64de6d4a622800e460018"),
}
BLUE = "#0F4D92"
GREY = "#767676"
DARK = "#272727"
SCALES = ["1M", "10M", "30M", "100M", "300M", "650M"]
MULTISEED = {"1M", "10M", "30M", "100M"}
SEEDS = ["s17", "s29", "s43"]
REF_REL = {"1M": 0.471, "10M": 0.141, "30M": 0.788, "100M": 0.864, "300M": 0.957, "650M": 0.296}
NBINS = 10


def load_inputs():
    loaded = {}
    for key, (path, expected) in INPUTS.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"SHA-256 mismatch for {path}: {digest}")
        loaded[key] = path
    return loaded


def main():
    paths = load_inputs()
    rows = [json.loads(l) for l in open(paths["probe"])]
    verdict = json.loads(paths["verdict"].read_text())
    fst = verdict["five_scale_table"]

    bin_edges = np.linspace(0, 1, NBINS + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    heat = np.full((len(SCALES), NBINS), np.nan)
    marker_rel = {}
    best_f1 = {}
    detail = {}
    for si, scale in enumerate(SCALES):
        seeds = SEEDS if scale in MULTISEED else ["s17"]
        per_seed_layer = []
        per_seed_best_rel = []
        n_layers = None
        for seed in seeds:
            run = f"RNA-Sc-{scale}_{seed}"
            rr = [r for r in rows if r["run"] == run]
            mx = max(r["ckpt_nt"] for r in rr)
            fin = [r for r in rr if r["ckpt_nt"] == mx]
            L = max(r["layer"] for r in fin) + 1
            n_layers = L
            f1 = np.array([next(r["f1_macro"] for r in fin if r["layer"] == li) for li in range(L)])
            rel = np.arange(L) / (L - 1)
            per_seed_layer.append((rel, f1))
            bl = int(np.argmax(f1))
            per_seed_best_rel.append(bl / (L - 1))
        # mean F1 across seeds on a common rel_depth grid (per-layer, aligned by rel)
        grid = np.linspace(0, 1, 200)
        interp = np.mean([np.interp(grid, rel, f1) for rel, f1 in per_seed_layer], axis=0)
        for b in range(NBINS):
            mask = (grid >= bin_edges[b]) & (grid < bin_edges[b + 1] if b < NBINS - 1 else grid <= 1.0)
            heat[si, b] = interp[mask].mean()
        rel_mean = float(np.mean(per_seed_best_rel))
        # five_scale_table holds 1M/10M/30M/100M/650M; 300M is single-seed, computed from ledger.
        auth_rel = fst[scale]["rel_mean"] if scale in fst else round(rel_mean, 3)
        auth_f1 = fst[scale]["f1_mean"] if scale in fst else round(float(np.mean([f1.max() for _, f1 in per_seed_layer])), 4)
        marker_rel[scale] = auth_rel
        best_f1[scale] = auth_f1
        detail[scale] = {"n_layers": n_layers, "seeds": seeds,
                         "computed_rel_mean": round(rel_mean, 4),
                         "authoritative_rel_mean": auth_rel}
        # 3rd verification: computed mean best-layer rel matches authoritative rel_mean
        assert abs(rel_mean - auth_rel) < 0.0015, (scale, rel_mean, auth_rel)
        assert abs(auth_rel - REF_REL[scale]) < 1e-9, (scale, auth_rel, REF_REL[scale])

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    im = ax.imshow(heat, aspect="auto", cmap="viridis", origin="upper",
                   vmin=np.nanmin(heat), vmax=np.nanmax(heat),
                   extent=[0, 1, len(SCALES) - 0.5, -0.5])
    for si, scale in enumerate(SCALES):
        rel = marker_rel[scale]
        single = scale not in MULTISEED
        ax.scatter([rel], [si], marker="o" if single else "D", s=90,
                   facecolors="none" if single else "#FFFFFF",
                   edgecolors="#FFFFFF" if single else "#B64342",
                   linewidths=1.8, zorder=5)
        ax.text(rel, si - 0.32, f"{rel:.3f}", ha="center", va="bottom",
                fontsize=8, color="#FFFFFF", fontweight="bold")
    ax.set_yticks(range(len(SCALES)))
    ax.set_yticklabels([f"{s}" + (" (s17)" if s not in MULTISEED else " (3-seed mean)") for s in SCALES])
    ax.set_xticks(bin_centers)
    ax.set_xticklabels([f"{bin_edges[i]:.1f}–{bin_edges[i+1]:.1f}" for i in range(NBINS)], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("relative depth  layer / (n_layers − 1)")
    ax.set_ylabel("model scale")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("family macro-F1 (mean over seeds)")
    ax.set_title("Where does family signal become readable, and how does that depth shift with scale?",
                 loc="left", fontsize=11, fontweight="bold", pad=10)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0], [0], marker="D", color="w", markerfacecolor="#FFFFFF",
                              markeredgecolor="#B64342", markersize=8, label="best-layer rel_mean (3-seed)"),
                       Line2D([0], [0], marker="o", color="w", markerfacecolor="none",
                              markeredgecolor="#FFFFFF", markersize=8, label="best-layer (single-seed s17)")],
              frameon=False, loc="lower right", fontsize=8)
    fig.text(0.01, -0.06,
             "Marker = mean relative depth of the per-seed best readout layer (s1_final_verdict five_scale_table). "
             "1M mid → 10M early (dip) → 30M/100M/300M deep → 650M shallow reversal. Single-seed scales: no error bars.",
             fontsize=8.5, color=GREY, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig3b_depth_scale_heatmap.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig3b_depth_scale_heatmap.pdf", bbox_inches="tight")
    plt.close(fig)
    print("FIG3B_OK")
    print(json.dumps({"marker_rel": marker_rel, "best_f1": best_f1, "detail": detail}, indent=2))


if __name__ == "__main__":
    main()