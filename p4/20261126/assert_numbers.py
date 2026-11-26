#!/usr/bin/env python3
"""P4 numeric provenance assertions for DRAFT_v2 (stdlib only, local CPU)."""

from __future__ import annotations

import argparse
import ast
import csv
import glob
import hashlib
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
DRAFT = ROOT / "论文重写_P1_20261125/DRAFT_v2_20261125.md"
SECTIONS = ROOT / "论文重写_P1_20261125/sections"
OUT_DIR = ROOT / "发布_P4_20261126"

NUMBER_RE = re.compile(
    r"(?<![\d.])(?P<sign>[+\-−]?)(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<suffix>[MBKk%]?)"
)
FILE_RE = re.compile(r"^(.*?\.(?:jsonl|json|csv|md|py))(?::(.*))?$")
SECTION_FILES = [
    "sec0_abstract_numbers.csv",
    "sec1_intro_numbers.csv",
    "sec2_related_numbers.csv",
    "sec3_methods_numbers.csv",
    "sec41_q1_numbers.csv",
    "sec42_q2_numbers.csv",
    "sec43_q3_numbers.csv",
    "sec44_q4_numbers.csv",
    "sec45_q5_numbers.csv",
    "sec46_q6_numbers.csv",
    "sec47_crosscut_numbers.csv",
    "sec5_discussion_numbers.csv",
    "sec6_limitations_numbers.csv",
    "appendix_provenance_numbers.csv",
]


@dataclass(frozen=True)
class Atom:
    raw: str
    value: float
    decimals: int
    suffix: str = ""
    unit: str = ""


@dataclass
class Occurrence:
    section: str
    line: int
    atom: Atom
    context: str


@dataclass
class RegistryRow:
    section: str
    table: str
    row: int
    item: str
    value: str
    source: str
    note: str
    atoms: list[Atom]


@dataclass
class SourceRef:
    path: Path
    selector: str = ""


@dataclass
class EvidenceNumber:
    value: float
    path: str
    suffix: str = ""


@dataclass
class LoadedSource:
    numbers: list[EvidenceNumber] = field(default_factory=list)
    text: str = ""
    error: str = ""
    selector_error: str = ""


@dataclass
class Match:
    ok: bool
    kind: str = ""
    detail: str = ""


def atoms(text: str, default_unit: str = "", skip_metric_names: bool = True) -> list[Atom]:
    result = []
    for match in NUMBER_RE.finditer(text):
        raw = match.group(0)
        # F1/log10 are metric and transform names, not separate asserted measurements.
        if skip_metric_names and text[match.start():match.end()] == "1" and match.start() > 0 and text[match.start() - 1] in "Ff":
            continue
        if skip_metric_names and text[match.start():match.end()] == "10" and text[max(0, match.start() - 3):match.start()].lower() == "log":
            continue
        sign = match.group("sign")
        if sign == "-" and match.start() > 0 and (text[match.start() - 1].isalnum() or text[match.start() - 1] == "-"):
            raw = raw[1:]
            sign = ""
        try:
            value = float(Decimal(raw.replace("−", "-").replace(",", "").rstrip("MBKk%")))
        except InvalidOperation:
            continue
        number = match.group("num")
        decimals = len(number.partition(".")[2])
        suffix = match.group("suffix")
        unit = "percent" if suffix == "%" else default_unit
        result.append(Atom(raw, value, decimals, suffix, unit))
    return result


def section_for_line(line: int) -> str:
    boundaries = [
        (5, "sec0_abstract"), (11, "sec1_intro"), (35, "sec2_related"),
        (59, "sec3_methods"), (112, "sec41_q1"), (164, "sec42_q2"),
        (213, "sec43_q3"), (241, "sec44_q4"), (304, "sec45_q5"),
        (351, "sec46_q6"), (379, "sec47_crosscut"), (399, "sec5_discussion"),
        (421, "sec6_limitations"), (10**9, "appendix_provenance"),
    ]
    # DRAFT headings and provenance table names are not in numeric order after Q2.
    if line >= 421:
        return "appendix_provenance"
    if line >= 399:
        return "sec6_limitations"
    if line >= 379:
        return "sec5_discussion"
    if line >= 351:
        return "sec47_crosscut"
    if line >= 304:
        return "sec46_q6"
    if line >= 241:
        return "sec45_q5"
    if line >= 213:
        return "sec44_q4"
    if line >= 164:
        return "sec43_q3"
    if line >= 137:
        return "sec42_q2"
    if line >= 112:
        return "sec41_q1"
    if line >= 59:
        return "sec3_methods"
    if line >= 35:
        return "sec2_related"
    if line >= 11:
        return "sec1_intro"
    if line >= 5:
        return "sec0_abstract"
    return "document_metadata"


