"""watch_all rfamcap 确定性补丁（2026-10-08）：

问题：rfamcap 臂（语料 273.9M nt，2.0B 预算 = 7.3 epoch 循环）在训练中
每过一个 epoch 边界会落盘一个 ckpt 并打印 DONE 帧吗？——实测日志：epoch
boundary 行不会写 DONE（DONE 只在预算达标时打印一次）。但 10-07 事故中
1-epoch 提前退出打印了 DONE（nt=0.27B）→ watch_all 据此 probe 了
ckpt_nt=200M 的早期 ckpt（100M_rfamcap 0.3448@L18 / 30M_rfamcap
0.2880@L7 都是 1-epoch 值，非终值）→ probed_runs() 因 manifest
final_nt 逻辑会在续跑 DONE 后触发 re-probe——但 handled 集合是内存态，
值守进程 10-02 启动后已把 rfamcap rid 标记 handled（0.27B 那次），
续跑真 DONE 后不会再次 probe！

修复（最小侵入，不改值守进程热路径）：
 1. 在 _cycle 的 todo 过滤后加"续跑复检"：rid 已 handled 但 probed_runs()
    的 final-probe 覆盖用 manifest final_nt 判定为"probe 落后于最终 ckpt"
    → 从 handled 移除并重新入队；
 2. 对 rfamcap/多 epoch 臂同样适用（scan_done 按 LOG 文件名 key，DONE 帧
    被续跑覆盖后 nt 是最新值）。

验证：语法检查 + 单元 dry-run（无副作用：只改 handled 逻辑）。
"""
import re
import sys

SRC = "/home/cunyuliu/rna-sc/rna_sc/watch_all.py"

PATCH_ANCHOR = """        done = scan_done()
        probed = probed_runs()
        todo = [rid for rid, d in done.items()
                if rid not in probed and rid not in handled]"""

PATCH_NEW = """        done = scan_done()
        probed = probed_runs()
        # rfamcap/multi-epoch recheck (2026-10-08): a run marked handled
        # from a PREMATURE DONE (1-epoch exit) must be re-probed once the
        # resumed run reaches its real budget DONE. probed_runs() already
        # drops runs whose probe predates manifest final_nt; here we also
        # un-mark handled for those, so the re-probe actually fires.
        for rid in list(handled):
            if rid in probed or rid not in done:
                continue
            rd = run_dir_of(rid)
            try:
                import json as _json
                with open(os.path.join(rd, "manifest.json")) as _mh:
                    _mnt = _json.load(_mh).get("final_nt") or 0
            except (OSError, _json.JSONDecodeError):
                continue
            # probe rows' max ckpt for this run
            _max_probe_nt = 0
            try:
                for line in open(PROBE_OUT):
                    try:
                        _r = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    if _r.get("run") == "RNA-Sc-" + rid[len("rnasc_"):]:
                        _max_probe_nt = max(_max_probe_nt,
                                            _r.get("ckpt_nt") or 0)
            except OSError:
                pass
            if _mnt and _max_probe_nt and _mnt - _max_probe_nt > 100_000_000:
                print("[watch-all] %s probe stale (manifest %d > probe %d) "
                      "-> requeue" % (rid, _mnt, _max_probe_nt), flush=True)
                handled.discard(rid)
        todo = [rid for rid, d in done.items()
                if rid not in probed and rid not in handled]"""


def main():
    with open(SRC, encoding="utf-8") as fh:
        code = fh.read()
    if PATCH_ANCHOR not in code:
        print("ANCHOR NOT FOUND — aborting (no changes made)")
        return 1
    if "rfamcap/multi-epoch recheck" in code:
        print("patch already applied")
        return 0
    code = code.replace(PATCH_ANCHOR, PATCH_NEW, 1)
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(code)
    import py_compile
    py_compile.compile(SRC, doraise=True)
    print("PATCH OK + syntax check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
