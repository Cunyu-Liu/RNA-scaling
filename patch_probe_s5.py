import argparse
import os
import sys

SRC = "/home/cunyuliu/rna-sc/rna_sc/probe.py"


def read_src():
    with open(SRC) as f:
        return f.read()


def patch_arg(src):
    old = """    ap.add_argument("--random-init", type=int, default=None,
                    help="S4 control: probe a RANDOM-INIT model with this "
                         "seed using the architecture from --run-dir; "
                         "excludes the inductive-bias/overparam explanation")
"""
    new = """    ap.add_argument("--random-init", type=int, default=None,
                    help="S4 control: probe a RANDOM-INIT model with this "
                         "seed using the architecture from --run-dir; "
                         "excludes the inductive-bias/overparam explanation")
    ap.add_argument("--moment-matched", type=int, default=None,
                    help="S5 control: probe a RANDOM-INIT model whose "
                         "weights are moment-matched per-parameter-tensor "
                         "to the trained run in --run-dir (seed controls "
                         "the randomization before matching); excludes "
                         "the good-init/weight-statistics explanation")
"""
    assert src.count(old) == 1, "arg block not found"
    return src.replace(old, new)


def patch_body(src):
    old = """    if args.random_init is not None:
        import torch as _t
        _t.manual_seed(args.random_init)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        ck = dict(ck)
        ck["nt"] = 0
"""
    new = """    if args.random_init is not None:
        import torch as _t
        _t.manual_seed(args.random_init)
        mcfg = ck["cfg"]["arch"]
        model = RNAMLMEncoder(d_model=mcfg["d_model"],
                              n_layers=mcfg["n_layers"],
                              n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
        ck = dict(ck)
        ck["nt"] = 0
    if args.moment_matched is not None:
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
    assert src.count(old) == 1, "body block not found"
    return src.replace(old, new)


def patch_name(src):
    old = """    print("classes=%d train=%d eval=%d" % (len(classes), len(y_tri), len(y_evi)))"""
    new = """    print("classes=%d train=%d eval=%d" % (len(classes), len(y_tri), len(y_evi)))
    print("model mode: random-init=%s moment-matched=%s" %
          (args.random_init, args.moment_matched))"""
    assert src.count(old) == 1, "name print not found"
    return src.replace(old, new)


def patch_run_name(src):
    old = """               ("_randinit%s" % args.random_init if args.random_init
                else "") +"""
    new = """               ("_randinit%s" % args.random_init if args.random_init
                else "") +
               ("_mommatch%s" % args.moment_matched if
                args.moment_matched is not None else "") +"""
    assert src.count(old) == 1, "run-name block not found"
    return src.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write patch (default: dry-run verify)")
    args = ap.parse_args()
    src = read_src()
    for fn in (patch_arg, patch_body, patch_name, patch_run_name):
        src = fn(src)
    if args.apply:
        with open(SRC, "w") as f:
            f.write(src)
        print("patched (written)")
    else:
        import ast
        ast.parse(src)
        print("dry-run: all 4 patches applied to text, syntax OK "
              "(use --apply to write)")


if __name__ == "__main__":
    main()
