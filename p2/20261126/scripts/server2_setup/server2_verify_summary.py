import json
from pathlib import Path

BASE = Path("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2")
LOGS = BASE / "logs/server2_setup"
OUT = BASE / "results/server2_setup"


def parse_manifest(path):
    rows = []
    for line in path.read_text().splitlines():
        sha256, relative = line.split("  ", 1)
        rows.append({"path": relative, "sha256": sha256})
    return rows


def verify_group(name, manifest_name, log_name, root, status_name=None):
    rows = parse_manifest(LOGS / manifest_name)
    log_lines = (LOGS / log_name).read_text().splitlines()
    ok_paths = {
        line[:-4] for line in log_lines
        if line.endswith(": OK")
    }
    expected_paths = {row["path"] for row in rows}
    failures = sorted(expected_paths - ok_paths)
    unexpected = sorted(ok_paths - expected_paths)
    for row in rows:
        path = root / row["path"]
        row["bytes"] = path.stat().st_size
        row["verified"] = row["path"] in ok_paths
    status = "PASS" if not failures and not unexpected else "FAIL"
    if status_name is not None:
        status_code = int((LOGS / status_name).read_text().strip())
        if status_code != 0:
            status = "FAIL"
    return {
        "group": name,
        "status": status,
        "file_count": len(rows),
        "verified_count": len(rows) - len(failures),
        "bytes": sum(row["bytes"] for row in rows),
        "failures": failures,
        "unexpected_ok_paths": unexpected,
        "files": rows,
    }


result = {
    "task": "X-server2",
    "source": "server1:/home/cunyuliu/rna-sc-p2 and server1:/teams/HoulabData_1788502323/liucunyu/rna-sc-p2",
    "destination": "server2",
    "method": "code rsync server1-to-server2; pre-existing assets retained and checked against server1 SHA-256 manifests",
    "groups": [
        verify_group("weights_and_data", "source_assets_sha256.txt", "assets_verify.log", BASE, "assets_verify.status"),
        verify_group("code_git", "source_code_sha256.txt", "code_verify.log", Path("/home/cunyuliu/rna-sc-p2")),
        verify_group("adapters", "source_adapters_sha256.txt", "adapters_verify.log", Path("/home/cunyuliu/rna-sc-p2")),
    ],
}
result["status"] = "PASS" if all(group["status"] == "PASS" for group in result["groups"]) else "FAIL"
with open(OUT / "transfer_verification.json", "w") as handle:
    json.dump(result, handle, indent=2)
print(json.dumps({key: value for key, value in result.items() if key != "groups"}, indent=2))
for group in result["groups"]:
    print(json.dumps({key: value for key, value in group.items() if key != "files"}, indent=2))
