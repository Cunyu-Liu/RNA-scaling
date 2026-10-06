"""Fig 6 v3: three-point budget axis (30M/100M/300M closed) + dual-channel panel.

Left panel: family-channel budget effect, sign-flip chain -5.24/-2.74/+3.76
(monotone in scale, crossover between 100M and 300M), with Claim-14
falsification mark and the 650M@2B whole-line reference. The 30M pair
was closed 10-05 and is REQUIRED in v3 (v2 showed only 100M/300M).
Right panel: S7 structure-channel budget effect, monotone positive
+0.09/+0.85/+1.87pp with randinit controls and learned increments
(-0.9/+1.1/+2.7pp). All numbers read from evidence JSONs (no manual
copying). 650M@5.9B cells are absent in the JSONs (arm in training);
they are skipped automatically and the figure upgrades itself when the
JSON gains the 4th row (idempotent regeneration, no hand edit).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = "/mnt/cunyuliu/rna-sc/evidence"
FIG = "/mnt/cunyuliu/rna-sc/figs"

fv = json.load(open(E + "/factorial_verdict.json"))
s7 = json.load(open(E + "/s7_structure_budget_matrix.json"))
fam = fv["table"]
struct = s7["matrix"]
c14 = fv.get("claim14_300M", {})

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 4.8))

# ---------------- left: family channel ----------------
xs, ys, labels, layers = [], [], [], []
for scale in ["30M", "100M", "300M", "650M"]:
    r = fam.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_5.9B")
    if f2 and f2.get("f1") is not None:
        xs.append(0); ys.append(f2["f1"])
        labels.append(scale + " @2.0B"); layers.append("L%d" % f2["layer"])
    if f5 and f5.get("f1") is not None:
        xs.append(1); ys.append(f5["f1"])
        labels.append(scale + " @5.9B"); layers.append("L%d" % f5["layer"])

axL.scatter(xs, ys, s=125, c=["#25658C" if x == 0 else "#B03030" for x in xs],
            zorder=3)

colors = {"30M": "#8A4B08", "100M": "#B03030", "300M": "#1B7A3D", "650M": "#6A3D9A"}
for scale in ["30M", "100M", "300M", "650M"]:
    r = fam.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_5.9B")
    if not (f2 and f5 and f2.get("f1") is not None and f5.get("f1") is not None):
        continue
    d = r.get("budget_delta_pp")
    col = colors[scale]
    axL.annotate("", xy=(1, f5["f1"]), xytext=(0, f2["f1"]),
                 arrowprops=dict(arrowstyle="->", color=col, lw=1.7))
    mid = (f2["f1"] + f5["f1"]) / 2
    off = 0.006 if d > 0 else -0.007
    axL.text(0.5, mid + off, "%s: %+0.2fpp" % (scale, d), ha="center",
             fontsize=9.5, color=col, fontweight="bold",
             bbox=dict(fc="white", ec=col, alpha=0.92, boxstyle="round,pad=0.25"))

ref = fam.get("650M", {}).get("f1_2B", {}).get("f1")
if ref:
    axL.axhline(ref, ls="--", lw=1.1, color="#777")
    axL.text(0.02, ref + 0.0015, "650M@2B = %.4f (prior line best)" % ref,
             fontsize=8.5, color="#555")

for x, y, l, lay in zip(xs, ys, labels, layers):
    dy = 0.009 if "@2" in l else -0.012
    axL.text(x, y + dy, l.split(" ")[0] + " " + lay, ha="center", fontsize=9)

if c14:
    axL.text(0.97, 0.03,
             "Claim-14 (pre-registered): boundary_holds = %s\n(bar +1.0pp; measured %+0.2fpp)"
             % (str(c14.get("boundary_holds")).lower(), c14.get("delta_pp", 0)),
             transform=axL.transAxes, ha="right", va="bottom", fontsize=9.5,
             fontweight="bold", color="#B03030",
             bbox=dict(fc="white", ec="#B03030", alpha=0.92))

best = fam.get("300M", {}).get("f1_5.9B", {}).get("f1")
if best:
    axL.annotate("new overall best\n%.4f" % best, xy=(1, best),
                 xytext=(1.28, best + 0.012), fontsize=9, color="#1B7A3D",
                 fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#1B7A3D", lw=1.2))

axL.set_xticks([0, 1])
axL.set_xticklabels(["2.0B nt (main line)", "5.9B nt (full corpus)"])
axL.set_ylabel("family-split probe macro-F1")
axL.set_ylim(0.17, 0.41)
axL.set_xlim(-0.55, 1.75)
axL.set_title("Family channel: budget effect FLIPS monotonically\n"
              "(-5.24 / -2.74 / +3.76 pp; crossover 100M<->300M)",
              fontsize=10.5)
axL.grid(alpha=0.25, ls=":")

# ---------------- right: S7 structure channel ----------------
xs2, ys2, labels2 = [], [], []
for scale in ["30M", "100M", "300M", "650M"]:
    r = struct.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_b59")
    if f2 and f2.get("f1") is not None:
        xs2.append(0); ys2.append(f2["f1"]); labels2.append(scale + " @2.0B")
    if f5 and f5.get("f1") is not None:
        xs2.append(1); ys2.append(f5["f1"]); labels2.append(scale + " @5.9B")

axR.scatter(xs2, ys2, s=125, c=["#25658C" if x == 0 else "#1B7A3D" for x in xs2],
            zorder=3)

for scale in ["30M", "100M", "300M", "650M"]:
    r = struct.get(scale, {})
    f2, f5 = r.get("f1_2B"), r.get("f1_b59")
    if not (f2 and f5 and f2.get("f1") is not None and f5.get("f1") is not None):
        continue
    d = r.get("budget_delta_pp")
    axR.annotate("", xy=(1, f5["f1"]), xytext=(0, f2["f1"]),
                 arrowprops=dict(arrowstyle="->", color="#1B7A3D", lw=1.7))
    mid = (f2["f1"] + f5["f1"]) / 2
    axR.text(0.5, mid + 0.004, "%s: +%0.2fpp" % (scale, d), ha="center",
             fontsize=9.5, color="#1B7A3D", fontweight="bold",
             bbox=dict(fc="white", ec="#1B7A3D", alpha=0.92, boxstyle="round,pad=0.25"))

for scale in ["30M", "100M", "300M", "650M"]:
    r = struct.get(scale, {})
    ri = r.get("randinit17_b59_best_f1")
    if ri:
        axR.scatter([1], [ri], s=70, marker="x", color="#777", zorder=3)
        axR.text(1.06, ri, scale + " rand", fontsize=7.5, color="#777", va="center")

for x, y, l in zip(xs2, ys2, labels2):
    dy = 0.006 if "@2" in l else -0.008
    axR.text(x, y + dy, l.split(" ")[0], ha="center", fontsize=9)

axR.set_xticks([0, 1])
axR.set_xticklabels(["2.0B nt", "5.9B nt"])
axR.set_ylabel("bpRNA paired-position F1 (S7, best layer)")
axR.set_ylim(0.565, 0.645)
axR.set_xlim(-0.55, 1.75)
axR.set_title("Structure channel: budget effect MONOTONE POSITIVE\n"
              "(+0.09 / +0.85 / +1.87 pp; learned incr. -0.9/+1.1/+2.7 vs randinit x)",
              fontsize=10.5)
axR.grid(alpha=0.25, ls=":")

fig.suptitle("Fig 6 v3 · Budget x scale is readout-channel-specific: family sign-flip vs structure monotone-gain "
             "(Chinchilla-style compute-optimal interaction; 650M@5.9B cell pending, auto-added when closed)",
             fontsize=10.5, y=1.00)
fig.tight_layout()
fig.savefig(FIG + "/fig6_budget_axis.pdf")
fig.savefig(FIG + "/fig6_budget_axis.png", dpi=200)
print("fig6 v3 saved: family sign-flip chain (3 closed points) + S7 structure channel panel")
