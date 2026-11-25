import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path("/home/cunyuliu/rna-sc-p2")
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
OUT = BASE / "results/sanity300"
P23 = BASE / "results/P2_3"
LOGS = BASE / "logs/sanity300"
CONDITIONS = P23 / "p2_3_cov_conditions.jsonl"
FREEZE = P23 / "p2_3_cov_freeze.json"
WEIGHT = BASE / "weights/RNA-Sc-300M_s17/ckpt_nt1900122218_step202784.pt"
ALPHABET = "ACGU"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def read_rows(path):
    return [json.loads(line) for line in open(path)]


def summarize(rows):
    cov = [row["cov"] for row in rows]
    ctrl = [row["ctrl"] for row in rows if row["ctrl"] is not None]
    old_drop = [row["old_drop"] for row in rows if row["old_drop"] is not None]
    return {
        "cov": {"mean": float(np.mean(cov)), "n": len(cov)},
        "ctrl": {"mean": float(np.mean(ctrl)), "n": len(ctrl)},
        "old_drop": {"mean": float(np.mean(old_drop)), "n": len(old_drop)},
        "cov_minus_ctrl": float(np.mean(cov) - np.mean(ctrl)),
    }


def validate_arm(result_path, rows_path, conditions, expected_order):
    result = json.loads(result_path.read_text())
    rows = read_rows(rows_path)
    assert [(row["condition_id"], row["mutation"]) for row in rows] == expected_order
    assert sha256(rows_path) == result["per_condition_sha256"]
    recomputed = summarize(rows)
    checks = {}
    for key in ("cov", "ctrl", "old_drop"):
        checks[key] = float.hex(recomputed[key]["mean"]) == float.hex(result[key]["mean"])
        assert recomputed[key]["n"] == result[key]["n"]
    checks["cov_minus_ctrl"] = float.hex(recomputed["cov_minus_ctrl"]) == float.hex(result["cov_minus_ctrl"])
    assert all(checks.values())
    assert result["cpu_fallback_count"] == 0
    return result, rows, {
        "bitwise_recompute": checks,
        "condition_order_identical": True,
        "n_cov": recomputed["cov"]["n"],
        "n_ctrl": recomputed["ctrl"]["n"],
        "cpu_fallback_count": result["cpu_fallback_count"],
    }


