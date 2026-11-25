from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.metadata
import json
import os
import random
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
OUT = BASE / "results" / "P2_3"
LOGS = BASE / "logs"
sys.path.insert(0, str(CODE))

ALPHABET = "ACGU"
COMP = {0: 3, 3: 0, 1: 2, 2: 1}
SEED = 17
N_SEQ = 100
MAX_PAIRS = 20
MAX_NT = 256
INITIAL_CONDITION_BATCH = 16
CONDITIONS = OUT / "p2_3_cov_conditions.jsonl"
FREEZE_META = OUT / "p2_3_cov_freeze.json"
OLD_ANCHOR = {
    "cov": 0.049607125636875415,
    "ctrl": 0.0026705753443465943,
    "cov_minus_ctrl": 0.04693655029252882,
    "old_drop": -0.015336274750000935,
    "n": 4920,
}
MODEL_SPECS = {
    "rinalmo_micro": ("RiNALMo-micro-36M", BASE / "ext" / "rinalmo"),
    "nucleicbert": ("NucleicBERT-404M", BASE / "ext" / "nucleicbert_repo"),
    "rinalmo_mega": ("RiNALMo-mega", BASE / "ext" / "rinalmo-mega"),
    "rinalmo_giga": ("RiNALMo-giga", BASE / "ext" / "rinalmo-giga"),
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(value, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def load_test():
    seqs, pairs_list, names, sources, test_indices = [], [], [], [], []
    pf = pq.ParquetFile(DATA)
    row_offset = 0
    for rb in pf.iter_batches(batch_size=50_000,
                              columns=["name", "source", "seq", "pairs", "split"]):
        d = rb.to_pydict()
        for ri, (name, source, s, p, sp) in enumerate(zip(
                d["name"], d["source"], d["seq"], d["pairs"], d["split"])):
            if sp == "test":
                seqs.append(s)
                pairs_list.append(p)
                names.append(name)
                sources.append(source)
                test_indices.append(row_offset + ri)
        row_offset += len(d["seq"])
    return seqs, pairs_list, names, sources, test_indices


def encode(seq):
    return [ALPHABET.index(b) for b in seq.upper().replace("T", "U")
            if b in ALPHABET][:MAX_NT]


def build_conditions(ids, pairs, rng, max_pairs=MAX_PAIRS):
    n = len(ids)
    valid = [(i - 1, j - 1) for i, j in pairs if i <= n and j <= n]
    paired_pos = set()
    for i, j in valid:
        paired_pos.add(i)
        paired_pos.add(j)
    unpaired = [p for p in range(n) if p not in paired_pos]
    rng.shuffle(valid)
    valid = valid[:max_pairs]
    conds = []
    for i, j in valid:
        xi = ids[i]
        if xi not in COMP:
            continue
        far = [k for k in unpaired if abs(k - i) > 5 and abs(k - j) > 5]
        k = rng.choice(far) if far else None
        muts = [b for b in range(4) if b != xi]
        conds.append({"i": i, "j": j, "k": k, "xi": xi, "muts": muts,
                      "ids": list(ids)})
    return conds


def freeze_conditions():
    OUT.mkdir(parents=True, exist_ok=True)
    seqs, pairs_list, names, sources, test_indices = load_test()
    assert len(seqs) == 1305, len(seqs)
    rng = random.Random(SEED)
    idx = rng.sample(range(len(seqs)), N_SEQ)
    samples = []
    conditions = []
    for sample_order, si in enumerate(idx):
        ids = encode(seqs[si])
        sample = {
            "sample_order": sample_order,
            "sample_id": f"test_index_{test_indices[si]}",
            "test_index": test_indices[si],
            "sequence_id": names[si],
            "source": sources[si],
            "encoded_length": len(ids),
            "sequence_sha256": hashlib.sha256(
                "".join(ALPHABET[b] for b in ids).encode()).hexdigest(),
            "skipped_forward": len(ids) < 20,
            "n_conditions": 0,
        }
        samples.append(sample)
        if len(ids) < 20:
            continue
        conds = build_conditions(ids, pairs_list[si], rng)
        sample["n_conditions"] = len(conds)
        for pair_order, c in enumerate(conds):
            cid = f"{sample['sample_id']}:pair_{pair_order:02d}:i{c['i']}:j{c['j']}"
            row = dict(c)
            row.update({
                "condition_id": cid,
                "sample_id": sample["sample_id"],
                "sample_order": sample_order,
                "test_index": test_indices[si],
                "sequence_id": names[si],
                "source": sources[si],
                "original_base": ALPHABET[c["xi"]],
                "mutations": [ALPHABET[m] for m in c["muts"]],
            })
            conditions.append(row)
    tmp = CONDITIONS.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as fh:
        for row in conditions:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    os.replace(tmp, CONDITIONS)
    meta = {
        "protocol": "P2.3 frozen COV-CTRL conditions",
        "seed": SEED,
        "n_test": len(seqs),
        "n_sampled": len(samples),
        "n_forward_samples": sum(not s["skipped_forward"] for s in samples),
        "n_conditions": len(conditions),
        "n_cov_mutations": sum(len(c["muts"]) for c in conditions),
        "n_ctrl_mutations": sum(len(c["muts"]) for c in conditions if c["k"] is not None),
        "max_pairs_per_sequence": MAX_PAIRS,
        "max_nt": MAX_NT,
        "bpRNA_path": str(DATA),
        "bpRNA_sha256": sha256_file(DATA),
        "conditions_sha256": sha256_file(CONDITIONS),
        "authoritative_source": str(CODE / "run_cov300.py"),
        "authoritative_source_sha256": sha256_file(CODE / "run_cov300.py"),
        "samples": samples,
    }
    write_json(FREEZE_META, meta)
    print(json.dumps({k: v for k, v in meta.items() if k != "samples"}, indent=2), flush=True)


def load_frozen():
    meta = json.load(open(FREEZE_META))
    assert sha256_file(DATA) == meta["bpRNA_sha256"]
    assert sha256_file(CONDITIONS) == meta["conditions_sha256"]
    conditions = [json.loads(line) for line in open(CONDITIONS)]
    assert len(conditions) == meta["n_conditions"]
    return meta, conditions


class BaseAdapter:
    def __init__(self, model, device):
        from rna_sc.census import GPUGuard
        self.guard = GPUGuard(device)
        self.guard.check()
        assert torch.cuda.is_available()
        self.device = device
        self.model = model.to(device).eval()
        assert next(self.model.parameters()).is_cuda

    def smoke(self, ids, read_pos, expected_vocab):
        assert self.guard.cpu_fallback_count == 0
        rows = [ids]
        probs = self.run_model_batch(rows, [read_pos])
        assert probs.shape == (1, 4), probs.shape
        assert torch.isfinite(probs).all()
        assert probs.device.type == "cpu"
        self.guard.verify_cuda_alive()
        return {
            "status": "PASS",
            "device": self.device,
            "model_device": str(next(self.model.parameters()).device),
            "bf16_autocast": True,
            "logits_vocab": expected_vocab,
            "probabilities_finite": True,
            "cpu_fallback_count": self.guard.cpu_fallback_count,
            "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        }


class RNAScAdapter(BaseAdapter):
    mask = 5
    pad = 4
    offset = 0
    vocab = 7

    def encode_ids(self, ids):
        return list(ids)

    def run_model_batch(self, rows, read_pos):
        T = max(len(r) for r in rows)
        ids = torch.tensor([r + [self.pad] * (T - len(r)) for r in rows],
                           dtype=torch.long, device=self.device)
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
            out = self.model(ids, return_all_hiddens=False)
            logits = out[0]
        assert logits.shape[-1] == self.vocab and logits.is_cuda
        probs = torch.softmax(logits.float(), dim=-1)
        out = []
        for bi, rp in zip(range(len(rows)), read_pos):
            out.append(probs[bi, rp, :4].cpu())
        return torch.stack(out)


class RiNALMoAdapter(BaseAdapter):
    mask = 4
    pad = 0
    offset = 1
    vocab = 28
    token_map = {0: 6, 1: 7, 2: 8, 3: 9}

    def encode_ids(self, ids):
        return [1] + [self.token_map[b] for b in ids] + [2]

    def run_model_batch(self, rows, read_pos):
        T = max(len(r) for r in rows)
        ids = torch.tensor([r + [self.pad] * (T - len(r)) for r in rows],
                           dtype=torch.long, device=self.device)
        attention_mask = (ids != self.pad).long()
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
            logits = self.model(ids, attention_mask=attention_mask).logits
        assert logits.shape[-1] == self.vocab and logits.is_cuda
        probs = torch.softmax(logits.float(), dim=-1)
        token_ids = torch.tensor([self.token_map[b] for b in range(4)],
                                 device=probs.device)
        out = []
        for bi, rp in zip(range(len(rows)), read_pos):
            out.append(probs[bi, rp, :].index_select(0, token_ids).cpu())
        return torch.stack(out)


class NucleicBERTAdapter(BaseAdapter):
    mask = 2
    pad = 0
    offset = 1
    vocab = 25
    token_map = {0: 6, 1: 8, 2: 11, 3: 20}

    def encode_ids(self, ids):
        return [3] + [self.token_map[b] for b in ids] + [4]

    def run_model_batch(self, rows, read_pos):
        T = max(len(r) for r in rows)
        ids = torch.tensor([r + [self.pad] * (T - len(r)) for r in rows],
                           dtype=torch.long, device=self.device)
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
            logits = self.model(ids)
        assert logits.shape[-1] == self.vocab and logits.is_cuda
        probs = torch.softmax(logits.float(), dim=-1)
        token_ids = torch.tensor([self.token_map[b] for b in range(4)],
                                 device=probs.device)
        out = []
        for bi, rp in zip(range(len(rows)), read_pos):
            out.append(probs[bi, rp, :].index_select(0, token_ids).cpu())
        return torch.stack(out)


def verify_rinalmo_tokenizer(path):
    from multimolecule.tokenisers import RnaTokenizer
    tok = RnaTokenizer.from_pretrained(path)
    assert tok("ACGU", add_special_tokens=False)["input_ids"] == [6, 7, 8, 9]
    full = tok("ACGU")["input_ids"]
    assert full[0] == 1 and full[-1] == 2
    assert tok.mask_token_id == 4 and tok.pad_token_id == 0
    assert tok.vocab_size == 28
    return {"ACGU": [6, 7, 8, 9], "CLS": 1, "EOS": 2,
            "MASK": 4, "PAD": 0, "logits_vocab": 28}


def verify_nucleicbert_tokenizer(path):
    from transformers import PreTrainedTokenizerFast
    tok_file = path / "nucleicbert" / "tokenizers" / "noncoding_seqs.json"
    tok = PreTrainedTokenizerFast(tokenizer_file=str(tok_file))
    ids = [tok.convert_tokens_to_ids(b) for b in ["a", "c", "g", "u"]]
    assert ids == [6, 8, 11, 20], ids
    for token, expected in {"[PAD]": 0, "[MASK]": 2, "[CLS]": 3, "[SEP]": 4}.items():
        assert tok.convert_tokens_to_ids(token) == expected, token
    return {"acgu": ids, "CLS": 3, "SEP": 4, "MASK": 2,
            "PAD": 0, "logits_vocab": 25}


def make_adapter(model_key, mode, device="cuda:0"):
    assert mode in ("trained", "randinit17")
    if model_key == "rnasc300m_sanity":
        from rna_sc.probe import load_encoder
        assert mode == "trained"
        run = BASE / "weights" / "RNA-Sc-300M_s17"
        if not run.exists():
            run = BASE / "weights" / "RNA-Sc-300M_s17_b59"
        model, ck = load_encoder(str(run))
        assert ck["nt"] == 5800296014
        return RNAScAdapter(model, device), {"checkpoint_nt": ck["nt"]}, None
    name, path = MODEL_SPECS[model_key]
    if model_key.startswith("rinalmo"):
        import multimolecule.models.rinalmo  # noqa: F401
        from multimolecule.models.rinalmo import RiNALMoForPreTraining
        token_info = verify_rinalmo_tokenizer(path)
        loading_report = None
        if mode == "trained":
            model, loading_info = RiNALMoForPreTraining.from_pretrained(
                path, output_loading_info=True)
            assert set(loading_info["missing_keys"]) == {"lm_head.decoder.bias"}
            assert not loading_info["unexpected_keys"]
            assert not loading_info["mismatched_keys"]
            assert not loading_info["error_msgs"]
            assert model.lm_head.decoder.bias.detach().count_nonzero().item() == 0
            loading_report = {k: sorted(v) if isinstance(v, set) else v
                              for k, v in loading_info.items()}
            loading_report["missing_decoder_bias_is_zero"] = True
            source = str(path / "model.safetensors")
        else:
            torch.manual_seed(17)
            from multimolecule.models.rinalmo import RiNALMoConfig
            config = RiNALMoConfig.from_pretrained(path)
            model = RiNALMoForPreTraining(config)
            source = None
        return RiNALMoAdapter(model, device), {
            "model": name, "mode": mode, "weight_source": source,
            "tokenizer": token_info, "loading_report": loading_report,
        }, token_info
    from rna_sc import probe_nucleicbert
    probe_nucleicbert.REPO = str(path)
    probe_nucleicbert.CKPT = str(path / "pretrained.pt")
    token_info = verify_nucleicbert_tokenizer(path)
    if mode == "randinit17":
        torch.manual_seed(17)
    model, layers = probe_nucleicbert.load_model(
        ckpt=str(path / "pretrained.pt"),
        random_init=None if mode == "trained" else 17)
    assert layers == 32
    return NucleicBERTAdapter(model, device), {
        "model": name, "mode": mode,
        "weight_source": None if mode == "randinit17" else str(path / "pretrained.pt"),
        "tokenizer": token_info,
    }, token_info


def condition_rows(c, adapter):
    base = list(c["ids"])
    rows, reads = [], []
    orig = adapter.encode_ids(base)
    orig[c["j"] + adapter.offset] = adapter.mask
    rows.append(orig)
    reads.append(c["j"] + adapter.offset)
    for m in c["muts"]:
        mut = adapter.encode_ids(base)
        mut[c["i"] + adapter.offset] = adapter.token_map[m] if hasattr(adapter, "token_map") else m
        mut[c["j"] + adapter.offset] = adapter.mask
        rows.append(mut)
        reads.append(c["j"] + adapter.offset)
    if c["k"] is not None:
        orig_k = adapter.encode_ids(base)
        orig_k[c["k"] + adapter.offset] = adapter.mask
        rows.append(orig_k)
        reads.append(c["k"] + adapter.offset)
        for m in c["muts"]:
            mut_k = adapter.encode_ids(base)
            mut_k[c["i"] + adapter.offset] = adapter.token_map[m] if hasattr(adapter, "token_map") else m
            mut_k[c["k"] + adapter.offset] = adapter.mask
            rows.append(mut_k)
            reads.append(c["k"] + adapter.offset)
    return rows, reads


def summarize_rows(rows):
    cov = [r["cov"] for r in rows]
    ctrl = [r["ctrl"] for r in rows if r["ctrl"] is not None]
    old_drop = [r["old_drop"] for r in rows if r["old_drop"] is not None]
    return {
        "cov": {"mean": float(np.mean(cov)), "n": len(cov)},
        "ctrl": {"mean": float(np.mean(ctrl)), "n": len(ctrl)},
        "old_drop": {"mean": float(np.mean(old_drop)), "n": len(old_drop)},
        "cov_minus_ctrl": float(np.mean(cov) - np.mean(ctrl)),
    }


def evaluate_model(adapter, model_key, mode, conditions, output_path):
    grouped = collections.OrderedDict()
    for c in conditions:
        grouped.setdefault(c["sample_id"], []).append(c)
    rows_out = []
    batch_size = INITIAL_CONDITION_BATCH
    reductions = []
    started = time.time()
    tmp = str(output_path) + ".tmp"
    n_done = 0
    with open(tmp, "w") as fh:
        for sample_id, group in grouped.items():
            pos = 0
            while pos < len(group):
                chunk = group[pos:pos + batch_size]
                flat_rows, flat_reads, spans = [], [], []
                for c in chunk:
                    rr, rp = condition_rows(c, adapter)
                    start = len(flat_rows)
                    flat_rows.extend(rr)
                    flat_reads.extend(rp)
                    spans.append((c, start, len(rr)))
                try:
                    probabilities = adapter.run_model_batch(flat_rows, flat_reads)
                except torch.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    if batch_size == 1:
                        raise
                    new_batch = {16: 8, 8: 4, 4: 1}[batch_size]
                    reductions.append({"from": batch_size, "to": new_batch,
                                       "sample_id": sample_id})
                    batch_size = new_batch
                    continue
                for c, start, n_rows in spans:
                    p_orig = probabilities[start]
                    ko = 1 + len(c["muts"])
                    pk_orig = probabilities[start + ko] if c["k"] is not None else None
                    for bi, m in enumerate(c["muts"]):
                        p_mut = probabilities[start + 1 + bi]
                        rec = {
                            "model_key": model_key,
                            "mode": mode,
                            "condition_id": c["condition_id"],
                            "sample_id": c["sample_id"],
                            "i": c["i"], "j": c["j"], "k": c["k"],
                            "mutation": ALPHABET[m],
                            "complement": ALPHABET[COMP[m]],
                            "cov": float(p_mut[COMP[m]] - p_orig[COMP[m]]),
                            "ctrl": None,
                            "old_drop": None,
                        }
                        if c["k"] is not None:
                            pk_mut = probabilities[start + ko + 1 + bi]
                            rec["ctrl"] = float(pk_mut[COMP[m]] - pk_orig[COMP[m]])
                            rec["old_drop"] = float(p_mut[m] - p_orig[m])
                        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
                        rows_out.append(rec)
                pos += len(chunk)
                n_done += len(chunk)
            print(f"[{model_key}:{mode}] {n_done}/{len(conditions)} conditions "
                  f"batch={batch_size} elapsed={time.time() - started:.1f}s", flush=True)
    os.replace(tmp, output_path)
    adapter.guard.verify_cuda_alive()
    summary = summarize_rows(rows_out)
    summary.update({
        "model_key": model_key,
        "mode": mode,
        "seed": 17,
        "n_conditions": len(conditions),
        "condition_ids_sha256": hashlib.sha256(
            "\n".join(c["condition_id"] for c in conditions).encode()).hexdigest(),
        "conditions_sha256": sha256_file(CONDITIONS),
        "initial_condition_batch": INITIAL_CONDITION_BATCH,
        "final_condition_batch": batch_size,
        "oom_reductions": reductions,
        "elapsed_seconds": time.time() - started,
        "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
        "cpu_fallback_count": adapter.guard.cpu_fallback_count,
        "per_condition_file": str(output_path),
        "per_condition_sha256": sha256_file(output_path),
    })
    return summary


def run_sanity():
    _, conditions = load_frozen()
    adapter, info, _ = make_adapter("rnasc300m_sanity", "trained")
    smoke_ids = adapter.encode_ids(conditions[0]["ids"])
    smoke = adapter.smoke(smoke_ids, conditions[0]["j"], adapter.vocab)
    write_json(LOGS / "P2_3_rnasc300m_smoke.json", smoke)
    per_condition = OUT / "p2_3_rnasc300m_sanity_per_condition.jsonl"
    result = evaluate_model(adapter, "rnasc300m_sanity", "trained",
                            conditions, per_condition)
    comparison = {}
    for key in ("cov", "ctrl", "old_drop"):
        new = result[key]["mean"]
        comparison[key] = {
            "old": OLD_ANCHOR[key], "new": new,
            "old_hex": float.hex(OLD_ANCHOR[key]), "new_hex": float.hex(new),
            "bitwise_equal": new == OLD_ANCHOR[key],
            "difference": new - OLD_ANCHOR[key],
        }
    new_delta = result["cov_minus_ctrl"]
    comparison["cov_minus_ctrl"] = {
        "old": OLD_ANCHOR["cov_minus_ctrl"], "new": new_delta,
        "old_hex": float.hex(OLD_ANCHOR["cov_minus_ctrl"]),
        "new_hex": float.hex(new_delta),
        "bitwise_equal": new_delta == OLD_ANCHOR["cov_minus_ctrl"],
        "difference": new_delta - OLD_ANCHOR["cov_minus_ctrl"],
    }
    comparison["n"] = {"old": OLD_ANCHOR["n"], "new": result["cov"]["n"],
                       "equal": result["cov"]["n"] == OLD_ANCHOR["n"]}
    result.update({"model_info": info, "smoke": smoke,
                   "old_anchor_comparison": comparison,
                   "sanity_pass": all(v["bitwise_equal"] for k, v in comparison.items()
                                      if k != "n") and comparison["n"]["equal"]})
    write_json(OUT / "p2_3_rnasc300m_sanity.json", result)
    print("SANITY", json.dumps(result["old_anchor_comparison"], indent=2), flush=True)
    if not result["sanity_pass"]:
        raise SystemExit(3)


def run_external(model_key):
    _, conditions = load_frozen()
    pair = {"model_key": model_key, "model": MODEL_SPECS[model_key][0],
            "scope": "observational_anchor", "seed": 17, "arms": {}}
    for mode in ("trained", "randinit17"):
        adapter, info, token_info = make_adapter(model_key, mode)
        smoke_ids = adapter.encode_ids(conditions[0]["ids"])
        read_pos = conditions[0]["j"] + adapter.offset
        smoke = adapter.smoke(smoke_ids, read_pos, adapter.vocab)
        smoke.update({"tokenizer_assertions": token_info})
        write_json(LOGS / f"P2_3_{model_key}_{mode}_smoke.json", smoke)
        per_condition = OUT / f"p2_3_external_cov_per_condition_{model_key}_{mode}.jsonl"
        result = evaluate_model(adapter, model_key, mode, conditions, per_condition)
        result.update({"model_info": info, "smoke": smoke})
        pair["arms"][mode] = result
        write_json(OUT / f"p2_3_{model_key}_{mode}.json", result)
        write_json(OUT / f"p2_3_{model_key}_pair.json", pair)
        print("ARM_COMPLETE", model_key, mode,
              json.dumps(result["cov_minus_ctrl"]), flush=True)
        del adapter
        torch.cuda.empty_cache()
    pair["trained_minus_randinit"] = (
        pair["arms"]["trained"]["cov_minus_ctrl"] -
        pair["arms"]["randinit17"]["cov_minus_ctrl"])
    pair["condition_ids_identical"] = (
        pair["arms"]["trained"]["condition_ids_sha256"] ==
        pair["arms"]["randinit17"]["condition_ids_sha256"])
    pair["status"] = "COMPLETE" if pair["condition_ids_identical"] else "FAILED_CONDITION_IDS"
    write_json(OUT / f"p2_3_{model_key}_pair.json", pair)
    print("PAIR_COMPLETE", model_key, pair["trained_minus_randinit"], flush=True)


def read_rows(path):
    return [json.loads(line) for line in open(path)]


def finalize():
    meta, conditions = load_frozen()
    expected_ids = [c["condition_id"] for c in conditions]
    models = []
    combined_tmp = str(OUT / "p2_3_external_cov_per_condition.jsonl") + ".tmp"
    validation = {"status": "PASS", "models": {}, "rna_fm": "NOT_RUN_WEIGHT_MISSING"}
    with open(combined_tmp, "w") as combined:
        for model_key, (model_name, _) in MODEL_SPECS.items():
            pair = json.load(open(OUT / f"p2_3_{model_key}_pair.json"))
            assert pair["status"] == "COMPLETE"
            arms = {}
            for mode in ("trained", "randinit17"):
                arm = pair["arms"][mode]
                path = OUT / f"p2_3_external_cov_per_condition_{model_key}_{mode}.jsonl"
                assert sha256_file(path) == arm["per_condition_sha256"]
                rows = read_rows(path)
                assert [(r["condition_id"], r["mutation"]) for r in rows] == [
                    (c["condition_id"], ALPHABET[m]) for c in conditions for m in c["muts"]]
                recomputed = summarize_rows(rows)
                checks = {}
                for key in ("cov", "ctrl", "old_drop"):
                    checks[key] = (float.hex(recomputed[key]["mean"]) ==
                                   float.hex(arm[key]["mean"]))
                    assert recomputed[key]["n"] == arm[key]["n"]
                checks["cov_minus_ctrl"] = (float.hex(recomputed["cov_minus_ctrl"]) ==
                                             float.hex(arm["cov_minus_ctrl"]))
                assert all(checks.values()), (model_key, mode, checks)
                validation["models"][f"{model_key}:{mode}"] = {
                    "bitwise_recompute": checks,
                    "condition_ids_identical": True,
                    "n_cov": arm["cov"]["n"], "n_ctrl": arm["ctrl"]["n"],
                }
                arms[mode] = arm
                for row in rows:
                    combined.write(json.dumps(row, separators=(",", ":")) + "\n")
            models.append({
                "model_key": model_key,
                "model": model_name,
                "scope": "observational_anchor",
                "status": "COMPLETE",
                "cov": arms["trained"]["cov"]["mean"],
                "ctrl": arms["trained"]["ctrl"]["mean"],
                "cov_minus_ctrl": arms["trained"]["cov_minus_ctrl"],
                "old_drop": arms["trained"]["old_drop"]["mean"],
                "n_cov": arms["trained"]["cov"]["n"],
                "n_ctrl": arms["trained"]["ctrl"]["n"],
                "randinit17_cov": arms["randinit17"]["cov"]["mean"],
                "randinit17_ctrl": arms["randinit17"]["ctrl"]["mean"],
                "randinit17_cov_minus_ctrl": arms["randinit17"]["cov_minus_ctrl"],
                "randinit17_old_drop": arms["randinit17"]["old_drop"]["mean"],
                "trained_minus_randinit": pair["trained_minus_randinit"],
            })
    os.replace(combined_tmp, OUT / "p2_3_external_cov_per_condition.jsonl")
    models.append({
        "model_key": "rna_fm", "model": "RNA-FM-96M",
        "scope": "observational_anchor", "status": "NOT_RUN_WEIGHT_MISSING",
    })
    fields = ["model_key", "model", "scope", "status", "cov", "ctrl",
              "cov_minus_ctrl", "old_drop", "n_cov", "n_ctrl",
              "randinit17_cov", "randinit17_ctrl", "randinit17_cov_minus_ctrl",
              "randinit17_old_drop", "trained_minus_randinit"]
    with open(OUT / "p2_3_external_cov.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(models)
    write_json(OUT / "p2_3_external_cov.json", {
        "protocol": "P2.3 pooled COV minus unpaired CTRL",
        "external_models": "observational anchors only",
        "conditions_sha256": meta["conditions_sha256"],
        "n_conditions": len(conditions),
        "models": models,
    })
    write_json(OUT / "p2_3_rnafm_status.json", {
        "model": "RNA-FM-96M", "status": "NOT_RUN_WEIGHT_MISSING",
        "value": None, "zero_filled": False,
    })
    write_json(OUT / "p2_3_validation.json", validation)
    make_figure([m for m in models if m["status"] == "COMPLETE"])
    create_manifest(meta)
    print("FINALIZE_PASS", len(models) - 1, "external models", flush=True)


def make_figure(models):
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(models))
    for i, model in enumerate(models):
        r = model["randinit17_cov_minus_ctrl"]
        t = model["cov_minus_ctrl"]
        ax.plot([i, i], [r, t], color="#B9C0C9", lw=1.5, zorder=1)
        ax.scatter(i, r, s=60, color="#8A94A6", label="randinit17" if i == 0 else None, zorder=3)
        ax.scatter(i, t, s=70, color="#D55E00", label="trained" if i == 0 else None, zorder=3)
    ax.axhline(0, color="#444444", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([m["model"].replace("-404M", "\n404M").replace("-36M", "\n36M")
                        for m in models])
    ax.set_ylabel("COV − CTRL (pooled probability difference)")
    ax.set_title("External MLMs — observational anchors")
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.99, 0.02, f"seed 17; n = {models[0]['n_cov']} mutations per arm",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#555555")
    fig.tight_layout()
    fig.savefig(OUT / "p2_3_external_cov.png", dpi=300)
    fig.savefig(OUT / "p2_3_external_cov.pdf")
    plt.close(fig)


def create_manifest(meta):
    import platform
    sanity_run = BASE / "weights" / "RNA-Sc-300M_s17"
    if not sanity_run.exists():
        sanity_run = BASE / "weights" / "RNA-Sc-300M_s17_b59"
    weight_files = {
        "rnasc300m_sanity": sanity_run / "ckpt_nt5800296014_step618357.pt",
        "rinalmo_micro": BASE / "ext" / "rinalmo" / "model.safetensors",
        "nucleicbert": BASE / "ext" / "nucleicbert_repo" / "pretrained.pt",
        "rinalmo_mega": BASE / "ext" / "rinalmo-mega" / "model.safetensors",
        "rinalmo_giga": BASE / "ext" / "rinalmo-giga" / "model.safetensors",
    }
    inputs = {name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
              for name, path in weight_files.items()}
    tokenizer_files = []
    for path in [BASE / "ext" / "rinalmo", BASE / "ext" / "rinalmo-mega",
                 BASE / "ext" / "rinalmo-giga"]:
        for name in ("config.json", "tokenizer_config.json"):
            tokenizer_files.append(path / name)
    tokenizer_files.extend([
        BASE / "ext" / "nucleicbert_repo" / "nucleicbert" / "tokenizers" / "noncoding_seqs.json",
        BASE / "ext" / "nucleicbert_repo" / "nucleicbert" / "models" / "bert.py",
    ])
    outputs = {}
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name != "p2_3_manifest.json" and not path.name.endswith(".tmp"):
            outputs[path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    packages = {}
    for name in ("torch", "numpy", "pandas", "pyarrow", "transformers",
                 "multimolecule", "tokenizers", "safetensors", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    manifest = {
        "task": "X-P23 / P2.3",
        "status": "COMPLETE_WITH_RNA_FM_NOT_RUN_WEIGHT_MISSING",
        "created_unix": time.time(),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(__file__),
        "authoritative_source_sha256": sha256_file(CODE / "run_cov300.py"),
        "bpRNA": {"path": str(DATA), "sha256": meta["bpRNA_sha256"]},
        "conditions_sha256": meta["conditions_sha256"],
        "weights": inputs,
        "tokenizer_and_adapter_files": [
            {"path": str(p), "sha256": sha256_file(p)} for p in tokenizer_files],
        "environment": {
            "python": sys.version, "platform": platform.platform(),
            "packages": packages, "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0),
            "torch_cuda": torch.version.cuda,
        },
        "outputs": outputs,
        "rna_fm": "NOT_RUN_WEIGHT_MISSING",
        "rnasc300m_sanity": (
            json.load(open(OUT / "p2_3_rnasc300m_sanity.json"))["sanity_pass"]
            if (OUT / "p2_3_rnasc300m_sanity.json").exists()
            else "SUBSTITUTE_B59_ANCHOR_MISMATCH"),
    }
    write_json(OUT / "p2_3_manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["freeze", "sanity", "external", "finalize"])
    parser.add_argument("--model", choices=list(MODEL_SPECS))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if args.command == "freeze":
        freeze_conditions()
    elif args.command == "sanity":
        run_sanity()
    elif args.command == "external":
        assert args.model
        run_external(args.model)
    else:
        finalize()


if __name__ == "__main__":
    main()
