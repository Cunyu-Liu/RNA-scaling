import hashlib
import json
import os
from pathlib import Path

import torch

SOURCE = Path("/root/rna-sc/runs")
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
OUT = BASE / "results" / "upload_main"
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
    expected = {}
    with (OUT / "weight_source_strip_sha256.tsv").open() as handle:
        next(handle)
        for line in handle:
            run, filename, _, source_hash, _, stripped_hash = line.rstrip("\n").split("\t")
            expected[run] = (source_hash, stripped_hash)
    records = []
    for run, filename in RUNS.items():
        source = SOURCE / run / filename
        source_hash = sha256(source)
        assert source_hash == expected[run][0], (run, source_hash)
        target_dir = BASE / "weights" / run
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        ckpt = torch.load(source, map_location="cpu", weights_only=False)
        original_state = ckpt["model"]
        original_keys = list(original_state)
        ckpt = {key: value for key, value in ckpt.items() if key != "opt"}
        temporary = target.with_suffix(target.suffix + ".tmp")
        torch.save(ckpt, temporary)
        os.replace(temporary, target)
        del ckpt
        stripped_hash = sha256(target)
        binary_matches_local = stripped_hash == expected[run][1]
        loaded = torch.load(target, map_location="cpu", weights_only=False)
        assert list(loaded["model"]) == original_keys
        assert all(torch.equal(original_state[key], loaded["model"][key])
                   for key in original_keys)
        assert "opt" not in loaded
        record = {
            "status": "PASS",
            "run": run,
            "source_path": str(source),
            "source_sha256": source_hash,
            "source_matches_local_backup": True,
            "target_path": str(target),
            "target_sha256": stripped_hash,
            "target_matches_local_stripped": binary_matches_local,
            "serialization_note": (
                "Remote torch 2.14.1 and local torch 2.8.0 may produce different "
                "container bytes; tensor equality is checked separately."
            ),
            "model_keys_exact_order": True,
            "model_tensors_bitwise_equal": True,
            "optimizer_present": False,
        }
        records.append(record)
        print(json.dumps(record), flush=True)
        del loaded, original_state
    (OUT / "remote_strip_verification.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