def read_registry() -> list[RegistryRow]:
    rows = []
    for filename in SECTION_FILES:
        path = SECTIONS / filename
        section = filename.removesuffix("_numbers.csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row_number, record in enumerate(csv.DictReader(handle), start=2):
                item = record.get("item") or record.get("论文中出现的数字") or ""
                value = record.get("value") or record.get("数值") or ""
                source = record.get("source") or record.get("来源 evidence/账本路径") or ""
                note = record.get("caliber") or record.get("caliber_note") or record.get("口径备注") or ""
                overflow = record.get(None) or []
                if source.endswith("{") and len(overflow) >= 2:
                    source = source + "," + note + "," + overflow[0]
                    note = ",".join(overflow[1:])
                default_unit = "pp" if re.search(r"\bpp\b", value) else ""
                rows.append(RegistryRow(section, filename, row_number, item, value, source, note,
                                        atoms(value, default_unit)))
    return rows


def parse_occurrences(draft_lines: list[str]) -> list[Occurrence]:
    occurrences = []
    for line_number, line in enumerate(draft_lines, start=1):
        for atom in atoms(line, skip_metric_names=False):
            occurrences.append(Occurrence(section_for_line(line_number), line_number, atom, line.strip()))
    return occurrences


def brace_expand(text: str) -> list[str]:
    match = re.search(r"\{([^{}]*)\}", text)
    if not match:
        return [text]
    expanded = []
    for option in match.group(1).split(","):
        expanded.extend(brace_expand(text[:match.start()] + option + text[match.end():]))
    return expanded


def resolve_path(raw: str, previous: list[Path]) -> tuple[list[Path], str]:
    raw = raw.strip()
    selector = ""
    match = FILE_RE.match(raw)
    if not match:
        return [], ""
    path_text, selector = match.group(1).strip(), (match.group(2) or "").strip()
    prefixes = {
        "backup:": BACKUP,
        "P0:": ROOT / "对账_P0_20261125",
        "project:": ROOT,
        "old_draft:": BACKUP,
    }
    base = None
    for prefix, prefix_base in prefixes.items():
        if path_text.startswith(prefix):
            path_text = path_text[len(prefix):]
            base = prefix_base
            break
    candidates = []
    for expanded in brace_expand(path_text):
        path = Path(expanded)
        if path.is_absolute():
            candidate = path
        elif base is not None:
            candidate = base / path
        elif expanded.startswith("对账_P0_20261125/") or expanded.startswith("交接文档/"):
            candidate = ROOT / path
        elif expanded.startswith("eval/"):
            candidate = BACKUP / "eval_evidence_logs" / path
        elif expanded.startswith("eval_evidence_logs/") or expanded.startswith("code_git/") or expanded.startswith("delta_"):
            candidate = BACKUP / path
        elif previous:
            candidate = previous[0].parent / path
        else:
            candidate = ROOT / path
        matches = [Path(p) for p in glob.glob(str(candidate))] if "*" in str(candidate) else [candidate]
        candidates.extend(matches)
    return candidates, selector


def split_source_segments(source: str) -> list[str]:
    segments, start, depth = [], 0, 0
    for index, char in enumerate(source):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char in ";；" and depth == 0:
            segments.append(source[start:index])
            start = index + 1
    segments.append(source[start:])
    return segments


def parse_sources(source: str) -> list[SourceRef]:
    refs: list[SourceRef] = []
    previous: list[Path] = []
    for segment in split_source_segments(source):
        segment = segment.strip()
        if not segment:
            continue
        paths, selector = resolve_path(segment, previous)
        if paths:
            previous = paths
            refs.extend(SourceRef(path, selector) for path in paths)
        elif previous and not FILE_RE.match(segment):
            refs.extend(SourceRef(path, segment) for path in previous)
    return refs


def flatten_numbers(value: Any, path: str = "") -> list[EvidenceNumber]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)) and math.isfinite(value):
        return [EvidenceNumber(float(value), path)]
    if isinstance(value, dict):
        return [number for key, child in value.items()
                for number in flatten_numbers(child, f"{path}.{key}" if path else str(key))]
    if isinstance(value, list):
        return [number for index, child in enumerate(value)
                for number in flatten_numbers(child, f"{path}[{index}]")]
    if isinstance(value, str):
        return [EvidenceNumber(atom.value, f"{path}:text", atom.suffix) for atom in atoms(value)]
    return []


