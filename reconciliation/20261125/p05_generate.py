from pathlib import Path
import csv
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = Path('/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc')
DRAFT = ROOT / 'delta_20261014/DRAFT_v1_final_20261014.md'
EVIDENCE = ROOT / 'eval_evidence_logs/evidence'
EVIDENCE_NAMES = [
    'covariation_test.json',
    'covariation_test_650M.json',
    'readout_heads_v3.json',
    'pair_probe_v4.json',
    'pair_probe_baseline.json',
    'p5_shuffle_threshold.json',
    'p4_loo_test.json',
    'p5rns_b59_verdict.json',
    'b59_random_delta.json',
    'b59_reseed_300vs650.json',
    's7_structure_budget_matrix.json',
    'hypothesis_evidence_audit.json',
]
INPUTS = [DRAFT] + [EVIDENCE / name for name in EVIDENCE_NAMES]
lines = DRAFT.read_text(encoding='utf-8').splitlines()
assert len(lines) == 1078, len(lines)


def excerpt(start, end=None):
    end = end or start
    return ' '.join(lines[i - 1].strip() for i in range(start, end + 1))


def quote(start, end=None):
    end = end or start
    return '\n'.join(f'> L{i}: {lines[i - 1]}' for i in range(start, end + 1))


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


abstract = '\n'.join(lines[21:75])
abstract_whitespace_words = len(abstract.split())
abstract_regex_words = len(re.findall(r"\b[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*\b", abstract))
abstract_numeric_tokens = len([token for token in abstract.split() if re.search(r'\d', token)])
abstract_numeric_literals = len(re.findall(r'(?<![A-Za-z])[-+−]?\d+(?:\.\d+)?(?:[x×%]|\s?pp|\s?B|\s?M)?', abstract))

contradictions = [
    {
        'id': 'C1',
        'locations': 'L598-L622 vs L404-L526; related L624-L665',
        'verdict': '旧四证据汇聚及 largely not yet learned 作废；终判为配对知识存在，线性读出与候选配对求解受限。',
        'rewrite': 'L598-L622 整体移出主文；§4.4 主文保留 L404-L526 的新证据链及 matched-prior 限定。',
        'evidence': 'covariation_test.json; covariation_test_650M.json; readout_heads_v3.json; pair_probe_v4.json; pair_probe_baseline.json',
    },
    {
        'id': 'C2',
        'locations': 'corrected L345-L352/L362-L368/L386-L402; superseded L598-L612',
        'verdict': '1M −0.047 等旧审计值作废；1M +0.007 为修正后的 own-best trained−randinit，不能与 TS0−trigram +0.001 混用。',
        'rewrite': '主文只留修正版及明确比较基准；旧值仅进 provenance。',
        'evidence': 'DRAFT L345-L352/L364/L386-L393; old block L598-L612',
    },
    {
        'id': 'C3',
        'locations': 'Abstract L20-L75 (body L22-L75)',
        'verdict': f'超载：{abstract_whitespace_words} whitespace words / {abstract_regex_words} regex words；{abstract_numeric_tokens} 个含数字 token，远超 15+ 门槛。',
        'rewrite': '压缩 L22-L75；矩阵、probe-seed retest 和逐尺度增量移回 Results，删除无条件 corpus-dominance 表述。',
        'evidence': 'DRAFT Abstract L22-L75; p05_generate.py deterministic counts',
    },
    {
        'id': 'C4',
        'locations': '§5.1 L959-L997; strong account L961-L980; revision L981-L997',
        'verdict': '强 finite-channel 账户已证伪，仅 family-classification channel 保留有限饱和账户；RNS 与 P5 non-rRNA 随预算移动。',
        'rewrite': '将 L981-L997 升格为 Q6 Results 主结果，建议置于现 §4.5 后；§5.1 只留解释与回指。',
        'evidence': 'p5rns_b59_verdict.json verdict/channels/matrix; s7_structure_budget_matrix.json budget_effect_monotone_note',
    },
    {
        'id': 'C5',
        'locations': 'M L153-L157/L747-L760/L798-L801; P5b L769-L774; P1 L776-L783; P4 L791-L801; downstream L913-L915',
        'verdict': '统一为“链 b 干预支持、定量形式证伪、post-hoc grade-B”；P5b 证伪间隙扩大预测，P4 证伪简单定量映射。',
        'rewrite': '删除整体 B→A− 和 survives qualitatively 的未限定表述；叙事主线及 §4.11 同步降级为待检验账户。',
        'evidence': 'p5_shuffle_threshold.json predictions/scales; p4_loo_test.json mean_err_1/mean_err_2; DRAFT P1 L776-L783',
    },
]

