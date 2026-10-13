P = "/home/cunyuliu/rna-sc/t437_gpu_watch.py"
s = open(P).read()

# Real peaks: 100M ~4.3GB, 300M ~8GB. Relax thresholds to 12/10GB,
# keep GPU order preferring the big free cards. Also fix early-return
# so a partial remaining list doesn't exit before all arms launch.
old = """ARMS = [
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_marscorpus",
     "logs/RNA-Sc-100M_s17_marscorpus.log", 26.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_marscorpus",
     "logs/RNA-Sc-300M_s17_marscorpus.log", 24.0),
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_rnacentral",
     "logs/RNA-Sc-100M_s17_rnacentral.log", 26.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_rnacentral",
     "logs/RNA-Sc-300M_s17_rnacentral.log", 24.0),
]"""
new = """ARMS = [
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_marscorpus",
     "logs/RNA-Sc-100M_s17_marscorpus.log", 12.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_marscorpus",
     "logs/RNA-Sc-300M_s17_marscorpus.log", 10.0),
    ("RNA-Sc-100M", "runs/RNA-Sc-100M_s17_rnacentral",
     "logs/RNA-Sc-100M_s17_rnacentral.log", 12.0),
    ("RNA-Sc-300M", "runs/RNA-Sc-300M_s17_rnacentral",
     "logs/RNA-Sc-300M_s17_rnacentral.log", 10.0),
]"""
assert old in s
s = s.replace(old, new)

# launched() gate: manifest.json may take minutes to appear; use a
# .launch marker written by launch() instead.
old2 = """def launched(run_dir):
    return os.path.exists(os.path.join(MNT, run_dir, "manifest.json"))"""
new2 = """def launched(run_dir):
    return os.path.exists(os.path.join(MNT, run_dir, ".launch"))


def mark_launched(run_dir):
    os.makedirs(os.path.join(MNT, run_dir), exist_ok=True)
    with open(os.path.join(MNT, run_dir, ".launch"), "w") as fh:
        fh.write(time.strftime("%F %T\\n"))"""
assert old2 in s
s = s.replace(old2, new2)

old3 = """    with open(log, "w") as lf:
        subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=lf,
                         start_new_session=True)
    print("[t437-watch] launched %s on GPU%d -> %s" %"""
new3 = """    with open(log, "w") as lf:
        subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=lf,
                         start_new_session=True)
    mark_launched(run_dir)
    print("[t437-watch] launched %s on GPU%d -> %s" %"""
assert old3 in s
s = s.replace(old3, new3)

# Fix the mid-loop early return: only exit when ALL arms launched.
old4 = """                remaining = remaining[1:]
                if not remaining:
                    return"""
new4 = """                remaining = remaining[1:]
                if not remaining:
                    break"""
assert old4 in s
s = s.replace(old4, new4)

open(P, "w").write(s)
print("t437 watcher v3: real thresholds 12/10GB, .launch marker, no early-exit")
