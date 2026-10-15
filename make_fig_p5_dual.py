"""fig_p5_dualchannel: 结果三左图最终版——双通道背离时间轴。

核心信息（回答"左图对泄漏结论的贡献"）：
  同一预训练过程、同一模型、同一批 probe 数据，只换切分方式：
  · random 通道（红）：F1 随预训练曝光单调上涨 —— 模型记住的家族统计
    越多，随机切分（家族重叠）兑现越多 = 记忆积累的兑现曲线
  · family 通道（蓝）：F1 平/降（30M 甚至磨蚀 0.34→0.19）—— 真·家族
    级泛化贴地板，不吃记忆
  两通道起点相近、随曝光持续分叉 —— 背离本身就是"random 高分=记忆兑现"
  的动态签名，是页内三条静态证据链（k-mer/randinit/家族贴地板）的时间轴版。
数据：family = probe_results.jsonl（b59 _ck 行 10 点/尺度）；
     random = random_midpoints_results.jsonl（12 点）+ eval_matrix_results
     （2B/5.8B 终态）。
"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

E = "/mnt/cunyuliu/rna-sc/evidence"
EV = "/mnt/cunyuliu/rna-sc/eval"
FIG = "/mnt/cunyuliu/rna-sc/figs"
C = {"main": "#4878A8", "deep": "#2E5170", "coral": "#D98E73",
     "grey": "#B0B0B0", "amber": "#E5B45A", "teal": "#6FAE9B",
     "ink": "#3A3A3A"}
SC = {"30M": "#6FAE9B", "100M": "#7BA3C7", "300M": "#4878A8",
      "650M": "#2E5170"}


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#8A8A8A")
    ax.spines[["left", "bottom"]].set_linewidth(0.7)
    ax.tick_params(colors=C["ink"], labelsize=8.5, length=3, width=0.7)
    ax.grid(alpha=0.16, ls=":", lw=0.5, color="#8A8A8A")
    ax.set_axisbelow(True)


# ---- family 时间轴（b59 _ck 行）----
fam = defaultdict(dict)
for line in open(os.path.join(EV, "probe_results.jsonl")):
    r = json.loads(line)
    if r.get("n_train", 0) < 20000 or "family" not in r.get("split", ""):
        continue
    run = r.get("run", "")
    nt = r.get("ckpt_nt")
    for arm in ("30M", "100M", "300M", "650M"):
        base = "RNA-Sc-%s_s17_b59" % arm
        if nt and (run == base or run.startswith(base + "_ck")):
            fam[arm][nt] = max(fam[arm].get(nt, 0), r["f1_macro"])

# ---- random 时间轴（中间点 + 终态）----
ran = defaultdict(dict)
for line in open(os.path.join(EV, "random_midpoints_results.jsonl")):
    r = json.loads(line)
    arm = r["run"].split("_s17")[0].replace("RNA-Sc-", "")
    ran[arm][r["ckpt_nt"]] = r["best_f1_macro"]
# 5.8B 终态用 b59_random_delta 预注册判据数字（同 19200/4800 协议、
# 10-13 收口的四尺度配对值），避免 eval_matrix 里旧批次行混入
brd = json.load(open(os.path.join(E, "b59_random_delta.json")))["table"]
for arm in ("30M", "100M", "300M", "650M"):
    ran[arm][5800296014] = brd[arm]["random_f1_5.9B"]

fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.0), sharex=True,
                         gridspec_kw={"hspace": 0.32, "wspace": 0.24})
order = ["30M", "100M", "300M", "650M"]
pos = {"30M": (0, 0), "100M": (0, 1), "300M": (1, 0), "650M": (1, 1)}
for arm in order:
    ax = axes[pos[arm][0]][pos[arm][1]]
    fts = sorted(fam[arm])
    rts = sorted(ran[arm])
    ax.plot([n / 1e9 for n in fts], [fam[arm][n] for n in fts], "-o",
            color=C["main"], lw=2.0, ms=5,
            label="family 切分（家族不相交）")
    ax.plot([n / 1e9 for n in rts], [ran[arm][n] for n in rts], "-s",
            color=C["coral"], lw=2.0, ms=5,
            label="random 切分（家族重叠）")
    # 背离箭头（首→尾 gap 变化）
    if fts and rts:
        f0, f1 = fam[arm][fts[0]], fam[arm][fts[-1]]
        r0, r1 = ran[arm][rts[0]], ran[arm][rts[-1]]
        ax.annotate("起点 Δ=%.2f" % (r0 - f0),
                    (fts[0] / 1e9, (f0 + r0) / 2), fontsize=7.8,
                    color="#707070", ha="left", va="center")
        ax.annotate("终点 Δ=%.2f" % (r1 - f1),
                    (fts[-1] / 1e9 - 0.15, (f1 + r1) / 2), fontsize=7.8,
                    color="#B26A50" if (r1 - f1) > (r0 - f0) else "#707070",
                    ha="right", va="center",
                    fontweight="bold" if (r1 - f1) > (r0 - f0) else "normal")
    ax.set_title("%s（%d 层）" % (arm, {"30M": 12, "100M": 23,
                                       "300M": 24, "650M": 28}[arm]),
                 fontsize=10.5, loc="left", pad=5, color=SC[arm],
                 fontweight="bold")
    if pos[arm][0] == 1:
        ax.set_xlabel("预训练曝光（B nt）", fontsize=9.5, color=C["ink"])
    if pos[arm][1] == 0:
        ax.set_ylabel("probe F1", fontsize=9.5, color=C["ink"])
    ax.set_xlim(0, 6.6)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    style(ax)

fig.suptitle(
    "双通道背离 = 泄漏红利的动态签名：random 涨（记忆兑现）vs family 平/降（真泛化地板）",
    fontsize=12, y=0.995, color=C["ink"])
fig.savefig(os.path.join(FIG, "fig_p5_dualchannel.png"), dpi=200,
            bbox_inches="tight")
plt.close(fig)
print("fig_p5_dualchannel saved")
for arm in order:
    rts = sorted(ran[arm])
    print(arm, "random pts:", [(round(n / 1e9, 1), ran[arm][n]) for n in rts])
