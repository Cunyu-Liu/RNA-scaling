#!/usr/bin/env /usr/bin/python3
"""Register new P2.8/9/10/11/12 + convergence + fig3b numbers into sections/*_numbers.csv.
Also emits convergence_evidence.json (derived terminal slopes) for provenance."""
import csv, json, hashlib
from pathlib import Path
import numpy as np

ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究")
SEC = ROOT / "论文重写_P1_20261125/sections"
B = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
P2 = "补证_P2_20261125/results"

# --- convergence evidence (derived slopes from manifest validations) ---
RUNS = B / "runs_final2_ckpt/runs"
conv = {}
for run in ["RNA-Sc-10M_s17","RNA-Sc-30M_s17","RNA-Sc-100M_s17","RNA-Sc-300M_s17","RNA-Sc-650M_s17",
            "RNA-Sc-30M_s17_b59","RNA-Sc-100M_s17_b59","RNA-Sc-300M_s17_b59","RNA-Sc-650M_s17_b59"]:
    v = json.loads((RUNS/run/"manifest.json").read_text())["validations"]
    nt = np.array([x["nt"] for x in v]); vl = np.array([x["val_loss"] for x in v])
    slope = float(np.polyfit(nt[-4:]/1e8, vl[-4:], 1)[0])
    conv[run] = {"final_val_loss": float(vl[-1]), "terminal_slope_per100M": round(slope, 6),
                 "final_nt": int(nt[-1]), "n_validations": len(v)}
conv_path = ROOT/P2/"P2_12/convergence_evidence.json"
conv_path.parent.mkdir(parents=True, exist_ok=True)
conv_path.write_text(json.dumps(conv, indent=2))
print("wrote", conv_path)

