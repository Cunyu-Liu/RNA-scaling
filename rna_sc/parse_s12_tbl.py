"""Parse existing cmscan.tbl -> S12 decoupling index (rescue stage, v2).

Fixes vs v1:
  - cmscan tblout column order: target=CM name (parts[0]), query=SEQUENCE
    name (parts[2]) — opposite of cmsearch. Best hit per SEQUENCE by bits.
  - wait for the cmscan PROCESS to exit (poll pgrep), not file stability
    (cmscan buffers output; stability fired mid-run).
"""
from __future__ import annotations

import collections
import json
import os
import subprocess
import time

WORK = "/mnt/cunyuliu/rna-sc/data/s12_work"
TBL = os.path.join(WORK, "cmscan.tbl")
IDENT = "/mnt/cunyuliu/rna-sc/evidence/s12_family_identity.json"
OUT = "/mnt/cunyuliu/rna-sc/evidence/s12_decoupling_index.json"


def wait_cmscan_exit(max_wait: int = 86400):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        r = subprocess.run(["pgrep", "-f", "cmscan.*Rfam.cm"],
                           capture_output=True)
        if r.returncode != 0:
            time.sleep(30)
            r2 = subprocess.run(["pgrep", "-f", "cmscan.*Rfam.cm"],
                                capture_output=True)
            if r2.returncode != 0:
                return
        time.sleep(30)
    print("[parse] max_wait exceeded, parsing anyway", flush=True)


def main():
    print("[parse] waiting for cmscan process to exit ...", flush=True)
    wait_cmscan_exit()
    time.sleep(5)
    with open(IDENT) as fh:
        ident = json.load(fh)
    fams = list(ident["families"].items())

    best = {}
    with open(TBL) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 16:
                continue
            cm_name = parts[0]          # target = CM
            seqname = parts[2]          # query = sequence
            bits = float(parts[14])
            if seqname not in best or bits > best[seqname][1]:
                best[seqname] = (cm_name, bits)

    per_fam = collections.defaultdict(list)
    for seqname, (cmname, bits) in best.items():
        per_fam[seqname.rsplit("_", 1)[0]].append(bits)

    rows = {}
    for fam, meta in fams:
        key = fam.replace(" ", "_")
        bits = per_fam.get(key, [])
        if not bits:
            continue
        rows[fam] = {
            **meta,
            "n_seq_hit": len(bits),
            "mean_cm_bits": round(sum(bits) / len(bits), 2),
            "mean_cm_bits_max": round(max(bits), 2),
        }
    max_bits = max((r["mean_cm_bits"] for r in rows.values()), default=1.0)
    for fam, r in rows.items():
        norm_cm = r["mean_cm_bits"] / max_bits
        r["decoupling_index"] = round(
            r["mean_pairwise_identity"] / max(1e-6, norm_cm), 4)

    import datetime
    with open(OUT, "w") as fh:
        json.dump({
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "n_families": len(rows),
            "n_families_total": len(fams),
            "method": "identity/(cmscan mean bits normalized)",
        }, fh, indent=2)
    print("[S12] %d/%d families with CM hits" % (len(rows), len(fams)))
    top = sorted(rows.items(), key=lambda kv: -kv[1]["decoupling_index"])[:10]
    for fam, r in top:
        print("  %s DI=%.3f (id=%.3f cm=%.1f)" % (
            fam, r["decoupling_index"], r["mean_pairwise_identity"],
            r["mean_cm_bits"]))


if __name__ == "__main__":
    main()