blacklist_hits = [
    {'id': 'BL-001', 'rule': 'not yet learned', 'match_type': 'exact', 'start': 619, 'end': 622, 'context': '作废旧审计的终句', 'action': '主文删除；如要求全文件字面清零，旧原文应归档到 DRAFT 外部而非保留在附录。'},
    {'id': 'BL-002', 'rule': 'zero-gain', 'match_type': 'exact', 'start': 619, 'end': 622, 'context': '旧 S7 四证据汇聚', 'action': '删除旧 S7 zero-gain 定性。'},
    {'id': 'BL-003', 'rule': 'corpus composition dominates（无条件式）', 'match_type': 'exact_unqualified', 'start': 133, 'end': 134, 'context': 'Introduction contribution (e)', 'action': '改为有模型家族、协议及外部观察性限制的结论。'},
    {'id': 'BL-004', 'rule': 'corpus composition dominates（无条件式）', 'match_type': 'semantic_unqualified', 'start': 47, 'end': 49, 'context': 'Abstract: corpus dominates parameters', 'action': '删除抽象中的普遍支配断言；改为受控 corpus-swap 的尺度依赖结果。'},
    {'id': 'BL-005', 'rule': 'corpus composition dominates（无条件式）', 'match_type': 'semantic_unqualified', 'start': 158, 'end': 160, 'context': 'Narrative spine: corpus story, not parameter story', 'action': '降级为本受控家族/预算内的解释，不作普遍二分。'},
    {'id': 'BL-006', 'rule': 'corpus composition dominates（无条件式）', 'match_type': 'semantic_unqualified', 'start': 731, 'end': 733, 'context': '§4.5: scaling is a corpus story', 'action': '保留 corpus_arm_verdict 的尺度梯度，删除普遍化口号。'},
    {'id': 'BL-007', 'rule': 'corpus composition dominates（无条件式）', 'match_type': 'heading_shorthand', 'start': 898, 'end': 906, 'context': '§4.10 标题及外部模型对比', 'action': '标题标明 external observational contrast；与 §6 L1008-L1023 黑箱限定同置。'},
    {'id': 'BL-008', 'rule': '10M valley', 'match_type': 'exact', 'start': 248, 'end': 248, 'context': '§4.1 标题 systematic', 'action': '改为 mean-level attrition at 10M，避免 systematic/per-seed universal 暗示。'},
    {'id': 'BL-009', 'rule': '10M valley', 'match_type': 'exact', 'start': 257, 'end': 258, 'context': '§4.1 650M era', 'action': '保留 three-seed mean 限定，替换黑名单标签。'},
    {'id': 'BL-010', 'rule': '10M valley', 'match_type': 'exact', 'start': 796, 'end': 797, 'context': 'P4 regime transition', 'action': '改为 10M attrition regime。'},
    {'id': 'BL-011', 'rule': '10M valley', 'match_type': 'exact', 'start': 946, 'end': 949, 'context': 'Discussion；虽有 three-seed mean 限定仍命中字面门', 'action': '替换标签，保留 2/3 seeds negative 与非逐种子普遍限定。'},
    {'id': 'BL-012', 'rule': '10M valley', 'match_type': 'semantic_variant', 'start': 29, 'end': 32, 'context': 'Abstract: 10M attrition valley', 'action': '同步替换，避免只清精确字符串而留下同义标签。'},
    {'id': 'BL-013A', 'rule': 'all 3 seeds', 'match_type': 'near_variant_probe_seed', 'start': 298, 'end': 302, 'context': '精确式 0 命中；此处为 3/3 probe seeds', 'action': '明确写成 3/3 probe seeds (29/43/61)，不得暗示三个训练种子。'},
    {'id': 'BL-013B', 'rule': 'all 3 seeds', 'match_type': 'near_variant_probe_seed', 'start': 57, 'end': 58, 'context': 'Abstract 的 across 3 seeds 与 L298-L302 是同一次 probe-seed retest', 'action': '保留 probe-seed 限定并压缩摘要，不得暗示三个训练种子。'},
    {'id': 'BL-014', 'rule': 'finite channel', 'match_type': 'lexical_variant_strong_account', 'start': 968, 'end': 976, 'context': 'finite task-information channel 是 leading explanation', 'action': '强账户已证伪，撤下 leading explanation。'},
    {'id': 'BL-015', 'rule': 'finite channel', 'match_type': 'exact_preregistered_history', 'start': 977, 'end': 980, 'context': '原预注册判据；有限通道账户 closes', 'action': '如保留历史，只放 Methods/provenance 且明确后续证伪；字面清零需改名。'},
    {'id': 'BL-016', 'rule': 'finite channel', 'match_type': 'exact_negated', 'start': 981, 'end': 984, 'context': 'REFUTED 否定语境，仍会被机械检索命中', 'action': '科学结论保留；P1 若执行字面零命中，改写为 strong account is refuted。'},
    {'id': 'BL-017', 'rule': 'finite channel', 'match_type': 'exact_limited_residual', 'start': 988, 'end': 991, 'context': '仅 family-Delta channel 的残余账户', 'action': '改成 family-classification-channel-specific saturation，删除通用标签。'},
]