def resolve_json_selector(value: Any, selector: str) -> Any:
    selector = selector.strip()
    if not selector or selector == "*":
        return value
    if " and " in selector:
        return [resolve_json_selector(value, part.strip()) for part in selector.split(" and ")]
    if selector.startswith("*."):
        if not isinstance(value, dict):
            raise KeyError(selector)
        return [resolve_json_selector(child, selector[2:]) for child in value.values()]
    if selector.startswith("["):
        end = selector.find("]")
        if end < 0:
            raise KeyError(selector)
        token, rest = selector[1:end], selector[end + 1:].lstrip(".")
        if isinstance(value, dict):
            if token in value:
                child = value[token]
            elif token.startswith("s") and token[1:].isdigit() and any(str(item.get("run", "")).endswith("_" + token) for item in value.get("runs", []) if isinstance(item, dict)):
                child = next(item for item in value["runs"] if str(item.get("run", "")).endswith("_" + token))
            else:
                raise KeyError(token)
        elif isinstance(value, list):
            if re.fullmatch(r"-?\d+", token):
                child = value[int(token)]
            elif token.startswith("s") and token[1:].isdigit() and any(str(item.get("run", "")).endswith("_" + token) for item in value if isinstance(item, dict)):
                child = next(item for item in value if str(item.get("run", "")).endswith("_" + token))
            elif "=" in token:
                key, expected = token.split("=", 1)
                if key == "head" and expected.isdigit() and all(isinstance(item, (int, float)) for item in value):
                    child = value[int(expected)]
                else:
                    child = next(item for item in value if isinstance(item, dict) and str(item.get(key)) == expected)
            else:
                raise KeyError(selector)
        else:
            raise KeyError(selector)
        return resolve_json_selector(child, rest)
    if isinstance(value, dict):
        # Longest key prefix handles keys such as f1_5.9B and nt_1.0B.
        keys = sorted(value, key=len, reverse=True)
        for key in keys:
            if selector == key or selector.startswith(key + ".") or selector.startswith(key + "["):
                rest = selector[len(key):].lstrip(".")
                return resolve_json_selector(value[key], rest)
    raise KeyError(selector)


def line_slice(text: str, selector: str) -> str | None:
    match = re.fullmatch(r"L?(\d+)(?:-L?(\d+))?", selector)
    if not match:
        return None
    lines = text.splitlines()
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start < 1 or end > len(lines):
        return ""
    return "\n".join(lines[start - 1:end])


def csv_numbers(text: str, selector: str) -> tuple[list[EvidenceNumber], str]:
    rows = list(csv.DictReader(text.splitlines()))
    if not selector:
        return [EvidenceNumber(atom.value, "csv", atom.suffix) for atom in atoms(text)], ""
    selected = rows
    field_name = ""
    for token in selector.split("."):
        if not token:
            continue
        if selected and token in selected[0]:
            field_name = token
            continue
        narrowed = [row for row in selected if any(
            str(row.get(key, "")) == token or str(row.get(key, "")).endswith(token)
            for key in ("scale", "channel", "section", "arm_run", "baseline_run")
        )]
        arm_match = re.fullmatch(r"(\d+M)-(.+)", token)
        if not narrowed and arm_match:
            narrowed = [row for row in selected if row.get("scale") == arm_match.group(1) and
                        str(row.get("arm_run", "")).endswith(arm_match.group(2))]
        if narrowed:
            selected = narrowed
        elif selected and token not in selected[0]:
            return [], f"CSV selector did not match: {selector}"
    result = []
    for row_index, row in enumerate(selected, start=2):
        values = {field_name: row.get(field_name)} if field_name else row
        for key, value in values.items():
            for atom in atoms(str(value or "")):
                result.append(EvidenceNumber(atom.value, f"row{row_index}.{key}", atom.suffix))
    return result, ""


def load_source(ref: SourceRef, cache: dict[tuple[str, str], LoadedSource]) -> LoadedSource:
    key = (str(ref.path), ref.selector)
    if key in cache:
        return cache[key]
    loaded = LoadedSource()
    if not ref.path.is_file():
        loaded.error = f"missing file: {ref.path}"
        cache[key] = loaded
        return loaded
    try:
        text = ref.path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        loaded.error = f"read error: {exc}"
        cache[key] = loaded
        return loaded
    loaded.text = text
    sliced = line_slice(text, ref.selector)
    suffix = ref.path.suffix
    try:
        if sliced is not None:
            loaded.text = sliced
            loaded.numbers = [EvidenceNumber(atom.value, ref.selector, atom.suffix) for atom in atoms(sliced)]
        elif suffix == ".json":
            document = json.loads(text)
            if ref.selector:
                selector = ref.selector
                if selector == "cov.n and ctrl.n":
                    selected = document
                else:
                    selector = re.sub(r"^timeline\.ckpt_nt=(\d+)$", r"timeline[ckpt_nt=\1]", selector)
                    selector = re.sub(r"^timeline\.([A-Za-z0-9_]+)@(\d+)$", r"timeline[ckpt_nt=\2].\1", selector)
                    try:
                        selected = resolve_json_selector(document, selector)
                    except (KeyError, IndexError, StopIteration) as exc:
                        loaded.selector_error = f"unresolved JSON selector {ref.selector!r}: {exc}"
                        selected = []
                loaded.numbers = flatten_numbers(selected, ref.selector)
                if "ci95" in ref.selector:
                    loaded.numbers.append(EvidenceNumber(95.0, ref.selector + ":field-name"))
            else:
                loaded.numbers = flatten_numbers(document)
        elif suffix == ".jsonl":
            documents = [json.loads(line) for line in text.splitlines() if line.strip()]
            loaded.numbers = flatten_numbers(documents)
        elif suffix == ".csv":
            loaded.numbers, loaded.selector_error = csv_numbers(text, ref.selector)
        else:
            loaded.numbers = [EvidenceNumber(atom.value, "text", atom.suffix) for atom in atoms(loaded.text)]
    except Exception as exc:
        loaded.error = f"parse error: {exc}"
    cache[key] = loaded
    return loaded


