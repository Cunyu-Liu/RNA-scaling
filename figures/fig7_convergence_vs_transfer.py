#!/usr/bin/env /usr/bin/python3
# Fig.7 — Convergence vs transfer (Q1/Q6).
# Question: Does lower pretraining loss mean better transfer? No — the budget effect reverses by scale.
# Input SHA-256 (verified at runtime), manifests from backup runs_final2_ckpt/runs/<run>/manifest.json:
# RNA-Sc-10M_s17: c8ac0a39fcdba3bf5c20f52f0f5caa220d2a61eca732c141467464d223e9fba4
# RNA-Sc-30M_s17: 3ad9c33665376f977db84fe6304c1abb05d1272e44decba221e2ea60b06723a4
# RNA-Sc-100M_s17: 933e25d85dc372b80bcdace77ffffc613c4eeda44b6aefdd0d2e1bf841d0f746
# RNA-Sc-300M_s17: 6465fa4b74a3b34892188586841e60900100570768a6687a0825a71200e0cfb1
# RNA-Sc-650M_s17: f657ea391fab327c3ff76691ec8f1f3ea851bb54af4c55ec55dbccb4d33afbfa
# RNA-Sc-30M_s17_b59: d1a5633a9b53dcf4a62c7a91e3df97b137f5afee2cdd3faa35665e9b0e782436
# RNA-Sc-100M_s17_b59: 2ec330f4666fbcc396cfaf0dce251a7f610483abd6d97950f3d5f1c40b342dd0
# RNA-Sc-300M_s17_b59: 23577e4fe93e1b853b14a4e4741934beb6388b8267b49a980786baad69a923d9
# RNA-Sc-650M_s17_b59: 8fe906fc6f5fa621f7e194329f08b589a943c664ef6c829ced623efda3c0f957
# factorial_verdict.json: 32b9b2d5d706b0e53085c9ea5740bb35db6d2f2cdc391256fa15a1ed232f2f2c
# Caliber: val_loss every 100M nt; terminal slope = linear fit of last 4 points (per 100M nt).
#   Panel c budget deltas = single-seed factorial (P2.11 remeasure: magnitudes within noise).

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
OUT = ROOT / "figs_v6"
B = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
RUNS = B / "runs_final2_ckpt" / "runs"
MANIFEST_SHA = {
    "RNA-Sc-10M_s17": "c8ac0a39fcdba3bf5c20f52f0f5caa220d2a61eca732c141467464d223e9fba4",
    "RNA-Sc-30M_s17": "3ad9c33665376f977db84fe6304c1abb05d1272e44decba221e2ea60b06723a4",
    "RNA-Sc-100M_s17": "933e25d85dc372b80bcdace77ffffc613c4eeda44b6aefdd0d2e1bf841d0f746",
    "RNA-Sc-300M_s17": "6465fa4b74a3b34892188586841e60900100570768a6687a0825a71200e0cfb1",
    "RNA-Sc-650M_s17": "f657ea391fab327c3ff76691ec8f1f3ea851bb54af4c55ec55dbccb4d33afbfa",
    "RNA-Sc-30M_s17_b59": "d1a5633a9b53dcf4a62c7a91e3df97b137f5afee2cdd3faa35665e9b0e782436",
    "RNA-Sc-100M_s17_b59": "2ec330f4666fbcc396cfaf0dce251a7f610483abd6d97950f3d5f1c40b342dd0",
    "RNA-Sc-300M_s17_b59": "23577e4fe93e1b853b14a4e4741934beb6388b8267b49a980786baad69a923d9",
    "RNA-Sc-650M_s17_b59": "8fe906fc6f5fa621f7e194329f08b589a943c664ef6c829ced623efda3c0f957",
}
FACT_SHA = "32b9b2d5d706b0e53085c9ea5740bb35db6d2f2cdc391256fa15a1ed232f2f2c"
BLUE = "#0F4D92"
BLUE2 = "#3775BA"
GREEN = "#42949E"
RED = "#B64342"
GREY = "#767676"
DARK = "#272727"
SCALE_COLOR = {"30M": "#42949E", "100M": "#3775BA", "300M": "#0F4D92", "650M": "#B64342"}
REF_FINAL = {("650M", "2B"): 0.7757, ("650M", "59B"): 0.7491,
             ("100M", "2B"): 0.7964, ("100M", "59B"): 0.7626,
             ("300M", "2B"): 0.7801, ("300M", "59B"): 0.7503}
REF_DELTA_PP = {"30M": -5.24, "100M": -2.74, "300M": 3.76, "650M": 1.15}


def load_traj(run):
    p = RUNS / run / "manifest.json"
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if digest != MANIFEST_SHA[run]:
        raise ValueError(f"SHA-256 mismatch for {p}: {digest}")
    v = json.loads(p.read_text())["validations"]
    nt = np.array([x["nt"] for x in v], dtype=float)
    vl = np.array([x["val_loss"] for x in v], dtype=float)
    return nt, vl


def terminal_slope(nt, vl):
    x = nt[-4:] / 1e8
    y = vl[-4:]
    return float(np.polyfit(x, y, 1)[0])


