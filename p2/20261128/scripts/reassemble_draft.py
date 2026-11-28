#!/usr/bin/env /usr/bin/python3
"""Reassemble DRAFT_v2 from sections (order + --- separators + header comment)."""
from pathlib import Path
ROOT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/论文重写_P1_20261125")
SEC = ROOT / "sections"
ORDER = ["sec0_abstract","sec1_intro","sec2_related","sec3_methods","sec41_q1","sec42_q2",
         "sec43_q3","sec44_q4","sec45_q5","sec46_q6","sec47_crosscut","sec5_discussion",
         "sec6_limitations","appendix_provenance"]
draft_path = ROOT / "DRAFT_v2_20261125.md"
header = draft_path.read_text().split("\n", 1)[0]
assert header.startswith("<!-- DRAFT_v2_20261125")
texts = []
for name in ORDER:
    t = (SEC / f"{name}.md").read_text()
    if not t.endswith("\n"):
        t += "\n"
    texts.append(t)
new = header + "\n\n" + "\n---\n\n".join(texts)
draft_path.write_text(new)
# byte-consistency verification: each section appears verbatim
lines = new.split("\n")
ok = True
for name, t in zip(ORDER, texts):
    if t.rstrip("\n") not in new:
        print("MISSING", name); ok = False
print("REASSEMBLED", len(new), "chars;", "sections", len(ORDER), "; byte-consistent", ok)
# report section heading line numbers (for assert boundaries)
import re
for i, l in enumerate(lines, 1):
    if re.match(r"^#{1,3} ", l) and ("4." in l or l.startswith("# ") or "Abstract" in l):
        print(i, l[:70])