"""watch_all main_arm 正则扩展补丁（2026-10-08）：

把 randinit/mommatch 自动对照的适用范围从 (_b59)? 扩到
(_b59|_rfamcap|_rinalmocorpus)? —— 三个语料臂家族（5.9B / Rfam 富集 /
RiNALMo 语料复刻）DONE 后自动获得同款对照三件套。
（rw1 臂刻意保持排除——重加权臂的对照语义不同，纪律不变。）
"""
import sys

SRC = "/home/cunyuliu/rna-sc/rna_sc/watch_all.py"

OLD = 'main_arm = re.fullmatch(r"RNA-Sc-(1M|10M|30M|100M|300M|650M)_s17(_b59)?", base)'
NEW = 'main_arm = re.fullmatch(r"RNA-Sc-(1M|10M|30M|100M|300M|650M)_s17(_b59|_rfamcap|_rinalmocorpus)?", base)'


def main():
    code = open(SRC, encoding="utf-8").read()
    if "_rinalmocorpus" in code:
        print("patch already applied")
        return 0
    if OLD not in code:
        print("ANCHOR NOT FOUND — abort")
        return 1
    code = code.replace(OLD, NEW, 1)
    open(SRC, "w", encoding="utf-8").write(code)
    import py_compile
    py_compile.compile(SRC, doraise=True)
    print("PATCH OK + syntax passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