def append(fname, rows, note_col="caliber"):
    p = SEC/fname
    with open(p, encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    nc = note_col if note_col in header else header[-1]
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for item, value, source, note in rows:
            w.writerow([item, value, source, note])
    print("appended", len(rows), "to", fname)

S8 = f"{P2}/P2_8"
# sec45_q5
append("sec45_q5_numbers.csv", [
 ("P2.8 650M attn_query absolute F1","0.5835",f"{S8}/650M_summary.json:positions.attn_query.f1","per-token paired-position F1, converged; 650M L15"),
 ("P2.8 650M resid_post absolute F1","0.5562",f"{S8}/650M_summary.json:positions.resid_post.f1","per-token paired-position F1, converged; 650M L15; authoritative caliber"),
 ("P2.8 650M rotation control F1","0.5478",f"{S8}/650M_summary.json:positions.resid_rot17.f1","random-rotation control, does not collapse"),
 ("P2.8 650M max net gain (resid_post)","+0.021",f"{S8}/650M_summary.json:positions.resid_post.f1; {S8}/650M_randinit17_summary.json:positions.resid_post.f1","trained-randinit 0.5562-0.5356=0.0206 displayed +0.021"),
 ("P2.8 650M attn_query net gain","+0.009",f"{S8}/650M_summary.json:positions.attn_query.f1; {S8}/650M_randinit17_summary.json:positions.attn_query.f1","trained-randinit 0.5835-0.5749=0.0086 displayed +0.009"),
 ("P2.8 per-token trivial floor","0.54",f"{S8}/p2_8_report.md","approximate trivial floor ~0.54; limited metric discriminability"),
 ("P2.10 converged authoritative F1","0.5562",f"{P2}/P2_10/p2_10_report.md","converged caliber authoritative; supersedes unconverged 0.5973/0.6101"),
 ("P2.9 MLM loss increase after erasure","+0.003",f"{P2}/P2_9/p2_9_report.md","INLP erasure vs random-direction control ~0; weak E1"),
 ("P2.9 probe AUC after 12 rounds","0.64",f"{P2}/P2_9/p2_9_report.md","erasure incomplete; pairing information distributed"),
 ("P2.9 INLP rounds","12",f"{P2}/P2_9/p2_9_report.md","12 erasure rounds; AUC still 0.64"),
])
# sec46_q6
S11 = f"{P2}/P2_11/budget_effect_paired_4scale.json"
append("sec46_q6_numbers.csv", [
 ("P2.12 30M paired budget effect","-5.86",f"{S11}:30M.budget_effect_pp_mean","recovered pool n=10 paired; mean -5.858 displayed -5.86; 0/10 positive"),
 ("P2.12 30M paired SD","0.91",f"{S11}:30M.budget_effect_pp_sd","sample SD ddof=1; 0.908"),
 ("P2.12 30M paired SEM","0.287",f"{S11}:30M.budget_effect_pp_sem","SD/sqrt(10)"),
 ("P2.12 100M paired budget effect","-1.65",f"{S11}:100M.budget_effect_pp_mean","mean -1.648 displayed -1.65; 1/10 positive"),
 ("P2.12 100M paired SD","1.42",f"{S11}:100M.budget_effect_pp_sd","1.421"),
 ("P2.12 100M paired SEM","0.449",f"{S11}:100M.budget_effect_pp_sem","SD/sqrt(10)"),
 ("P2.11 300M paired budget effect","-0.74",f"{S11}:300M.budget_effect_pp_mean","5/10 positive; uncertain; original +3.76 not reproduced"),
 ("P2.11 300M paired SD","4.38",f"{S11}:300M.budget_effect_pp_sd","4.377"),
 ("P2.11 300M paired SEM","1.384",f"{S11}:300M.budget_effect_pp_sem","SD/sqrt(10)"),
 ("P2.11 650M paired budget effect","+3.06",f"{S11}:650M.budget_effect_pp_mean","mean 3.056 displayed +3.06; 9/10 positive; sign robust"),
 ("P2.11 650M paired SD","2.68",f"{S11}:650M.budget_effect_pp_sd","2.678"),
 ("P2.11 650M paired SEM","0.847",f"{S11}:650M.budget_effect_pp_sem","SD/sqrt(10)"),
 ("P2.12 30M F1 2B mean","0.2560",f"{P2}/P2_11/30M_2B/summary.json:mean_f1","10 runs mean; recovered pool"),
 ("P2.12 30M F1 5.9B mean","0.1974",f"{P2}/P2_11/30M_59B/summary.json:mean_f1","10 runs mean"),
 ("P2.12 100M F1 2B mean","0.3153",f"{P2}/P2_11/100M_2B/summary.json:mean_f1","10 runs mean"),
 ("P2.12 100M F1 5.9B mean","0.2989",f"{P2}/P2_11/100M_59B/summary.json:mean_f1","10 runs mean"),
 ("near-converged 650M 5.9B val loss","0.7491",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.final_val_loss","terminal validation loss"),
 ("near-converged 650M 5.9B terminal slope","-0.0004",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.terminal_slope_per100M","per 100M nt, last-4-point linear fit; -0.000443"),
 ("2B main terminal slope","-0.003",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17.terminal_slope_per100M","approx ~-0.003/100M nt; 650M 2B -0.003231"),
])
# sec6_limitations
append("sec6_limitations_numbers.csv", [
 ("per-token trivial floor","0.54",f"{S8}/p2_8_report.md","approximate; limited discriminability"),
 ("P2.9 erasure MLM increase","+0.003",f"{P2}/P2_9/p2_9_report.md","~random-direction control"),
 ("P2.9 residual probe AUC","0.64",f"{P2}/P2_9/p2_9_report.md","after 12 INLP rounds"),
 ("family F1 subsample SD","0.07",f"{P2}/P2_11/p2_11_report.md","approx SD~0.07; subsample sensitive"),
 ("recovered-pool contamination offset","0.06",f"{P2}/P2_11/p2_11_report.md","absolute F1 raised ~0.06; ~99.7% original"),
 ("2B terminal slope","-0.003",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17.terminal_slope_per100M","approx ~-0.003/100M nt"),
 ("5.9B terminal slope","-0.0005",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.terminal_slope_per100M","approx ~-0.0005/100M nt; near convergence"),
 ("650M paired budget effect","+3.06",f"{S11}:650M.budget_effect_pp_mean","9/10 positive"),
 ("650M paired SD","2.68",f"{S11}:650M.budget_effect_pp_sd","2.678"),
 ("300M paired budget effect","-0.74",f"{S11}:300M.budget_effect_pp_mean","5/10 positive; uncertain"),
 ("300M paired SD","4.38",f"{S11}:300M.budget_effect_pp_sd","4.377"),
], note_col="caliber_note")
# appendix_provenance
append("appendix_provenance_numbers.csv", [
 ("P2.10 unconverged probe_structure 6-epoch","0.5973",f"{P2}/P2_10/p2_10_report.md","unconverged caliber, fitting artifacts; demoted"),
 ("P2.10 unconverged readout_heads linear","0.6101",f"{P2}/P2_10/p2_10_report.md","unconverged caliber, fitting artifacts; demoted"),
 ("P2.10 converged authoritative","0.5562",f"{P2}/P2_10/p2_10_report.md","converged caliber authoritative"),
 ("P2.12 30M paired effect","-5.86",f"{S11}:30M.budget_effect_pp_mean","recovered pool; 0/10 positive"),
 ("P2.12 30M paired SD","0.91",f"{S11}:30M.budget_effect_pp_sd","0.908"),
 ("P2.12 100M paired effect","-1.65",f"{S11}:100M.budget_effect_pp_mean","1/10 positive"),
 ("P2.12 100M paired SD","1.42",f"{S11}:100M.budget_effect_pp_sd","1.421"),
 ("P2.11 300M paired effect","-0.74",f"{S11}:300M.budget_effect_pp_mean","5/10 positive"),
 ("P2.11 300M paired SD","4.38",f"{S11}:300M.budget_effect_pp_sd","4.377"),
 ("P2.11 650M paired effect","+3.06",f"{S11}:650M.budget_effect_pp_mean","9/10 positive"),
 ("P2.11 650M paired SD","2.68",f"{S11}:650M.budget_effect_pp_sd","2.678"),
 ("P2.11 650M paired SEM","0.85",f"{S11}:650M.budget_effect_pp_sem","0.847 displayed 0.85"),
])
# sec41_q1
append("sec41_q1_numbers.csv", [
 ("near-converged 650M 5.9B val loss","0.7491",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.final_val_loss","terminal validation loss"),
 ("near-converged 650M 5.9B terminal slope","-0.0004",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.terminal_slope_per100M","per 100M nt"),
 ("650M 5.9B family F1","0.3747","eval_evidence_logs/evidence/factorial_verdict.json:table.650M.f1_5.9B.f1","original terminal protocol single-seed"),
 ("650M 2B family F1","0.3632","eval_evidence_logs/evidence/factorial_verdict.json:table.650M.f1_2B.f1","original terminal protocol single-seed"),
 ("650M budget effect","+1.15","eval_evidence_logs/evidence/factorial_verdict.json:table.650M.budget_delta_pp","single-seed E1; 0.3747-0.3632"),
])
# sec3_methods
append("sec3_methods_numbers.csv", [
 ("2B terminal slope","-0.003",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17.terminal_slope_per100M","approx ~-0.003/100M nt; not fully plateaued"),
 ("5.9B terminal slope","-0.0005",f"{P2}/P2_12/convergence_evidence.json:RNA-Sc-650M_s17_b59.terminal_slope_per100M","approx ~-0.0005/100M nt; near convergence"),
])
# sec44_q4 (fig3b rel_mean)
append("sec44_q4_numbers.csv", [
 ("fig3b 1M best-layer rel_mean","0.471","eval_evidence_logs/evidence/s1_final_verdict.json:five_scale_table.1M.rel_mean","3-seed mean best-layer rel_depth"),
 ("fig3b 10M best-layer rel_mean","0.141","eval_evidence_logs/evidence/s1_final_verdict.json:five_scale_table.10M.rel_mean","3-seed mean"),
 ("fig3b 30M best-layer rel_mean","0.788","eval_evidence_logs/evidence/s1_final_verdict.json:five_scale_table.30M.rel_mean","3-seed mean"),
 ("fig3b 100M best-layer rel_mean","0.864","eval_evidence_logs/evidence/s1_final_verdict.json:five_scale_table.100M.rel_mean","3-seed mean"),
 ("fig3b 300M best-layer rel_mean","0.957","eval_evidence_logs/eval/probe_results.jsonl","single-seed s17 best L22/(24-1)=0.957; computed from ledger"),
 ("fig3b 650M best-layer rel_mean","0.296","eval_evidence_logs/evidence/s1_final_verdict.json:five_scale_table.650M.rel_mean","single-seed s17"),
])
print("REGISTRATION_DONE")