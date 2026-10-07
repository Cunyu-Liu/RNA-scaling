"""closeout_b59 自动重绘补丁（2026-10-08）：

650M_b59 收口后（factorial_verdict 刷新 650M 行），自动重跑
make_result_figs_v2.py——fig6_v4 幂等自升级第四点（family/structure 双
通道），fig1_v2 同步刷新（650M@5.9B probe 行落盘后曲线重算）。
纯绘图（CPU matplotlib），零 GPU 需求，超时 10 分钟兜底。

验证：py_compile + 补丁幂等（重复运行 skip）。
"""
import sys

SRC = "/home/cunyuliu/rna-sc/rna_sc/closeout_b59.py"

OLD = '''def factorial_verdict(device: int) -> None:
    log = os.path.join(MNT, "logs", "closeout_b59_verdict.log")
    with open(log, "a") as lf:
        subprocess.run([PY, "-m", "rna_sc.factorial_verdict",
                        "--device", str(device)],
                       cwd=ROOT, stdout=lf, stderr=lf, timeout=7200)
    with open(TLOG, "a") as fh:
        fh.write("\\n- [closeout-b59] 3x2 factorial verdict refreshed "
                 "(evidence/factorial_verdict.json; Claim-14 test)\\n")'''

NEW = '''def factorial_verdict(device: int) -> None:
    log = os.path.join(MNT, "logs", "closeout_b59_verdict.log")
    with open(log, "a") as lf:
        subprocess.run([PY, "-m", "rna_sc.factorial_verdict",
                        "--device", str(device)],
                       cwd=ROOT, stdout=lf, stderr=lf, timeout=7200)
    with open(TLOG, "a") as fh:
        fh.write("\\n- [closeout-b59] 3x2 factorial verdict refreshed "
                 "(evidence/factorial_verdict.json; Claim-14 test)\\n")
    # 2026-10-08 auto-fig patch: idempotent self-upgrade of fig6_v4 (4th
    # point) + fig1_v2 after the verdict JSON gains the 650M row. Pure
    # matplotlib on CPU; 10-min timeout guard.
    try:
        figlog = os.path.join(MNT, "logs", "closeout_b59_figs.log")
        with open(figlog, "a") as lf:
            subprocess.run(
                [PY, "/home/cunyuliu/rna-sc/make_result_figs_v2.py"],
                cwd=ROOT, stdout=lf, stderr=lf, timeout=600)
        with open(TLOG, "a") as fh:
            fh.write("\\n- [closeout-b59] fig6_v4/fig1_v2 auto-refreshed "
                     "(idempotent 4-point self-upgrade)\\n")
    except subprocess.TimeoutExpired:
        with open(TLOG, "a") as fh:
            fh.write("\\n- [closeout-b59] fig auto-refresh TIMEOUT "
                     "(rerun make_result_figs_v2.py manually)\\n")'''


def main() -> int:
    with open(SRC, encoding="utf-8") as fh:
        code = fh.read()
    if "auto-fig patch" in code:
        print("patch already applied")
        return 0
    if OLD not in code:
        print("ANCHOR NOT FOUND — aborting (no changes)")
        return 1
    code = code.replace(OLD, NEW, 1)
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(code)
    import py_compile
    py_compile.compile(SRC, doraise=True)
    print("PATCH OK + syntax passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
