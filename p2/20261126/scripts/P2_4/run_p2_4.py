from __future__ import annotations

import argparse
import json
import time

import numpy as np
import torch

from p2_4_common import (
    ALPHABET, ARMS, BATCH, K, OUT, SEED, WEIGHTS, coordinate_validation,
    long_range_mask, paired_f1, pair_mask, sha256, write_json,
)
from rna_sc.census import GPUGuard
from rna_sc.model import RNAMLMEncoder
from rna_sc.probe import load_encoder


def load_model(arm: str, device: str):
    spec = ARMS[arm]
    run_dir = WEIGHTS / spec["run"]
    model, checkpoint = load_encoder(str(run_dir))
    architecture = checkpoint["cfg"]["arch"]
    assert architecture["n_layers"] == spec["layers"]
    if spec["randinit"]:
        torch.manual_seed(SEED)
        model = RNAMLMEncoder(
            d_model=architecture["d_model"],
            n_layers=architecture["n_layers"],
            n_heads=architecture["n_heads"],
            d_ff=architecture["d_ff"],
        )
        checkpoint = dict(checkpoint)
        checkpoint["nt"] = 0
    model = model.to(device).eval()
    assert next(model.parameters()).is_cuda
    checkpoint_path = run_dir / f"ckpt_nt1900122218_step202784.pt"
    assert checkpoint_path.is_file()
    return model, checkpoint, checkpoint_path


def encode(model, seqs, layer: int, device: str, batch: int = BATCH,
           mean_pool: bool = False):
    outputs = []
    reductions = []
    current = batch
    index = 0
    model.eval()
    while index < len(seqs):
        end = min(index + current, len(seqs))
        chunk = seqs[index:end]
        ids = [[ALPHABET.index(base) for base in seq] for seq in chunk]
        assert all(ids)
        width = max(len(row) for row in ids)
        tokens = None
        pad = None
        try:
            tokens = torch.tensor(
                [row + [4] * (width - len(row)) for row in ids],
                dtype=torch.long, device=device)
            pad = tokens == 4
            with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
                logits, _, hiddens = model(tokens, return_all_hiddens=True)
                assert logits.is_cuda and logits.dtype == torch.bfloat16
                hidden = hiddens[layer]
                assert hidden.shape[:2] == tokens.shape
                assert hidden.dtype == torch.float32
                hidden = hidden.float()
            if mean_pool:
                masked = hidden.masked_fill(pad.unsqueeze(-1), 0.0)
                lengths = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
                outputs.append((masked.sum(1) / lengths).cpu())
            else:
                for row in range(len(chunk)):
                    outputs.append(hidden[row, :len(ids[row])].cpu())
            index = end
            if index % 200 < current or index == len(seqs):
                print(f"encoded {index}/{len(seqs)} mean_pool={mean_pool} "
                      f"batch={current}", flush=True)
        except torch.cuda.OutOfMemoryError:
            del tokens, pad
            torch.cuda.empty_cache()
            if current == 1:
                raise
            current = 2 if current == 4 else 1
            reductions.append(current)
            print(f"CUDA OOM: reducing forward batch to {current}", flush=True)
    if mean_pool:
        return torch.cat(outputs, 0), reductions
    return outputs, reductions


def rns_per_real(real_emb, random_emb, k: int, device: str):
    real = torch.nn.functional.normalize(real_emb.to(device), dim=1)
    random = torch.nn.functional.normalize(random_emb.to(device), dim=1)
    real_random = real @ random.T
    real_real = real @ real.T
    real_real.diagonal().fill_(-2.0)
    best_rr, _ = real_real.topk(k, dim=1)
    best_ra, _ = real_random.topk(k, dim=1)
    candidates = torch.cat([best_rr, best_ra], dim=1)
    thresholds, _ = candidates.topk(k, dim=1)
    threshold = thresholds[:, -1].unsqueeze(1)
    n_random = (real_random >= threshold).float().sum(1).clamp(max=k)
    return (n_random / k).cpu().numpy()


