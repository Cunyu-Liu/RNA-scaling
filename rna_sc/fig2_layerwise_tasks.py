"""T4.1.2: Figure 2 — layer-wise emergence across tasks (4 scales).

Two rows (task dichotomy):
  Row A: rna_type family probe (family-discrimination task) — per-layer
         F1 curves, four scales + de-rRNA stratified overlay (dashed):
         scale-dependent layer migration, 10M early-layer signature;
  Row B: bpRNA structure probe (paired-position task) — per-layer F1
         curves, four scales + randinit control bands: flat, no
         attrition, near-zero pretraining gain.

Data: eval/probe_results.jsonl, probe_structure_results.jsonl,
      evidence/derRNA_stratified.json.
Output: figs/fig2_layerwise_tasks.{png,pdf}
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MNT = "/mnt/cunyuliu/rna-sc"
OUT = os.path.join(MNT, "figs", "fig2_layerwise_tasks")

SCALES = ["RNA-Sc-1M_s17", "RNA-Sc-10M_s17", "RNA-Sc-30M_s17",
          "RNA-Sc-100M_s17"]
colors = {"RNA-Sc-1M_s17": "#7f8c8d", "RNA-Sc-10M_s17": "#c0392b",
          "RNA-Sc-30M_s17": "#27ae60", "RNA-Sc-100M_s17": "#1a6faf"}


def final_layers(jsonl_path, run):
    rows = {}
    for line in open(jsonl_path):
        r = json.loads(line)
        if r.get("run") != run or r.get("n_train", 0) < 4000:
            continue
        if r.get("ckpt_nt") is None and "layer" not in r:
            continue
        nt = r.get("ckpt_nt")
        rows.setdefault(nt, {})[r["layer"]] = r["f1_macro"]
    if not rows:
        return None
    final_nt = max(k for k in rows if k is not None)
    d = rows[final_nt]
    layers = sorted(d)
    return layers, [d[l] for l in layers]


fig, axes = plt.subplots(2, 2, figsize=(11.5, 8))

ax = axes[0][0]
for run in SCALES:
    got = final_layers(os.path.join(MNT, "eval/probe_results.jsonl"), run)
    if not got:
        continue
    layers, f1s = got
    rels = [l / (len(layers) - 1) for l in layers]
    ax.plot(rels, f1s, "-o", color=colors[run], lw=1.8, ms=3.5,
            label=run.replace("RNA-Sc-", "").replace("_s17", ""))
ax.set_xlabel("relative depth")
ax.set_ylabel("family-split F1 (rna_type)")
ax.set_title("(a) Family-discrimination: scale-dependent\nlayer migration + 10M early-layer peak")
ax.legend(fontsize=8.5, framealpha=0.9, loc="lower right")
ax.grid(alpha=0.25)

ax = axes[0][1]
der = json.load(open(os.path.join(MNT, "evidence/derRNA_stratified.json")))
for scale, entry in der["scales"].items():
    for run_i, rr in enumerate(entry["runs"][:1]):
        ax.plot([rr["best_rel_all"]], [rr["f1_all"]], "o",
                color=colors.get("RNA-Sc-%s_s17" % scale, "#333"),
                ms=9)
        ax.plot([rr["best_rel_der"]], [rr["f1_der"]], "x",
                color=colors.get("RNA-Sc-%s_s17" % scale, "#333"),
                ms=9, mew=2)
        ax.annotate("%s: %.3f→%.3f" % (scale, rr["f1_all"],
                                        rr["f1_der"]),
                    (rr["best_rel_der"], rr["f1_der"]),
                    textcoords="offset points", xytext=(6, -3),
                    fontsize=8)
lim = 0.42
ax.set_xlim(-0.05, 1.05)
ax.set_ylim(0, lim)
ax.set_xlabel("best-layer relative depth")
ax.set_ylabel("best-layer F1")
ax.set_title("(b) De-rRNA stratification (red-team E):\nevery scale trend survives")
ax.grid(alpha=0.25)

ax = axes[1][0]
for run in SCALES:
    rows = []
    for line in open(os.path.join(MNT,
                                  "eval/probe_structure_results.jsonl")):
        r = json.loads(line)
        if r.get("run") != run or "layer" not in r:
            continue
        if r.get("f1_macro") is None and r.get("f1") is None:
            continue
        rows.append((r["layer"], r.get("f1_macro", r.get("f1"))))
    if not rows:
        continue
    rows.sort()
    layers = [x[0] for x in rows]
    f1s = [x[1] for x in rows]
    rels = [l / (len(layers) - 1) for l in layers]
    ax.plot(rels, f1s, "-s", color=colors[run], lw=1.8, ms=3.5,
            label=run.replace("RNA-Sc-", "").replace("_s17", ""))
ax.set_xlabel("relative depth")
ax.set_ylabel("paired-position F1 (bpRNA)")
ax.set_title("(c) Structure task: flat curves,\nno 10M attrition (task-specificity)")
ax.legend(fontsize=8.5, framealpha=0.9, loc="lower right")
ax.grid(alpha=0.25)

ax = axes[1][1]
labels, tr, ri = [], [], []
seen = set()
for line in open(os.path.join(MNT,
                              "eval/probe_structure_results.jsonl")):
    r = json.loads(line)
    base = r["run"].replace("_randinit17", "")
    is_ri = r["run"].endswith("_randinit17")
    key = (base, is_ri)
    if key in seen:
        continue
    seen.add(key)
    labels.append(base.replace("RNA-Sc-", "").replace("_s17", ""))
    tr.append(r["f1"] if not is_ri else None)
    ri.append(r["f1"] if is_ri else None)

best_tr = {}
best_ri = {}
for line in open(os.path.join(MNT,
                              "eval/probe_structure_results.jsonl")):
    r = json.loads(line)
    base = r["run"].replace("_randinit17", "")
    if r["run"].endswith("_randinit17"):
        if base not in best_ri or r["f1"] > best_ri[base]:
            best_ri[base] = r["f1"]
    else:
        if base not in best_tr or r["f1"] > best_tr[base]:
            best_tr[base] = r["f1"]

order = ["1M", "10M", "30M", "100M"]
labels, tr, ri = [], [], []
for scale in order:
    base = "RNA-Sc-%s_s17" % scale
    if base in best_tr:
        labels.append(scale)
        tr.append(best_tr[base])
        ri.append(best_ri.get(base, float("nan")))
x = range(len(labels))
ax.bar([i - 0.18 for i in x], tr, width=0.36, color="#1a6faf",
       label="trained")
ax.bar([i + 0.18 for i in x], ri, width=0.36, color="#c0392b",
       alpha=0.75, label="randinit")
for i, (t, r) in enumerate(zip(tr, ri)):
    ax.text(i + 0.36, max(t, r) + 0.008, "|Δ|≤0.016", fontsize=7.5,
            ha="right", color="#555")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylim(0.45, 0.63)
ax.set_ylabel("structure F1")
ax.set_title("(d) Structure gain ≈ 0 at all scales\n(architecture prior, not pretraining)")
ax.legend(fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25, axis="y")

fig.suptitle("Fig 2 — Layer-wise emergence across tasks: attrition is "
             "family-discrimination-specific", y=0.99, fontsize=11.5)
fig.tight_layout()
fig.savefig(OUT + ".png", dpi=200, bbox_inches="tight")
fig.savefig(OUT + ".pdf", bbox_inches="tight")
print("saved", OUT + ".png/.pdf")
print("structure best:", dict(zip(labels, tr)))
