"""Fix closeout_b59.run_probe idempotency bug (json spacing assumption)."""
import ast

P = "rna_sc/closeout_b59.py"
src = open(P).read()

old = """def run_probe(arm: str, device: int) -> None:
    log = os.path.join(MNT, "logs", "probe_%s_auto_b59.log" % arm)
    rows = _final_rows(arm)
    if not rows:
        with open(log, "a") as lf:
            subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                            os.path.join(MNT, "runs", arm), "--device",
                            str(device)], cwd=ROOT, stdout=lf, stderr=lf,
                           timeout=14400)
    # randinit control (idempotent)
    rand_name = "%s_randinit17" % arm
    if not any(rand_name in l for l in _final_rows_string(arm)):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--random-init", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass


def _final_rows_string(arm: str) -> list[str]:
    p = os.path.join(MNT, "eval", "probe_results.jsonl")
    out = []
    if os.path.exists(p):
        with open(p) as fh:
            out = [l for l in fh if '"%s' % arm in l]
    return out"""

new = """def _have_randinit(arm: str) -> bool:
    \"\"\"True if a randinit17 control run row exists for this arm.
    Uses parsed-json matching (not string formatting, which breaks on
    json.dump spacing differences).\"\"\"
    rand_name = "%s_randinit17" % arm
    for r in _final_rows(arm):
        if r.get("run") == rand_name:
            return True
    return False


def run_probe(arm: str, device: int) -> None:
    log = os.path.join(MNT, "logs", "probe_%s_auto_b59.log" % arm)
    rows = _final_rows(arm)
    if not rows:
        with open(log, "a") as lf:
            subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                            os.path.join(MNT, "runs", arm), "--device",
                            str(device)], cwd=ROOT, stdout=lf, stderr=lf,
                           timeout=14400)
    # randinit control (idempotent, parsed-json check)
    if not _have_randinit(arm):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--random-init", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass"""

if old not in src:
    raise SystemExit("run_probe block not found - abort")
src = src.replace(old, new)
open(P, "w").write(src)
ast.parse(src)
print("patched OK, syntax OK")
