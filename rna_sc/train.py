"""Training runner for one RNA-Sc run (model x seed x corpus arm).

Follows the TokBench p4_train manifest discipline:
  - GPU-only (GPUGuard; cpu_fallback_count must be 0);
  - budget in cumulative valid nt (2.0B default; smoke override allowed);
  - validation on the held-out `validation` split (never family_test/test);
  - checkpoints every ckpt_nt with val loss recorded (S6 time axis);
  - incremental manifest.json so partial progress survives crashes.

Usage:
  python -m rna_sc.train --model RNA-Sc-10M --seed 17 --device 6 \
      --out-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-10M_s17
  python -m rna_sc.train --model RNA-Sc-30M --seed 17 --device 1 \
      --corpus-nseq 1000000 --corpus-tag c1M \
      --out-dir /mnt/cunyuliu/rna-sc/runs/RNA-Sc-30M_s17_c1M
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rna_sc.config import resolve_config, SPLIT_8080
from rna_sc.census import GPUGuard, count_params
from rna_sc.data import iter_mlm_batches, count_valid_nt, IGNORE
from rna_sc.model import RNAMLMEncoder, PAD


def build_model(cfg) -> RNAMLMEncoder:
    s = cfg.spec
    model = RNAMLMEncoder(d_model=s.d_model, n_layers=s.n_layers,
                           n_heads=s.n_heads, d_ff=s.d_ff)
    torch.manual_seed(cfg.seed)
    return model


def _t(batch, key, device):
    return torch.tensor(batch[key], dtype=torch.long, device=device)


def lr_at(nt: int, cfg) -> float:
    base, warmup, budget = cfg.lr, cfg.warmup_nt, cfg.budget_nt
    if nt < warmup:
        return base * (nt / max(1, warmup))
    progress = min(1.0, (nt - warmup) / max(1, budget - warmup))
    return base * 0.5 * (1.0 + math.cos(math.pi * progress))


@torch.no_grad()
def validate(cfg, model, device) -> dict:
    guard = GPUGuard(device)
    guard.check()
    model.eval()
    gen = iter_mlm_batches(SPLIT_8080, cfg.val_split, cfg.seed,
                           cfg.context_nt, cfg.batch_nt,
                           corpus_nseq=None, max_batches=None)
    total_nll, total_nt, n_batches = 0.0, 0, 0
    val_target_nt = 0
    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        for batch in gen:
            ids = _t(batch, "ids", device)
            tgt = _t(batch, "targets", device)
            logits, _ = model(ids)
            tgt_f = tgt.clone()
            tgt_f[tgt == IGNORE] = 0  # gather-safe; ignored in loss below
            lp = torch.log_softmax(logits.float(), dim=-1)
            sel = (tgt != IGNORE)
            ll = lp.gather(-1, tgt_f.unsqueeze(-1)).squeeze(-1)
            ll = torch.where(sel, ll, torch.zeros_like(ll))
            b_nt = int(sel.sum().item())
            total_nll += float(-ll.sum().item())
            total_nt += b_nt
            n_batches += 1
            val_target_nt += count_valid_nt(batch)
            if total_nt >= cfg.val_nt:
                break
    val_loss = total_nll / max(1, total_nt)
    guard.verify_cuda_alive()
    return {"val_loss": val_loss, "val_nt": total_nt, "val_batches": n_batches,
            "val_seqs_streamed_nt": val_target_nt, "cpu_fallback_count": 0}


def run(model_id: str, seed: int, device: int, out_dir: str,
        corpus_nseq: int | None = None, corpus_tag: str = "full",
        smoke_nt: int | None = None, resume_from: str | None = None,
        cluster_allowlist: str | None = None) -> dict:
    dev = "cuda:%d" % device
    assert torch.cuda.is_available(), "CUDA required (no silent CPU fallback)"
    guard = GPUGuard(dev)
    guard.check()
    allowlist = None
    if cluster_allowlist:
        import pyarrow.parquet as pq
        allowlist = set(pq.read_table(cluster_allowlist)
                        .column("cluster_id").to_pylist())
        print("[allowlist] %s: %d clusters" % (cluster_allowlist,
                                               len(allowlist)), flush=True)
    cfg = resolve_config(model_id, seed, dev, corpus_nseq=corpus_nseq,
                         corpus_tag=corpus_tag, smoke_nt=smoke_nt,
                         cluster_allowlist=cluster_allowlist)
    if smoke_nt is not None:
        cfg = cfg.__class__(
            run_id=cfg.run_id, spec=cfg.spec, seed=cfg.seed, device=cfg.device,
            budget_nt=smoke_nt, batch_nt=cfg.batch_nt,
            context_nt=cfg.context_nt, lr=cfg.lr,
            warmup_nt=int(0.02 * smoke_nt), ckpt_nt=max(1, smoke_nt // 2),
            val_interval_nt=max(1, smoke_nt // 2), val_nt=min(cfg.val_nt, 2_000_000),
            val_split=cfg.val_split, mlm_p=cfg.mlm_p,
            corpus_nseq=cfg.corpus_nseq, corpus_tag=cfg.corpus_tag,
            cluster_allowlist=cfg.cluster_allowlist,
            diversity_mode=cfg.diversity_mode, smoke_nt=smoke_nt)
    os.makedirs(out_dir, exist_ok=True)

    model = build_model(cfg).to(dev)
    pc = count_params(model)

    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr,
                            betas=(0.9, 0.95), weight_decay=0.1)
    step, cumulative_nt, last_ckpt_nt, last_val_nt = 0, 0, 0, 0
    best_val, best_ck = float("inf"), None
    if resume_from and os.path.exists(resume_from):
        payload = torch.load(resume_from, map_location=dev, weights_only=False)
        model.load_state_dict(payload["model"])
        opt.load_state_dict(payload["opt"])
        cumulative_nt = payload["nt"]
        step = payload["step"]
        last_ckpt_nt = cumulative_nt
        last_val_nt = cumulative_nt
        print("[resume] %s nt=%d step=%d" % (resume_from, cumulative_nt, step),
              flush=True)

    t0 = time.time()
    perf_nt = 0
    torch.cuda.reset_peak_memory_stats(dev)

    manifest = {
        "project": "rna-sc", "run_id": cfg.run_id,
        "model_id": model_id, "role": cfg.spec.role, "seed": seed,
        "device": dev, "config": cfg.to_dict(),
        "params": pc.total_params,
        "non_embedding_params": pc.non_embedding_params,
        "checkpoints": [], "validations": [],
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    gen = None
    done = False
    while not done:
        gen = iter_mlm_batches(SPLIT_8080, "train", cfg.seed, cfg.context_nt,
                               cfg.batch_nt, corpus_nseq=cfg.corpus_nseq,
                               cluster_allowlist=allowlist)
        for batch in gen:
            if cumulative_nt >= cfg.budget_nt:
                done = True
                break
            if cumulative_nt < last_ckpt_nt:
                # resume fast-forward: deterministic batches -> skip until
                # the pre-crash exposure point is reached again.
                cumulative_nt = min(last_ckpt_nt,
                                    cumulative_nt + count_valid_nt(batch))
                step += 1
                continue
            ids = _t(batch, "ids", dev)
            tgt = _t(batch, "targets", dev)
            for g in opt.param_groups:
                g["lr"] = lr_at(cumulative_nt, cfg)
            model.train()
            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                _, loss = model(ids, tgt)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            vnt = count_valid_nt(batch)
            cumulative_nt += vnt
            perf_nt += vnt
            step += 1
            if step % 200 == 0:
                print("[%s] nt=%.0fM step=%d loss=%.4f lr=%.2e" % (
                    cfg.run_id, cumulative_nt / 1e6, step,
                    float(loss.item()), opt.param_groups[0]["lr"]), flush=True)
            if cfg.val_interval_nt and \
                    cumulative_nt - last_val_nt >= cfg.val_interval_nt:
                last_val_nt = cumulative_nt
                v = validate(cfg, model, dev)
                assert v["cpu_fallback_count"] == 0
                manifest["validations"].append(
                    {"nt": cumulative_nt, "step": step, **v})
                ck_path = os.path.join(
                    out_dir, "ckpt_nt%09d_step%06d.pt" % (cumulative_nt, step))
                torch.save({"model": model.state_dict(),
                            "opt": opt.state_dict(),
                            "nt": cumulative_nt, "step": step,
                            "val_loss": v["val_loss"], "run_id": cfg.run_id,
                            "model_id": model_id, "seed": seed,
                            "cfg": cfg.to_dict()}, ck_path)
                manifest["checkpoints"].append(
                    {"nt": cumulative_nt, "step": step,
                     "val_loss": v["val_loss"], "path": ck_path})
                if v["val_loss"] < best_val:
                    best_val, best_ck = v["val_loss"], ck_path
                print("[%s] VAL nt=%d step=%d val=%.4f (best=%.4f)" % (
                    cfg.run_id, cumulative_nt, step, v["val_loss"], best_val),
                    flush=True)
                with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
                    json.dump(manifest, fh, indent=2, default=str)
        # generator exhausted: full-split streaming epoch ends here.
        # corpus-capped arms cannot loop; full-split arms stop too (budget
        # 2.0B nt < one streaming epoch of 14.1M sequences, ~5.9B nt).
        done = True
    guard.verify_cuda_alive()
    manifest.update({
        "final_nt": cumulative_nt, "final_step": step,
        "best_val_loss": best_val if best_val != float("inf") else None,
        "best_checkpoint": best_ck,
        "throughput_nt_s": perf_nt / max(1e-9, time.time() - t0),
        "peak_vram_mb": torch.cuda.max_memory_allocated(dev) / (1024 ** 2),
        "wall_seconds": time.time() - t0,
        "cpu_fallback_count": guard.cpu_fallback_count,
        "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "DONE",
    })
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    print("DONE %s | nt=%d steps=%d best_val=%.4f | %.0f nt/s peak=%.0fMB "
          "fallback=%d" % (cfg.run_id, cumulative_nt, step,
                           best_val if best_val != float("inf") else -1,
                           manifest["throughput_nt_s"],
                           manifest["peak_vram_mb"], guard.cpu_fallback_count),
          flush=True)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--corpus-nseq", type=int, default=None)
    ap.add_argument("--corpus-tag", default="full")
    ap.add_argument("--cluster-allowlist", default=None,
                    help="parquet with cluster_id column (S2 cluster-"
                         "stratified arm)")
    ap.add_argument("--smoke-nt", type=int, default=None)
    ap.add_argument("--resume-from", default=None)
    args = ap.parse_args()
    run(args.model, args.seed, args.device, args.out_dir,
        corpus_nseq=args.corpus_nseq, corpus_tag=args.corpus_tag,
        smoke_nt=args.smoke_nt, resume_from=args.resume_from,
        cluster_allowlist=args.cluster_allowlist)


if __name__ == "__main__":
    main()
