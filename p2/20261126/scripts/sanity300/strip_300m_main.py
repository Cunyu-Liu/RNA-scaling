import hashlib
import json
import os
from pathlib import Path

import torch

SOURCE = Path("/root/rna-sc/runs/RNA-Sc-300M_s17/ckpt_nt1900122218_step202784.pt")
EXPECTED_SOURCE_SHA256 = "4f761014594fd937e357170a089c37ce79e68e23220432d9b7a6cd5085f66166"
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
TARGET = BASE / "weights/RNA-Sc-300M_s17/ckpt_nt1900122218_step202784.pt"
OUT = BASE / "results/sanity300"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    assert not TARGET.exists(), f"Refusing to overwrite {TARGET}"
    source_hash = sha256(SOURCE)
    assert source_hash == EXPECTED_SOURCE_SHA256
    original = torch.load(SOURCE, map_location="cpu", weights_only=False)
    assert original["nt"] == 1900122218
    assert original["step"] == 202784
    assert "opt" in original
    original_state = original["model"]
    original_keys = list(original_state)
    stripped = {key: value for key, value in original.items() if key != "opt"}
    temporary = TARGET.with_suffix(TARGET.suffix + ".tmp")
    torch.save(stripped, temporary)
    os.replace(temporary, TARGET)
    del stripped
    target_hash = sha256(TARGET)
    loaded = torch.load(TARGET, map_location="cpu", weights_only=False)
    assert list(loaded["model"]) == original_keys
    assert all(torch.equal(original_state[key], loaded["model"][key])
               for key in original_keys)
    assert "opt" not in loaded
    record = {
        "status": "PASS",
        "run": "RNA-Sc-300M_s17",
        "source_path": str(SOURCE),
        "local_readonly_backup_path": "/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc/runs_final2_ckpt/runs/RNA-Sc-300M_s17/ckpt_nt1900122218_step202784.pt",
        "source_sha256": source_hash,
        "source_matches_local_backup": True,
        "target_path": str(TARGET),
        "target_bytes": TARGET.stat().st_size,
        "target_sha256": target_hash,
        "checkpoint_nt": loaded["nt"],
        "checkpoint_step": loaded["step"],
        "model_tensors": len(original_keys),
        "model_keys_exact_order": True,
        "model_tensors_bitwise_equal": True,
        "optimizer_present": False,
    }
    (OUT / "weight_strip_verification.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(record, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