zero_rules = {
    'all 3 seeds（精确式）': r'(?i)all\s+3\s+seeds',
    '机制已证明': r'机制已证明',
    'APE/RIPE（独立词，忽略大小写）': r'(?i)\b(?:APE|RIPE)\b',
}
full_text = '\n'.join(lines)
zero_counts = {name: len(re.findall(pattern, full_text)) for name, pattern in zero_rules.items()}
assert all(count == 0 for count in zero_counts.values()), zero_counts
assert len(re.findall(r'(?i)not yet learned', full_text)) == 1
assert len(re.findall(r'(?i)zero-gain', full_text)) == 1
assert len(re.findall(r'(?i)corpus composition dominates', full_text)) == 1
assert len(re.findall(r'(?i)10M valley', full_text)) == 4
assert len(re.findall(r'(?i)finite-channel', full_text)) == 3

parts = [
    '# P0.5 — DRAFT 五条内部矛盾冻结裁决\n',
    '- 只读对象：`delta_20261014/DRAFT_v1_final_20261014.md`，共 1078 行；行号以该文件为准。',
    '- 裁决原则：较晚、直接干预或 probe-free 的证据优先；旧审计只作 provenance，不与终判并列为当前结论。',
    '- 本任务未修改 DRAFT、账本、evidence 或交接文档。机读版见 `p05_draft_contradictions.csv`；输入哈希见 `p05_draft_contradictions.manifest.json`。\n',
    '## C1 — §4.4 旧“未学会/四证据汇聚”账户作废\n',
    '**位置**：旧块 L598-L622；新证据链 L404-L526，另有 L624-L665 的独立 forward/interpretability 支持。\n',
    '**旧表述原文（精确摘录）**：\n',
    quote(598, 608),
    quote(614, 622),
    '**终判证据**：COV−CTRL 从 1M 的 0.00415 增至 650M 的 0.09572，且 650M randinit 为 0.00004（`covariation_test.json` 与 `covariation_test_650M.json` 的 `cov_minus_ctrl`）；Partner-Oracle 为 0.9996/0.9992/0.9983（`readout_heads_v3.json: models.{30M,100M,650M}.partner_oracle`）；pair AUC 为 0.9319/0.9397/0.9524，但 model-free `dist_ident` 已达 0.922（`pair_probe_v4.json`、`pair_probe_baseline.json`）。因此只能声称配对信息存在且净增量有限，不能声称结构预测已解决。\n',
    '**裁决**：L619-L622 的 “S7 zero-gain / Four-way convergence / structure information is largely not yet learned” 以及 L614-L618 的 “pretraining contributes ≈0” 作为跨读出方式的全任务终判，均被后续直接证据推翻；≤100M own-best 线性读出近零这一局部结果仍保留。终判统一为：**配对知识在表示与 forward pass 中存在；线性 readout 严重低读，候选配对生成/匹配求解器是结构预测缺口；raw pair probe 还必须扣除 distance+composition prior。**\n',
    '**重写落点**：§4.4 主文保留 L404-L526 的 COV → remote readout → Oracle/pair probe → matched-prior correction；L598-L622 整段移至 provenance，不在主文保留“旧结论仍有效”的视觉并列。\n',
    '## C2 — superseded 数字与修正版并存\n',
    '**行号清单**：修正说明 L345-L352；当前三数据集表 L362-L368；own-best 修正版 L386-L393；重定性 L395-L402；旧值块 L598-L612（核心旧数字 L606-L608）。\n',
    quote(345, 352),
    quote(384, 393),
    quote(598, 608),
    '**裁决**：旧 `1M −0.047 / 10M −0.010 / 30M −0.000 / 100M +0.013 / 650M +0.021` 不再作为当前结果。修正后的 own-best trained−randinit 是 `1M +0.007, 10M −0.001, 30M −0.003, 100M +0.004`。注意 L364 的 1M `+0.001` 是 **TS0−trigram**，与 L349/L387 的 **own-best trained−randinit +0.007** 比较基准不同，二者都不可混写。\n',
    '**重写落点**：§4.4 主文只保留修正版及显式 comparator；旧向量整体移 provenance，并标注 weak training subset 与 metric mismatch 已修正。\n',
    '## C3 — Abstract 超载\n',
    '**位置**：标题 L20，正文 L22-L75。代表摘录：\n',
    quote(29, 41),
    quote(47, 60),
    f'**实测**：空白分词 **{abstract_whitespace_words} words**；连字符/撇号合并的 regex 口径 **{abstract_regex_words} words**。含至少一个数字的空白 token **{abstract_numeric_tokens} 个**；数值字面量 regex **{abstract_numeric_literals} 个**。主报告采用前一种词数与“含数字 token”口径，后两者用于复核，避免把 `0.4491±0.015` 等如何切分隐藏起来。\n',
    '**裁决**：符合“约 550 词、15+ 数字”的超载预期。当前摘要混入完整预算矩阵、probe-seed retest、多个对照增量及机制解释，且 L47-L49 仍含无条件 corpus-dominance 断言。\n',
    '**重写落点**：重写 Abstract L22-L75，只保留研究设计、主要标度/协议结论和最关键的受控预算/语料结果；逐尺度矩阵回到 §4.1/§4.5/§4.7，probe-seed 细节回到 §4.1，结构读出回到 §4.4。\n',
    '## C4 — §5.1 强 finite-channel 已证伪；修订账户升格 Q6 主结果\n',
    '**位置**：§5.1 全段 L959-L997；旧强账户 L961-L980，其中 leading explanation 在 L968-L976；预注册判据 L977-L980；终判与修订账户 L981-L997。\n',
    quote(961, 983),
    quote(984, 997),
    '**裁决**：`p5rns_b59_verdict.json: verdict` 明确 “TWO of three channels MOVE … family-channel story, not a global representation story”；`matrix` 给出 non-rRNA budget delta 0.1093/0.2908/0.3629，RNS delta −0.0105/−0.0313/−0.0243。故 “Data quantity is excluded” 与 “finite task-information channel is the leading explanation” 只能保留为被检验并否决的历史账户； family-classification channel 可保留有限饱和解释，不可外推为全局表示上限。\n',
    '**Q6 升格落点建议**：在现 §4.5 后、现 §4.6 前新增 Results 小节 **“Budget moves representation channels: the 30M plateau is family-channel-specific 【Q6】”**。将 L981-L997 的判据、三通道矩阵和修订结论前移为该节主体；§5.1 只保留一段 Discussion 解释与回指。S7 的 +0.09/+0.85/+1.87pp 用 `s7_structure_budget_matrix.json: budget_effect_monotone_note` 作交叉支持，不重复堆表。\n',
    '## C5 — 假说 M：链 b 支持不等于三链定量账户成立\n',
    '**所有直接/延伸位置**：叙事主线 L153-L157；M 与三链账户 L747-L760；P5b L769-L774；P1/chain b L776-L783；P3/P4 及总判 L785-L801；§4.11 延伸账户 L913-L915。关键原文：\n',
    quote(153, 157),
    quote(747, 760),
    quote(762, 774),
    quote(776, 783),
    quote(791, 801),
    '**裁决**：统一措辞冻结为 **“链 b 干预支持、定量形式证伪、post-hoc grade-B”**。P1 的 de-rRNA 干预支持 chain b，但不能把整体三链账户升为 A−；P5b 的 gap 从 0.9401 降至 0.8086（`p5_shuffle_threshold.json: scales.30M.gap` 与 `scales.650M.gap`）证伪“随规模扩大”的预测；P4 的 `mean_err_1=0.3046`、`mean_err_2=0.7447`（`p4_loo_test.json`）否定简单线性/capacity-shift 定量形式。\n',
    '**重写落点**：L153-L157 改为待检验解释；L747-L760 保留 post-hoc grade-B 标签并预告两个证伪分支；L781-L783 删除整体 `B → A−`；L798-L801 用上述冻结句替换 “survives qualitatively”；L913-L915 改为 “consistent with the still-post-hoc account”，不得当作独立验证。\n',
    '## 对账顺带发现的异常（不并入五条裁决）\n',
    '- `pair_probe_v4.json` 的 100M AUC 是 **0.9397**，DRAFT L488/L510 写 **0.938**；不是四位小数直接舍入，需要 P1 回账本确认，不能强行凑数。',
    '- `b59_random_delta.json` 仍只含 30M/100M/300M，且 `pending=["650M"]`；DRAFT L823-L829、L990-L991 却写四尺度及 650M −1.85pp。Q6 的 RNS/P5 主裁决有独立 evidence 支持，但该 650M random cell 需另补权威账本/evidence 后才能保留。',
    '- `hypothesis_evidence_audit.json` 的 M 项仍写 P2/P3/P4 在途和 “主链证实”，属于较早审计状态；本裁决采用较晚的 `p4_loo_test.json` 与 `p5_shuffle_threshold.json`，不沿用其整体升级措辞。',
    '- `b59_reseed_300vs650.json` 的键为模型训练 run、内层键 29/43/61 为 probe seeds；它支持 L298-L302 的 probe-head retest，不构成三个独立训练种子。\n',
]
(OUT / 'p05_draft_contradictions.md').write_text('\n'.join(parts), encoding='utf-8')

