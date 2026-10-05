"""Patch closeout_b59.py: add idempotent mommatch17 control (align 3-piece set)."""
P = "/home/cunyuliu/rna-sc/rna_sc/closeout_b59.py"
src = open(P).read()

old = """    # randinit control (idempotent, parsed-json check)
    if not _have_randinit(arm):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--random-init", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass
"""

new = """    # randinit control (idempotent, parsed-json check)
    if not _have_randinit(arm):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--random-init", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass
    # mommatch control (added 2026-10-05: 30M_b59 closed without it
    # because closeout raced ahead of watch_all controls; align the
    # randinit+mommatch 3-piece set for every b59 arm)
    if not _have_mommatch(arm):
        with open(log, "a") as lf:
            try:
                subprocess.run([PY, "-m", "rna_sc.probe", "--run-dir",
                                os.path.join(MNT, "runs", arm),
                                "--moment-matched", "17", "--device",
                                str(device)], cwd=ROOT, stdout=lf,
                               stderr=lf, timeout=14400)
            except subprocess.TimeoutExpired:
                pass
"""

assert old in src, "run_probe anchor not found"
src = src.replace(old, new)

old_helper = "def _have_randinit(arm: str) -> bool:"

new_helper = """def _have_mommatch(arm: str) -> bool:
    # True if a mommatch17 control row exists for this arm.
    mom_name = "%s_mommatch17" % arm
    for r in _final_rows(arm):
        if r.get("run") == mom_name:
            return True
    return False


def _have_randinit(arm: str) -> bool:"""

assert old_helper in src, "helper anchor not found"
src = src.replace(old_helper, new_helper)

open(P, "w").write(src)
print("patched closeout_b59.py: +_have_mommatch +mommatch block")
