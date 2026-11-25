import argparse
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path("/home/cunyuliu/rna-sc-p2")
CODE = ROOT / "code_git"
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
DATA = BASE / "data/bpRNA_parsed.parquet"
RUN = BASE / "weights/RNA-Sc-300M_s17"
OUT = BASE / "results/sanity300"
P23 = BASE / "results/P2_3"
ORIGINAL_SCRIPT = CODE / "run_cov300.py"
MIGRATED_SCRIPT = ROOT / "p2_3/run_p2_3_cov.py"
EXPECTED_ORIGINAL_SHA256 = "c82ac6cf81ca7dd0943a458d500127d7608d9a138db97f1c6466c34b02dfad2f"
EXPECTED_MIGRATED_SHA256 = "693c5b8fd37fc76c057f24905ad544a03ccaad119bea069f0e6cc88fed8e007b"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_original():
    assert sha256(ORIGINAL_SCRIPT) == EXPECTED_ORIGINAL_SHA256
    sys.path.insert(0, str(CODE))
    module = load_module("original_cov300", ORIGINAL_SCRIPT)
    module.BPRNA = str(DATA)
    module.RUN = str(RUN)
    return module


def compare_summary(new, old):
    result = {}
    for key in ("cov", "ctrl", "old_drop"):
        result[key] = {
            "old": old[key]["mean"],
            "new": new[key]["mean"],
            "old_hex": float.hex(old[key]["mean"]),
            "new_hex": float.hex(new[key]["mean"]),
            "bitwise_equal": new[key]["mean"] == old[key]["mean"],
            "difference": new[key]["mean"] - old[key]["mean"],
            "n_equal": new[key]["n"] == old[key]["n"],
        }
    result["cov_minus_ctrl"] = {
        "old": old["cov_minus_ctrl"],
        "new": new["cov_minus_ctrl"],
        "old_hex": float.hex(old["cov_minus_ctrl"]),
        "new_hex": float.hex(new["cov_minus_ctrl"]),
        "bitwise_equal": new["cov_minus_ctrl"] == old["cov_minus_ctrl"],
        "difference": new["cov_minus_ctrl"] - old["cov_minus_ctrl"],
    }
    return result


