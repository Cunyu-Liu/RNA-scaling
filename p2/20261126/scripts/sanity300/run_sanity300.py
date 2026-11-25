import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import torch

ROOT = Path("/home/cunyuliu/rna-sc-p2")
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
SCRIPT = ROOT / "p2_3/run_p2_3_cov.py"
EXPECTED_SCRIPT_SHA256 = "693c5b8fd37fc76c057f24905ad544a03ccaad119bea069f0e6cc88fed8e007b"
OUT = BASE / "results/sanity300"
LOGS = BASE / "logs/sanity300"


def load_original():
    actual = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert actual == EXPECTED_SCRIPT_SHA256
    spec = importlib.util.spec_from_file_location("p2_3_original", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    module.LOGS = LOGS
    return module


def make_main_adapter(module):
    def load(model_key, mode, device="cuda:0"):
        assert model_key == "rnasc300m_sanity" and mode == "trained"
        from rna_sc.probe import load_encoder
        run = BASE / "weights/RNA-Sc-300M_s17"
        model, checkpoint = load_encoder(str(run), ckpt_nt=1900122218)
        assert checkpoint["nt"] == 1900122218
        assert checkpoint["step"] == 202784
        return module.RNAScAdapter(model, device), {
            "checkpoint_nt": checkpoint["nt"],
            "checkpoint_step": checkpoint["step"],
            "weight_path": str(run / "ckpt_nt1900122218_step202784.pt"),
            "weight_sha256": module.sha256_file(
                run / "ckpt_nt1900122218_step202784.pt"),
        }, None
    return load


def run_trained():
    module = load_original()
    module.make_adapter = make_main_adapter(module)
    module.run_sanity()


def run_batch1():
    module = load_original()
    module.INITIAL_CONDITION_BATCH = 1
    _, conditions = module.load_frozen()
    adapter, info, _ = make_main_adapter(module)("rnasc300m_sanity", "trained")
    per_condition = OUT / "rnasc300m_main_batch1_per_condition.jsonl"
    result = module.evaluate_model(adapter, "rnasc300m_s17_main_batch1", "trained",
                                   conditions, per_condition)
    result["model_info"] = info
    result["diagnostic"] = "Only condition batch changed 16 to 1 to match authoritative run_cov300.py"
    module.write_json(OUT / "rnasc300m_main_batch1.json", result)
    print("BATCH1_COMPLETE", json.dumps({
        "cov": result["cov"],
        "ctrl": result["ctrl"],
        "cov_minus_ctrl": result["cov_minus_ctrl"],
        "old_anchor": module.OLD_ANCHOR,
    }, indent=2), flush=True)


def run_randinit():
    module = load_original()
    _, conditions = module.load_frozen()
    from rna_sc.probe import load_encoder
    from rna_sc.model import RNAMLMEncoder
    run = BASE / "weights/RNA-Sc-300M_s17"
    _, checkpoint = load_encoder(str(run), ckpt_nt=1900122218)
    torch.manual_seed(17)
    config = checkpoint["cfg"]["arch"]
    model = RNAMLMEncoder(d_model=config["d_model"],
                          n_layers=config["n_layers"],
                          n_heads=config["n_heads"],
                          d_ff=config["d_ff"])
    adapter = module.RNAScAdapter(model, "cuda:0")
    smoke_ids = adapter.encode_ids(conditions[0]["ids"])
    smoke = adapter.smoke(smoke_ids, conditions[0]["j"], adapter.vocab)
    module.write_json(LOGS / "rnasc300m_randinit17_smoke.json", smoke)
    per_condition = OUT / "rnasc300m_randinit17_per_condition.jsonl"
    result = module.evaluate_model(adapter, "rnasc300m_s17_main", "randinit17",
                                   conditions, per_condition)
    result.update({
        "model_info": {
            "architecture": config,
            "random_init_seed": 17,
            "source": "same architecture as main-arm checkpoint; all parameters reinitialized",
        },
        "smoke": smoke,
    })
    module.write_json(OUT / "rnasc300m_randinit17.json", result)
    print("RANDINIT_COMPLETE", json.dumps({
        "cov": result["cov"],
        "ctrl": result["ctrl"],
        "cov_minus_ctrl": result["cov_minus_ctrl"],
    }, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["trained", "randinit17", "batch1"])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if args.mode == "trained":
        run_trained()
    elif args.mode == "randinit17":
        run_randinit()
    else:
        run_batch1()


if __name__ == "__main__":
    main()
