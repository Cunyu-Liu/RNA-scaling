from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import random
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch

from rna_sc.census import GPUGuard
from rna_sc.probe import load_encoder

ALPHABET = "ACGU"
GPU_BUDGET_BYTES = 9 * 1024**3


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def collect_token_states(model, device, seqs, pairs_list, n_layers,
                         cache_dir, split, context_nt=256):
    model = model.to(device).eval()
    encoded = []
    labels = []
    for seq, pairs in zip(seqs, pairs_list):
        ids = [ALPHABET.index(b) for b in seq.upper().replace("T", "U")
               if b in ALPHABET][:context_nt]
        n = len(ids)
        if n < 4:
            continue
        paired = [0] * n
        for i, j in pairs:
            if i <= n and j <= n:
                paired[i - 1] = 1
                paired[j - 1] = 1
        encoded.append(ids)
        labels.extend(paired)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=False)
    total_tokens = sum(len(ids) for ids in encoded)
    states = [np.lib.format.open_memmap(
        cache_dir / f"{split}_layer{layer}.npy", mode="w+", dtype=np.float32,
        shape=(total_tokens, model.d_model)) for layer in range(n_layers)]
    offset = 0
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for ids in encoded:
            n = len(ids)
            x = torch.tensor([ids], device=device)
            logits, _, hids = model(x, return_all_hiddens=True)
            if not logits.is_cuda or logits.dtype != torch.bfloat16:
                raise RuntimeError("CUDA BF16 forward assertion failed")
            for li, h in enumerate(hids):
                if h.dtype != torch.float32:
                    raise RuntimeError("FP32 residual hidden-state assertion failed")
                states[li][offset:offset + n] = h[0, :n].cpu().numpy()
            offset += n
    for state in states:
        state.flush()
    y = torch.tensor(labels, dtype=torch.long)
    return states, y


def class_f1(pred, y, positive_class):
    tp = sum(1 for p, t in zip(pred, y)
             if p == positive_class and t == positive_class)
    fp = sum(1 for p, t in zip(pred, y)
             if p == positive_class and t != positive_class)
    fn = sum(1 for p, t in zip(pred, y)
             if p != positive_class and t == positive_class)
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return f1, precision, recall, {"tp": tp, "fp": fp, "fn": fn}


