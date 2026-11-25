from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
OUT = ROOT / "results/P2_1"
CODE = Path("/home/cunyuliu/rna-sc-p2/code_git")
OLD = OUT / "reference/old_probe_structure_results.jsonl"
BPRNA = ROOT / "data/bpRNA_parsed.parquet"
UNITS = [
    ("100M", "trained_early_1.8B", "RNA-Sc-100M_s17_rfamcap_ckpt1800083135", 1800083135, 23),
    ("100M", "trained_final_1.9B", "RNA-Sc-100M_s17_rfamcap_ckpt1900086380", 1900086380, 23),
    ("30M", "trained_final_1.9B", "RNA-Sc-30M_s17_rfamcap_ckpt1900086380", 1900086380, 12),
    ("30M", "trained_early_1.8B", "RNA-Sc-30M_s17_rfamcap_ckpt1800083135", 1800083135, 12),
    ("100M", "randinit17", "RNA-Sc-100M_s17_rfamcap_randinit17", 1900086380, 23),
    ("30M", "randinit17", "RNA-Sc-30M_s17_rfamcap_randinit17", 1900086380, 12),
]
LEGACY_FIELDS = ["f1", "acc", "precision", "recall", "n_tokens_train", "n_tokens_eval"]
FAMILY = {
    "30M": {"main": 0.2466, "rfamcap": 0.2880, "delta_pp": 4.14},
    "100M": {"main": 0.3263, "rfamcap": 0.3297, "delta_pp": 0.34},
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_json(path, value):
    with open(path, "w") as fh:
        json.dump(value, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0])
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def best_row(rows):
    return max(rows, key=lambda row: row["f1_paired_legacy_unrounded"])


def f1_from_predictions(pred, y, positive):
    pred = np.asarray(pred)
    y = np.asarray(y)
    tp = int(np.sum((pred == positive) & (y == positive)))
    fp = int(np.sum((pred == positive) & (y != positive)))
    fn = int(np.sum((pred != positive) & (y == positive)))
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0