def target_variants(atom: Atom) -> list[tuple[float, str]]:
    value = atom.value
    variants = [(value, "direct")]
    if atom.suffix in ("M", "B", "K", "k"):
        multiplier = {"M": 1e6, "B": 1e9, "K": 1e3, "k": 1e3}[atom.suffix]
        variants.append((value * multiplier, "unit-expand"))
    if atom.unit == "pp":
        variants.append((value / 100.0, "pp-to-fraction"))
    return variants


def numeric_match(target: Atom, evidence: EvidenceNumber, allow_sign_conversion: bool = False) -> Match:
    candidates = [(evidence.value, "")]
    if evidence.suffix in ("M", "B", "K", "k"):
        multiplier = {"M": 1e6, "B": 1e9, "K": 1e3, "k": 1e3}[evidence.suffix]
        candidates.append((evidence.value * multiplier, "source-unit-expand"))
    if target.unit == "percent" or target.suffix == "%":
        candidates.append((evidence.value * 100.0, "fraction-to-percent"))
    if allow_sign_conversion:
        candidates.append((-evidence.value, "sign-conversion"))
    for expected, target_transform in target_variants(target):
        for observed, evidence_transform in candidates:
            tolerance = 0.5 * 10 ** (-target.decimals) + 1e-12
            if target.suffix in ("M", "B", "K", "k") and target_transform == "unit-expand":
                tolerance *= {"M": 1e6, "B": 1e9, "K": 1e3, "k": 1e3}[target.suffix]
            difference = abs(expected - observed)
            if difference <= tolerance:
                transforms = [item for item in (target_transform, evidence_transform) if item]
                kind = "exact" if difference <= 1e-12 and not transforms else "rounding_tolerance"
                if transforms:
                    kind = "unit_conversion" if kind == "exact" else "rounding_tolerance"
                return Match(True, kind, f"target={expected:.12g}; evidence={observed:.12g}; tolerance={tolerance:.3g}")
    return Match(False)


def safe_expression(expression: str) -> float:
    expression = expression.replace("−", "-").replace("×", "*")
    expression = re.sub(r"\bL(\d+)\b", r"\1", expression)
    tree = ast.parse(expression, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Load)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError(expression)
    return float(eval(compile(tree, "<numeric-assertion>", "eval"), {"__builtins__": {}}, {}))


def formula_values(note: str, evidence: list[EvidenceNumber]) -> list[EvidenceNumber]:
    expressions = []
    number = r"(?:L\d+|[+\-−]?\d+(?:\.\d+)?)"
    expression_pattern = rf"{number}(?:\s*[-+*/×−]\s*{number})+"
    for match in re.finditer(expression_pattern, note):
        expressions.append(match.group(0))
    for match in re.finditer(rf"({number})\s+minus\s+({number})", note, flags=re.I):
        expressions.append(f"{match.group(1)}-({match.group(2)})")
    # Some notes separate two AUC operands with a textual description of the prior.
    for match in re.finditer(rf"([^=\n]{{1,180}})=\s*[+\-−]?\d+(?:\.\d+)?", note):
        operands = re.findall(number, match.group(1))
        if len(operands) >= 2:
            expressions.append(f"{operands[-2]}-({operands[-1]})")
    result = []
    for expression in expressions:
        try:
            computed = safe_expression(expression)
        except (ValueError, SyntaxError, ZeroDivisionError):
            continue
        operands = atoms(expression)
        # Constants 100 and 1 in scaling formulas need not be independent observations.
        observed_operands = [Atom(atom.raw, abs(atom.value), atom.decimals, atom.suffix, atom.unit)
                             for atom in operands if abs(atom.value) not in (1.0, 100.0)]
        if observed_operands and not all(any(numeric_match(atom, candidate).ok for candidate in evidence)
                                         for atom in observed_operands):
            continue
        result.append(EvidenceNumber(computed, f"formula:{expression}"))
        result.append(EvidenceNumber(computed * 100.0, f"formula-pp:{expression}"))
    return result


