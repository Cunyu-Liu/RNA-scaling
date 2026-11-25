import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import torch

BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "staging" / "upload_main" / "weights"
RUNS = {
    "RNA-Sc-30M_s17": "ckpt_nt1900121822_step202784.pt",
    "RNA-Sc-100M_s17": "ckpt_nt1900122218_step202784.pt",
    "RNA-Sc-650M_s17": "ckpt_nt1900122218_step202784.pt",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    spec = importlib.util.spec_from_file_location(
        "rnasc_model_for_strip", BACKUP / "code_git" / "rna_sc" / "model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    RNAMLMEncoder = module.RNAMLMEncoder

    records = []
    for run, filename in RUNS.items():
        source = BACKUP / "runs_final2_ckpt" / "runs" / run / filename
        manifest = json.loads((source.parent / "manifest.json").read_text())
        latest = max(manifest["checkpoints"], key=lambda row: row["nt"])
        expected_nt = int(filename.split("_nt")[1].split("_")[0])
        assert latest["nt"] == expected_nt, (run, latest, expected_nt)
        target_dir = OUT / run
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        record = {
            "run": run,
            "file": filename,
            "source_path": str(source),
            "source_bytes": source.stat().st_size,
            "source_sha256": sha256(source),
            "manifest_latest_nt": latest["nt"],
        }
        print(json.dumps({"event": "stripping", **record}), flush=True)
        ckpt = torch.load(source, map_location="cpu", weights_only=False)
        assert ckpt["nt"] == expected_nt
        assert "opt" in ckpt
        original_keys = list(ckpt["model"])
        original_state = ckpt["model"]
        ckpt = {key: value for key, value in ckpt.items() if key != "opt"}
        torch.save(ckpt, target)
        del ckpt
        loaded = torch.load(target, map_location="cpu", weights_only=False)
        assert "opt" not in loaded
        assert list(loaded["model"]) == original_keys
        exact = all(torch.equal(original_state[key], loaded["model"][key])
                    for key in original_keys)
        assert exact
        arch = loaded["cfg"]["arch"]
        model = RNAMLMEncoder(
            d_model=arch["d_model"], n_layers=arch["n_layers"],
            n_heads=arch["n_heads"], d_ff=arch["d_ff"])
        model.load_state_dict(loaded["model"], strict=True)
        record.update({
            "stripped_bytes": target.stat().st_size,
            "stripped_sha256": sha256(target),
            "model_tensors": len(loaded["model"]),
            "model_keys_exact_order": True,
            "model_tensors_bitwise_equal": exact,
            "strict_load": True,
            "optimizer_present": False,
            "nt": loaded["nt"],
            "step": loaded["step"],
            "arch": arch,
        })
        records.append(record)
        (target_dir / "strip_record.json").write_text(
            json.dumps(record, indent=2) + "\n")
        print(json.dumps({"event": "stripped", **record}), flush=True)
        del model, loaded, original_state
    (OUT / "strip_verification.json").write_text(
        json.dumps(records, indent=2) + "\n")
    with (OUT / "weight_source_strip_sha256.tsv").open("w") as handle:
        handle.write("run\tfile\tsource_bytes\tsource_sha256\tstripped_bytes\tstripped_sha256\n")
        for row in records:
            handle.write("\t".join(str(row[key]) for key in (
                "run", "file", "source_bytes", "source_sha256",
                "stripped_bytes", "stripped_sha256")) + "\n")


if __name__ == "__main__":
    main()