bparts = [
    '# P0.5 — DRAFT 黑名单检索门命中清单\n',
    '- 范围：DRAFT 全文 L1-L1078；大小写不敏感；APE/RIPE 使用独立词边界，避免误伤普通子串。',
    '- 当前基线：精确字面命中 10 处；另列 8 处同义、跨行或否定语境变体，共 18 条记录。否定语境也列入，因为机械检索不会因 “REFUTED” 自动豁免。',
    '- P1 复核建议同时报告 `exact=0` 与 `semantic review=0`。若旧原文移入同一文件的 provenance 附录，`not yet learned` 等仍会字面命中；若要求全文件清零，应把旧原文归档到 DRAFT 外部。',
    '- 机读版：`p05_blacklist_hits.csv`；输入哈希：`p05_blacklist_hits.manifest.json`。\n',
    '## 命中明细\n',
]
for hit in blacklist_hits:
    bparts.extend([
        f"### {hit['id']} — {hit['rule']} — L{hit['start']}" + (f"-L{hit['end']}" if hit['end'] != hit['start'] else ''),
        f"- 类型：`{hit['match_type']}`；语境：{hit['context']}。",
        f"- 处置：{hit['action']}",
        quote(hit['start'], hit['end']),
        '',
    ])
bparts.append('## 精确零命中规则\n')
for name, count in zero_counts.items():
    bparts.append(f'- `{name}`：**{count} 命中**。')