def smoke(model, device: str):
    coordinate_validation()
    seqs = ["ACGUACGU", "AACCGGUU"]
    pooled, reductions = encode(model, seqs, 16, device, batch=4,
                                mean_pool=True)
    assert pooled.shape[0] == 2 and not reductions
    torch.manual_seed(SEED)
    head_a = torch.nn.Linear(pooled.shape[1], 2).to(device)
    perm_a = torch.randperm(1000, device=device)
    torch.manual_seed(SEED)
    head_b = torch.nn.Linear(pooled.shape[1], 2).to(device)
    perm_b = torch.randperm(1000, device=device)
    assert all(torch.equal(a, b) for a, b in zip(
        head_a.state_dict().values(), head_b.state_dict().values()))
    assert torch.equal(perm_a, perm_b)
    print(json.dumps({
        "smoke": "PASS", "device": device,
        "gpu": torch.cuda.get_device_name(0),
        "dtype": "bfloat16_autocast_fp32_residual_states",
        "pooled_shape": list(pooled.shape),
        "head_seed": SEED, "head_reproducible": True,
        "coordinate_1based_to_0based": True,
        "cpu_fallback": False,
    }), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=list(ARMS))
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--batch", type=int, default=BATCH, choices=[4, 2, 1])
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; CPU fallback is forbidden")
    device = f"cuda:{args.device}"
    GPUGuard(device).check()
    torch.cuda.reset_peak_memory_stats()
    model, checkpoint, checkpoint_path = load_model(args.arm, device)
    if args.smoke:
        assert args.arm == "100M"
        smoke(model, device)
        return

    freeze_path = OUT / "p2_4_shared_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    assert freeze["status"] == "FROZEN"
    spec = ARMS[args.arm]
    layer = spec["layer"]
    unit = OUT / "units" / args.arm
    unit.mkdir(parents=True, exist_ok=True)
    summary_path = unit / "unit_summary.json"
    if summary_path.exists():
        raise FileExistsError(f"refusing to overwrite completed unit: {unit}")
    start = time.time()
    random_seqs = [row["sequence"] for row in freeze["random_rows"]]
    train = freeze["train_rows"]
    test = freeze["test_rows"]
    assert len(random_seqs) == 4500 and len(train) == 2000

    print(f"arm={args.arm} layer={layer} random_init={spec['randinit']}", flush=True)
    random_emb, reductions_random = encode(
        model, random_seqs, layer, device, args.batch, mean_pool=True)
    train_emb, reductions_train = encode(
        model, [row["sequence"] for row in train], layer, device, args.batch)
    x_train = torch.cat(train_emb, 0)
    y_train = torch.cat([
        pair_mask(row["pairs"], len(row["sequence"])) for row in train], 0)
    del train_emb
    n_pos = int(y_train.sum().item())
    n_neg = len(y_train) - n_pos
    class_weights = torch.tensor(
        [n_pos / len(y_train), n_neg / len(y_train)], dtype=torch.float32,
        device=device)

    torch.manual_seed(SEED)
    head = torch.nn.Linear(x_train.shape[1], 2)
    head.to(device)
    optimizer = torch.optim.Adam(head.parameters(), lr=1e-3)
    x_device = x_train.to(device)
    y_device = y_train.to(device)
    losses = []
    for epoch in range(3):
        permutation = torch.randperm(len(x_device), device=device)
        for begin in range(0, len(x_device), 65536):
            indices = permutation[begin:begin + 65536]
            logits = head(x_device[indices])
            loss = torch.nn.functional.cross_entropy(
                logits, y_device[indices], weight=class_weights)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        losses.append(float(loss.item()))
        print(f"head epoch={epoch} loss={losses[-1]:.8f}", flush=True)
    head.eval()
    torch.save({"state_dict": head.state_dict(), "layer": layer,
                "head_seed": SEED, "arm": args.arm}, unit / "head.pt")
    del x_device, y_device, x_train, y_train, optimizer
    torch.cuda.empty_cache()

    test_emb, reductions_test = encode(
        model, [row["sequence"] for row in test], layer, device, args.batch)
    test_mean = torch.stack([emb.mean(0) for emb in test_emb], 0)
    rns = rns_per_real(test_mean, random_emb, K, device)
    assert len(rns) == len(test)
    records = []
    with torch.no_grad():
        for row, emb, rns_value in zip(test, test_emb, rns):
            pred = head(emb.to(device)).argmax(-1).cpu()
            truth = pair_mask(row["pairs"], len(row["sequence"]))
            lr_mask = long_range_mask(row["pairs"], len(row["sequence"]))
            all_f1 = paired_f1(truth, pred)
            long_f1 = paired_f1(truth[lr_mask], pred[lr_mask]) if lr_mask.any() else None
            records.append({
                "arm": args.arm,
                "run": "RNA-Sc-100M_s17_randinit17" if spec["randinit"] else spec["run"],
                "layer": layer,
                "sequence_id": row["sequence_id"],
                "source_row": row["source_row"],
                "name": row["name"],
                "source": row["source"],
                "length": len(row["sequence"]),
                "rns": float(rns_value),
                "all_f1": all_f1,
                "long_f1": long_f1,
            })
    output_path = unit / "p2_4_per_sequence.jsonl"
    with output_path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
    peak = torch.cuda.max_memory_reserved()
    summary = {
        "arm": args.arm,
        "run": records[0]["run"],
        "status": "COMPLETE",
        "layer": layer,
        "n_layers": spec["layers"],
        "random_init_seed": SEED if spec["randinit"] else None,
        "head_seed": SEED,
        "bootstrap_seed_not_used_here": SEED,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256(checkpoint_path),
        "checkpoint_nt": checkpoint.get("nt"),
        "shared_freeze_sha256": sha256(freeze_path),
        "n_train": len(train),
        "n_test": len(test),
        "n_random": len(random_seqs),
        "train_tokens": n_pos + n_neg,
        "train_positive_tokens": n_pos,
        "class_weights": [n_pos / (n_pos + n_neg), n_neg / (n_pos + n_neg)],
        "head_losses": losses,
        "forward_batch_initial": args.batch,
        "forward_batch_reductions": {
            "random": reductions_random, "train": reductions_train,
            "test": reductions_test,
        },
        "device": device,
        "gpu": torch.cuda.get_device_name(args.device),
        "dtype": "bfloat16_autocast_fp32_residual_states",
        "cpu_fallback_count": 0,
        "max_memory_reserved_bytes": int(peak),
        "elapsed_seconds": time.time() - start,
        "output_sha256": sha256(output_path),
    }
    if peak > 20 * 1024 ** 3:
        raise RuntimeError(f"P2.4 GPU budget exceeded: {peak}")
    write_json(summary_path, summary)
    print(json.dumps({key: summary[key] for key in [
        "arm", "status", "n_test", "max_memory_reserved_bytes",
        "elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