def run_one_layer(x_train, y_train, x_eval, y_eval, device, seed,
                  probe_batch_size, epochs=6, lr=1e-3):
    torch.manual_seed(seed)
    d = x_train.shape[1]
    weight = torch.zeros(d, 2, device=device, requires_grad=True)
    x_train_d = torch.from_numpy(np.asarray(x_train)).to(device).float()
    x_eval_d = torch.from_numpy(np.asarray(x_eval)).to(device).float()
    y_train_d = y_train.to(device)
    n_pos = float((y_train_d == 1).sum())
    n_neg = float(len(y_train_d) - n_pos)
    class_weight = torch.tensor([1.0, max(1.0, n_neg / max(1.0, n_pos))],
                                device=device)
    optimizer = torch.optim.AdamW([weight], lr=lr, weight_decay=0.01)
    for _ in range(epochs):
        permutation = torch.randperm(len(x_train_d), device=device)
        for i in range(0, len(x_train_d), probe_batch_size):
            idx = permutation[i:i + probe_batch_size]
            loss = torch.nn.functional.cross_entropy(
                x_train_d[idx] @ weight, y_train_d[idx], weight=class_weight)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    with torch.no_grad():
        logits = x_eval_d @ weight
        pred = logits.argmax(-1).cpu()
        acc = float((pred == y_eval).float().mean())
    pred_list = pred.tolist()
    y_list = y_eval.tolist()
    f1_paired, precision, recall, paired_counts = class_f1(
        pred_list, y_list, 1)
    f1_unpaired, precision_unpaired, recall_unpaired, unpaired_counts = class_f1(
        pred_list, y_list, 0)
    f1_macro = (f1_paired + f1_unpaired) / 2.0
    metrics = {
        "acc_unrounded": acc,
        "f1_paired_legacy_unrounded": f1_paired,
        "precision_unrounded": precision,
        "recall_unrounded": recall,
        "f1_unpaired_unrounded": f1_unpaired,
        "precision_unpaired_unrounded": precision_unpaired,
        "recall_unpaired_unrounded": recall_unpaired,
        "f1_macro_unrounded": f1_macro,
        "paired_confusion": paired_counts,
        "unpaired_confusion": unpaired_counts,
    }
    return metrics, pred.numpy().astype(np.int8)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--ckpt-nt", required=True, type=int)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--n-train-seqs", type=int, default=8000)
    parser.add_argument("--n-eval-seqs", type=int, default=1500)
    parser.add_argument("--random-init", type=int, default=None)
    parser.add_argument("--probe-batch-size", type=int, default=512)
    parser.add_argument("--bprna", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--prediction-out", required=True)
    parser.add_argument("--unit-summary-out", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    device = f"cuda:{args.device}"
    guard = GPUGuard(device)
    guard.check()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    torch.cuda.set_per_process_memory_fraction(
        GPU_BUDGET_BYTES / torch.cuda.get_device_properties(args.device).total_memory,
        device=args.device)
    torch.cuda.reset_peak_memory_stats(args.device)

    run_dir = Path(args.run_dir)
    model, checkpoint = load_encoder(str(run_dir), ckpt_nt=args.ckpt_nt)
    if int(checkpoint["nt"]) != args.ckpt_nt:
        raise AssertionError(
            f"checkpoint nt mismatch: requested {args.ckpt_nt}, loaded {checkpoint['nt']}")
    checkpoint_path = run_dir / (
        f"ckpt_nt{int(checkpoint['nt'])}_step{int(checkpoint['step'])}.pt")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    checkpoint_sha256 = sha256_file(checkpoint_path)
    base_run = run_dir.name
    architecture = dict(checkpoint["cfg"]["arch"])
    n_layers = int(architecture["n_layers"])
    if args.random_init is not None:
        from rna_sc.model import RNAMLMEncoder
        torch.manual_seed(args.random_init)
        model = RNAMLMEncoder(
            d_model=architecture["d_model"], n_layers=n_layers,
            n_heads=architecture["n_heads"], d_ff=architecture["d_ff"])
        run_name = f"{base_run}_randinit{args.random_init}"
        effective_ckpt_nt = 0
    else:
        run_name = f"{base_run}_ckpt{args.ckpt_nt}"
        effective_ckpt_nt = args.ckpt_nt

    table = pq.read_table(args.bprna).to_pydict()
    by_split = {"train": [], "test": []}
    for i, split in enumerate(table["split"]):
        if split in by_split:
            by_split[split].append(i)
    rng = random.Random(17)
    n_train = 1 if args.smoke else args.n_train_seqs
    n_eval = 1 if args.smoke else args.n_eval_seqs
    train_indices = rng.sample(by_split["train"], min(n_train, len(by_split["train"])))
    eval_indices = rng.sample(by_split["test"], min(n_eval, len(by_split["test"])))
    train_seqs = [table["seq"][i] for i in train_indices]
    train_pairs = [table["pairs"][i] for i in train_indices]
    eval_seqs = [table["seq"][i] for i in eval_indices]
    eval_pairs = [table["pairs"][i] for i in eval_indices]
    sample_payload = {
        "sample_seed": 17,
        "train_indices": train_indices,
        "eval_indices": eval_indices,
        "train_names": [table["name"][i] for i in train_indices],
        "eval_names": [table["name"][i] for i in eval_indices],
    }
    sample_sha256 = hashlib.sha256(json.dumps(
        sample_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({"event": "sample", "train_seqs": len(train_indices),
                      "eval_seqs": len(eval_indices),
                      "sample_sha256": sample_sha256}), flush=True)

    x_train, y_train = collect_token_states(
        model, device, train_seqs, train_pairs, n_layers,
        Path(args.cache_dir) / "train", "train")
    x_eval, y_eval = collect_token_states(
        model, device, eval_seqs, eval_pairs, n_layers,
        Path(args.cache_dir) / "eval", "eval")
    guard.verify_cuda_alive()
    print(json.dumps({"event": "states", "train_tokens": len(y_train),
                      "eval_tokens": len(y_eval),
                      "paired_rate_train": float(y_train.float().mean()),
                      "paired_rate_eval": float(y_eval.float().mean())}), flush=True)

    if args.smoke:
        metrics, pred = run_one_layer(
            x_train[0], y_train, x_eval[0], y_eval, device, 17,
            args.probe_batch_size, epochs=1)
        smoke = {
            "status": "PASS", "run": run_name, "device": device,
            "device_name": torch.cuda.get_device_name(args.device),
            "cuda": True, "bf16_forward": True, "one_layer_head": True,
            "prediction_shape": list(pred.shape),
            "train_tokens": len(y_train), "eval_tokens": len(y_eval),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(args.device),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(args.device),
            "cpu_fallback_count": guard.cpu_fallback_count,
            "metrics": metrics,
        }
        print("P2_1_SMOKE " + json.dumps(smoke, sort_keys=True), flush=True)
        del x_train, x_eval
        gc.collect()
        shutil.rmtree(args.cache_dir)
        return

    for path in (args.out_jsonl, args.prediction_out, args.unit_summary_out):
        if os.path.exists(path):
            raise FileExistsError(f"refusing to overwrite unit evidence: {path}")
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    script_path = Path(__file__).resolve()
    model_path = script_path.parent / "model.py"
    probe_path = script_path.parent / "probe.py"
    bprna_sha256 = sha256_file(args.bprna)
    script_sha256 = sha256_file(script_path)
    model_sha256 = sha256_file(model_path)
    probe_sha256 = sha256_file(probe_path)
    predictions = []
    best = None
    for layer in range(n_layers):
        metrics, pred = run_one_layer(
            x_train[layer], y_train, x_eval[layer], y_eval, device,
            seed=17 + layer, probe_batch_size=args.probe_batch_size)
        predictions.append(pred)
        row = {
            "run": run_name,
            "base_run": base_run,
            "task": "bpRNA paired-position",
            "layer": layer,
            "rel_depth": round(layer / (n_layers - 1), 3),
            "acc": round(metrics["acc_unrounded"], 4),
            "f1": round(metrics["f1_paired_legacy_unrounded"], 4),
            "f1_paired_legacy": round(metrics["f1_paired_legacy_unrounded"], 4),
            "precision": round(metrics["precision_unrounded"], 4),
            "recall": round(metrics["recall_unrounded"], 4),
            "f1_unpaired": round(metrics["f1_unpaired_unrounded"], 6),
            "f1_macro": round(metrics["f1_macro_unrounded"], 6),
            "precision_unpaired": round(metrics["precision_unpaired_unrounded"], 6),
            "recall_unpaired": round(metrics["recall_unpaired_unrounded"], 6),
            **metrics,
            "n_tokens_train": len(y_train),
            "n_tokens_eval": len(y_eval),
            "n_layers": n_layers,
            "ckpt_nt": effective_ckpt_nt,
            "requested_ckpt_nt": args.ckpt_nt,
            "checkpoint_step": int(checkpoint["step"]),
            "checkpoint_file": checkpoint_path.name,
            "checkpoint_sha256": checkpoint_sha256,
            "weight_source": "randinit" if args.random_init is not None else "trained",
            "random_init_seed": args.random_init,
            "architecture_source_ckpt_nt": args.ckpt_nt,
            "architecture": architecture,
            "bprna_sha256": bprna_sha256,
            "sample_sha256": sample_sha256,
            "script_sha256": script_sha256,
            "model_source_sha256": model_sha256,
            "probe_loader_sha256": probe_sha256,
            "sample_seed": 17,
            "head_seed": 17 + layer,
            "epochs": 6,
            "probe_batch_size": args.probe_batch_size,
            "learning_rate": 1e-3,
            "weight_decay": 0.01,
            "context_nt": 256,
            "state_cache_dtype": "float32_disk_memmap_lossless",
            "head_compute_dtype": "float32",
            "pair_coordinates": "1-based_to_0-based_i-1_j-1",
            "device": device,
            "cpu_fallback_count": guard.cpu_fallback_count,
        }
        with open(args.out_jsonl, "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("LAYER " + json.dumps({
            "run": run_name, "layer": layer, "acc": row["acc"],
            "f1_paired_legacy": row["f1_paired_legacy"],
            "f1_macro": row["f1_macro"],
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(args.device),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(args.device),
        }), flush=True)
        if best is None or metrics["f1_paired_legacy_unrounded"] > best["f1_paired_legacy_unrounded"]:
            best = row

    prediction_path = Path(args.prediction_out)
    np.savez_compressed(
        prediction_path,
        predictions=np.stack(predictions),
        y_eval=y_eval.numpy().astype(np.int8),
        train_indices=np.asarray(train_indices, dtype=np.int32),
        eval_indices=np.asarray(eval_indices, dtype=np.int32),
        layers=np.arange(n_layers, dtype=np.int32))
    del x_train, x_eval
    gc.collect()
    shutil.rmtree(args.cache_dir)
    guard.verify_cuda_alive()
    peak_allocated = torch.cuda.max_memory_allocated(args.device)
    peak_reserved = torch.cuda.max_memory_reserved(args.device)
    if peak_reserved > GPU_BUDGET_BYTES:
        raise RuntimeError(f"GPU lane B budget exceeded: {peak_reserved}")
    summary = {
        "status": "COMPLETE",
        "run": run_name,
        "base_run": base_run,
        "ckpt_nt": effective_ckpt_nt,
        "requested_ckpt_nt": args.ckpt_nt,
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_sha256,
        "weight_source": "randinit" if args.random_init is not None else "trained",
        "random_init_seed": args.random_init,
        "n_layers_written": len(predictions),
        "best_layer": best["layer"],
        "best_f1_paired_legacy": best["f1_paired_legacy"],
        "best_f1_macro": best["f1_macro"],
        "best_acc": best["acc"],
        "best_precision": best["precision"],
        "best_recall": best["recall"],
        "n_tokens_train": len(y_train),
        "n_tokens_eval": len(y_eval),
        "sample_sha256": sample_sha256,
        "bprna_sha256": bprna_sha256,
        "script_sha256": script_sha256,
        "model_source_sha256": model_sha256,
        "probe_loader_sha256": probe_sha256,
        "layers_jsonl": str(Path(args.out_jsonl).resolve()),
        "layers_jsonl_sha256": sha256_file(args.out_jsonl),
        "predictions": str(prediction_path.resolve()),
        "predictions_sha256": sha256_file(prediction_path),
        "device": device,
        "device_name": torch.cuda.get_device_name(args.device),
        "peak_allocated_bytes": peak_allocated,
        "peak_reserved_bytes": peak_reserved,
        "gpu_budget_bytes": GPU_BUDGET_BYTES,
        "feature_cache": "FP32 disk memmap, numerically identical to source FP32 states",
        "feature_cache_removed": True,
        "cpu_fallback_count": guard.cpu_fallback_count,
        "started_utc": started,
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.unit_summary_out, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("UNIT_COMPLETE " + json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