def main():
    old_rows = read_jsonl(OLD)
    old_by_run = {}
    old_line_numbers = {}
    for line_number, row in enumerate(old_rows, 1):
        old_by_run.setdefault(row["run"], []).append(row)
        old_line_numbers[(row["run"], row["layer"])] = line_number

    all_rows = []
    unit_records = {}
    prediction_checks = []
    for scale, condition, unit, requested_nt, expected_layers in UNITS:
        unit_dir = OUT / "units" / unit
        rows = read_jsonl(unit_dir / "layers.jsonl")
        with open(unit_dir / "summary.json") as fh:
            summary = json.load(fh)
        assert summary["status"] == "COMPLETE"
        assert summary["n_layers_written"] == expected_layers == len(rows)
        assert summary["cpu_fallback_count"] == 0
        assert summary["peak_reserved_bytes"] <= 9 * 1024**3
        assert [row["layer"] for row in rows] == list(range(expected_layers))
        assert len({row["run"] for row in rows}) == 1
        assert all(row["requested_ckpt_nt"] == requested_nt for row in rows)
        assert all(row["n_tokens_train"] == 1006208 for row in rows)
        assert all(row["n_tokens_eval"] == 164418 for row in rows)
        assert all(row["probe_batch_size"] == 512 for row in rows)
        assert all(row["epochs"] == 6 for row in rows)
        assert all(row["head_seed"] == 17 + row["layer"] for row in rows)
        assert all(row["sample_seed"] == 17 for row in rows)
        assert all(row["cpu_fallback_count"] == 0 for row in rows)
        expected_source = "randinit" if condition == "randinit17" else "trained"
        assert all(row["weight_source"] == expected_source for row in rows)
        if expected_source == "randinit":
            assert all(row["ckpt_nt"] == 0 and row["random_init_seed"] == 17 for row in rows)
        else:
            assert all(row["ckpt_nt"] == requested_nt for row in rows)

        with np.load(unit_dir / "predictions.npz") as data:
            predictions = data["predictions"]
            y_eval = data["y_eval"]
            assert predictions.shape == (expected_layers, 164418)
            assert y_eval.shape == (164418,)
            assert np.array_equal(data["layers"], np.arange(expected_layers))
            for row in rows:
                layer = row["layer"]
                pred = predictions[layer]
                paired = f1_from_predictions(pred, y_eval, 1)
                unpaired = f1_from_predictions(pred, y_eval, 0)
                macro = (paired + unpaired) / 2
                acc = float((torch.from_numpy(pred) == torch.from_numpy(y_eval)).float().mean())
                assert abs(paired - row["f1_paired_legacy_unrounded"]) < 1e-12
                assert abs(unpaired - row["f1_unpaired_unrounded"]) < 1e-12
                assert abs(macro - row["f1_macro_unrounded"]) < 1e-12
                assert abs(acc - row["acc_unrounded"]) < 1e-12
                assert round(paired, 4) == row["f1_paired_legacy"] == row["f1"]
                assert round(macro, 6) == row["f1_macro"]
            prediction_checks.append({
                "unit": unit, "shape": list(predictions.shape),
                "all_layers_recomputed_from_saved_predictions": True,
                "predictions_sha256": sha256_file(unit_dir / "predictions.npz"),
            })
        for row in rows:
            row["scale"] = scale
            row["condition"] = condition
            row["unit_dir"] = str(unit_dir)
        best = best_row(rows)
        assert best["layer"] == summary["best_layer"]
        assert best["f1_paired_legacy"] == summary["best_f1_paired_legacy"]
        unit_records[unit] = {
            "scale": scale, "condition": condition, "rows": rows,
            "best": best, "summary": summary, "requested_nt": requested_nt,
        }
        all_rows.extend(rows)

    assert len(all_rows) == 105
    assert len({(row["run"], row["layer"]) for row in all_rows}) == 105
    assert len({row["sample_sha256"] for row in all_rows}) == 1
    merged = OUT / "p2_1_rfamcap_structure_layers.jsonl"
    with open(merged, "w") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    old_target_run = "RNA-Sc-100M_s17_rfamcap"
    old_target = sorted(old_by_run[old_target_run], key=lambda row: row["layer"])
    assert len(old_target) == 23
    adjudication_candidates = []
    adjudication_layer_rows = []
    for unit in [
        "RNA-Sc-100M_s17_rfamcap_ckpt1800083135",
        "RNA-Sc-100M_s17_rfamcap_ckpt1900086380",
    ]:
        record = unit_records[unit]
        new_rows = sorted(record["rows"], key=lambda row: row["layer"])
        mismatches = []
        metric_match_counts = Counter()
        exact_layers = []
        for old, new in zip(old_target, new_rows):
            assert old["layer"] == new["layer"]
            changed = {}
            new_field_map = {
                "f1": "f1_paired_legacy", "acc": "acc",
                "precision": "precision", "recall": "recall",
                "n_tokens_train": "n_tokens_train", "n_tokens_eval": "n_tokens_eval",
            }
            for old_field, new_field in new_field_map.items():
                equal = old[old_field] == new[new_field]
                metric_match_counts[old_field] += int(equal)
                if not equal:
                    changed[old_field] = {"old": old[old_field], "new": new[new_field]}
            if not changed:
                exact_layers.append(old["layer"])
            else:
                mismatches.append({
                    "layer": old["layer"],
                    "old_line_number": old_line_numbers[(old_target_run, old["layer"])],
                    "differences": changed,
                })
            adjudication_layer_rows.append({
                "candidate_ckpt_nt": record["requested_nt"],
                "candidate_checkpoint_file": new_rows[old["layer"]]["checkpoint_file"],
                "layer": old["layer"],
                "old_line_number": old_line_numbers[(old_target_run, old["layer"])],
                "old_f1": old["f1"], "new_f1": new["f1_paired_legacy"],
                "old_acc": old["acc"], "new_acc": new["acc"],
                "old_precision": old["precision"], "new_precision": new["precision"],
                "old_recall": old["recall"], "new_recall": new["recall"],
                "old_n_tokens_train": old["n_tokens_train"],
                "new_n_tokens_train": new["n_tokens_train"],
                "old_n_tokens_eval": old["n_tokens_eval"],
                "new_n_tokens_eval": new["n_tokens_eval"],
                "all_five_fields_exact": not changed,
                "mismatch_fields": ";".join(changed),
            })
        adjudication_candidates.append({
            "ckpt_nt": record["requested_nt"],
            "checkpoint_file": record["best"]["checkpoint_file"],
            "checkpoint_sha256": record["best"]["checkpoint_sha256"],
            "layers_compared": 23,
            "exact_layers": exact_layers,
            "exact_layer_count": len(exact_layers),
            "all_23_layers_exact": len(exact_layers) == 23,
            "metric_match_counts": dict(metric_match_counts),
            "mismatches": mismatches,
            "new_layer20_f1_paired_legacy": new_rows[20]["f1_paired_legacy"],
            "new_best_layer": record["best"]["layer"],
            "new_best_f1_paired_legacy": record["best"]["f1_paired_legacy"],
        })
    matching = [c for c in adjudication_candidates if c["all_23_layers_exact"]]
    if len(matching) == 1:
        verdict = "single_checkpoint_identified"
        source_ckpt_nt = matching[0]["ckpt_nt"]
        source_checkpoint_file = matching[0]["checkpoint_file"]
    elif len(matching) == 2:
        verdict = "checkpoint_indistinguishable"
        source_ckpt_nt = None
        source_checkpoint_file = None
    else:
        verdict = "not_reproduced"
        source_ckpt_nt = None
        source_checkpoint_file = None
    old_best = max(old_target, key=lambda row: row["f1"])
    adjudication = {
        "comparison_rule": "literal equality at each of 23 layers for rounded f1/acc/precision/recall and integer train/eval token counts",
        "historical_target": {"f1_paired_legacy": 0.5924, "layer": 20},
        "old_evidence": {
            "path": str(OLD), "sha256": sha256_file(OLD),
            "run": old_target_run, "line_numbers_1_based": [369, 391],
            "best_row": old_best,
            "best_row_line_number": old_line_numbers[(old_target_run, old_best["layer"])],
        },
        "candidates": adjudication_candidates,
        "verdict": verdict,
        "source_ckpt_nt": source_ckpt_nt,
        "source_checkpoint_file": source_checkpoint_file,
    }
    write_json(OUT / "p2_1_ckpt_adjudication.json", adjudication)
    write_csv(OUT / "p2_1_ckpt_adjudication_layers.csv", adjudication_layer_rows)

    main_best = {
        scale: max(old_by_run[f"RNA-Sc-{scale}_s17"], key=lambda row: row["f1"])
        for scale in ["30M", "100M"]
    }
    summary_rows = []
    for scale, condition, unit, requested_nt, expected_layers in UNITS:
        record = unit_records[unit]
        best = record["best"]
        random_best = unit_records[f"RNA-Sc-{scale}_s17_rfamcap_randinit17"]["best"]
        is_trained = condition != "randinit17"
        is_final = condition == "trained_final_1.9B"
        summary_rows.append({
            "scale": scale,
            "run": unit,
            "condition": condition,
            "ckpt_nt": best["ckpt_nt"],
            "architecture_source_ckpt_nt": requested_nt,
            "checkpoint_file": best["checkpoint_file"],
            "checkpoint_sha256": best["checkpoint_sha256"],
            "best_layer": best["layer"],
            "f1_paired_legacy": f"{best['f1_paired_legacy']:.4f}",
            "f1_macro": f"{best['f1_macro']:.6f}",
            "f1_unpaired": f"{best['f1_unpaired']:.6f}",
            "accuracy": f"{best['acc']:.4f}",
            "precision_paired": f"{best['precision']:.4f}",
            "recall_paired": f"{best['recall']:.4f}",
            "n_train_seqs": 8000,
            "n_eval_seqs": 1305,
            "n_tokens_train": best["n_tokens_train"],
            "n_tokens_eval": best["n_tokens_eval"],
            "randinit_best_layer": random_best["layer"] if is_trained else "",
            "randinit_best_f1_paired_legacy": f"{random_best['f1_paired_legacy']:.4f}" if is_trained else "",
            "trained_minus_randinit_pp": f"{100 * (best['f1_paired_legacy_unrounded'] - random_best['f1_paired_legacy_unrounded']):+.4f}" if is_trained else "",
            "main_legacy_best_layer": main_best[scale]["layer"] if is_final else "",
            "main_legacy_f1_paired_legacy": f"{main_best[scale]['f1']:.4f}" if is_final else "",
            "rfamcap_minus_main_pp": f"{100 * (best['f1_paired_legacy_unrounded'] - main_best[scale]['f1']):+.4f}" if is_final else "",
            "peak_reserved_mib": f"{record['summary']['peak_reserved_bytes'] / 1024**2:.2f}",
            "cpu_fallback_count": record["summary"]["cpu_fallback_count"],
        })
    write_csv(OUT / "p2_1_rfamcap_structure_summary.csv", summary_rows)

    channel_rows = []
    for scale in ["30M", "100M"]:
        final = unit_records[f"RNA-Sc-{scale}_s17_rfamcap_ckpt1900086380"]["best"]
        random_best = unit_records[f"RNA-Sc-{scale}_s17_rfamcap_randinit17"]["best"]
        structure_delta = 100 * (final["f1_paired_legacy_unrounded"] - main_best[scale]["f1"])
        channel_rows.append({
            "scale": scale,
            "family_main_legacy_f1": f"{FAMILY[scale]['main']:.4f}",
            "family_rfamcap_final_f1": f"{FAMILY[scale]['rfamcap']:.4f}",
            "family_rfamcap_minus_main_pp_preregistered": f"{FAMILY[scale]['delta_pp']:+.2f}",
            "structure_main_legacy_best_layer": main_best[scale]["layer"],
            "structure_main_legacy_paired_f1": f"{main_best[scale]['f1']:.4f}",
            "structure_rfamcap_final_best_layer": final["layer"],
            "structure_rfamcap_final_paired_f1": f"{final['f1_paired_legacy']:.4f}",
            "structure_rfamcap_minus_main_pp": f"{structure_delta:+.4f}",
            "structure_randinit_best_layer": random_best["layer"],
            "structure_randinit_best_paired_f1": f"{random_best['f1_paired_legacy']:.4f}",
            "structure_trained_minus_randinit_pp": f"{100 * (final['f1_paired_legacy_unrounded'] - random_best['f1_paired_legacy_unrounded']):+.4f}",
            "selection_note": "best layer on TS0; descriptive, not independent confirmatory generalization",
        })
    write_csv(OUT / "p2_1_channel_specificity.csv", channel_rows)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    styles = {
        "trained_early_1.8B": ("#56B4E9", "--", "RFamCap 1.8B"),
        "trained_final_1.9B": ("#D55E00", "-", "RFamCap 1.9B"),
        "randinit17": ("#666666", ":", "randinit17"),
    }
    for axis, scale in zip(axes, ["30M", "100M"]):
        for condition in ["trained_early_1.8B", "trained_final_1.9B", "randinit17"]:
            matches = [record for record in unit_records.values()
                       if record["scale"] == scale and record["condition"] == condition]
            assert len(matches) == 1
            rows = sorted(matches[0]["rows"], key=lambda row: row["layer"])
            color, linestyle, label = styles[condition]
            axis.plot([row["layer"] for row in rows],
                      [row["f1_paired_legacy_unrounded"] for row in rows],
                      color=color, linestyle=linestyle, marker="o", markersize=3,
                      linewidth=1.6, label=label)
        axis.set_title(f"RNA-Sc-{scale}")
        axis.set_xlabel("Encoder layer")
        axis.set_xticks([0, 5, 11] if scale == "30M" else [0, 5, 10, 15, 20, 22])
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Paired-position F1 (legacy paired class)")
    axes[1].legend(frameon=False, loc="best")
    fig.suptitle("RFamCap structure probe on bpRNA TS0 (best layer selected on TS0)")
    fig.tight_layout()
    (OUT / "figs").mkdir(exist_ok=True)
    fig.savefig(OUT / "figs/p2_1_rfamcap_structure.png", dpi=300)
    fig.savefig(OUT / "figs/p2_1_rfamcap_structure.pdf")
    plt.close(fig)

    logs_out = OUT / "logs"
    logs_out.mkdir(exist_ok=True)
    for source in sorted((ROOT / "logs/P2_1").glob("*.log")):
        shutil.copy2(source, logs_out / source.name)

    validation = {
        "status": "PASS",
        "units_complete": 6,
        "layer_rows": len(all_rows),
        "expected_layer_rows": 105,
        "unique_run_layer_keys": 105,
        "n_train_seqs": 8000,
        "n_eval_seqs": 1305,
        "n_eval_seqs_requested": 1500,
        "n_tokens_train": 1006208,
        "n_tokens_eval": 164418,
        "sample_sha256_unique": len({row["sample_sha256"] for row in all_rows}) == 1,
        "sample_sha256": all_rows[0]["sample_sha256"],
        "probe_batch_size_all_rows": 512,
        "epochs_all_rows": 6,
        "cuda_fallback_count_total": sum(row["cpu_fallback_count"] for row in all_rows),
        "max_peak_reserved_mib": max(record["summary"]["peak_reserved_bytes"] for record in unit_records.values()) / 1024**2,
        "prediction_recomputation": prediction_checks,
        "adjudication_verdict": verdict,
        "acceptance_complete": len(all_rows) == 105 and len(matching) <= 2,
    }
    write_json(OUT / "p2_1_validation.json", validation)

    report_lines = [
        "# P2.1 RFamCap 结构探针执行汇总",
        "",
        "- 六个单元、105 个层行全部完成；8000/1305 序列（test 请求 1500，实际全集 1305），1,006,208/164,418 token，6 epochs，token batch=512。",
        "- 所有预测已从 NPZ 逐层重算 paired/unpaired/macro-F1 与 accuracy，结果与 JSONL 一致；CPU fallback=0。",
        f"- checkpoint 裁决：**{verdict}**；来源 ckpt_nt={source_ckpt_nt}，文件={source_checkpoint_file}。",
        "- legacy 指标为 paired 正类 F1；真 macro-F1 为新增敏感性口径，不能与旧 main macro 称呼混用。",
        "",
        "| 尺度 | 条件 | ckpt_nt | best layer | paired F1 | macro-F1 | trained−randinit (pp) | RFamCap−main (pp) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        report_lines.append(
            f"| {row['scale']} | {row['condition']} | {row['ckpt_nt']} | {row['best_layer']} | "
            f"{row['f1_paired_legacy']} | {row['f1_macro']} | {row['trained_minus_randinit_pp']} | {row['rfamcap_minus_main_pp']} |")
    report_lines.extend([
        "",
        "终预算 family 对照仍采用预注册既有值：30M +4.14pp、100M +0.34pp；本任务未重跑 family。",
        "1.8B 是近终点轨迹，不是旧 family 账本的 0.2B；结构曲线与差值均为 TS0 选层的描述性结果。",
        "",
    ])
    (OUT / "p2_1_report.md").write_text("\n".join(report_lines))

    inputs = []
    input_paths = [
        CODE / "rna_sc/probe_structure_p2_1.py",
        CODE / "rna_sc/probe_structure.py",
        CODE / "rna_sc/probe.py",
        CODE / "rna_sc/model.py",
        CODE.parent / "run_p2_1.sh",
        CODE.parent / "run_p2_1_resume_30m_randinit.sh",
        CODE.parent / "finalize_p2_1.py",
        BPRNA,
        OLD,
    ]
    for scale in ["30M", "100M"]:
        for nt, step in [(1800083135, 238007), (1900086380, 250287)]:
            input_paths.append(ROOT / f"weights/RNA-Sc-{scale}_s17_rfamcap/ckpt_nt{nt}_step{step}.pt")
    for path in input_paths:
        inputs.append({"path": str(path), "bytes": path.stat().st_size,
                       "sha256": sha256_file(path)})
    output_files = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"manifest.json", "manifest_sha256.tsv", "driver.pid", "resume_driver.pid"}:
            continue
        if path in input_paths:
            continue
        output_files.append({"path": str(path.relative_to(OUT)), "bytes": path.stat().st_size,
                             "sha256": sha256_file(path)})
    manifest = {
        "task": "P2_1",
        "protocol": "prereg/P2_1.md",
        "status": "COMPLETE",
        "units": 6,
        "layer_rows": 105,
        "sampling": {"seed": 17, "train_sequences": 8000, "eval_sequences": 1305,
                     "eval_sequences_requested": 1500,
                     "eval_selection": "min(1500, full test split)=1305",
                     "train_tokens": 1006208, "eval_tokens": 164418},
        "probe": {"epochs": 6, "token_batch_size": 512, "optimizer": "AdamW",
                  "lr": 0.001, "weight_decay": 0.01, "head_seed": "17+layer",
                  "state_cache_dtype": "FP32 disk memmap (numerically identical to source FP32 states)",
                  "head_compute_dtype": "FP32"},
        "randinit": {"seed": 17, "architecture_source": "same-scale final 1.9B checkpoint cfg.arch",
                     "checkpoint_repetitions": 0},
        "gpu": {"device": "cuda:0", "lane": "B", "budget_bytes": 9 * 1024**3,
                "cpu_fallback_count": 0,
                "max_peak_reserved_mib": validation["max_peak_reserved_mib"]},
        "metric_calibers": {"legacy": "paired positive-class F1",
                            "added": "true binary macro-F1=(paired+unpaired)/2"},
        "adjudication_verdict": verdict,
        "adjudication_source_ckpt_nt": source_ckpt_nt,
        "inputs": inputs,
        "outputs": output_files,
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "cuda_runtime": torch.version.cuda,
                        "gpu": torch.cuda.get_device_name(0)},
    }
    write_json(OUT / "manifest.json", manifest)
    with open(OUT / "manifest_sha256.tsv", "w") as fh:
        fh.write("sha256\tbytes\tpath\n")
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path.name not in {"manifest_sha256.tsv", "driver.pid", "resume_driver.pid"}:
                fh.write(f"{sha256_file(path)}\t{path.stat().st_size}\t{path.relative_to(OUT)}\n")
    print(json.dumps({"status": "PASS", "rows": len(all_rows),
                      "verdict": verdict, "source_ckpt_nt": source_ckpt_nt,
                      "summary": summary_rows}, indent=2))


if __name__ == "__main__":
    main()