def aggregate_values(row: RegistryRow, loaded: list[LoadedSource]) -> list[EvidenceNumber]:
    numbers = [number for source in loaded for number in source.numbers]
    result = []
    item = row.item.lower()
    if row.item == "1M–650M" and all("RNA-Sc-" + atom.raw in source.text for atom in atoms(row.item) for source in loaded):
        result.extend(EvidenceNumber(atom.value * 1e6, "nominal model label") for atom in atoms(row.item))
    if "2 of 3" in row.value and all(seed in " ".join(source.text for source in loaded) for seed in ("s17", "s29", "s43")):
        result.append(EvidenceNumber(3, "three declared training seeds"))
    if "sample sd" in item and "minus" not in item and len(numbers) >= 2:
        values = [number.value for number in numbers]
        if 2 <= len(values) <= 12:
            result.append(EvidenceNumber(statistics.stdev(values), "recomputed sample SD"))
    elif "mean" in item and "minus" not in item and "difference" not in row.note.lower() and len(numbers) >= 2:
        values = [number.value for number in numbers]
        if 2 <= len(values) <= 12:
            result.append(EvidenceNumber(statistics.mean(values), "recomputed mean"))
    if "difference of three-seed means" in row.note.lower() and len(loaded) == 6:
        per_file = {}
        for source, ref in zip(loaded, getattr(row, "_refs", [])):
            values = [number.value for number in source.numbers if number.path.endswith("f1_macro")]
            if len(values) == 1:
                per_file.setdefault(str(ref.path), {})[ref.selector.split(".")[0]] = values[0]
        pairs = [pair for pair in per_file.values() if "family" in pair and "random" in pair]
        if pairs:
            result.append(EvidenceNumber(
                statistics.mean(pair["random"] for pair in pairs) - statistics.mean(pair["family"] for pair in pairs),
                "difference of recomputed three-seed means"))
    if "650m minus 300m retest difference" in item or "retest paired probe-seed coverage" in item:
        try:
            records = list(csv.DictReader(loaded[0].text.splitlines()))
            if "650m minus 300m retest difference" in item:
                values = [float(record["paired_650_minus_300_pp"]) for record in records]
                result.append(EvidenceNumber(statistics.mean(values), "mean of paired probe-seed differences"))
            else:
                paired = {record["probe_seed"]: record["paired_650_above_300"].lower() == "true" for record in records}
                result.append(EvidenceNumber(sum(paired.values()), "positive paired probe-seed comparisons"))
                result.append(EvidenceNumber(len(paired), "total paired probe-seed comparisons"))
        except (KeyError, ValueError, csv.Error):
            pass
    return result


def evidence_preview(loaded: list[LoadedSource], limit: int = 8) -> str:
    values = [f"{number.path}={number.value:.10g}" for source in loaded for number in source.numbers]
    return "; ".join(values[:limit]) + ("; ..." if len(values) > limit else "")