bparts.extend([
    '',
    '## P1 清零复核口径\n',
    '1. 逐字重扫 `not yet learned`、`zero-gain`、`corpus composition dominates`、`10M valley`、`all 3 seeds`、`finite-channel`、`机制已证明`、独立词 `APE/RIPE`。',
    '2. 人工复查本文件的 8 条扩展变体，尤其是 Abstract 的 `corpus dominates parameters`、`10M attrition valley`、`across 3 seeds` 和 Results 的 `3/3 seeds`。',
    '3. `finite-channel` 的 L981-L984 虽为证伪句，仍是字面命中；按项目选择的“全文零命中”或“肯定式零命中”口径处理，并在复核结果中注明。',
    '4. 不把 probe-seed retest 改成训练种子重复，也不为清词而删除必要的否定结果；可改写标签并保留科学含义。',
])
(OUT / 'p05_blacklist_hits.md').write_text('\n'.join(bparts), encoding='utf-8')

with (OUT / 'p05_draft_contradictions.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['id', 'locations', 'verdict', 'rewrite', 'evidence'])
    writer.writeheader()
    writer.writerows(contradictions)

with (OUT / 'p05_blacklist_hits.csv').open('w', encoding='utf-8', newline='') as handle:
    fieldnames = ['id', 'rule', 'match_type', 'lines', 'excerpt', 'context', 'action']
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for hit in blacklist_hits:
        writer.writerow({
            'id': hit['id'],
            'rule': hit['rule'],
            'match_type': hit['match_type'],
            'lines': f"L{hit['start']}-L{hit['end']}",
            'excerpt': excerpt(hit['start'], hit['end']),
            'context': hit['context'],
            'action': hit['action'],
        })

input_records = [
    {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
    for path in INPUTS
]
for stem in ['p05_draft_contradictions', 'p05_blacklist_hits']:
    manifest = {
        'task': 'P0.5',
        'source_draft': str(DRAFT),
        'script': str(OUT / 'p05_generate.py'),
        'inputs': input_records,
        'outputs': [
            {'path': str(OUT / f'{stem}.md'), 'sha256': sha256(OUT / f'{stem}.md')},
            {'path': str(OUT / f'{stem}.csv'), 'sha256': sha256(OUT / f'{stem}.csv')},
        ],
    }
    (OUT / f'{stem}.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print(json.dumps({
    'draft_lines': len(lines),
    'abstract_whitespace_words': abstract_whitespace_words,
    'abstract_regex_words': abstract_regex_words,
    'abstract_numeric_tokens': abstract_numeric_tokens,
    'abstract_numeric_literals': abstract_numeric_literals,
    'blacklist_records': len(blacklist_hits),
    'zero_rules': zero_counts,
    'output_dir': str(OUT),
}, ensure_ascii=False, indent=2))
