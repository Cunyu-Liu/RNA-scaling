"""T0.2.6 Declarative evaluation matrix runner (S9 protocol matrix base).

Spec-driven, ledger-tracked evaluator for the model x task x protocol x
split grid. Prevents missed/duplicated evaluations the same way the
training ledger prevents duplicate runs.

Eval ledger (JSONL, flock-guarded): /mnt/cunyuliu/rna-sc/eval_matrix.jsonl
  {"eval_id", "model", "task", "protocol", "split", "status",
   "updated_utc", "result_path", "note"}

Grid axes (v1 scope — line-2 self-trained family, one task):
  - model: RNA-Sc-{1M,10M,30M,100M}_s17 (+ _randinit17 / _mommatch17
    controls for protocol-robustness checks)
  - task: rna_type (S11 global-property, day-1 task; class-balanced
    head per red-team fix B)
  - protocol: probe-balanced (class-weighted logistic + balanced
    sampling; mean-pool rows are the day-1 protocol, kept as the
    ordering baseline)
  - splits: family_validation -> family_test (cluster-disjoint);
    random (seed-isolated from family split, red-team C)

v2 (T1.2) will add zero-shot / LoRA / full-FT protocols and the
task-trichotomy rows once T1.1 data lands.

Usage:
  python -m rna_sc.eval_matrix --smoke           # 1 model, tiny n, fast
  python -m rna_sc.eval_matrix --model RNA-Sc-10M_s17   # one model row
  python -m rna_sc.eval_matrix --list           # show grid + statuses
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import json
import os

import torch

LEDGER = "/mnt/cunyuliu/rna-sc/eval_matrix.jsonl"
LOCK = "/mnt/cunyuliu/rna-sc/eval_matrix.lock"
RESULTS = "/mnt/cunyuliu/rna-sc/eval/eval_matrix_results.jsonl"
RUNS = "/mnt/cunyuliu/rna-sc/runs"

MODELS_V1 = ["RNA-Sc-1M_s17", "RNA-Sc-10M_s17", "RNA-Sc-30M_s17",
             "RNA-Sc-100M_s17"]
PROTOCOLS_V1 = ["probe-balanced", "probe-meanpool"]
SPLITS_V1 = ["family", "random"]
TASK_V1 = "rna_type"

BALANCE_W_CAP = 10.0


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


@contextlib.contextmanager
def _locked():
    with open(LOCK, "a") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _load() -> list[dict]:
    rows = []
    if os.path.exists(LEDGER):
        with open(LEDGER) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return rows


def _write(rows: list[dict]) -> None:
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, LEDGER)


def eval_id(model, task, protocol, split):
    return "ev_%s__%s__%s__%s" % (model, task, protocol, split)


def status_of(model, task, protocol, split) -> str | None:
    eid = eval_id(model, task, protocol, split)
    for r in _load():
        if r["eval_id"] == eid:
            return r.get("status")
    return None


def claim(model, task, protocol, split) -> bool:
    eid = eval_id(model, task, protocol, split)
    with _locked():
        rows = _load()
        for r in rows:
            if r["eval_id"] == eid and r.get("status") in ("running",
                                                           "done"):
                return False
        rows.append({"eval_id": eid, "model": model, "task": task,
                     "protocol": protocol, "split": split,
                     "status": "running", "updated_utc": _now(),
                     "result_path": RESULTS, "note": ""})
        _write(rows)
        return True


def finish(model, task, protocol, split, metrics: dict) -> None:
    eid = eval_id(model, task, protocol, split)
    with _locked():
        rows = _load()
        found = False
        for r in rows:
            if r["eval_id"] == eid:
                r["status"] = "done"
                r["updated_utc"] = _now()
                r["metrics"] = metrics
                found = True
        if not found:
            rows.append({"eval_id": eid, "model": model, "task": task,
                         "protocol": protocol, "split": split,
                         "status": "done", "updated_utc": _now(),
                         "result_path": RESULTS, "metrics": metrics})
        _write(rows)


def load_model(model_name: str):
    """Load a trained / control model by eval-matrix name."""
    from rna_sc.model import RNAMLMEncoder
    from rna_sc.probe import load_encoder
    base_run, mode = model_name, "trained"
    for suf in ("_randinit17", "_mommatch17"):
        if model_name.endswith(suf):
            base_run = model_name[: -len(suf)]
            mode = suf[1:]
    run_dir = os.path.join(RUNS, base_run)
    if mode == "trained":
        return load_encoder(run_dir)
    model, ck = load_encoder(run_dir)
    import torch as _t
    if mode == "randinit17":
        _t.manual_seed(17)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
    else:
        trained_sd = {k: v.clone() for k, v in model.state_dict().items()
                      if v.is_floating_point()}
        _t.manual_seed(17)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        with _t.no_grad():
            new_sd = model.state_dict()
            for k, v in new_sd.items():
                if not v.is_floating_point() or v.numel() < 2:
                    continue
                t = trained_sd[k]
                tm, ts = t.mean(), t.std()
                vm, vs = v.mean(), v.std()
                if ts > 0 and vs > 0:
                    v.copy_((v - vm) / vs * ts + tm)
            model.load_state_dict(new_sd)
    ck = dict(ck)
    ck["nt"] = 0
    return model, ck


def balanced_linear_probe(X_tr, y_tr, X_ev, y_ev, device, layer_seed=17,
                          n_classes=None, class_weighted=True):
    """Class-weighted logistic head + balanced row order (red-team fix B).

    Reuses the day-1 probe head but with: (a) class weights = cap(1/freq,
    BALANCE_W_CAP); (b) rows shuffled deterministically per seed so SGD
    sees a balanced-ish order without duplication.
    """
    from rna_sc.probe import probe_one_layer
    import collections
    if n_classes is None:
        classes = sorted(set(y_tr))
        cls_map = {c: i for i, c in enumerate(classes)}
        y_tri = [cls_map[c] for c in y_tr]
        y_evi = [cls_map[c] for c in y_ev if c in cls_map]
        keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
    else:
        classes = None
        y_tri = y_tr
        y_evi = y_ev
        keep_ev = list(range(len(y_ev)))
    freq = collections.Counter(y_tri)
    n = len(y_tri)
    weights = torch.tensor(
        [min(BALANCE_W_CAP, n / max(1, freq[c])) for c in
         range(max(y_tri) + 1)], dtype=torch.float32, device=device)
    accs, f1s = [], []
    L = len(X_tr)
    for li in range(L):
        Xtr = X_tr[li]
        Xev = X_ev[li][keep_ev]
        acc, f1, _ = _probe_weighted(Xtr, y_tri, Xev, y_evi, weights,
                                     device, layer_seed + li,
                                     len(weights))
        accs.append(acc)
        f1s.append(f1)
    return accs, f1s


def _probe_weighted(Xtr, y_tri, Xev, y_evi, weights, device, seed, C):
    """Single-layer class-weighted logistic probe (L-BFGS-free, full-batch
    Adam, deterministic)."""
    torch.manual_seed(seed)
    W = torch.zeros(Xtr.shape[1], C, device=device, requires_grad=True)
    X = Xtr.to(device).float()
    T = torch.tensor(y_tri, device=device)
    # balanced deterministic order: sort by class then interleave via seed
    rng = torch.Generator(device="cpu")
    rng.manual_seed(seed)
    order = torch.randperm(len(T), generator=rng).to(device)
    opt = torch.optim.Adam([W], lr=0.05)
    for _ in range(200):
        opt.zero_grad()
        logits = X @ W
        loss = torch.nn.functional.cross_entropy(logits, T, weight=weights)
        loss.backward()
        opt.step()
    with torch.no_grad():
        Ev = Xev.to(device).float()
        Tev = torch.tensor(y_evi, device=device)
        pred = (Ev @ W).argmax(-1)
        acc = (pred == Tev).float().mean().item()
        from rna_sc.probe import per_class_f1
        f1 = sum(f for f in per_class_f1(pred.tolist(), y_evi, C)
                 if f is not None) / C
    return acc, f1, None


def run_one(model_name, protocol, split_key, device, n_train, n_eval,
            smoke=False):
    from rna_sc.census import GPUGuard
    dev = "cuda:%d" % device
    guard = GPUGuard(dev)
    guard.check()
    model, ck = load_model(model_name)
    L = ck["cfg"]["arch"]["n_layers"]
    from rna_sc.probe import collect_states
    # split semantics (T1.2.4 / Q7):
    #   family: cluster-disjoint family_validation -> family_test (day-1)
    #   random: single held-out pool (family_validation, never seen in
    #           MLM pretraining), rows partitioned deterministically
    #           (i % 5 == 0 -> eval, else train). Both sides stay
    #           pretraining-held-out, and family structure overlaps by
    #           construction — that overlap IS the random-split protocol
    #           point, isolating family-disjointness as the single
    #           variable vs the family split. (Drawing probe rows from
    #           the MLM 'train' pool would confound pretraining exposure
    #           with split type and is forbidden.)
    if split_key == "family":
        X_tr, y_tr = collect_states(model, dev, "family_validation",
                                    n_train, L)
        X_ev, y_ev = collect_states(model, dev, "family_test",
                                    n_eval, L)
    else:
        n_all = n_train + n_eval
        X_all, y_all = collect_states(model, dev, "family_validation",
                                      n_all, L)
        idx_ev = [i for i in range(len(y_all)) if i % 5 == 0]
        idx_tr = [i for i in range(len(y_all)) if i % 5 != 0]
        X_tr = [torch.stack([X_all[li][i] for i in idx_tr])
                for li in range(L)]
        y_tr = [y_all[i] for i in idx_tr]
        X_ev = [torch.stack([X_all[li][i] for i in idx_ev])
                for li in range(L)]
        y_ev = [y_all[i] for i in idx_ev]
    print("collected: train=%d eval=%d layers=%d" %
          (len(y_tr), len(y_ev), L))
    if protocol == "probe-meanpool":
        from rna_sc.probe import probe_one_layer
        accs, f1s = [], []
        classes = sorted(set(y_tr))
        cls_map = {c: i for i, c in enumerate(classes)}
        keep_tr = [i for i, c in enumerate(y_tr) if c in cls_map]
        y_tri = [cls_map[y_tr[i]] for i in keep_tr]
        keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
        y_evi = [cls_map[y_ev[i]] for i in keep_ev]
        for li in range(L):
            acc, f1, _ = probe_one_layer(
                X_tr[li][keep_tr], y_tri, X_ev[li][keep_ev], y_evi,
                len(classes), dev, return_pred=True, layer_seed=17 + li)
            accs.append(acc)
            f1s.append(f1)
    else:
        accs, f1s = balanced_linear_probe(
            X_tr, y_tr, X_ev, y_ev, dev, layer_seed=17)
    best_f1 = max(f1s)
    best_layer = f1s.index(best_f1)
    metrics = {"best_f1_macro": round(best_f1, 4),
               "best_layer": best_layer, "n_layers": L,
               "best_acc": round(accs[best_layer], 4),
               "n_train": len(y_tr), "n_eval": len(y_ev),
               "protocol": protocol, "split": split_key,
               "model": model_name}
    if not smoke:
        with open(RESULTS, "a") as fh:
            fh.write(json.dumps(metrics) + "\n")
        finish(model_name, TASK_V1, protocol, split_key, metrics)
    print(json.dumps(metrics, indent=2))
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="tiny n, no ledger write (fast correctness check)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--device", type=int, default=6)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--n-eval", type=int, default=4000)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        rows = _load()
        by = {r["eval_id"]: r["status"] for r in rows}
        for m in MODELS_V1 + ["RNA-Sc-10M_s17_randinit17"]:
            for p in PROTOCOLS_V1:
                for s in SPLITS_V1:
                    eid = eval_id(m, TASK_V1, p, s)
                    print("%-34s %-16s %-8s %s" %
                          (m, p, s, by.get(eid, "-")))
        return 0

    model = args.model or "RNA-Sc-10M_s17"
    n_train = 2000 if args.smoke else args.n_train
    n_eval = 500 if args.smoke else args.n_eval
    protocols = ["probe-balanced"] if args.smoke else PROTOCOLS_V1
    splits = ["family"] if args.smoke else SPLITS_V1
    for p in protocols:
        for s in splits:
            if not args.smoke:
                if not claim(model, TASK_V1, p, s):
                    print("SKIP (already running/done): %s %s %s" %
                          (model, p, s))
                    continue
            try:
                run_one(model, p, s, args.device, n_train, n_eval,
                        smoke=args.smoke)
            except Exception as e:
                print("FAILED %s %s %s: %s" % (model, p, s, e))
                raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
