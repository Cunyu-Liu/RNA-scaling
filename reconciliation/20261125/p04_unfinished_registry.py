#!/usr/bin/env python3
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BACKUP = Path('/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc')
OUT = Path('/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125')
EVAL = BACKUP / 'eval_evidence_logs/eval'
RUNS = BACKUP / 'runs_final2_ckpt/runs'
ARMS = [
    'RNA-Sc-30M_s17_marscorpus',
    'RNA-Sc-100M_s17_marscorpus',
    'RNA-Sc-300M_s17_marscorpus',
    'RNA-Sc-30M_s17_rnacentral',
    'RNA-Sc-100M_s17_rnacentral',
    'RNA-Sc-300M_s17_rnacentral',
    'RNA-Sc-30M_s17_rfamcap',
    'RNA-Sc-100M_s17_rfamcap',
]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def file_record(path):
    return {
        'path': str(path),
        'size_bytes': path.stat().st_size,
        'sha256': sha256(path),
    }


def main():
    generated_at = datetime.now().astimezone().isoformat(timespec='seconds')
    eval_files = sorted(EVAL.glob('*.jsonl'))
    search_matches = []
    probe_counts = Counter()
    task_counts = defaultdict(Counter)
    ckpt_nts = defaultdict(set)
    evidence_lines = defaultdict(list)
    parse_errors = []
    for path in eval_files:
        raw = path.read_bytes()
        lowered = raw.lower()
        for term in (b'marscorpus', b'rnacentral'):
            start = 0
            while True:
                index = lowered.find(term, start)
                if index < 0:
                    break
                search_matches.append({'file': str(path), 'term': term.decode(), 'byte_offset': index})
                start = index + len(term)
        if path.name.startswith('._'):
            continue
        with path.open('r', encoding='utf-8') as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    parse_errors.append({'file': str(path), 'line': line_number, 'error': str(exc)})
                    continue
                run = str(row.get('run', ''))
                if 'rfamcap' not in run:
                    continue
                task = str(row.get('task', ''))
                probe_counts[run] += 1
                task_counts[run][task] += 1
                if 'ckpt_nt' in row:
                    ckpt_nts[run].add(row['ckpt_nt'])
                evidence_lines[(run, task, path.name)].append(line_number)

    inventory = {}
    for arm in ARMS:
        directory = RUNS / arm
        checkpoints = sorted(directory.glob('*.pt')) if directory.is_dir() else []
        inventory[arm] = {
            'directory': str(directory),
            'directory_exists': directory.is_dir(),
            'checkpoint_count': len(checkpoints),
            'checkpoints': [
                {'path': str(path), 'size_bytes': path.stat().st_size}
                for path in checkpoints
            ],
            'directory_entries': sorted(path.name for path in directory.iterdir()) if directory.is_dir() else [],
        }

    status_path = BACKUP / 'status.md'
    status_lines = status_path.read_text(encoding='utf-8').splitlines()
    status_refs = {}
    for arm in ARMS:
        for line_number, line in enumerate(status_lines, 1):
            if f'**{arm}**' in line:
                status_refs[arm] = {'line': line_number, 'text': line}
    ledger_path = BACKUP / 'ledger.jsonl'
    ledger_lines = ledger_path.read_text(encoding='utf-8').splitlines()
    ledger_tail = [
        {'line': line_number, 'record': json.loads(ledger_lines[line_number - 1])}
        for line_number in range(max(1, len(ledger_lines) - 4), len(ledger_lines) + 1)
    ]
    ledger_unfinished_mentions = [
        {'line': line_number, 'text': line}
        for line_number, line in enumerate(ledger_lines, 1)
        if 'marscorpus' in line.lower() or 'rnacentral' in line.lower()
    ]

    manifests = [
        RUNS / arm / 'manifest.json'
        for arm in (
            'RNA-Sc-100M_s17_marscorpus',
            'RNA-Sc-300M_s17_marscorpus',
            'RNA-Sc-30M_s17_rfamcap',
            'RNA-Sc-100M_s17_rfamcap',
        )
    ]
    manifest_data = {str(path): json.loads(path.read_text(encoding='utf-8')) for path in manifests}
    inputs = eval_files + [status_path, ledger_path] + manifests

    assert not search_matches, 'MARS/RNAcentral probe matches appeared; static registry wording needs revision'
    assert not parse_errors, f'JSONL parse errors: {parse_errors}'
    assert inventory['RNA-Sc-100M_s17_marscorpus']['checkpoint_count'] == 4
    assert inventory['RNA-Sc-300M_s17_marscorpus']['checkpoint_count'] == 2
    assert all(inventory[f'RNA-Sc-{size}_s17_rnacentral']['checkpoint_count'] == 0 for size in ('30M', '100M', '300M'))
    assert task_counts['RNA-Sc-30M_s17_rfamcap']['bpRNA paired-position'] == 0
    assert task_counts['RNA-Sc-100M_s17_rfamcap']['bpRNA paired-position'] == 23

    rows = [
        {
            '未完成臂/证据缺口': 'MARS 30M（训练与探针均未完成；status.md 无此行）',
            '权重位置': f"{RUNS / 'RNA-Sc-30M_s17_marscorpus'}：目录为空，无 ckpt",
            '可复测性': '不可从备份复测；须先训练并产生权重。全量 eval/*.jsonl 的 marscorpus 原始字节检索为 0 行。',
        },
        {
            '未完成臂/证据缺口': 'MARS 100M（状态快照 400M/2000M，20.0%；无探针）',
            '权重位置': f"{RUNS / 'RNA-Sc-100M_s17_marscorpus'}：4 个 ckpt，最新 ckpt_nt400023183_step041442.pt",
            '可复测性': '可复测现有 400,023,183 nt 中间权重；不能冒充完整 2B 臂。全量探针检索为 0 行。',
        },
        {
            '未完成臂/证据缺口': 'MARS 300M（状态快照 200M/2000M，10.0%；无探针）',
            '权重位置': f"{RUNS / 'RNA-Sc-300M_s17_marscorpus'}：2 个 ckpt，最新 ckpt_nt200010618_step020735.pt",
            '可复测性': '可复测现有 200,010,618 nt 中间权重；不能冒充完整 2B 臂。全量探针检索为 0 行。',
        },
        {
            '未完成臂/证据缺口': 'RNAcentral 30M（训练与探针均未完成；status.md 无此行）',
            '权重位置': f"{RUNS / 'RNA-Sc-30M_s17_rnacentral'}：目录为空，无 ckpt",
            '可复测性': '不可从备份复测；须先训练并产生权重。全量 eval/*.jsonl 的 rnacentral 原始字节检索为 0 行。',
        },
        {
            '未完成臂/证据缺口': 'RNAcentral 100M（状态快照 300M/2000M，15.0%，但备份无权重；无探针）',
            '权重位置': f"{RUNS / 'RNA-Sc-100M_s17_rnacentral'}：目录为空，无 ckpt",
            '可复测性': '不可从备份复测。状态快照称 ckpts=3，与本地空目录不符；须找回权重或重训，不能登记为可复测。',
        },
        {
            '未完成臂/证据缺口': 'RNAcentral 300M（状态快照 200M/2000M，10.0%，但备份无权重；无探针）',
            '权重位置': f"{RUNS / 'RNA-Sc-300M_s17_rnacentral'}：目录为空，无 ckpt",
            '可复测性': '不可从备份复测。状态快照称 ckpts=2，与本地空目录不符；须找回权重或重训，不能登记为可复测。',
        },
        {
            '未完成臂/证据缺口': 'RFamCap 30M：bpRNA 结构探针缺口（训练 DONE；分类探针已在位）',
            '权重位置': f"{RUNS / 'RNA-Sc-30M_s17_rfamcap'}：2 个留存 ckpt，最新 ckpt_nt1900086380_step250287.pt",
            '可复测性': '可用 1,900,086,380 nt 权重补测 bpRNA；现有 rna_type 为 24 行，bpRNA 为 0 行。此项是探针缺口，不是训练未完成。',
        },
    ]

    csv_path = OUT / 'p04_unfinished_registry.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['未完成臂/证据缺口', '权重位置', '可复测性'])
        writer.writeheader()
        writer.writerows(rows)

    rfamcap_30_global = task_counts['RNA-Sc-30M_s17_rfamcap']['rna_type classification (S11 global property)']
    rfamcap_100_global = task_counts['RNA-Sc-100M_s17_rfamcap']['rna_type classification (S11 global property)']
    rfamcap_100_structure = task_counts['RNA-Sc-100M_s17_rfamcap']['bpRNA paired-position']
    md = [
        '# P0.4 未完成臂登记',
        '',
        f'- 生成时间：`{generated_at}`',
        f'- 备份根（只读）：`{BACKUP}`',
        '- 范围：RNA-Sc 受控家族纯测评证据对账；未修改备份或交接文档。',
        f'- 检索范围：`eval_evidence_logs/eval/*.jsonl` 共 {len(eval_files)} 个文件（含 {sum(path.name.startswith("._") for path in eval_files)} 个 AppleDouble 元数据文件）；对全部文件做不区分大小写的原始字节检索，`marscorpus` 与 `rnacentral` 均为 **0 命中**。',
        '',
        '## 三列表',
        '',
        '| 未完成臂/证据缺口 | 权重位置 | 可复测性 |',
        '|---|---|---|',
    ]
    for row in rows:
        md.append('| ' + ' | '.join(row[key].replace('|', '\\|') for key in ('未完成臂/证据缺口', '权重位置', '可复测性')) + ' |')
    md.extend([
        '',
        '## RFamCap 30M/100M 对照核查',
        '',
        f'- 两者训练 manifest 均为 `DONE`，`final_nt=2000003378`；备份各留存 1,800,083,135 与 1,900,086,380 nt 两个检查点（manifest 历史记录各 17 个）。探针使用的最终留存点为 1,900,086,380 nt。',
        f'- 30M：`rna_type` {rfamcap_30_global} 行，覆盖 `ckpt_nt=200006790` 与 `1900086380`；`bpRNA paired-position` 0 行，因此只登记结构探针缺口。',
        f'- 100M：`rna_type` {rfamcap_100_global} 行（两个 ckpt 各 23 行），`bpRNA paired-position` {rfamcap_100_structure} 行；分类与结构探针均在位，不列入未完成表。',
        '- 计数来源：`probe_results.jsonl` 与 `probe_structure_results.jsonl` 中按 `run`、`task` 全量解析计数；具体行号见两个 manifest 的 `rfamcap_evidence_lines`。不是训练种子重复，也不涉及 bootstrap。',
        '',
        '## 停机状态与判读边界',
        '',
        '- `status.md:3` 快照生成于 `2026-10-14T12:20:03`；第 7、10、25、27 行分别保留 MARS 100M、RNAcentral 100M、MARS 300M、RNAcentral 300M 的 `RUNNING`，均为 `thr=0 nt/s`，末尾汇总为 4 个非 DONE。',
        f'- `ledger.jsonl` 共 {len(ledger_lines)} 行，尾部 5 行均为 DONE，最新一行是第 {len(ledger_lines)} 行 `rnasc_30M_s17b59`，`updated_utc=2026-10-04T19:30:22.447398Z`；全账本 MARS/RNAcentral 记录为 {len(ledger_unfinished_mentions)} 行。具体尾部记录见 manifest。',
        '- 裁决：文件支持“训练已停滞的停机快照”判读，不支持把这些臂写成已完成；旧 `RUNNING` 不是 2026-11-25 的实时进程证据。远端当日 `nvidia-smi` 仅见 codonflow/llr 两个 Python 进程，未见 RNA-Sc 进程（详见 `p04_remote_check.md`）。',
        '',
        '## 异常',
        '',
        '- RNAcentral 100M/300M 的 `status.md` 分别称已有 3/2 个 ckpt，但备份对应目录为空；不能推定权重可复测。',
        '- MARS 30M 与 RNAcentral 30M 目录也为空，且未进入 `status.md`；不能将 30M 视作已有中间权重。',
        '- RFamCap 30M 缺 bpRNA 结构探针，而 RFamCap 100M 在位。',
        '',
        '## 复现',
        '',
        '```bash',
        f"/usr/bin/python3 '{OUT / 'p04_unfinished_registry.py'}'",
        '```',
        '',
        '输入哈希、逐文件检索结果、权重目录清单和探针行号见 `p04_manifest.json` 与 `p04_unfinished_registry.manifest.json`。',
        '',
    ])
    (OUT / 'p04_unfinished_registry.md').write_text('\n'.join(md), encoding='utf-8')

    line_refs = []
    for (run, task, filename), lines in sorted(evidence_lines.items()):
        line_refs.append({
            'run': run,
            'task': task,
            'file': str(EVAL / filename),
            'count': len(lines),
            'line_numbers': lines,
            'ckpt_nt': sorted(ckpt_nts[run]),
        })
    base_manifest = {
        'task': 'P0.4',
        'generated_at': generated_at,
        'generator_script': str(OUT / 'p04_unfinished_registry.py'),
        'generator_script_sha256': sha256(OUT / 'p04_unfinished_registry.py'),
        'backup_root_read_only': str(BACKUP),
        'search': {
            'glob': str(EVAL / '*.jsonl'),
            'terms_case_insensitive': ['marscorpus', 'rnacentral'],
            'method': 'raw byte search over every matched file; JSON parsing excludes AppleDouble ._* files',
            'eval_file_count': len(eval_files),
            'appledouble_file_count': sum(path.name.startswith('._') for path in eval_files),
            'match_count': len(search_matches),
            'matches': search_matches,
            'json_parse_errors': parse_errors,
        },
        'input_files': [file_record(path) for path in inputs],
        'run_inventory': inventory,
        'status_refs': status_refs,
        'ledger': {
            'path': str(ledger_path),
            'line_count': len(ledger_lines),
            'tail': ledger_tail,
            'marscorpus_rnacentral_mentions': ledger_unfinished_mentions,
        },
        'rfamcap_probe_counts': {
            run: {
                'total': probe_counts[run],
                'by_task': dict(task_counts[run]),
                'ckpt_nt': sorted(ckpt_nts[run]),
            }
            for run in sorted(probe_counts)
        },
        'rfamcap_evidence_lines': line_refs,
        'run_manifest_final_fields': {
            path: {
                key: data.get(key)
                for key in ('status', 'final_nt', 'final_step', 'best_checkpoint', 'end_utc')
            }
            for path, data in manifest_data.items()
        },
        'note': 'Checkpoint contents were not hashed because only filenames, sizes and manifest metadata were used. No model evaluation or training was run.',
    }
    manifest = dict(base_manifest)
    manifest['manifest_role'] = 'P0.4 local retrieval input hashes'
    (OUT / 'p04_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    registry_manifest = dict(base_manifest)
    registry_manifest['manifest_role'] = 'Inputs and evidence for p04_unfinished_registry.md/.csv'
    registry_manifest['outputs'] = [
        str(OUT / 'p04_unfinished_registry.md'),
        str(OUT / 'p04_unfinished_registry.csv'),
    ]
    (OUT / 'p04_unfinished_registry.manifest.json').write_text(json.dumps(registry_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'rows': len(rows),
        'eval_files': len(eval_files),
        'probe_search_matches': len(search_matches),
        'rfamcap_counts': base_manifest['rfamcap_probe_counts'],
        'outputs': [str(csv_path), str(OUT / 'p04_unfinished_registry.md'), str(OUT / 'p04_manifest.json')],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