def main():
    fact_path = B / "eval_evidence_logs" / "evidence" / "factorial_verdict.json"
    assert hashlib.sha256(fact_path.read_bytes()).hexdigest() == FACT_SHA
    fact = json.loads(fact_path.read_text())["table"]

    traj = {}
    slopes = {}
    finals = {}
    for run in MANIFEST_SHA:
        nt, vl = load_traj(run)
        traj[run] = (nt, vl)
        slopes[run] = terminal_slope(nt, vl)
        finals[run] = float(vl[-1])
    # 3rd verification: final val losses match contract reference
    for (scale, bud), ref in REF_FINAL.items():
        run = f"RNA-Sc-{scale}_s17" + ("_b59" if bud == "59B" else "")
        assert abs(finals[run] - ref) < 5e-5, (run, finals[run], ref)
    for scale, ref in REF_DELTA_PP.items():
        assert abs(fact[scale]["budget_delta_pp"] - ref) < 1e-9, scale

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (axa, axb, axc) = plt.subplots(1, 3, figsize=(14.0, 4.4),
                                        gridspec_kw={"width_ratios": [1.25, 1.0, 1.0]})

    # panel a: val-loss trajectories, 2B solid + 5.9B dashed
    for scale in ["100M", "300M", "650M"]:
        c = SCALE_COLOR[scale]
        nt2, vl2 = traj[f"RNA-Sc-{scale}_s17"]
        nt5, vl5 = traj[f"RNA-Sc-{scale}_s17_b59"]
        axa.plot(nt2 / 1e9, vl2, "-", color=c, lw=1.8, label=f"{scale} 2B" if scale == "100M" else None)
        axa.plot(nt5 / 1e9, vl5, "--", color=c, lw=1.5)
        axa.scatter([nt2[-1] / 1e9], [vl2[-1]], color=c, s=28, zorder=5)
        axa.scatter([nt5[-1] / 1e9], [vl5[-1]], color=c, s=28, marker="s", zorder=5)
    axa.plot([], [], "-", color=GREY, label="2B iso-token (solid)")
    axa.plot([], [], "--", color=GREY, label="5.9B (dashed)")
    axa.set_xlabel("pretraining tokens (B)")
    axa.set_ylabel("validation loss")
    axa.set_title("a  2B still descending; 5.9B near plateau", loc="left", fontsize=10.5)
    axa.legend(frameon=False, fontsize=7.5, loc="upper right", ncol=2)
    axa.text(0.02, 0.04, "2B terminal slope ~ −0.003/100M\n5.9B ~ −0.0005/100M (≈10× flatter)",
             transform=axa.transAxes, fontsize=8, color=GREY, va="bottom")

    # panel b: terminal slope bars 2B vs 5.9B
    scales_b = ["30M", "100M", "300M", "650M"]
    x = np.arange(len(scales_b))
    s2 = [slopes[f"RNA-Sc-{s}_s17"] for s in scales_b]
    s5 = [slopes[f"RNA-Sc-{s}_s17_b59"] for s in scales_b]
    axb.bar(x - 0.2, s2, 0.4, color=BLUE, label="2B", zorder=3)
    axb.bar(x + 0.2, s5, 0.4, color=GREEN, label="5.9B", zorder=3)
    axb.axhline(0, color=DARK, lw=0.9)
    axb.set_xticks(x)
    axb.set_xticklabels(scales_b)
    axb.set_ylabel("terminal val-loss slope (per 100M nt)")
    axb.set_title("b  5.9B an order of magnitude flatter", loc="left", fontsize=10.5)
    axb.legend(frameon=False, fontsize=8.5)
    for xi, v in zip(x - 0.2, s2):
        axb.text(xi, v - 0.0003, f"{v:.4f}", ha="center", va="top", fontsize=7, color=DARK)
    for xi, v in zip(x + 0.2, s5):
        axb.text(xi, v - 0.0003, f"{v:.4f}", ha="center", va="top", fontsize=7, color=DARK)

    # panel c: delta val loss vs delta family F1 (single-seed factorial)
    for scale in scales_b:
        dv = finals[f"RNA-Sc-{scale}_s17_b59"] - finals[f"RNA-Sc-{scale}_s17"]
        df = fact[scale]["budget_delta_pp"]
        c = SCALE_COLOR[scale]
        axc.scatter([dv], [df], color=c, s=80, zorder=5)
        axc.annotate(f"{scale}\n{df:+.2f}pp", (dv, df), textcoords="offset points",
                     xytext=(8, 6), fontsize=8, color=DARK)
    axc.axhline(0, color=DARK, lw=0.9)
    axc.axvline(0, color=DARK, lw=0.9)
    axc.set_xlabel("Δ val loss (5.9B − 2B);  negative = better LM")
    axc.set_ylabel("Δ family F1 (pp, 5.9B − 2B)")
    axc.set_title("c  Lower loss ≠ better transfer", loc="left", fontsize=10.5)
    axc.text(0.02, 0.96, "100M: lower val loss\nbut F1 drops (reversal)", transform=axc.transAxes,
             fontsize=8, color=RED, va="top")
    axc.text(0.98, 0.04, "single-seed factorial;\nP2.11: magnitudes within noise", transform=axc.transAxes,
             fontsize=7.5, color=GREY, ha="right", va="bottom")

    fig.suptitle("Does lower pretraining loss mean better transfer? No — the budget effect reverses by scale.",
                 fontsize=12, fontweight="bold", x=0.01, ha="left", y=1.03)
    fig.tight_layout()
    fig.savefig(OUT / "fig7_convergence_vs_transfer.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig7_convergence_vs_transfer.pdf", bbox_inches="tight")
    plt.close(fig)
    print("FIG7_OK")
    print(json.dumps({"slopes_per100M": slopes, "final_val": finals,
                      "delta_pp": REF_DELTA_PP}, indent=2))


if __name__ == "__main__":
    main()