def main():
    conditions = read_rows(CONDITIONS)
    expected_order = [(condition["condition_id"], ALPHABET[m])
                      for condition in conditions for m in condition["muts"]]
    trained, trained_rows, trained_validation = validate_arm(
        OUT / "p2_3_rnasc300m_sanity.json",
        OUT / "p2_3_rnasc300m_sanity_per_condition.jsonl",
        conditions, expected_order)
    randinit, randinit_rows, randinit_validation = validate_arm(
        OUT / "rnasc300m_randinit17.json",
        OUT / "rnasc300m_randinit17_per_condition.jsonl",
        conditions, expected_order)
    batch1, batch1_rows, batch1_validation = validate_arm(
        OUT / "rnasc300m_main_batch1.json",
        OUT / "rnasc300m_main_batch1_per_condition.jsonl",
        conditions, expected_order)
    assert trained["condition_ids_sha256"] == randinit["condition_ids_sha256"] == batch1["condition_ids_sha256"]
    assert trained["conditions_sha256"] == sha256(CONDITIONS)
    original = json.loads((OUT / "original_run_cov300_diagnostic.json").read_text())
    protocol = json.loads((OUT / "protocol_verification.json").read_text())
    weight = json.loads((OUT / "weight_strip_verification.json").read_text())
    smoke = json.loads((OUT / "gpu_smoke.json").read_text())
    assert original["original_equals_migrated_batch1_bitwise"]
    assert protocol["status"] == "PASS_PROTOCOL_IDENTITY"
    assert weight["status"] == smoke["status"] == "PASS"
    assert not trained["sanity_pass"]
    trained_minus_randinit = trained["cov_minus_ctrl"] - randinit["cov_minus_ctrl"]
    validation = {
        "status": "PASS_EVIDENCE_INTEGRITY_ANCHOR_MISMATCH_RETAINED",
        "trained": trained_validation,
        "randinit17": randinit_validation,
        "batch1_diagnostic": batch1_validation,
        "all_condition_ids_identical": True,
        "original_equals_migrated_batch1_bitwise": True,
        "protocol_identity": True,
        "anchor_bitwise_pass": False,
        "external_cov_confidence_upgrade": "FROZEN",
    }
    write_json(OUT / "validation.json", validation)
    summary = {
        "task": "X-sanity300",
        "status": "COMPLETE_ANCHOR_MISMATCH_EXTERNAL_COV_UPGRADE_FROZEN",
        "model": "RNA-Sc-300M_s17",
        "checkpoint": {
            "nt": 1900122218,
            "step": 202784,
            "path": str(WEIGHT),
            "sha256": sha256(WEIGHT),
            "source_matches_readonly_backup": True,
            "model_tensors_bitwise_equal_after_opt_strip": True,
        },
        "protocol": {
            "source": "X-P23 run_p2_3_cov.py; only output paths and main checkpoint assertion adapted",
            "seed": 17,
            "n_test": 1305,
            "n_sampled": 100,
            "n_conditions": len(conditions),
            "condition_batch": 16,
            "conditions_sha256": sha256(CONDITIONS),
        },
        "trained": {
            "cov": trained["cov"]["mean"],
            "ctrl": trained["ctrl"]["mean"],
            "cov_minus_ctrl": trained["cov_minus_ctrl"],
            "old_drop": trained["old_drop"]["mean"],
            "n_cov": trained["cov"]["n"],
            "n_ctrl": trained["ctrl"]["n"],
        },
        "randinit17": {
            "cov": randinit["cov"]["mean"],
            "ctrl": randinit["ctrl"]["mean"],
            "cov_minus_ctrl": randinit["cov_minus_ctrl"],
            "old_drop": randinit["old_drop"]["mean"],
            "n_cov": randinit["cov"]["n"],
            "n_ctrl": randinit["ctrl"]["n"],
        },
        "trained_minus_randinit": trained_minus_randinit,
        "old_anchor": trained["old_anchor_comparison"],
        "anchor_bitwise_pass": False,
        "batch1_diagnostic": {
            "cov": batch1["cov"]["mean"],
            "ctrl": batch1["ctrl"]["mean"],
            "cov_minus_ctrl": batch1["cov_minus_ctrl"],
            "old_drop": batch1["old_drop"]["mean"],
            "original_function_result_bitwise_identical": True,
            "cov_minus_ctrl_difference_from_old_anchor": original["old_anchor_comparison"]["cov_minus_ctrl"]["difference"],
        },
        "migration_conclusion": "Protocol identity and same-hardware original-function cross-check pass; preregistered old-anchor bitwise test fails.",
        "external_cov_confidence_upgrade": "FROZEN_NO_UPGRADE",
        "cuda": {
            "device": torch.cuda.get_device_name(0),
            "smoke_pass": True,
            "cpu_fallback_count": 0,
        },
    }
    write_json(OUT / "sanity300_summary.json", summary)
    fields = ["arm", "condition_batch", "cov", "ctrl", "cov_minus_ctrl", "old_drop", "n_cov", "n_ctrl"]
    csv_rows = []
    for arm, batch, result in (
            ("main_trained", 16, trained),
            ("main_randinit17", 16, randinit),
            ("main_trained_batch1_diagnostic", 1, batch1)):
        csv_rows.append({
            "arm": arm, "condition_batch": batch,
            "cov": result["cov"]["mean"], "ctrl": result["ctrl"]["mean"],
            "cov_minus_ctrl": result["cov_minus_ctrl"],
            "old_drop": result["old_drop"]["mean"],
            "n_cov": result["cov"]["n"], "n_ctrl": result["ctrl"]["n"],
        })
    original_result = original["result"]
    csv_rows.append({
        "arm": "original_function_batch1_diagnostic", "condition_batch": 1,
        "cov": original_result["cov"]["mean"], "ctrl": original_result["ctrl"]["mean"],
        "cov_minus_ctrl": original_result["cov_minus_ctrl"],
        "old_drop": original_result["old_drop"]["mean"],
        "n_cov": original_result["cov"]["n"], "n_ctrl": original_result["ctrl"]["n"],
    })
    with open(OUT / "sanity300_summary.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    packages = {}
    for name in ("torch", "numpy", "pandas", "pyarrow"):
        packages[name] = importlib.metadata.version(name)
    inputs = {}
    for name, path in (
            ("weight", WEIGHT),
            ("bpRNA", BASE / "data/bpRNA_parsed.parquet"),
            ("conditions", CONDITIONS),
            ("freeze", FREEZE),
            ("original_script", ROOT / "code_git/run_cov300.py"),
            ("migrated_script", ROOT / "p2_3/run_p2_3_cov.py"),
            ("wrapper", ROOT / "run_sanity300.py"),
            ("diagnostic_script", ROOT / "diagnose_sanity300_protocol.py")):
        inputs[name] = {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    logs = {}
    for path in sorted(LOGS.glob("*")):
        if path.is_file():
            logs[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "task": "X-sanity300",
        "status": summary["status"],
        "created_unix": time.time(),
        "inputs": inputs,
        "source_original_checkpoint": {
            "path": weight["source_path"],
            "sha256": weight["source_sha256"],
            "matches_readonly_backup": True,
            "readonly_backup_path": weight["local_readonly_backup_path"],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": packages,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0),
            "torch_cuda": torch.version.cuda,
        },
        "logs": logs,
        "anchor_bitwise_pass": False,
        "external_cov_confidence_upgrade": "FROZEN_NO_UPGRADE",
    }
    outputs = {}
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name not in ("manifest.json", "evidence_sha256.tsv") and not path.name.endswith(".tmp"):
            outputs[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest["outputs"] = outputs
    write_json(OUT / "manifest.json", manifest)
    with open(OUT / "evidence_sha256.tsv", "w") as handle:
        handle.write("path\tsha256\tbytes\n")
        for path in sorted(OUT.iterdir()):
            if path.is_file() and path.name != "evidence_sha256.tsv":
                handle.write(f"{path.name}\t{sha256(path)}\t{path.stat().st_size}\n")
        for path in sorted(LOGS.glob("*")):
            if path.is_file():
                handle.write(f"logs/{path.name}\t{sha256(path)}\t{path.stat().st_size}\n")
    print(json.dumps({
        "status": summary["status"],
        "trained_cov_minus_ctrl": trained["cov_minus_ctrl"],
        "randinit17_cov_minus_ctrl": randinit["cov_minus_ctrl"],
        "trained_minus_randinit": trained_minus_randinit,
        "anchor_bitwise_pass": False,
        "original_equals_migrated_batch1_bitwise": True,
        "n_outputs": len(outputs),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
