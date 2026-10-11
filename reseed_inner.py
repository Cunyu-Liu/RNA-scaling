"""INNER 复测任务（被 reseed_b59_300vs650.py 以文件方式调用）。"""
import json
import sys

import torch

sys.path.insert(0, "/home/cunyuliu/rna-sc")
from rna_sc import probe as P

run_id, layer, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
model, ck = P.load_encoder("/mnt/cunyuliu/rna-sc/runs/" + run_id)
model = model.to("cuda:5").eval()
n_layers = ck["cfg"]["arch"]["n_layers"]
if layer >= n_layers:
    print(json.dumps({"run": run_id, "layer": layer, "seed": seed,
                      "error": "layer_oob"}))
    sys.exit(0)
X_all, y_tr = P.collect_states(model, "cuda:5", "family_validation", 8000,
                               n_layers)
X_tr = X_all[layer]
X_ev_all, y_ev = P.collect_states(model, "cuda:5", "family_test", 4000,
                                  n_layers)
X_ev = X_ev_all[layer]
# class 映射（照抄 probe main：train 的类字典，双方过滤）
classes = sorted(set(y_tr))
cls_map = {c: i for i, c in enumerate(classes)}
keep_tr = [i for i, c in enumerate(y_tr) if c in cls_map]
y_tri = [cls_map[c] for c in y_tr if c in cls_map]
X_tr = X_tr[keep_tr]
keep_ev = [i for i, c in enumerate(y_ev) if c in cls_map]
y_evi = [cls_map[c] for c in y_ev if c in cls_map]
X_ev = X_ev[keep_ev]
acc, f1 = P.probe_one_layer(X_tr, y_tri, X_ev, y_evi,
                            n_classes=len(classes),
                            device="cuda:5", layer_seed=seed)
print(json.dumps({"run": run_id, "layer": layer, "seed": seed,
                  "f1_macro": round(float(f1), 4)}))
