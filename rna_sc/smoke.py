"""Smoke tests (acceptance A6): model shape, ALiBi, masking, batching, loss drop.

Run on a GPU:  python -m rna_sc.smoke --device 6
Covers: parameter counts vs targets, forward/backward, deterministic masking,
nt-budgeted batching, loss decreases over 30 steps, CPU-fallback guard.
"""
from __future__ import annotations

import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.config import resolve_config, SPLIT_8080
from rna_sc.census import GPUGuard, count_params
from rna_sc.data import iter_mlm_batches, count_valid_nt, IGNORE, _apply_mlm
from rna_sc.model import RNAMLMEncoder, PAD, MASK, CLS


def t(name, ok):
    print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    return ok


def main(device: int) -> int:
    dev = "cuda:%d" % device
    assert torch.cuda.is_available(), "CUDA required"
    guard = GPUGuard(dev)
    guard.check()
    all_ok = True

    print("== 1. masking determinism ==")
    ids = [0, 1, 2, 3] * 10
    a1 = _apply_mlm(ids, 12345)
    a2 = _apply_mlm(ids, 12345)
    same = a1[0] == a2[0] and a1[1] == a2[1]
    n_targets = sum(1 for x in a1[1] if x != IGNORE)
    frac = n_targets / len(ids)
    all_ok &= t("deterministic mask", same)
    all_ok &= t("mask fraction ~15%% (%.3f)" % frac, 0.10 <= frac <= 0.20)

    print("== 2. model forward/backward + hidden states ==")
    from rna_sc.specs import FAMILY
    for mid, spec in FAMILY.items():
        m = RNAMLMEncoder(spec.d_model, spec.n_layers, spec.n_heads,
                          spec.d_ff).to(dev)
        pc = count_params(m)
        ok = pc.within(spec.target_params, tol=0.12)
        all_ok &= t("%s params=%d target=%d (within 12%%)"
                    % (mid, pc.total_params, spec.target_params), ok)
        if mid == "RNA-Sc-10M":
            B, T = 2, 64
            ids_t = torch.randint(0, 4, (B, T), device=dev)
            ids_t[0, -8:] = PAD
            in_t = ids_t.clone()
            in_t[1, :10] = MASK
            tgt = torch.full((B, T), IGNORE, device=dev, dtype=torch.long)
            tgt[1, :10] = ids_t[1, :10]
            logits, loss, hids = m(in_t, tgt, return_all_hiddens=True)
            shape_ok = (tuple(logits.shape) == (B, T, 7)
                        and len(hids) == spec.n_layers
                        and all(h.shape == (B, T, spec.d_model) for h in hids))
            all_ok &= t("10M forward shapes (logits %s, %d hiddens)"
                        % (tuple(logits.shape), len(hids)), shape_ok)
            loss.backward()
            grad_ok = m.blocks[0].attn.qkv.weight.grad is not None
            all_ok &= t("10M backward grads flow", grad_ok)
            pad_ok = bool(torch.isfinite(loss))
            all_ok &= t("10M loss finite (%.4f)" % float(loss), pad_ok)

    print("== 3. batching over real split (train) ==")
    cfg = resolve_config("RNA-Sc-10M", 17, dev)
    gen = iter_mlm_batches(SPLIT_8080, "train", 17, cfg.context_nt,
                           cfg.batch_nt, corpus_nseq=200)
    b = next(iter(gen))
    T = len(b["ids"][0])
    all_ok &= t("batch shapes ids=%s targets=%s"
                % ([len(b["ids"]), T], [len(b["targets"]), T]),
                len(b["ids"][0]) == len(b["targets"][0]))
    all_ok &= t("valid_nt>0 (%d)" % b["valid_nt"], b["valid_nt"] > 0)
    max_rows = cfg.batch_nt // max(1, T)
    all_ok &= t("nt-budget respected (rows=%d <= %d)"
                % (len(b["ids"]), max_rows + 1), len(b["ids"]) <= max_rows + 1)

    print("== 4. loss decreases over 30 steps (RNA-Sc-1M) ==")
    spec = FAMILY["RNA-Sc-1M"]
    m = RNAMLMEncoder(spec.d_model, spec.n_layers, spec.n_heads,
                      spec.d_ff).to(dev)
    opt = torch.optim.AdamW(m.parameters(), lr=6e-4)
    losses = []
    gen = iter_mlm_batches(SPLIT_8080, "train", 17, 128,
                           batch_nt=8192, corpus_nseq=400)
    n = 0
    for batch in gen:
        if n >= 30:
            break
        ids = torch.tensor(batch["ids"], dtype=torch.long, device=dev)
        tgt = torch.tensor(batch["targets"], dtype=torch.long, device=dev)
        _, loss = m(ids, tgt)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss))
        n += 1
    dropped = losses[-1] < losses[0]
    all_ok &= t("loss %.3f -> %.3f" % (losses[0], losses[-1]), dropped)

    print("== 5. GPU guard ==")
    all_ok &= t("cpu_fallback_count == 0", guard.cpu_fallback_count == 0)

    print("SMOKE RESULT:", "ALL PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=0)
    args = ap.parse_args()
    sys.exit(main(args.device))
