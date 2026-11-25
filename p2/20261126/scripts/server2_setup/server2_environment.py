import importlib
import json
import platform
import sys

import torch

modules = [
    "numpy", "pandas", "pyarrow", "scipy", "sklearn", "multimolecule",
    "transformers", "huggingface_hub", "tokenizers", "safetensors",
]
versions = {}
for name in modules:
    try:
        module = importlib.import_module(name)
        versions[name] = getattr(module, "__version__", "unknown")
    except Exception as exc:
        versions[name] = {"error": repr(exc)}
result = {
    "hostname": platform.node(),
    "platform": platform.platform(),
    "python": sys.version,
    "executable": sys.executable,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "torch": torch.__version__,
    "torch_file": torch.__file__,
    "torch_cuda_build": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "cuda_device_count": torch.cuda.device_count(),
    "packages": versions,
}
if torch.cuda.is_available():
    result["device_name"] = torch.cuda.get_device_name(0)
    result["device_capability"] = list(torch.cuda.get_device_capability(0))
with open("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/server2_setup/environment_versions.json", "w") as handle:
    json.dump(result, handle, indent=2)
print(json.dumps(result, indent=2))
