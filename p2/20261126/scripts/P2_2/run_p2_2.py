from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch

ROOT = Path("/home/cunyuliu/rna-sc-p2")
CODE = ROOT / "code_git"
BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
DATA = BASE / "data" / "bpRNA_parsed.parquet"
RUN = BASE / "weights" / "RNA-Sc-30M_s17"
OUT = BASE / "results" / "P2_2"
LOGS = OUT / "logs"
sys.path.insert(0, str(CODE))

ALPHABET = "ACGU"
COMP = {0: 3, 3: 0, 1: 2, 2: 1}
MASK = 5
PAD = 4
SEED = 17
MAX_NT = 192
MIN_NT = 24
MAX_PER_SOURCE = 40
COMMON_PER_SOURCE = 20
MIN_SOURCE_N = 12
MAX_PAIRS = 20
K = 10
BOOTSTRAP_N = 2000
INITIAL_CONDITION_BATCH = 16
LAYER = 8

FROZEN_SEQS = OUT / "p2_2_frozen_sequences.jsonl"
RANDOM_POOL = OUT / "p2_2_random_pool.jsonl"
CONDITIONS = OUT / "p2_2_cov_conditions.jsonl"
FREEZE_META = OUT / "p2_2_freeze.json"
RNS_ROWS = OUT / "p2_2_rns_per_sequence.jsonl"
NEIGHBORS = OUT / "p2_2_rns_neighbors.jsonl"
MUTATIONS = OUT / "p2_2_cov_per_mutation.jsonl"
RUN_SUMMARY = OUT / "p2_2_gpu_run_summary.json"
PER_SEQUENCE = OUT / "evidence" / "p2_2_rns_cov_per_sequence.csv"
PER_FAMILY = OUT / "evidence" / "p2_2_rns_cov_per_family.csv"
SUMMARY = OUT / "evidence" / "p2_2_rns_cov.json"
VALIDATION = OUT / "p2_2_validation.json"
MANIFEST = OUT / "p2_2_manifest.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lines(values):
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(value, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def encode(seq):
    return [ALPHABET.index(b) for b in seq.upper().replace("T", "U")
            if b in ALPHABET][:MAX_NT]


def build_conditions(ids, pairs, rng):
    n = len(ids)
    valid = [(i - 1, j - 1) for i, j in pairs if i <= n and j <= n]
    valid_pair_n = len(valid)
    paired_pos = set()
    for i, j in valid:
        paired_pos.add(i)
        paired_pos.add(j)
    unpaired = [p for p in range(n) if p not in paired_pos]
    rng.shuffle(valid)
    valid = valid[:MAX_PAIRS]
    conditions = []
    for i, j in valid:
        xi = ids[i]
        if xi not in COMP:
            continue
        far = [k for k in unpaired if abs(k - i) > 5 and abs(k - j) > 5]
        k = rng.choice(far) if far else None
        muts = [b for b in range(4) if b != xi]
        conditions.append({"i": i, "j": j, "k": k, "xi": xi, "muts": muts})
    return conditions, valid_pair_n


def source_queue():
    by_source = collections.OrderedDict()
    test_counts = collections.Counter()
    pf = pq.ParquetFile(DATA)
    row_offset = 0
    for rb in pf.iter_batches(batch_size=50_000,
                              columns=["name", "source", "seq", "pairs", "split"]):
        d = rb.to_pydict()
        for ri, (name, source, seq, pairs, split) in enumerate(zip(
                d["name"], d["source"], d["seq"], d["pairs"], d["split"])):
            test_index = row_offset + ri
            if split != "test":
                continue
            test_counts[source] += 1
            clean = "".join(b for b in seq.upper().replace("T", "U")
                            if b in ALPHABET)[:MAX_NT]
            if len(clean) < MIN_NT:
                continue
            queue = by_source.setdefault(source, [])
            if len(queue) < MAX_PER_SOURCE:
                queue.append({
                    "test_index": test_index,
                    "sample_id": f"test_index_{test_index}",
                    "sequence_id": name,
                    "source": source,
                    "source_queue_index": len(queue),
                    "length": len(clean),
                    "sequence": clean,
                    "sequence_sha256": hashlib.sha256(clean.encode()).hexdigest(),
                    "pairs_1based": pairs,
                })
        row_offset += len(d["seq"])
    retained = collections.OrderedDict(
        (source, rows) for source, rows in by_source.items() if len(rows) >= MIN_SOURCE_N)
    selected = []
    conditions = []
    rng = random.Random(SEED)
    for source, rows in retained.items():
        for row in rows[:COMMON_PER_SOURCE]:
            row = dict(row)
            row["selected_order"] = len(selected)
            ids = encode(row["sequence"])
            assert len(ids) == row["length"]
            conds, valid_pair_n = build_conditions(ids, row["pairs_1based"], rng)
            row["valid_pair_n"] = valid_pair_n
            row["sampled_pair_n"] = len(conds)
            row["ctrl_pair_n"] = sum(c["k"] is not None for c in conds)
            selected.append(row)
            for pair_order, cond in enumerate(conds):
                condition = dict(cond)
                condition.update({
                    "condition_id": f"{row['sample_id']}:pair_{pair_order:02d}:i{cond['i']}:j{cond['j']}",
                    "sample_id": row["sample_id"],
                    "sequence_id": row["sequence_id"],
                    "source": row["source"],
                    "selected_order": row["selected_order"],
                    "pair_order": pair_order,
                    "original_base": ALPHABET[cond["xi"]],
                    "mutations": [ALPHABET[m] for m in cond["muts"]],
                })
                conditions.append(condition)
    queue_rows = []
    for source in by_source:
        queue_rows.append({
            "source": source,
            "test_n": test_counts[source],
            "eligible_queue_n_capped_40": len(by_source[source]),
            "retained_pre_pair": source in retained,
            "selected_common_n": min(COMMON_PER_SOURCE, len(retained.get(source, []))),
            "label_scope": "coarse bpRNA source; not fine-grained Rfam ID",
        })
    return selected, conditions, queue_rows


def mono_freq(seqs):
    counts = {b: 0 for b in ALPHABET}
    for seq in seqs:
        for b in seq:
            counts[b] += 1
    total = sum(counts.values())
    return {b: counts[b] / total for b in ALPHABET}


def load_model():
    from rna_sc.probe import load_encoder
    checkpoints = sorted(RUN.glob("ckpt_*.pt"))
    assert len(checkpoints) == 1, checkpoints
    model, ck = load_encoder(str(RUN))
    assert ck["cfg"]["arch"]["n_layers"] == 12
    assert LAYER == int(round(0.75 * (12 - 1)))
    assert ck["nt"] == 1900121822, ck["nt"]
    return model, ck, checkpoints[0]


def input_files(script_path):
    return {
        "bpRNA_split_parquet": DATA,
        "checkpoint": RUN / "ckpt_nt1900121822_step202784.pt",
        "checkpoint_manifest": RUN / "manifest.json",
        "execution_script": script_path,
        "run_cov300": CODE / "run_cov300.py",
        "s14_rns": CODE / "rna_sc" / "s14_rns.py",
        "s14_rns_ext": CODE / "rna_sc" / "s14_rns_ext.py",
        "s14_rns_cov": CODE / "rna_sc" / "s14_rns_cov.py",
        "model_and_tokenizer": CODE / "rna_sc" / "model.py",
        "load_encoder": CODE / "rna_sc" / "probe.py",
    }


def freeze():
    from rna_sc.s14_rns import ks_check, make_random_pool
    OUT.mkdir(parents=True, exist_ok=True)
    selected, conditions, queue_rows = source_queue()
    assert len(selected) == 109, len(selected)
    assert len({r["sequence_id"] for r in selected}) == len(selected)
    real = [r["sequence"] for r in selected]
    random_seqs, target_mono, target_di = make_random_pool(real, 3, seed=SEED)
    real_mono = mono_freq(real)
    random_mono = mono_freq(random_seqs)
    ks_d, ks_p = ks_check([len(s) for s in real], [len(s) for s in random_seqs])
    mono_dev = {b: abs(real_mono[b] - random_mono[b]) for b in ALPHABET}
    qc = {
        "ks_d": ks_d,
        "ks_p": ks_p,
        "ks_pass": ks_p > 0.05,
        "mono_max_deviation": max(mono_dev.values()),
        "mono_deviation_by_base": mono_dev,
        "mono_pass": max(mono_dev.values()) < 0.02,
        "n_real": len(real),
        "n_random": len(random_seqs),
        "random_multiplier_exact": len(random_seqs) == 3 * len(real),
        "real_mono": real_mono,
        "random_mono": random_mono,
        "target_mono": target_mono,
        "target_di": target_di,
    }
    qc["passed"] = qc["ks_pass"] and qc["mono_pass"] and qc["random_multiplier_exact"]
    random_rows = [{"random_id": f"random_{i:04d}", "random_order": i,
                    "length": len(seq), "sequence": seq,
                    "sequence_sha256": hashlib.sha256(seq.encode()).hexdigest()}
                   for i, seq in enumerate(random_seqs)]
    write_jsonl(FROZEN_SEQS, selected)
    write_jsonl(RANDOM_POOL, random_rows)
    write_jsonl(CONDITIONS, conditions)
    write_csv(OUT / "p2_2_source_queue.csv", queue_rows,
              ["source", "test_n", "eligible_queue_n_capped_40", "retained_pre_pair",
               "selected_common_n", "label_scope"])
    inputs = {}
    for name, path in input_files(Path(__file__).resolve()).items():
        inputs[name] = {"path": str(path), "sha256": sha256_file(path),
                        "bytes": path.stat().st_size}
    meta = {
        "task": "X-P22 / P2.2",
        "protocol": "prereg/P2_2.md",
        "status": "FROZEN_RANDOM_POOL_QC_PASS" if qc["passed"] else "FAILED_RANDOM_POOL_QC",
        "seed": SEED,
        "model": "RNA-Sc-30M_s17",
        "checkpoint_nt": 1900121822,
        "n_layers": 12,
        "rns_layer_zero_indexed": LAYER,
        "max_nt": MAX_NT,
        "min_nt": MIN_NT,
        "max_per_source_queue": MAX_PER_SOURCE,
        "common_per_source": COMMON_PER_SOURCE,
        "min_source_n_pre_pair": MIN_SOURCE_N,
        "min_source_n_post_pair": MIN_SOURCE_N,
        "max_pairs": MAX_PAIRS,
        "k": K,
        "bootstrap_n": BOOTSTRAP_N,
        "n_selected": len(selected),
        "n_conditions": len(conditions),
        "n_sources": len({r["source"] for r in selected}),
        "sequence_ids_sha256": sha256_lines([r["sequence_id"] for r in selected]),
        "frozen_sequences_sha256": sha256_file(FROZEN_SEQS),
        "random_pool_sha256": sha256_file(RANDOM_POOL),
        "conditions_sha256": sha256_file(CONDITIONS),
        "random_pool_qc": qc,
        "inputs": inputs,
        "tokenizer": {"type": "single-nucleotide", "ACGU": [0, 1, 2, 3],
                      "PAD": PAD, "MASK": MASK, "CLS": 6, "vocab_total": 7},
        "source_label_scope": "coarse bpRNA source; not fine-grained Rfam ID",
    }
    write_json(FREEZE_META, meta)
    write_csv(OUT / "evidence" / "p2_2_input_hashes.csv",
              [{"input": name, **info} for name, info in inputs.items()],
              ["input", "path", "sha256", "bytes"])
    print(json.dumps({k: v for k, v in meta.items() if k != "inputs"}, indent=2), flush=True)
    if not qc["passed"]:
        raise SystemExit(2)


def load_frozen():
    meta = json.load(open(FREEZE_META))
    assert meta["random_pool_qc"]["passed"]
    assert sha256_file(FROZEN_SEQS) == meta["frozen_sequences_sha256"]
    assert sha256_file(RANDOM_POOL) == meta["random_pool_sha256"]
    assert sha256_file(CONDITIONS) == meta["conditions_sha256"]
    assert sha256_file(DATA) == meta["inputs"]["bpRNA_split_parquet"]["sha256"]
    assert sha256_file(Path(__file__).resolve()) == meta["inputs"]["execution_script"]["sha256"]
    seqs = read_jsonl(FROZEN_SEQS)
    random_rows = read_jsonl(RANDOM_POOL)
    conditions = read_jsonl(CONDITIONS)
    assert len(seqs) == meta["n_selected"]
    assert len(conditions) == meta["n_conditions"]
    return meta, seqs, random_rows, conditions


def forward_probs(model, device, rows, read_pos):
    max_len = max(len(row) for row in rows)
    ids = torch.tensor([row + [PAD] * (max_len - len(row)) for row in rows],
                       dtype=torch.long, device=device)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        logits, _ = model(ids, return_all_hiddens=False)
    assert logits.is_cuda and logits.shape[-1] == 7
    probs = torch.softmax(logits.float(), dim=-1)
    return torch.stack([probs[bi, rp, :4].cpu()
                        for bi, rp in enumerate(read_pos)])


def condition_forward_rows(cond):
    base = encode(cond["sequence"])
    rows = []
    reads = []
    orig = list(base)
    orig[cond["j"]] = MASK
    rows.append(orig)
    reads.append(cond["j"])
    for m in cond["muts"]:
        mut = list(base)
        mut[cond["i"]] = m
        mut[cond["j"]] = MASK
        rows.append(mut)
        reads.append(cond["j"])
    if cond["k"] is not None:
        orig_k = list(base)
        orig_k[cond["k"]] = MASK
        rows.append(orig_k)
        reads.append(cond["k"])
        for m in cond["muts"]:
            mut_k = list(base)
            mut_k[cond["i"]] = m
            mut_k[cond["k"]] = MASK
            rows.append(mut_k)
            reads.append(cond["k"])
    return rows, reads


def smoke():
    from rna_sc.census import GPUGuard
    LOGS.mkdir(parents=True, exist_ok=True)
    meta, seqs, _, conditions = load_frozen()
    assert torch.cuda.is_available()
    device = "cuda:0"
    guard = GPUGuard(device)
    guard.check()
    model, ck, checkpoint = load_model()
    model = model.to(device).eval()
    assert next(model.parameters()).is_cuda
    by_sample = collections.OrderedDict()
    for cond in conditions:
        by_sample.setdefault(cond["sample_id"], []).append(cond)
    sample = next(row for row in seqs if row["sample_id"] in by_sample)
    cond = dict(by_sample[sample["sample_id"]][0])
    cond["sequence"] = sample["sequence"]
    rows, reads = condition_forward_rows(cond)
    ids = torch.tensor([rows[0]], dtype=torch.long, device=device)
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        logits, _, hiddens = model(ids, return_all_hiddens=True)
    assert logits.shape == (1, len(rows[0]), 7)
    assert len(hiddens) == 12
    assert hiddens[LAYER].shape == (1, len(rows[0]), 480)
    probs = forward_probs(model, device, rows[:2], reads[:2])
    assert probs.shape == (2, 4) and torch.isfinite(probs).all()
    guard.verify_cuda_alive()
    result = {
        "status": "PASS",
        "cuda_available": True,
        "cuda_device": torch.cuda.get_device_name(0),
        "model_device": str(next(model.parameters()).device),
        "torch_cuda": torch.version.cuda,
        "bf16_autocast": True,
        "checkpoint": str(checkpoint),
        "checkpoint_nt": ck["nt"],
        "n_layers": len(hiddens),
        "rns_layer_zero_indexed": LAYER,
        "hidden_shape": list(hiddens[LAYER].shape),
        "logits_shape": list(logits.shape),
        "mask_id": MASK,
        "pad_id": PAD,
        "probabilities_finite": True,
        "cpu_fallback_count": guard.cpu_fallback_count,
        "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
        "script_sha256": meta["inputs"]["execution_script"]["sha256"],
    }
    write_json(LOGS / "p2_2_smoke.json", result)
    print(json.dumps(result, indent=2), flush=True)


def embed(model, device, seqs):
    output = []
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for start in range(0, len(seqs), 8):
            chunk = seqs[start:start + 8]
            rows = [encode(seq) for seq in chunk]
            max_len = max(len(row) for row in rows)
            ids = torch.tensor([row + [PAD] * (max_len - len(row)) for row in rows],
                               dtype=torch.long, device=device)
            pad = ids == PAD
            _, _, hiddens = model(ids, return_all_hiddens=True)
            h = hiddens[LAYER]
            assert h.shape[:2] == ids.shape
            masked = h.float().masked_fill(pad.unsqueeze(-1), 0.0)
            lengths = (~pad).sum(-1).clamp(min=1).float().unsqueeze(-1)
            output.append((masked.sum(1) / lengths).cpu())
    return torch.cat(output, dim=0)


def compute_rns(model, device, seqs, random_rows):
    real_emb = embed(model, device, [row["sequence"] for row in seqs])
    random_emb = embed(model, device, [row["sequence"] for row in random_rows])
    real = torch.nn.functional.normalize(real_emb.to(device), dim=1)
    rand = torch.nn.functional.normalize(random_emb.to(device), dim=1)
    combined = torch.cat([real, rand], dim=0)
    similarities = real @ combined.T
    similarities.fill_diagonal_(float("-inf"))
    values, indices = similarities.topk(K, dim=1)
    n_random = (indices >= len(seqs)).sum(dim=1)
    rns = n_random.float() / K
    srr = real @ real.T
    sra = real @ rand.T
    rr = srr.clone()
    rr.diagonal().fill_(-2.0)
    best_rr, _ = rr.topk(K, dim=1)
    best_ra, _ = sra.topk(K, dim=1)
    candidates = torch.cat([best_rr, best_ra], dim=1)
    threshold = candidates.topk(K, dim=1).values[:, -1].unsqueeze(1)
    legacy_n_random = (sra >= threshold).float().sum(1).clamp(max=K)
    legacy_rns = legacy_n_random / K
    assert torch.equal(rns.cpu(), legacy_rns.cpu())
    rns_rows = []
    neighbor_rows = []
    all_ids = [row["sample_id"] for row in seqs] + [row["random_id"] for row in random_rows]
    for i, row in enumerate(seqs):
        rns_rows.append({
            "sample_id": row["sample_id"],
            "sequence_id": row["sequence_id"],
            "source": row["source"],
            "length": row["length"],
            "rns_layer_zero_indexed": LAYER,
            "rns_at_10": float(rns[i].cpu()),
            "random_neighbor_n": int(n_random[i].cpu()),
            "legacy_threshold_rns_equal": True,
        })
        for rank in range(K):
            neighbor_index = int(indices[i, rank].cpu())
            neighbor_rows.append({
                "sample_id": row["sample_id"],
                "rank": rank + 1,
                "neighbor_id": all_ids[neighbor_index],
                "neighbor_type": "random" if neighbor_index >= len(seqs) else "real",
                "cosine_similarity": float(values[i, rank].cpu()),
            })
    write_jsonl(RNS_ROWS, rns_rows)
    write_jsonl(NEIGHBORS, neighbor_rows)
    return rns_rows


def evaluate_cov(model, device, seqs, conditions):
    from rna_sc.census import GPUGuard
    guard = GPUGuard(device)
    guard.check()
    seq_by_id = {row["sample_id"]: row for row in seqs}
    grouped = collections.OrderedDict()
    for cond in conditions:
        grouped.setdefault(cond["sample_id"], []).append(cond)
    batch_size = INITIAL_CONDITION_BATCH
    reductions = []
    started = time.time()
    tmp = MUTATIONS.with_suffix(".jsonl.tmp")
    done = 0
    with open(tmp, "w") as fh:
        for sample_id, group in grouped.items():
            pos = 0
            while pos < len(group):
                chunk = group[pos:pos + batch_size]
                flat_rows = []
                flat_reads = []
                spans = []
                for original in chunk:
                    cond = dict(original)
                    cond["sequence"] = seq_by_id[sample_id]["sequence"]
                    rows, reads = condition_forward_rows(cond)
                    start = len(flat_rows)
                    flat_rows.extend(rows)
                    flat_reads.extend(reads)
                    spans.append((cond, start, len(rows)))
                try:
                    probabilities = forward_probs(model, device, flat_rows, flat_reads)
                except torch.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    if batch_size == 1:
                        raise
                    new_batch = {16: 8, 8: 4, 4: 1}[batch_size]
                    reductions.append({"from": batch_size, "to": new_batch,
                                       "sample_id": sample_id})
                    batch_size = new_batch
                    continue
                for cond, start, _ in spans:
                    p_orig = probabilities[start]
                    ctrl_offset = 1 + len(cond["muts"])
                    pk_orig = probabilities[start + ctrl_offset] if cond["k"] is not None else None
                    for mutation_index, m in enumerate(cond["muts"]):
                        p_mut = probabilities[start + 1 + mutation_index]
                        record = {
                            "condition_id": cond["condition_id"],
                            "sample_id": sample_id,
                            "sequence_id": cond["sequence_id"],
                            "source": cond["source"],
                            "pair_order": cond["pair_order"],
                            "i": cond["i"],
                            "j": cond["j"],
                            "k": cond["k"],
                            "mutation": ALPHABET[m],
                            "complement": ALPHABET[COMP[m]],
                            "p_orig_complement": float(p_orig[COMP[m]]),
                            "p_mut_complement": float(p_mut[COMP[m]]),
                            "cov": float(p_mut[COMP[m]] - p_orig[COMP[m]]),
                            "p_orig_ctrl_complement": None,
                            "p_mut_ctrl_complement": None,
                            "ctrl": None,
                        }
                        if cond["k"] is not None:
                            pk_mut = probabilities[start + ctrl_offset + 1 + mutation_index]
                            record["p_orig_ctrl_complement"] = float(pk_orig[COMP[m]])
                            record["p_mut_ctrl_complement"] = float(pk_mut[COMP[m]])
                            record["ctrl"] = float(pk_mut[COMP[m]] - pk_orig[COMP[m]])
                        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
                pos += len(chunk)
                done += len(chunk)
            print(f"COV {done}/{len(conditions)} conditions batch={batch_size} "
                  f"elapsed={time.time() - started:.1f}s", flush=True)
    os.replace(tmp, MUTATIONS)
    guard.verify_cuda_alive()
    return {
        "initial_condition_batch": INITIAL_CONDITION_BATCH,
        "final_condition_batch": batch_size,
        "oom_reductions": reductions,
        "elapsed_seconds": time.time() - started,
        "cpu_fallback_count": guard.cpu_fallback_count,
    }


def run_gpu():
    from rna_sc.census import GPUGuard
    meta, seqs, random_rows, conditions = load_frozen()
    assert torch.cuda.is_available()
    device = "cuda:0"
    guard = GPUGuard(device)
    guard.check()
    torch.cuda.reset_peak_memory_stats()
    started = time.time()
    model, ck, checkpoint = load_model()
    model = model.to(device).eval()
    assert next(model.parameters()).is_cuda
    rns_rows = compute_rns(model, device, seqs, random_rows)
    print(f"RNS_COMPLETE n={len(rns_rows)} mean={np.mean([r['rns_at_10'] for r in rns_rows]):.8f}",
          flush=True)
    cov_info = evaluate_cov(model, device, seqs, conditions)
    guard.verify_cuda_alive()
    summary = {
        "status": "GPU_RUN_COMPLETE",
        "model": "RNA-Sc-30M_s17",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_nt": ck["nt"],
        "n_layers": ck["cfg"]["arch"]["n_layers"],
        "rns_layer_zero_indexed": LAYER,
        "n_real": len(seqs),
        "n_random": len(random_rows),
        "rns_mean_all_selected": float(np.mean([r["rns_at_10"] for r in rns_rows])),
        "rns_rows_sha256": sha256_file(RNS_ROWS),
        "neighbors_sha256": sha256_file(NEIGHBORS),
        "mutations_sha256": sha256_file(MUTATIONS),
        "n_conditions": len(conditions),
        "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
        "total_elapsed_seconds": time.time() - started,
        **cov_info,
    }
    write_json(RUN_SUMMARY, summary)
    print(json.dumps(summary, indent=2), flush=True)


def average_rank(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def spearman(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return None
    return float(np.corrcoef(average_rank(x), average_rank(y))[0, 1])


def bootstrap_spearman(x, y, seed=SEED, n_boot=BOOTSTRAP_N):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rng = np.random.default_rng(seed)
    values = []
    degenerate = 0
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), size=len(x))
        rho = spearman(x[idx], y[idx])
        if rho is None or not math.isfinite(rho):
            degenerate += 1
        else:
            values.append(rho)
    if not values:
        return {"ci95_low": None, "ci95_high": None, "valid_resamples": 0,
                "degenerate_resamples": degenerate}
    low, high = np.percentile(values, [2.5, 97.5])
    return {"ci95_low": float(low), "ci95_high": float(high),
            "valid_resamples": len(values), "degenerate_resamples": degenerate}


def aggregate(rows, family_min_n=MIN_SOURCE_N):
    for row in rows:
        if row["cov_mutation_n"] == 0:
            row["exclusion_reason"] = "no_valid_pair_within_192nt"
        elif row["ctrl_mutation_n"] == 0:
            row["exclusion_reason"] = "no_valid_unpaired_ctrl_for_any_pair"
        else:
            row["exclusion_reason"] = ""
        row["main_pair_analysis_included"] = not row["exclusion_reason"]
    main = [row for row in rows if row["main_pair_analysis_included"]]
    x = [row["rns_at_10"] for row in main]
    y = [row["cov_minus_ctrl"] for row in main]
    sequence_stats = {
        "n": len(main),
        "rho": spearman(x, y),
        "bootstrap": {"seed": SEED, "n_resamples": BOOTSTRAP_N,
                      "method": "sequence resampling with replacement; percentile CI; average ranks",
                      **bootstrap_spearman(x, y)},
        "sequence_ids_sha256": sha256_lines([row["sequence_id"] for row in main]),
    }
    families = []
    for source in dict.fromkeys(row["source"] for row in rows):
        source_all = [row for row in rows if row["source"] == source]
        source_main = [row for row in main if row["source"] == source]
        included = len(source_main) >= family_min_n
        family = {
            "source": source,
            "selected_n": len(source_all),
            "n": len(source_main),
            "family_aggregation_included": included,
            "exclusion_reason": "" if included else "post_pair_n_below_12",
            "rns_at_10_mean": float(np.mean([r["rns_at_10"] for r in source_main])) if source_main else None,
            "cov_mean": float(np.mean([r["cov"] for r in source_main])) if source_main else None,
            "ctrl_mean": float(np.mean([r["ctrl"] for r in source_main])) if source_main else None,
            "cov_minus_ctrl_mean": float(np.mean([r["cov_minus_ctrl"] for r in source_main])) if source_main else None,
            "cov_mutation_n": sum(r["cov_mutation_n"] for r in source_main),
            "ctrl_mutation_n": sum(r["ctrl_mutation_n"] for r in source_main),
            "label_scope": "coarse bpRNA source; not fine-grained Rfam ID",
        }
        families.append(family)
    family_included = [row for row in families if row["family_aggregation_included"]]
    if len(family_included) >= 3:
        fx = [row["rns_at_10_mean"] for row in family_included]
        fy = [row["cov_minus_ctrl_mean"] for row in family_included]
        family_stats = {
            "status": "DESCRIPTIVE_ONLY",
            "n_sources": len(family_included),
            "rho": spearman(fx, fy),
            "source_n": {row["source"]: row["n"] for row in family_included},
            "bootstrap_descriptive": {"seed": SEED, "n_resamples": BOOTSTRAP_N,
                                      **bootstrap_spearman(fx, fy)},
        }
    else:
        family_stats = {"status": "NOT_ESTIMABLE_SOURCE_N_LT_3",
                        "n_sources": len(family_included), "rho": None,
                        "source_n": {row["source"]: row["n"] for row in family_included}}
    included_ids = {row["sample_id"] for row in main}
    included_sources = {row["source"] for row in family_included}
    for row in rows:
        row["family_aggregation_included"] = (
            row["main_pair_analysis_included"] and row["source"] in included_sources)
        if not row["main_pair_analysis_included"]:
            row["family_exclusion_reason"] = row["exclusion_reason"]
        elif row["source"] not in included_sources:
            row["family_exclusion_reason"] = "source_post_pair_n_below_12"
        else:
            row["family_exclusion_reason"] = ""
        assert (row["sample_id"] in included_ids) == row["main_pair_analysis_included"]
    return sequence_stats, families, family_stats


def make_figures(rows, families, sequence_stats, family_stats):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    main = [row for row in rows if row["main_pair_analysis_included"]]
    sources = list(dict.fromkeys(row["source"] for row in main))
    palette = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#666666"]
    colors = {source: palette[i % len(palette)] for i, source in enumerate(sources)}
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for source in sources:
        subset = [row for row in main if row["source"] == source]
        ax.scatter([r["rns_at_10"] for r in subset], [r["cov_minus_ctrl"] for r in subset],
                   s=35, alpha=0.78, color=colors[source], edgecolor="white", linewidth=0.35,
                   label=source)
    ax.axhline(0, color="#888888", lw=0.8, ls="--")
    ax.set_xlabel("RNS@10 (RNA-Sc-30M, L8)")
    ax.set_ylabel("Per-sequence COV − CTRL")
    ci = sequence_stats["bootstrap"]
    ax.set_title(f"Sequence level: Spearman ρ = {sequence_stats['rho']:.3f}; n = {sequence_stats['n']}\n"
                 f"Bootstrap 95% CI [{ci['ci95_low']:.3f}, {ci['ci95_high']:.3f}]")
    ax.legend(frameon=False, fontsize=8, ncol=2, title="bpRNA source")
    fig.tight_layout()
    fig.savefig(OUT / "figs" / "p2_2_rns_cov_sequence.png", dpi=300)
    fig.savefig(OUT / "figs" / "p2_2_rns_cov_sequence.pdf")
    plt.close(fig)
    included = [row for row in families if row["family_aggregation_included"]]
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    for row in included:
        ax.scatter(row["rns_at_10_mean"], row["cov_minus_ctrl_mean"], s=70,
                   color=colors.get(row["source"], "#666666"), edgecolor="white", linewidth=0.5)
        ax.annotate(f"{row['source']} (n={row['n']})",
                    (row["rns_at_10_mean"], row["cov_minus_ctrl_mean"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=9)
    ax.axhline(0, color="#888888", lw=0.8, ls="--")
    ax.set_xlabel("Mean RNS@10 (equal-weight sequence mean)")
    ax.set_ylabel("Mean per-sequence COV − CTRL")
    if family_stats["rho"] is not None:
        ax.set_title(f"Source level (descriptive): Spearman ρ = {family_stats['rho']:.3f}; "
                     f"sources = {family_stats['n_sources']}")
    else:
        ax.set_title("Source level: not estimable (<3 eligible sources)")
    fig.tight_layout()
    fig.savefig(OUT / "figs" / "p2_2_rns_cov_family.png", dpi=300)
    fig.savefig(OUT / "figs" / "p2_2_rns_cov_family.pdf")
    plt.close(fig)


def finalize():
    meta, frozen, _, conditions = load_frozen()
    rns_rows = read_jsonl(RNS_ROWS)
    mutations = read_jsonl(MUTATIONS)
    condition_by_sample = collections.defaultdict(list)
    for cond in conditions:
        condition_by_sample[cond["sample_id"]].append(cond)
    mutations_by_sample = collections.defaultdict(list)
    for row in mutations:
        mutations_by_sample[row["sample_id"]].append(row)
    rns_by_sample = {row["sample_id"]: row for row in rns_rows}
    rows = []
    for frozen_row in frozen:
        sample_id = frozen_row["sample_id"]
        sample_mutations = mutations_by_sample[sample_id]
        cov_values = [row["cov"] for row in sample_mutations]
        ctrl_values = [row["ctrl"] for row in sample_mutations if row["ctrl"] is not None]
        conds = condition_by_sample[sample_id]
        cov = float(np.mean(cov_values)) if cov_values else None
        ctrl = float(np.mean(ctrl_values)) if ctrl_values else None
        row = {
            "sequence_id": frozen_row["sequence_id"],
            "sample_id": sample_id,
            "test_index": frozen_row["test_index"],
            "selected_order": frozen_row["selected_order"],
            "source": frozen_row["source"],
            "source_queue_index": frozen_row["source_queue_index"],
            "length": frozen_row["length"],
            "sequence_sha256": frozen_row["sequence_sha256"],
            "rns_layer_zero_indexed": LAYER,
            "rns_at_10": rns_by_sample[sample_id]["rns_at_10"],
            "cov": cov,
            "ctrl": ctrl,
            "cov_minus_ctrl": cov - ctrl if cov is not None and ctrl is not None else None,
            "valid_pair_n": frozen_row["valid_pair_n"],
            "sampled_pair_n": len(conds),
            "cov_pair_n": len({r["condition_id"] for r in sample_mutations}),
            "ctrl_pair_n": sum(c["k"] is not None for c in conds),
            "cov_mutation_n": len(cov_values),
            "ctrl_mutation_n": len(ctrl_values),
        }
        rows.append(row)
    sequence_stats, families, family_stats = aggregate(rows)
    fields = ["sequence_id", "sample_id", "test_index", "selected_order", "source",
              "source_queue_index", "length", "sequence_sha256", "rns_layer_zero_indexed",
              "rns_at_10", "cov", "ctrl", "cov_minus_ctrl", "valid_pair_n", "sampled_pair_n",
              "cov_pair_n", "ctrl_pair_n", "cov_mutation_n", "ctrl_mutation_n",
              "main_pair_analysis_included", "exclusion_reason", "family_aggregation_included",
              "family_exclusion_reason"]
    write_csv(PER_SEQUENCE, rows, fields)
    family_fields = ["source", "selected_n", "n", "family_aggregation_included", "exclusion_reason",
                     "rns_at_10_mean", "cov_mean", "ctrl_mean", "cov_minus_ctrl_mean",
                     "cov_mutation_n", "ctrl_mutation_n", "label_scope"]
    write_csv(PER_FAMILY, families, family_fields)
    pooled_cov = [row["cov"] for row in mutations]
    pooled_ctrl = [row["ctrl"] for row in mutations if row["ctrl"] is not None]
    main_rows = [row for row in rows if row["main_pair_analysis_included"]]
    rho = sequence_stats["rho"]
    ci = sequence_stats["bootstrap"]
    if rho is not None and rho < 0 and not (ci["ci95_low"] <= 0 <= ci["ci95_high"]):
        verdict = "NEGATIVE_DIRECTION_SUPPORTED_WITHIN_THIS_PROTOCOL"
    elif rho is not None and rho > 0:
        verdict = "REVERSE_DIRECTION_RNS_NOT_A_STRUCTURE_PROXY"
    else:
        verdict = "PROXY_RELATION_NOT_ESTABLISHED_CI_CROSSES_ZERO_OR_NEAR_ZERO"
    summary = {
        "task": "X-P22 / P2.2",
        "status": "COMPLETE",
        "model": "RNA-Sc-30M_s17",
        "checkpoint_nt": 1900121822,
        "rns_layer_zero_indexed": LAYER,
        "common_sequence_view_nt": MAX_NT,
        "sequence_level": sequence_stats,
        "source_level": family_stats,
        "source_aggregation": "equal-weight per-sequence means within source; descriptive only",
        "pooled_mutation_sensitivity_all_selected": {
            "cov": float(np.mean(pooled_cov)),
            "cov_n": len(pooled_cov),
            "ctrl": float(np.mean(pooled_ctrl)),
            "ctrl_n": len(pooled_ctrl),
            "cov_minus_ctrl": float(np.mean(pooled_cov) - np.mean(pooled_ctrl)),
            "note": "mutation-pooled global sensitivity; not the per-sequence Spearman input and not Q5 headline",
        },
        "unweighted_per_sequence_means_main_set": {
            "rns_at_10": float(np.mean([r["rns_at_10"] for r in main_rows])),
            "cov": float(np.mean([r["cov"] for r in main_rows])),
            "ctrl": float(np.mean([r["ctrl"] for r in main_rows])),
            "cov_minus_ctrl": float(np.mean([r["cov_minus_ctrl"] for r in main_rows])),
        },
        "verdict": verdict,
        "proxy_downgrade": verdict != "NEGATIVE_DIRECTION_SUPPORTED_WITHIN_THIS_PROTOCOL",
        "comparison_boundary": "192nt/source-queue absolute COV values must not be mixed with Q5 100-sequence/256nt headline",
        "old_s14_nll": "not used; masked-marginal NLL is not COV",
        "protocol": {
            "random_pool_seed": SEED,
            "pair_ctrl_seed": SEED,
            "bootstrap_seed": SEED,
            "random_multiplier": 3,
            "rns_k": K,
            "max_pairs_per_sequence": MAX_PAIRS,
            "bootstrap_n": BOOTSTRAP_N,
            "random_pool_qc": meta["random_pool_qc"],
            "inputs": meta["inputs"],
            "frozen_sequences_sha256": meta["frozen_sequences_sha256"],
            "random_pool_sha256": meta["random_pool_sha256"],
            "conditions_sha256": meta["conditions_sha256"],
        },
    }
    write_json(SUMMARY, summary)
    make_figures(rows, families, sequence_stats, family_stats)
    validation = validate_outputs()
    write_json(VALIDATION, validation)
    assert validation["status"] == "PASS", validation
    create_manifest()
    print(json.dumps({"sequence_level": sequence_stats, "source_level": family_stats,
                      "pooled": summary["pooled_mutation_sensitivity_all_selected"],
                      "verdict": verdict, "validation": validation["status"]}, indent=2), flush=True)


def validate_outputs():
    meta, frozen, _, conditions = load_frozen()
    with open(PER_SEQUENCE) as fh:
        rows = list(csv.DictReader(fh))
    with open(PER_FAMILY) as fh:
        families = list(csv.DictReader(fh))
    summary = json.load(open(SUMMARY))
    rns_rows = read_jsonl(RNS_ROWS)
    mutations = read_jsonl(MUTATIONS)
    main = [row for row in rows if row["main_pair_analysis_included"] == "True"]
    assert len(rows) == len(frozen) == len(rns_rows) == meta["n_selected"]
    assert len({row["sequence_id"] for row in main}) == len(main)
    assert all(row["rns_at_10"] and row["cov"] and row["ctrl"] and row["cov_minus_ctrl"]
               for row in main)
    assert all(row["exclusion_reason"] for row in rows if row["main_pair_analysis_included"] == "False")
    x = np.array([float(row["rns_at_10"]) for row in main])
    y = np.array([float(row["cov_minus_ctrl"]) for row in main])
    rho = spearman(x, y)
    boot = bootstrap_spearman(x, y)
    assert float.hex(rho) == float.hex(summary["sequence_level"]["rho"])
    for key, value in boot.items():
        if isinstance(value, float):
            assert float.hex(value) == float.hex(summary["sequence_level"]["bootstrap"][key])
        else:
            assert value == summary["sequence_level"]["bootstrap"][key]
    recomputed_sequence, recomputed_families, recomputed_family = aggregate([
        {**row,
         "rns_at_10": float(row["rns_at_10"]),
         "cov": float(row["cov"]) if row["cov"] else None,
         "ctrl": float(row["ctrl"]) if row["ctrl"] else None,
         "cov_minus_ctrl": float(row["cov_minus_ctrl"]) if row["cov_minus_ctrl"] else None,
         "valid_pair_n": int(row["valid_pair_n"]),
         "sampled_pair_n": int(row["sampled_pair_n"]),
         "cov_pair_n": int(row["cov_pair_n"]),
         "ctrl_pair_n": int(row["ctrl_pair_n"]),
         "cov_mutation_n": int(row["cov_mutation_n"]),
         "ctrl_mutation_n": int(row["ctrl_mutation_n"])} for row in rows])
    assert recomputed_sequence["n"] == summary["sequence_level"]["n"]
    assert float.hex(recomputed_sequence["rho"]) == float.hex(summary["sequence_level"]["rho"])
    assert len(recomputed_families) == len(families)
    assert recomputed_family["n_sources"] == summary["source_level"]["n_sources"]
    if recomputed_family["rho"] is not None:
        assert float.hex(recomputed_family["rho"]) == float.hex(summary["source_level"]["rho"])
    expected_mutations = sum(len(cond["muts"]) for cond in conditions)
    expected_ctrl = sum(len(cond["muts"]) for cond in conditions if cond["k"] is not None)
    assert len(mutations) == expected_mutations
    assert sum(row["ctrl"] is not None for row in mutations) == expected_ctrl
    assert sum(int(row["cov_mutation_n"]) for row in rows) == expected_mutations
    assert sum(int(row["ctrl_mutation_n"]) for row in rows) == expected_ctrl
    pooled_cov = float(np.mean([row["cov"] for row in mutations]))
    pooled_ctrl = float(np.mean([row["ctrl"] for row in mutations if row["ctrl"] is not None]))
    pooled = summary["pooled_mutation_sensitivity_all_selected"]
    assert float.hex(pooled_cov) == float.hex(pooled["cov"])
    assert float.hex(pooled_ctrl) == float.hex(pooled["ctrl"])
    assert float.hex(pooled_cov - pooled_ctrl) == float.hex(pooled["cov_minus_ctrl"])
    for rel in ["figs/p2_2_rns_cov_sequence.png", "figs/p2_2_rns_cov_family.png"]:
        path = OUT / rel
        assert path.stat().st_size > 10_000
        with open(path, "rb") as fh:
            assert fh.read(8) == b"\x89PNG\r\n\x1a\n"
    assert meta["random_pool_qc"]["passed"]
    return {
        "status": "PASS",
        "n_selected_rows": len(rows),
        "n_main_sequence_rows": len(main),
        "excluded_rows_with_reason": sum(row["main_pair_analysis_included"] == "False" for row in rows),
        "sequence_ids_complete_and_unique": True,
        "rns_cov_exact_same_main_sequence_set": True,
        "average_rank_spearman_recomputed_bitwise": True,
        "sequence_bootstrap_recomputed_bitwise": True,
        "family_statistics_recomputed_bitwise": True,
        "mutation_counts_recomputed": {"cov": expected_mutations, "ctrl": expected_ctrl},
        "pooled_statistics_recomputed_bitwise": True,
        "random_pool_qc_pass": True,
        "legacy_threshold_rns_matches_exact_topk": all(row["legacy_threshold_rns_equal"] for row in rns_rows),
        "two_png_scatters_valid": True,
    }


def create_manifest():
    shutil.copyfile(Path(__file__).resolve(), OUT / "run_p2_2.py")
    packages = {}
    for name in ("torch", "numpy", "scipy", "pandas", "pyarrow", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    outputs = {}
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"p2_2_manifest.json", "manifest_sha256.tsv"}:
            continue
        if path.name.endswith(".tmp"):
            continue
        outputs[str(path.relative_to(OUT))] = {"sha256": sha256_file(path),
                                               "bytes": path.stat().st_size}
    gpu = json.load(open(RUN_SUMMARY))
    manifest = {
        "task": "X-P22 / P2.2",
        "status": "COMPLETE",
        "created_unix": time.time(),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "protocol": "prereg/P2_2.md",
        "checkpoint": gpu["checkpoint"],
        "checkpoint_sha256": gpu["checkpoint_sha256"],
        "checkpoint_nt": gpu["checkpoint_nt"],
        "random_pool_qc": json.load(open(FREEZE_META))["random_pool_qc"],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": packages,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "torch_cuda": torch.version.cuda,
        },
        "gpu_run": {key: gpu[key] for key in [
            "peak_allocated_mib", "peak_reserved_mib", "initial_condition_batch",
            "final_condition_batch", "oom_reductions", "cpu_fallback_count",
            "total_elapsed_seconds"]},
        "outputs": outputs,
    }
    write_json(MANIFEST, manifest)
    lines = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "manifest_sha256.tsv" and not path.name.endswith(".tmp"):
            lines.append(f"{path.relative_to(OUT)}\t{sha256_file(path)}")
    tmp = OUT / "manifest_sha256.tsv.tmp"
    tmp.write_text("\n".join(lines) + "\n")
    os.replace(tmp, OUT / "manifest_sha256.tsv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["freeze", "smoke", "run", "finalize"])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if args.command == "freeze":
        freeze()
    elif args.command == "smoke":
        smoke()
    elif args.command == "run":
        run_gpu()
    else:
        finalize()


if __name__ == "__main__":
    main()
