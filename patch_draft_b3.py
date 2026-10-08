"""DRAFT B3 双向黑盒 limitation 补丁 + S8 二期 backlog（2026-10-08）。

在 Limitations 的 B3（leakage residue）段后追加双向黑盒段；S8 接触图
二期 backlog 写入 TASKS 附注。
"""
DRAFT = "/home/cunyuliu/rna-sc/preprint/DRAFT_v1.md"

OLD = """- Architecture scope: the ladder is a single encoder recipe (width/
  depth scaling only); architecture×scale interactions are untested
  (RiNALMo-arch axis Q5 remains open), so scale claims are
  within-family by construction."""

NEW = """- Bidirectional corpus black-box (external-model comparisons, added
  2026-10-08): our family-split evaluation is defined over OUR cluster
  partition of RNAcentral R22; published models (RiNALMo, RNA-FM) were
  trained on corpus manifests we cannot audit, which almost certainly
  include sequences homologous to our evaluation families (their
  four-database mix spans the whole ncRNA space). The comparison is
  therefore doubly confounded in opposite directions: their corpus is a
  black box to our split (possible same-family exposure → their
  family-split numbers may be deflated or inflated, unknowable), and
  our split is a black box to their training (we cannot verify what
  they saw). Consequently all external-model rows are observational
  anchors, not controlled attributions; the controlled corpus axis is
  the replica arm (T4.3.5, RiNALMo-recipe corpus, B1 held-out removal
  — direction-valid for the "corpus organization" factor while the
  sequence-source factor remains approximated). We state this
  explicitly to preempt both directions of reviewer attack.
- Architecture scope: the ladder is a single encoder recipe (width/
  depth scaling only); architecture×scale interactions are untested
  (RiNALMo-arch axis Q5 remains open), so scale claims are
  within-family by construction."""


def main():
    code = open(DRAFT, encoding="utf-8").read()
    if "Bidirectional corpus black-box" in code:
        print("already patched")
        return
    if OLD not in code:
        print("ANCHOR NOT FOUND")
        return 1
    open(DRAFT, "w", encoding="utf-8").write(code.replace(OLD, NEW, 1))
    print("B3 bidirectional limitation added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
