import ast

SRC = "/home/cunyuliu/rna-sc/rna_sc/probe.py"

BUGGY = """    if args.moment_matched is not None:
        import torch as _t
        _t.manual_seed(args.moment_matched)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        with _t.no_grad():
            src_sd = model.state_dict()
            for k, v in model.state_dict().items():
                if v.is_floating_point() and v.numel() > 1:
                    std = v.std()
                    src_sd[k].copy_(v * (1.0 / std) if std > 0 else v)
            model.load_state_dict(src_sd)
        ck = dict(ck)
        ck["nt"] = 0
"""

FIXED = """    if args.moment_matched is not None:
        import torch as _t
        # capture TRAINED per-tensor moments BEFORE replacing the model
        trained_sd = {k: v.clone() for k, v in model.state_dict().items()
                      if v.is_floating_point()}
        _t.manual_seed(args.moment_matched)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        with _t.no_grad():
            new_sd = model.state_dict()
            n_matched = 0
            for k, v in new_sd.items():
                if not v.is_floating_point() or v.numel() < 2:
                    continue
                t = trained_sd[k]
                tm, ts = t.mean(), t.std()
                vm, vs = v.mean(), v.std()
                if ts > 0 and vs > 0:
                    v.copy_((v - vm) / vs * ts + tm)
                    n_matched += 1
            model.load_state_dict(new_sd)
            print("moment-matched %d tensors to trained moments" %
                  n_matched)
        ck = dict(ck)
        ck["nt"] = 0
"""


def main():
    with open(SRC) as f:
        src = f.read()
    assert src.count(BUGGY) == 1, "buggy block not found (count=%d)" % \
        src.count(BUGGY)
    src = src.replace(BUGGY, FIXED)
    ast.parse(src)
    with open(SRC, "w") as f:
        f.write(src)
    print("fixed + syntax OK (trained-moment capture before re-init)")


if __name__ == "__main__":
    main()
