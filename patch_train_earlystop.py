"""train.py 早停补丁（2026-10-08，用户指令：loss 收敛到不下降为止，
早停 + 5 轮耐心值）：

- 新参数 --early-stop-patience N（默认 0 = 关闭，零行为变化）
- 语义：连续 N 个 val 点（VAL_INTERVAL_NT=100M nt 间隔）无 best 改善
  → 提前置 done；manifest 记 stop_reason='early_stop'（预算到期则为
  'budget'）；DONE 帧格式不变（watch_all/closeout 兼容零改动）
- best ckpt 逻辑不变（best_checkpoint 仍是最优 val 点）
- lr 余弦是按 budget 的：早停意味着 lr 未到尾部——诚实记入 manifest
  （cosine_truncated=True），论文口径可辨
"""
import sys

SRC = "/home/cunyuliu/rna-sc/rna_sc/train.py"

ANCHOR_RUN_SIG = """def run(model_id: str, seed: int, device: int, out_dir: str,
        corpus_nseq: int | None = None, corpus_tag: str = "full",
        smoke_nt: int | None = None, resume_from: str | None = None,
        cluster_allowlist: str | None = None,
        budget_nt: int | None = None,
        train_parquet: str | None = None) -> dict:"""

NEW_RUN_SIG = """def run(model_id: str, seed: int, device: int, out_dir: str,
        corpus_nseq: int | None = None, corpus_tag: str = "full",
        smoke_nt: int | None = None, resume_from: str | None = None,
        cluster_allowlist: str | None = None,
        budget_nt: int | None = None,
        train_parquet: str | None = None,
        early_stop_patience: int = 0) -> dict:"""

ANCHOR_BEST = """    step, cumulative_nt, last_ckpt_nt, last_val_nt = 0, 0, 0, 0
    best_val, best_ck = float("inf"), None"""
NEW_BEST = """    step, cumulative_nt, last_ckpt_nt, last_val_nt = 0, 0, 0, 0
    best_val, best_ck = float("inf"), None
    es_bad = 0            # early-stop: consecutive vals without improvement
    stop_reason = "budget\""""

ANCHOR_VALBLOCK = """                if v["val_loss"] < best_val:
                    best_val, best_ck = v["val_loss"], ck_path
                print("[%s] VAL nt=%d step=%d val=%.4f (best=%.4f)" % ("""
NEW_VALBLOCK = """                if v["val_loss"] < best_val:
                    best_val, best_ck = v["val_loss"], ck_path
                    es_bad = 0
                else:
                    es_bad += 1
                    if early_stop_patience and es_bad >= early_stop_patience:
                        print("[%s] EARLY-STOP: %d vals without improvement "
                              "(best=%.4f @patience=%d) -> stop" % (
                                  cfg.run_id, es_bad, best_val,
                                  early_stop_patience), flush=True)
                        stop_reason = "early_stop"
                        done = True
                print("[%s] VAL nt=%d step=%d val=%.4f (best=%.4f)" % ("""

ANCHOR_MANIFEST = """        "cpu_fallback_count": guard.cpu_fallback_count,
        "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "DONE",
    }"""
NEW_MANIFEST = """        "cpu_fallback_count": guard.cpu_fallback_count,
        "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "DONE",
        "stop_reason": stop_reason,
        "early_stop_patience": early_stop_patience or None,
        "cosine_truncated": (stop_reason == "early_stop"),
    }"""

ANCHOR_ARG = """    ap.add_argument("--train-parquet", default=None,
                    help="override TRAIN data source parquet (rfamcap arm; "
                         "validate keeps streaming SPLIT_8080)")
    args = ap.parse_args()
    run(args.model, args.seed, args.device, args.out_dir,
        corpus_nseq=args.corpus_nseq, corpus_tag=args.corpus_tag,
        smoke_nt=args.smoke_nt, resume_from=args.resume_from,
        cluster_allowlist=args.cluster_allowlist,
        budget_nt=args.budget_nt, train_parquet=args.train_parquet)"""
NEW_ARG = """    ap.add_argument("--train-parquet", default=None,
                    help="override TRAIN data source parquet (rfamcap arm; "
                         "validate keeps streaming SPLIT_8080)")
    ap.add_argument("--early-stop-patience", type=int, default=0,
                    help="stop after N consecutive val points without "
                         "improvement (0 = disabled, budget-bound as "
                         "before); user request 2026-10-08: patience 5")
    args = ap.parse_args()
    run(args.model, args.seed, args.device, args.out_dir,
        corpus_nseq=args.corpus_nseq, corpus_tag=args.corpus_tag,
        smoke_nt=args.smoke_nt, resume_from=args.resume_from,
        cluster_allowlist=args.cluster_allowlist,
        budget_nt=args.budget_nt, train_parquet=args.train_parquet,
        early_stop_patience=args.early_stop_patience)"""


def apply(code, old, new):
    if new.split("\n")[1].strip() in code and old not in code:
        print("already patched segment:", old.split("\n")[0][:50])
        return code, False
    if old not in code:
        raise SystemExit("ANCHOR NOT FOUND: %s..." % old[:60])
    return code.replace(old, new, 1), True


def main():
    code = open(SRC, encoding="utf-8").read()
    changed = False
    for old, new in [(ANCHOR_RUN_SIG, NEW_RUN_SIG),
                     (ANCHOR_BEST, NEW_BEST),
                     (ANCHOR_VALBLOCK, NEW_VALBLOCK),
                     (ANCHOR_MANIFEST, NEW_MANIFEST),
                     (ANCHOR_ARG, NEW_ARG)]:
        code, did = apply(code, old, new)
        changed = changed or did
    open(SRC, "w", encoding="utf-8").write(code)
    import py_compile
    py_compile.compile(SRC, doraise=True)
    print("PATCH %s + syntax OK" % ("applied" if changed else "noop"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