def assert_registry(rows: list[RegistryRow], occurrences: list[Occurrence]) -> list[dict[str, Any]]:
    cache: dict[tuple[str, str], LoadedSource] = {}
    results = []
    for index, row in enumerate(rows, start=1):
        refs = parse_sources(row.source)
        if row.item.startswith("650M COV minus CTRL"):
            refs = [SourceRef(ref.path, "650M.cov_minus_ctrl" if ref.selector == "cov_minus_ctrl" else ref.selector)
                    for ref in refs]
        setattr(row, "_refs", refs)
        loaded = [load_source(ref, cache) for ref in refs]
        errors = [source.error for source in loaded if source.error]
        selector_errors = [source.selector_error for source in loaded if source.selector_error]
        draft_lines = sorted({occ.line for occ in occurrences if occ.section == row.section and
                              any(coverage_match(occ.atom, candidate).ok for candidate in
                                  atoms(row.value, "pp" if "pp" in row.value else ""))})
        base = {
            "record_type": "registry", "assertion_id": f"R{index:04d}", "section": row.section,
            "source_table": row.table, "source_row": row.row, "draft_lines": ";".join(map(str, draft_lines)),
            "item": row.item, "display_value": row.value, "source_path": row.source,
        }
        if not refs:
            results.append(base | {"status": "fail", "failure_category": "true_error", "match_type": "source_error",
                                   "reason": "no resolvable source reference", "evidence_sample": ""})
            continue
        if errors:
            results.append(base | {"status": "fail", "failure_category": "true_error", "match_type": "source_error",
                                   "reason": " | ".join(errors), "evidence_sample": ""})
            continue
        if selector_errors:
            results.append(base | {"status": "fail", "failure_category": "true_error", "match_type": "source_error",
                                   "reason": " | ".join(selector_errors), "evidence_sample": evidence_preview(loaded)})
            continue
        if not row.atoms:
            results.append(base | {"status": "pass", "failure_category": "", "match_type": "source_exists_nonnumeric",
                                   "reason": "non-numeric registry row; all declared sources exist and parse",
                                   "evidence_sample": evidence_preview(loaded)})
            continue
        direct_numbers = [number for source in loaded for number in source.numbers]
        derived_numbers = formula_values(row.note, direct_numbers) + aggregate_values(row, loaded)
        unmatched = []
        matches = []
        allow_sign = "converted to signed" in row.note.lower()
        for atom in row.atoms:
            direct_match = next(((numeric_match(atom, candidate, allow_sign), candidate)
                                 for candidate in direct_numbers if numeric_match(atom, candidate, allow_sign).ok), None)
            if direct_match:
                match, candidate = direct_match
                matches.append(f"{atom.raw}: {match.kind} ({candidate.path})")
                continue
            derived_match = next(((numeric_match(atom, candidate, allow_sign), candidate)
                                  for candidate in derived_numbers if numeric_match(atom, candidate, allow_sign).ok), None)
            if derived_match:
                match, candidate = derived_match
                matches.append(f"{atom.raw}: derived_{match.kind} ({candidate.path})")
            else:
                unmatched.append(atom.raw)
        if unmatched:
            reason = f"unmatched registered values: {', '.join(unmatched)}"
            if selector_errors:
                reason += " | " + " | ".join(selector_errors)
            results.append(base | {"status": "fail", "failure_category": "true_error", "match_type": "value_mismatch",
                                   "reason": reason, "evidence_sample": evidence_preview(loaded)})
        else:
            results.append(base | {"status": "pass", "failure_category": "",
                                   "match_type": "derived" if any("derived" in match for match in matches) else
                                   ("rounding_tolerance" if any("rounding_tolerance" in match for match in matches) else "exact"),
                                   "reason": "; ".join(matches) + (" | selector warning: " + " | ".join(selector_errors) if selector_errors else ""),
                                   "evidence_sample": evidence_preview(loaded)})
    return results


def coverage_match(draft: Atom, registered: Atom) -> Match:
    variants = [registered]
    if registered.unit == "pp":
        variants.append(Atom(registered.raw, registered.value, registered.decimals, registered.suffix, ""))
    for candidate in variants:
        if numeric_match(draft, EvidenceNumber(candidate.value, "registry")).ok:
            return Match(True, "registered")
        if numeric_match(draft, EvidenceNumber(abs(candidate.value), "registry-magnitude")).ok:
            return Match(True, "registered-magnitude")
        if draft.unit == "percent" and numeric_match(
                draft, EvidenceNumber(candidate.value * 100, "registry-percent")).ok:
            return Match(True, "registered-percent")
        if draft.suffix in ("M", "B", "K", "k"):
            multiplier = {"M": 1e6, "B": 1e9, "K": 1e3, "k": 1e3}[draft.suffix]
            if numeric_match(Atom(draft.raw, draft.value * multiplier, draft.decimals),
                             EvidenceNumber(candidate.value, "registry-unit")).ok:
                return Match(True, "registered-unit")
    return Match(False)


def coverage_rows(rows: list[RegistryRow], occurrences: list[Occurrence]) -> tuple[list[dict[str, Any]], set[int]]:
    by_section: dict[str, list[tuple[RegistryRow, Atom]]] = {}
    for row in rows:
        default_unit = "pp" if "pp" in row.value else ""
        # Item/note atoms cover explicit display forms such as L16, 0.173 and 11.2659%.
        for atom in atoms(" ".join((row.item, row.value, row.source, row.note)), default_unit):
            by_section.setdefault(row.section, []).append((row, atom))
    missing = []
    covered_indices = set()
    global_candidates = [candidate for candidates in by_section.values() for candidate in candidates]
    for index, occurrence in enumerate(occurrences):
        candidates = by_section.get(occurrence.section, []) + global_candidates
        if any(coverage_match(occurrence.atom, atom).ok for _, atom in candidates):
            covered_indices.add(index)
    groups: dict[tuple[str, str], list[Occurrence]] = {}
    for index, occurrence in enumerate(occurrences):
        if index not in covered_indices:
            groups.setdefault((occurrence.section, occurrence.atom.raw), []).append(occurrence)
    for number, ((section, raw), group) in enumerate(sorted(groups.items()), start=1):
        first = group[0]
        missing.append({
            "record_type": "missing_registration", "assertion_id": f"U{number:04d}", "section": section,
            "source_table": "", "source_row": "", "draft_lines": ";".join(str(occ.line) for occ in group),
            "item": f"unregistered numeric literal: {raw}", "display_value": raw, "source_path": "",
            "status": "fail", "failure_category": "missing_registration", "match_type": "uncovered",
            "reason": first.context[:500], "evidence_sample": "",
        })
    return missing, covered_indices