def run_original():
    module = load_original()
    assert torch.cuda.is_available()
    seqs, pairs_list = module.load_test()
    assert len(seqs) == 1305
    model, checkpoint = module.load_encoder(str(RUN), ckpt_nt=1900122218)
    assert checkpoint["nt"] == 1900122218 and checkpoint["step"] == 202784
    model = model.to("cuda:0").eval()
    assert next(model.parameters()).is_cuda
    result = module.evaluate_model(model, "cuda:0", seqs, pairs_list, 100, 17)
    torch.cuda.synchronize(0)
    assert np.isfinite(result["cov_minus_ctrl"])
    batch1 = json.loads((OUT / "rnasc300m_main_batch1.json").read_text())
    migrated_summary = {
        "cov": batch1["cov"], "ctrl": batch1["ctrl"],
        "old_drop": batch1["old_drop"],
        "cov_minus_ctrl": batch1["cov_minus_ctrl"],
    }
    record = {
        "status": "PASS_CUDA_ORIGINAL_FUNCTION_COMPLETE",
        "authoritative_script": str(ORIGINAL_SCRIPT),
        "authoritative_script_sha256": EXPECTED_ORIGINAL_SHA256,
        "weight_path": str(RUN / "ckpt_nt1900122218_step202784.pt"),
        "weight_sha256": sha256(RUN / "ckpt_nt1900122218_step202784.pt"),
        "bpRNA_sha256": sha256(DATA),
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "model_device": str(next(model.parameters()).device),
        "result": result,
        "old_anchor_comparison": compare_summary(result, module.OLD_ANCHOR) if hasattr(module, "OLD_ANCHOR") else compare_summary(result, {
            "cov": {"mean": 0.049607125636875415, "n": 4920},
            "ctrl": {"mean": 0.0026705753443465943, "n": 4920},
            "old_drop": {"mean": -0.015336274750000935, "n": 4920},
            "cov_minus_ctrl": 0.04693655029252882,
        }),
        "migrated_batch1_comparison": compare_summary(result, migrated_summary),
    }
    record["original_equals_migrated_batch1_bitwise"] = all(
        value["bitwise_equal"] and value.get("n_equal", True)
        for value in record["migrated_batch1_comparison"].values())
    (OUT / "original_run_cov300_diagnostic.json").write_text(
        json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


def verify_protocol():
    original = load_original()
    assert sha256(MIGRATED_SCRIPT) == EXPECTED_MIGRATED_SHA256
    migrated = load_module("migrated_cov", MIGRATED_SCRIPT)
    meta, frozen = migrated.load_frozen()
    seqs, pairs_list = original.load_test()
    rng = random.Random(17)
    indices = rng.sample(range(len(seqs)), 100)
    expected_conditions = []
    expected_samples = []
    for sample_order, index in enumerate(indices):
        ids = original.encode(seqs[index])
        expected_samples.append({
            "sample_order": sample_order,
            "encoded_length": len(ids),
            "sequence_sha256": hashlib.sha256(
                "".join(original.ALPHABET[b] for b in ids).encode()).hexdigest(),
            "skipped_forward": len(ids) < 20,
        })
        if len(ids) >= 20:
            expected_conditions.extend(original.build_conditions(ids, pairs_list[index], rng))
    keys = ("i", "j", "k", "xi", "muts", "ids")
    actual_conditions = [{key: row[key] for key in keys} for row in frozen]
    actual_samples = [{key: row[key] for key in expected_samples[0]} for row in meta["samples"]]
    assert actual_samples == expected_samples
    assert actual_conditions == expected_conditions
    assert original.COMP == migrated.COMP
    assert original.MASK == migrated.RNAScAdapter.mask
    assert len(frozen) == 1640
    assert sum(len(row["muts"]) for row in frozen) == 4920
    assert sum(len(row["muts"]) for row in frozen if row["k"] is not None) == 4920

    batch16_rows = [json.loads(line) for line in open(OUT / "p2_3_rnasc300m_sanity_per_condition.jsonl")]
    batch1_rows = [json.loads(line) for line in open(OUT / "rnasc300m_main_batch1_per_condition.jsonl")]
    row_keys16 = [(row["condition_id"], row["mutation"]) for row in batch16_rows]
    row_keys1 = [(row["condition_id"], row["mutation"]) for row in batch1_rows]
    assert row_keys16 == row_keys1
    numeric = {}
    for key in ("cov", "ctrl", "old_drop"):
        a = np.array([row[key] for row in batch16_rows], dtype=float)
        b = np.array([row[key] for row in batch1_rows], dtype=float)
        difference = a - b
        numeric[key] = {
            "max_abs_difference": float(np.max(np.abs(difference))),
            "mean_abs_difference": float(np.mean(np.abs(difference))),
            "n_bitwise_equal": int(np.sum(a == b)),
            "n": len(a),
        }
    record = {
        "status": "PASS_PROTOCOL_IDENTITY",
        "n_test": len(seqs),
        "n_sampled": len(indices),
        "n_conditions": len(frozen),
        "n_cov_mutations": 4920,
        "n_ctrl_mutations": 4920,
        "bpRNA_sha256": sha256(DATA),
        "conditions_sha256": sha256(P23 / "p2_3_cov_conditions.jsonl"),
        "original_script_sha256": EXPECTED_ORIGINAL_SHA256,
        "migrated_script_sha256": EXPECTED_MIGRATED_SHA256,
        "sequence_sampling_identical": True,
        "pair_sampling_identical": True,
        "ctrl_positions_identical": True,
        "condition_payloads_identical": True,
        "mask_and_complement_definitions_identical": True,
        "batch16_vs_batch1_condition_order_identical": True,
        "batch16_vs_batch1_numeric": numeric,
        "old_anchor": {
            "cov": 0.049607125636875415,
            "ctrl": 0.0026705753443465943,
            "old_drop": -0.015336274750000935,
            "cov_minus_ctrl": 0.04693655029252882,
        },
    }
    (OUT / "protocol_verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["original", "verify"])
    args = parser.parse_args()
    if args.command == "original":
        run_original()
    else:
        verify_protocol()


if __name__ == "__main__":
    main()
