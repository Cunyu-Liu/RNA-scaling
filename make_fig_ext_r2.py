"""fig_ext_emergence_v5r2: 页 6 右下（外部佐证）重画——v5 色板+补 our 曲线。"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"
C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A", "acc": "#C27BA0"}

rows = [json.loads(l) for l in open(os.path.join(EV, "probe_structure_ext.jsonl"))]
by_run = defaultdict(dict)
for r in rows:
    if "randinit" in r["run"] or "s29" in r["run"]:
        continue
    by_run[r["run"]][r["layer"]] = r.get("f1_macro", r.get("f1", 0))

fig, ax = plt.subplots(figsize=(9.8, 5.6))
colors = {"RiNALMo-rinalmo-micro-33M": C["teal"],
          "RiNALMo-rinalmo-mega-148M": C["amber"],
          "RiNALMo-rinalmo-giga-650M": C["acc"],
          "RNA-Sc-100M_s17": "#7BA3C7",
          "RNA-Sc-650M_s17": C["deep"],
          "RNA-FM-96M": "#8A8A8A",
          "NucleicBERT-404M": "#1B7A3D"}
labels = {"RiNALMo-rinalmo-micro-33M": "RiNALMo-micro 33M",
          "RiNALMo-rinalmo-mega-148M": "RiNALMo-mega 148M",
          "RiNALMo-rinalmo-giga-650M": "RiNALMo-giga 651M",
          "RNA-Sc-100M_s17": "ours-100M",
          "RNA-Sc-650M_s17": "ours-650M",
          "RNA-FM-96M": "RNA-FM 96M",
          "NucleicBERT-404M": "NucleicBERT 404M"}
for run, layers in by_run.items():
    if run not in colors:
        continue
    ls = sorted(layers)
    rels = [l / (max(ls) or 1) for l in ls]
    f1s = [layers[l] for l in ls]
    lw = 2.6 if "RiNALMo" in run else 1.7
    ax.plot(rels, f1s, "-o", color=colors[run], lw=lw, ms=4,
            label=labels.get(run, run), alpha=0.92, zorder=3)
    bi = int(np.argmax(f1s))
    ax.scatter([rels[bi]], [f1s[bi]], s=90, color=colors[run], zorder=5,
               marker="*", edgecolors="white", linewidths=0.8)
ax.axhline(0.3799, ls=":", lw=1.4, color="#999")
ax.text(0.99, 0.385, "randinit 地板 0.380（全部架构一致）", ha="right",
        fontsize=8.4, color="#777")
ax.set_xlabel("相对深度", fontsize=10, color=C["ink"])
ax.set_ylabel("bpRNA 结构 probe F1（线性头）", fontsize=10, color=C["ink"])
ax.set_ylim(0.35, 0.78)
ax.set_title("④ 外部佐证：RiNALMo 深层陡升（giga 0.728）——结构涌现非个例",
             fontsize=11, loc="left", pad=8, color=C["ink"])
ax.legend(fontsize=8.4, loc="lower left", ncol=2, framealpha=0.92)
ax.text(0.5, 0.60, "判读：giga > mega 深层增益 = 涌现的层维度证据\n官方 ckpt 单点无时间轴——时间轴涌现仅自训家族可测（S6）",
        ha="center", transform=ax.transAxes, fontsize=8.4, color="#555",
        bbox=dict(fc="#FBFBFB", ec="#BBB", boxstyle="round,pad=0.35", alpha=0.92))
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(colors=C["ink"], labelsize=8.5)
ax.grid(alpha=0.16, ls=":", lw=0.5)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_ext_emergence_v5r2.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_ext_emergence_v5r2 saved")
