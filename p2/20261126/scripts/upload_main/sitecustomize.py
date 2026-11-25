import os
import sys

PROJECT = "/home/cunyuliu/rna-sc-p2"
CODE = os.path.join(PROJECT, "code_git")
if CODE not in sys.path:
    sys.path.insert(0, CODE)

import rna_sc.config

rna_sc.config.SPLIT_8080 = os.path.abspath(os.environ.get(
    "RNA_SC_SPLIT_8080",
    "/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data/"
    "release22_split_8080.parquet",
))