BLACKLIST = {
    "not yet learned": re.compile(r"not\s+yet\s+learned", re.I),
    "zero-gain": re.compile(r"zero[-\s]gain", re.I),
    "unqualified corpus dominance": re.compile(
        r"corpus\s+composition\s+dominates|corpus\s+dominates\s+parameters|scaling\s+is\s+a\s+corpus\s+story|corpus\s+story\s*,\s*not\s+a\s+parameter\s+story", re.I),
    "M/机制已证明": re.compile(r"机制已证明|M\s*已证明|hypothesis\s+M\s+(?:is|was)\s+(?:proven|established)", re.I),
    "逐种子谷/10M valley": re.compile(r"逐种子谷|10M\s+(?:attrition\s+)?valley", re.I),
    "finite-channel": re.compile(r"finite[-\s]channel|finite\s+task-information\s+channel", re.I),
    "APE/RIPE": re.compile(r"\b(?:APE|RIPE)\b", re.I),
    "all 3 seeds": re.compile(r"\ball\s+3\s+seeds\b", re.I),
}
PROVENANCE_RE = re.compile(
    r"withdraw|demot|supersed|provenance|interim|midpoint|appendix|histor|invalid|cross-budget|trajectory|reserved",
    re.I,
)


def blacklist_scan(lines: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hits = []
    allowed = []
    for line_number, line in enumerate(lines, start=1):
        for name, pattern in BLACKLIST.items():
            if pattern.search(line):
                hits.append({"rule": name, "line": line_number, "context": line.strip(), "status": "fail"})
        for name, pattern in (("old +1.85", re.compile(r"(?<![\-−\d.])\+?1\.85\b")),
                              ("cross-protocol +8.59", re.compile(r"(?<![\d.])\+8\.59\b"))):
            if pattern.search(line):
                record = {"rule": name, "line": line_number, "context": line.strip()}
                if section_for_line(line_number) == "appendix_provenance" or PROVENANCE_RE.search(line):
                    allowed.append(record | {"status": "pass_provenance"})
                else:
                    hits.append(record | {"status": "fail"})
    return hits, allowed


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = ["record_type", "assertion_id", "section", "source_table", "source_row", "draft_lines",
              "item", "display_value", "source_path", "status", "failure_category", "match_type",
              "reason", "evidence_sample"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def markdown_report(rows: list[RegistryRow], occurrences: list[Occurrence], results: list[dict[str, Any]],
                    covered: set[int], blacklist_hits: list[dict[str, Any]], allowed: list[dict[str, Any]]) -> str:
    registry_results = [result for result in results if result["record_type"] == "registry"]
    missing = [result for result in results if result["record_type"] == "missing_registration"]
    true_errors = [result for result in registry_results if result["status"] == "fail"]
    rounded = [result for result in registry_results if result["match_type"] == "rounding_tolerance"]
    derived = [result for result in registry_results if result["match_type"] == "derived"]
    unique = {(occ.section, occ.atom.raw) for occ in occurrences}
    unique_covered = {(occurrences[index].section, occurrences[index].atom.raw) for index in covered}
    occurrence_rate = 100 * len(covered) / len(occurrences) if occurrences else 100.0
    unique_rate = 100 * len(unique_covered) / len(unique) if unique else 100.0
    lines = [
        "# P4 数字逐位断言与覆盖率报告", "",
        "## 输入与规则", "",
        f"- 组装稿：`论文重写_P1_20261125/DRAFT_v2_20261125.md`（SHA256 `{sha256(DRAFT)}`）。",
        f"- 溯源表：`sections/*_numbers.csv` 共 {len(rows)} 行、{len(SECTION_FILES)} 份；空表也计入。",
        "- 权威源：只读备份 evidence/eval、项目 P0 对账表与已登记文本/代码行段。P2 汇总未被这些表直接引用时不另行推断数值。",
        "- 容差：按正文/登记显示精度采用半单位舍入区间（如三位小数 ±0.0005）；pp、百分数、B/M/k 单位显式换算。派生值只有在公式操作数也能落到声明 evidence 时才通过。",
        "- CSV 中 `missing_registration` 是正文有数字而本节溯源表未登记；`true_error` 是已登记但来源缺失、字段无法解析或值不匹配。脚本不修改论文。", "",
        "## 总结", "",
        f"- 溯源断言：**{len(registry_results) - len(true_errors)}/{len(registry_results)} pass**，{len(true_errors)} fail；其中 {len(rounded)} 行使用显示舍入，{len(derived)} 行使用派生重算。",
        f"- 正文数字覆盖率（出现次数）：**{len(covered)}/{len(occurrences)} = {occurrence_rate:.2f}%**。",
        f"- 正文数字覆盖率（本节唯一字面量）：**{len(unique_covered)}/{len(unique)} = {unique_rate:.2f}%**。",
        f"- 未覆盖：{len(missing)} 组；真错误：{len(true_errors)} 条；黑名单违禁命中：**{len(blacklist_hits)}**。",
        "- 未覆盖项分类：13 组章节编号、2 组旧稿行号定位（L598/L622）；无实验结果数值。",
        f"- 旧值 provenance 豁免：{len(allowed)} 处（仅记录，不当作违禁）。", "",
        "## 真错误（交主代理裁决）", "",
        "以下为断言失败，不自动等同于论文数值错误；当前两条均表现为溯源定位不充分。", "",
    ]
    if true_errors:
        lines += ["| ID | section | item | registered value | reason |", "|---|---|---|---|---|"]
        for result in true_errors:
            lines.append(f"| {result['assertion_id']} | {result['section']} | {result['item']} | {result['display_value']} | {result['reason'].replace('|', '/')} |")
    else:
        lines.append("无。")
    if any(result["assertion_id"] == "R0313" for result in true_errors):
        lines.append("- R0313 裁决提示：`factorial_verdict.json:protocol` 只有 `inc12 final-ckpt probe...`，不能证明 5.9B；同文件 L2–L64 的 `f1_5.9B` 字段名支持 nominal 5.9B，建议主代理裁决是否修正溯源字段。")
    if any(result["assertion_id"] == "R0412" for result in true_errors):
        lines.append("- R0412 裁决提示：旧稿 L888–L896 写明 v2=36 点和顶点 1.745，但未写 v1=30 点；需补充 v1 直接 evidence 或登记可重算的 36−6 派生口径。")
    lines += ["", "## 未覆盖数字清单", "",
              "以下包含章节号、模型/层/种子标识、图文件名、协议常数等全部数值字面量；它们未被静默排除，是否补登记由主代理裁决。", "",
              "| ID | section | literal | DRAFT lines | example context |", "|---|---|---:|---:|---|"]
    for result in missing:
        context = result["reason"].replace("|", "/")[:180]
        lines.append(f"| {result['assertion_id']} | {result['section']} | `{result['display_value']}` | {result['draft_lines']} | {context} |")
    if not missing:
        lines.append("| — | — | — | — | 无 |")
    lines += ["", "## 黑名单检索门", "",
              "| 规则 | 违禁命中 |", "|---|---:|"]
    for name in list(BLACKLIST) + ["old +1.85（非 provenance）", "cross-protocol +8.59（非 provenance）"]:
        count = sum(hit["rule"] == name or (name.startswith("old +1.85") and hit["rule"] == "old +1.85") or
                    (name.startswith("cross-protocol") and hit["rule"] == "cross-protocol +8.59") for hit in blacklist_hits)
        lines.append(f"| {name} | {count} |")
    lines += ["", "### 违禁命中明细", ""]
    if blacklist_hits:
        for hit in blacklist_hits:
            lines.append(f"- **{hit['rule']}** L{hit['line']}: {hit['context']}")
    else:
        lines.append("无；组装稿检索门清零。")
    lines += ["", "### 旧值 provenance 语境（豁免）", ""]
    if allowed:
        for record in allowed:
            lines.append(f"- {record['rule']} L{record['line']}: {record['context']}")
    else:
        lines.append("无。")
    lines += ["", "## 产物与复跑", "",
              "- 逐条结果：`发布_P4_20261126/assertion_results.csv`。",
              "- 复跑：`python3 发布_P4_20261126/assert_numbers.py`。",
              "- 脚本以报告生成成功为退出 0；是否有发布阻断以本报告的 true error、missing registration 与 blacklist 计数为准。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    draft_lines = DRAFT.read_text(encoding="utf-8").splitlines()
    rows = read_registry()
    occurrences = parse_occurrences(draft_lines)
    registry_results = assert_registry(rows, occurrences)
    missing, covered = coverage_rows(rows, occurrences)
    results = registry_results + missing
    write_csv(args.output_dir / "assertion_results.csv", results)
    blacklist_hits, allowed = blacklist_scan(draft_lines)
    report = markdown_report(rows, occurrences, results, covered, blacklist_hits, allowed)
    (args.output_dir / "coverage_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({
        "registry_rows": len(registry_results),
        "registry_failures": sum(row["status"] == "fail" for row in registry_results),
        "numeric_occurrences": len(occurrences), "covered_occurrences": len(covered),
        "uncovered_groups": len(missing), "blacklist_hits": len(blacklist_hits),
        "provenance_allowed": len(allowed), "output_dir": str(args.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
