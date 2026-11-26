from __future__ import annotations

import argparse
import json
from pathlib import Path

from p3_train import (
    RETENTION_TARGETS_NT,
    due_retention_target,
    load_spec,
    resolve_frozen,
    validate_retention_targets,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    configs = {}
    for path in args.config:
        spec = load_spec(path)
        resolve_frozen(spec)
        configs[spec["run_id"]] = {
            "retain_ckpt_nt": spec["retain_ckpt_nt"],
            "budget_nt": spec["budget_nt"],
            "schedule_budget_nt": spec["schedule_budget_nt"],
            "max_final_nt": spec["max_final_nt"],
            "val_interval_nt": spec["val_interval_nt"],
            "required_free_disk_mib": spec["required_free_disk_mib"],
        }

    final_target = RETENTION_TARGETS_NT[-1]
    checkpoints = []
    validations = []
    last_val_nt = 0
    cumulative_nt = 0
    while cumulative_nt < final_target:
        valid_nt = min(16_384, final_target - cumulative_nt)
        cumulative_nt += valid_nt
        if (cumulative_nt >= final_target
                or cumulative_nt - last_val_nt >= 100_000_000):
            last_val_nt = cumulative_nt
            validations.append(cumulative_nt)
            target = due_retention_target(
                cumulative_nt, checkpoints, RETENTION_TARGETS_NT)
            if target is not None:
                checkpoints.append({
                    "nt": cumulative_nt,
                    "retention_target_nt": target,
                })
    actual_targets = [item["retention_target_nt"] for item in checkpoints]
    final_nt = checkpoints[-1]["nt"]
    duplicate_suppressed = due_retention_target(
        final_nt, checkpoints, RETENTION_TARGETS_NT) is None

    invalid_policy_rejected = False
    try:
        validate_retention_targets([500_000_000, 1_000_000_000], final_target)
    except RuntimeError:
        invalid_policy_rejected = True

    checkpoint_bytes = {"300M": 3_625_432_769, "650M": 7_995_654_245}
    total_bytes = 8 * sum(checkpoint_bytes.values())
    result = {
        "mode": "CPU_DRY_RUN_ONLY_NOT_FORMAL_TRAINING",
        "configs": configs,
        "validation_count": len(validations),
        "validation_first_last_nt": [validations[0], validations[-1]],
        "retention_targets": actual_targets,
        "retained_actual_nt": [item["nt"] for item in checkpoints],
        "retained_checkpoint_count": len(checkpoints),
        "final_nt": final_nt,
        "exact_iso_budget": final_nt == 1_900_122_218,
        "final_is_retained": actual_targets[-1] == final_target,
        "duplicate_suppressed": duplicate_suppressed,
        "invalid_policy_rejected": invalid_policy_rejected,
        "four_run_checkpoint_bytes": total_bytes,
        "four_run_checkpoint_gib": total_bytes / 1024 ** 3,
        "atomic_write_temp_gib": max(checkpoint_bytes.values()) / 1024 ** 3,
    }
    result["pass"] = (
        len(configs) == 4
        and all(value["retain_ckpt_nt"] == RETENTION_TARGETS_NT
                and value["budget_nt"] == value["max_final_nt"] == final_target
                and value["schedule_budget_nt"] == 2_000_000_000
                for value in configs.values())
        and len(validations) == 19
        and actual_targets == RETENTION_TARGETS_NT
        and len(checkpoints) == 4
        and final_nt == 1_900_122_218
        and duplicate_suppressed
        and invalid_policy_rejected
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
