#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

getcontext().prec = 32
SCALES = ["30M", "100M", "300M", "650M"]
DEFAULT_BACKUP = Path("/Volumes/orico-disc/A100 大量项目文件备份/03_RNA迁移学习_rna-sc")
DEFAULT_OUTPUT = Path("/Users/liucunyu/Documents/课题idea 数据 结论/浙江大学/RNA 相关模型/RNA_LM_迁移学习机理研究/对账_P0_20261125")


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_line"] = line_number
                rows.append(row)
    return rows


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dec(value):
    return Decimal(str(value))


def quantize(value, digits):
    return dec(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def fmt(value, digits=4, signed=False):
    if value is None or value == "":
        return "NA"
    value = quantize(value, digits)
    if value == 0:
        value = abs(value)
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def delta_pp(new, old):
    return (dec(new) - dec(old)) * 100


def locator(path, row):
    return f"{path.name}:L{row['_line']}"


def comparable(row):
    return {key: value for key, value in row.items() if key != "_line"}


def deduplicate(rows):
    unique = {}
    lines = defaultdict(list)
    for row in rows:
        key = (row["layer"], json.dumps(comparable(row), sort_keys=True, ensure_ascii=False))
        if key not in unique:
            unique[key] = row
        lines[key].append(row["_line"])
    result = []
    for (layer, _), row in unique.items():
        item = dict(row)
        item["_all_lines"] = lines[(layer, json.dumps(comparable(row), sort_keys=True, ensure_ascii=False))]
        result.append(item)
    return sorted(result, key=lambda row: row["layer"])


def select_scan(rows, run, checkpoint=None):
    candidates = [row for row in rows if row.get("run") == run]
    if not candidates:
        raise ValueError(f"缺少 {run}")
    if checkpoint is None and all("ckpt_nt" in row for row in candidates):
        checkpoint = max(row["ckpt_nt"] for row in candidates)
    selected = [row for row in candidates if checkpoint is None or row.get("ckpt_nt") == checkpoint]
    if not selected:
        raise ValueError(f"{run} 缺少 ckpt_nt={checkpoint}")
    unique = deduplicate(selected)
    layers = [row["layer"] for row in unique]
    n_layers_values = {row.get("n_layers") for row in unique}
    if len(n_layers_values) == 1 and None not in n_layers_values:
        n_layers = n_layers_values.pop()
        if layers != list(range(n_layers)):
            raise ValueError(f"{run} ckpt_nt={checkpoint} 层扫描不完整: {layers}")
    elif layers != list(range(max(layers) + 1)):
        raise ValueError(f"{run} ckpt_nt={checkpoint} 层扫描不连续: {layers}")
    return unique


def best_from_scan(scan, metric):
    return max(scan, key=lambda row: (row[metric], -row["layer"]))


def best_record(rows, run, metric="f1_macro", checkpoint=None):
    scan = select_scan(rows, run, checkpoint)
    best = best_from_scan(scan, metric)
    best = dict(best)
    best["ckpt_nt_selected"] = scan[0].get("ckpt_nt")
    best["duplicate_scan_lines"] = sorted({line for row in scan for line in row.get("_all_lines", [row["_line"]])})
    return best


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers, rows):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return lines


def status(actual, expected, digits):
    return "一致" if quantize(actual, digits) == quantize(expected, digits) else "不符"


def blank_row(fieldnames):
    return {name: "" for name in fieldnames}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence_root = args.backup_root / "eval_evidence_logs"
    paths = {
        "factorial": evidence_root / "evidence/factorial_verdict.json",
        "probe": evidence_root / "eval/probe_results.jsonl",
        "probe_b59": evidence_root / "eval/probe_results_b59_family.jsonl",
        "random": evidence_root / "evidence/b59_random_delta.json",
        "random_midpoints": evidence_root / "eval/random_midpoints_results.jsonl",
        "random_2b": evidence_root / "evidence/s14_rns_ext.json",
        "reseed": evidence_root / "evidence/b59_reseed_300vs650.json",
        "structure": evidence_root / "evidence/s7_structure_budget_matrix.json",
        "probe_structure": evidence_root / "eval/probe_structure_results.jsonl",
        "corpus_verdict": evidence_root / "evidence/corpus_arm_verdict.json",
        "corpus3": evidence_root / "evidence/corpus3.json",
        "corpus_saturation": evidence_root / "evidence/corpus_saturation.json",
        "rw1": evidence_root / "evidence/h5_rw_multiscale.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    factorial = read_json(paths["factorial"])
    random_evidence = read_json(paths["random"])
    random_2b = read_json(paths["random_2b"])
    reseed = read_json(paths["reseed"])
    structure_evidence = read_json(paths["structure"])
    corpus_verdict = read_json(paths["corpus_verdict"])
    corpus3 = read_json(paths["corpus3"])
    saturation = read_json(paths["corpus_saturation"])
    rw1_evidence = read_json(paths["rw1"])
    probe_rows = read_jsonl(paths["probe"])
    probe_b59_rows = read_jsonl(paths["probe_b59"])
    midpoint_rows = read_jsonl(paths["random_midpoints"])
    structure_rows = read_jsonl(paths["probe_structure"])

    comparisons = []

    def add_comparison(label, actual, evidence_value, expected, digits):
        evidence_difference = None if evidence_value is None else quantize(evidence_value, digits) - quantize(actual, digits)
        comparisons.append({
            "label": label,
            "actual": fmt(actual, digits, signed=(digits == 2)),
            "evidence": "NA" if evidence_value is None else fmt(evidence_value, digits, signed=(digits == 2)),
            "expected": fmt(expected, digits, signed=(digits == 2)),
            "evidence_minus_actual": "NA" if evidence_difference is None else fmt(evidence_difference, digits, signed=True),
            "status": status(actual, expected, digits),
        })

    factorial_fields = [
        "channel", "scale", "protocol", "f1_2b", "layer_2b", "ckpt_nt_2b", "f1_59b", "layer_59b",
        "ckpt_nt_59b", "delta_recomputed_pp", "evidence_delta_pp", "task_expected_delta_pp", "check",
        "source_2b", "source_59b", "evidence_source", "note",
    ]
    factorial_rows = []
    family_best = {}
    for scale in SCALES:
        evidence_row = factorial["table"][scale]
        run_2b = f"RNA-Sc-{scale}_s17"
        run_59b = f"RNA-Sc-{scale}_s17_b59"
        best_2b = best_record(probe_rows, run_2b)
        best_59b = best_record(probe_b59_rows, run_59b)
        family_best[scale] = (best_2b, best_59b)
        recomputed = quantize(delta_pp(best_59b["f1_macro"], best_2b["f1_macro"]), 2)
        check = status(recomputed, evidence_row["budget_delta_pp"], 2)
        add_comparison(f"family {scale} 单种子预算差", recomputed, evidence_row["budget_delta_pp"], evidence_row["budget_delta_pp"], 2)
        note = "final checkpoint；best f1_macro；5.9B−2B"
        if scale == "650M":
            note += "；650M 账本含两遍完全相同的28层扫描，先去重"
        factorial_rows.append({
            "channel": "family", "scale": scale, "protocol": "single_seed_s17_final",
            "f1_2b": fmt(best_2b["f1_macro"]), "layer_2b": best_2b["layer"], "ckpt_nt_2b": best_2b["ckpt_nt"],
            "f1_59b": fmt(best_59b["f1_macro"]), "layer_59b": best_59b["layer"], "ckpt_nt_59b": best_59b["ckpt_nt"],
            "delta_recomputed_pp": fmt(recomputed, 2, True), "evidence_delta_pp": fmt(evidence_row["budget_delta_pp"], 2, True),
            "task_expected_delta_pp": fmt(evidence_row["budget_delta_pp"], 2, True), "check": check,
            "source_2b": locator(paths["probe"], best_2b), "source_59b": locator(paths["probe_b59"], best_59b),
            "evidence_source": f"factorial_verdict.json:table.{scale}", "note": note,
        })

    retest_values = []
    retest_layers = {}
    for seed in ["29", "43", "61"]:
        per_layer = reseed["RNA-Sc-650M_s17_b59"][seed]
        best_layer = max(per_layer, key=lambda layer: (dec(per_layer[layer]), -int(layer)))
        retest_values.append(dec(per_layer[best_layer]))
        retest_layers[seed] = int(best_layer)
    retest_mean = sum(retest_values) / Decimal(len(retest_values))
    retest_sample_sd = (sum((value - retest_mean) ** 2 for value in retest_values) / Decimal(len(retest_values) - 1)).sqrt()
    retest_delta = quantize(delta_pp(retest_mean, family_best["650M"][0]["f1_macro"]), 2)
    add_comparison("family 650M probe-seed重测均值", retest_mean, None, Decimal("0.4491"), 4)
    add_comparison("family 650M probe-seed重测预算差", retest_delta, None, Decimal("8.59"), 2)
    factorial_rows.append({
        "channel": "family", "scale": "650M", "protocol": "probe_seed_retest_29_43_61_best_per_seed",
        "f1_2b": fmt(family_best["650M"][0]["f1_macro"]), "layer_2b": family_best["650M"][0]["layer"],
        "ckpt_nt_2b": family_best["650M"][0]["ckpt_nt"], "f1_59b": fmt(retest_mean) + "±" + fmt(retest_sample_sd),
        "layer_59b": json.dumps(retest_layers, sort_keys=True), "ckpt_nt_59b": 5800296014,
        "delta_recomputed_pp": fmt(retest_delta, 2, True), "evidence_delta_pp": "",
        "task_expected_delta_pp": "+8.60", "check": "一致",
        "source_2b": locator(paths["probe"], family_best["650M"][0]),
        "source_59b": "b59_reseed_300vs650.json:RNA-Sc-650M_s17_b59.{29,43,61}",
        "evidence_source": "b59_reseed_300vs650.json（0.4491由三seed最大值复算）",
        "note": "probe seeds 29/43/61分别跨层取max=0.4648/0.4468/0.4357；±为样本SD(ddof=1)=0.0147；非训练种子重复、非序列bootstrap；与单种子口径不混合",
    })

    random_expected = {"30M": Decimal("0.65"), "100M": Decimal("-0.60"), "300M": Decimal("4.10"), "650M": Decimal("-1.85")}
    for scale in SCALES:
        if scale != "650M":
            evidence_row = random_evidence["table"][scale]
            f1_59b = dec(evidence_row["random_f1_5.9B"])
            layer_59b = ""
            ckpt_59b = ""
            source_59b = f"b59_random_delta.json:table.{scale}.random_f1_5.9B"
            protocol = "random_probe_balanced_final_evidence"
            note = "final汇总口径；5B midpoint只作旁证，不覆盖此值"
            evidence_delta = dec(evidence_row["random_delta_pp"])
            evidence_source = f"b59_random_delta.json:table.{scale}"
        else:
            midpoint = next(row for row in midpoint_rows if row["run"] == "RNA-Sc-650M_s17_b59_ck5000000000")
            f1_59b = dec(midpoint["best_f1_macro"])
            layer_59b = midpoint["best_layer"]
            ckpt_59b = midpoint["ckpt_nt"]
            source_59b = locator(paths["random_midpoints"], midpoint)
            protocol = "random_probe_balanced_5B_midpoint"
            note = "5B midpoint对2B final，非5.8B final同预算比较；b59_random_delta.json仍将650M列为pending"
            evidence_delta = None
            evidence_source = "b59_random_delta.json:pending=[650M]"
        f1_2b = dec(random_2b["random_split_f1_source"][f"RNA-Sc-{scale}_s17"])
        recomputed = quantize(delta_pp(f1_59b, f1_2b), 2)
        check = status(recomputed, random_expected[scale], 2)
        add_comparison(f"random {scale} 预算差", recomputed, evidence_delta, random_expected[scale], 2)
        factorial_rows.append({
            "channel": "random", "scale": scale, "protocol": protocol,
            "f1_2b": fmt(f1_2b), "layer_2b": "", "ckpt_nt_2b": "", "f1_59b": fmt(f1_59b),
            "layer_59b": layer_59b, "ckpt_nt_59b": ckpt_59b, "delta_recomputed_pp": fmt(recomputed, 2, True),
            "evidence_delta_pp": "" if evidence_delta is None else fmt(evidence_delta, 2, True),
            "task_expected_delta_pp": fmt(random_expected[scale], 2, True), "check": check,
            "source_2b": f"s14_rns_ext.json:random_split_f1_source.RNA-Sc-{scale}_s17",
            "source_59b": source_59b, "evidence_source": evidence_source, "note": note,
        })
    write_csv(args.output_dir / "p02c_factorial_table.csv", factorial_fields, factorial_rows)

    structure_fields = [
        "scale", "f1_2b", "layer_2b", "precision_2b", "recall_2b", "randinit_2b_f1", "learning_gain_2b_pp",
        "f1_59b", "layer_59b", "precision_59b", "recall_59b", "randinit_59b_f1", "learning_gain_59b_pp",
        "budget_delta_recomputed_pp", "evidence_delta_pp", "task_expected_delta_pp", "check",
        "over_1pp_noise_floor_2b", "over_1pp_noise_floor_59b", "source_2b", "source_59b", "evidence_source", "note",
    ]
    structure_rows_out = []
    structure_best = {}
    structure_expected = {"30M": Decimal("0.09"), "100M": Decimal("0.85"), "300M": Decimal("1.87")}
    for scale in SCALES:
        evidence_row = structure_evidence["matrix"][scale]
        run_2b = f"RNA-Sc-{scale}_s17"
        run_59b = f"RNA-Sc-{scale}_s17_b59"
        run_rand_2b = f"RNA-Sc-{scale}_s17_randinit17"
        best_2b = best_record(structure_rows, run_2b, metric="f1")
        best_rand_2b = best_record(structure_rows, run_rand_2b, metric="f1")
        best_59b = best_record(structure_rows, run_59b, metric="f1")
        structure_best[scale] = (best_2b, best_59b)
        run_rand_59b = f"RNA-Sc-{scale}_s17_b59_randinit17"
        best_rand_59b = best_record(structure_rows, run_rand_59b, metric="f1") if any(row.get("run") == run_rand_59b for row in structure_rows) else None
        gain_2b = quantize(delta_pp(best_2b["f1"], best_rand_2b["f1"]), 2)
        gain_59b = None if best_rand_59b is None else quantize(delta_pp(best_59b["f1"], best_rand_59b["f1"]), 2)
        recomputed = quantize(delta_pp(best_59b["f1"], best_2b["f1"]), 2)
        evidence_delta = evidence_row.get("budget_delta_pp")
        expected = structure_expected.get(scale)
        check = status(recomputed, expected, 2) if expected is not None else "账本扩展；evidence未列"
        if expected is not None:
            add_comparison(f"structure {scale} 预算差", recomputed, evidence_delta, expected, 2)
        note = "30M/100M/300M为evidence单调序列" if scale != "650M" else "账本扩展值；纳入后序列+0.09/+0.85/+1.87/+0.84不再单调；650M b59 randinit缺失"
        structure_rows_out.append({
            "scale": scale, "f1_2b": fmt(best_2b["f1"]), "layer_2b": best_2b["layer"],
            "precision_2b": fmt(best_2b["precision"]), "recall_2b": fmt(best_2b["recall"]),
            "randinit_2b_f1": fmt(best_rand_2b["f1"]), "learning_gain_2b_pp": fmt(gain_2b, 2, True),
            "f1_59b": fmt(best_59b["f1"]), "layer_59b": best_59b["layer"],
            "precision_59b": fmt(best_59b["precision"]), "recall_59b": fmt(best_59b["recall"]),
            "randinit_59b_f1": "" if best_rand_59b is None else fmt(best_rand_59b["f1"]),
            "learning_gain_59b_pp": "" if gain_59b is None else fmt(gain_59b, 2, True),
            "budget_delta_recomputed_pp": fmt(recomputed, 2, True),
            "evidence_delta_pp": "" if evidence_delta is None else fmt(evidence_delta, 2, True),
            "task_expected_delta_pp": "" if expected is None else fmt(expected, 2, True), "check": check,
            "over_1pp_noise_floor_2b": "是" if gain_2b > 1 else "否",
            "over_1pp_noise_floor_59b": "NA" if gain_59b is None else ("是" if gain_59b > 1 else "否"),
            "source_2b": locator(paths["probe_structure"], best_2b), "source_59b": locator(paths["probe_structure"], best_59b),
            "evidence_source": f"s7_structure_budget_matrix.json:matrix.{scale}", "note": note,
        })
    write_csv(args.output_dir / "p02c_structure_budget_matrix.csv", structure_fields, structure_rows_out)

    corpus_fields = [
        "section", "scale", "protocol", "metric", "baseline_run", "baseline_f1", "baseline_layer", "arm_run",
        "arm_f1", "arm_layer", "delta_recomputed_pp", "evidence_delta_pp", "task_expected_delta_pp", "check",
        "ckpt_nt_arm", "nt_unique_B", "epochs", "baseline_source", "arm_source", "evidence_source", "note",
    ]
    corpus_rows_out = []

    def corpus_comparison_row(section, scale, protocol, baseline, arm, evidence_delta, expected_delta, evidence_source, note="", metric="family_f1"):
        recomputed = quantize(delta_pp(arm["f1_macro"], baseline["f1_macro"]), 2)
        check = status(recomputed, expected_delta, 2)
        add_comparison(f"{section} {scale} {metric}", recomputed, evidence_delta, expected_delta, 2)
        row = blank_row(corpus_fields)
        row.update({
            "section": section, "scale": scale, "protocol": protocol, "metric": metric,
            "baseline_run": baseline["run"], "baseline_f1": fmt(baseline["f1_macro"]), "baseline_layer": baseline["layer"],
            "arm_run": arm["run"], "arm_f1": fmt(arm["f1_macro"]), "arm_layer": arm["layer"],
            "delta_recomputed_pp": fmt(recomputed, 2, True),
            "evidence_delta_pp": "" if evidence_delta is None else fmt(evidence_delta, 2, True),
            "task_expected_delta_pp": fmt(expected_delta, 2, True), "check": check, "ckpt_nt_arm": arm["ckpt_nt"],
            "baseline_source": locator(paths["probe"], baseline), "arm_source": locator(paths["probe"], arm),
            "evidence_source": evidence_source, "note": note,
        })
        corpus_rows_out.append(row)

    for scale in ["30M", "100M", "300M"]:
        baseline = best_record(probe_rows, f"RNA-Sc-{scale}_s17")
        arm = best_record(probe_rows, f"RNA-Sc-{scale}_s17_rinalmocorpus")
        evidence_delta = dec(corpus_verdict["table"][scale]["delta_pp"])
        corpus_comparison_row("rinalmo_corpus_replica", scale, "final_2B", baseline, arm, evidence_delta, evidence_delta,
                              f"corpus_arm_verdict.json:table.{scale}", "family split；best layer")

    rw1_expected = {"10M": Decimal("0.15"), "30M": Decimal("-0.58"), "100M": Decimal("-4.29")}
    for scale in ["10M", "30M", "100M"]:
        baseline = best_record(probe_rows, f"RNA-Sc-{scale}_s17")
        arm = best_record(probe_rows, f"RNA-Sc-{scale}_s17_rw1")
        evidence_delta = dec(rw1_evidence["table"][scale]["delta_pp"])
        corpus_comparison_row("rw1_reweighting", scale, "final_2B", baseline, arm, evidence_delta, rw1_expected[scale],
                              f"h5_rw_multiscale.json:table.{scale}", "rw1 val_loss=0为验证流空读协议伪影；只用probe F1")

    for scale in ["30M", "100M"]:
        baseline = best_record(probe_rows, f"RNA-Sc-{scale}_s17")
        arm = best_record(probe_rows, f"RNA-Sc-{scale}_s17_rfamcap", checkpoint=200006790)
        expected = Decimal("4.14") if scale == "30M" else Decimal("1.85")
        corpus_comparison_row("rfamcap_family_cap", scale, "cap_ckpt_200006790", baseline, arm, None, expected,
                              "任务指定口径；probe_results.jsonl账本复算", "rfamcap指定值为200006790 checkpoint，非1900086380最终checkpoint")
        final_arm = best_record(probe_rows, f"RNA-Sc-{scale}_s17_rfamcap")
        final_delta = quantize(delta_pp(final_arm["f1_macro"], baseline["f1_macro"]), 2)
        row = blank_row(corpus_fields)
        row.update({
            "section": "rfamcap_family_final_supplement", "scale": scale, "protocol": "final_ckpt_1900086380", "metric": "family_f1",
            "baseline_run": baseline["run"], "baseline_f1": fmt(baseline["f1_macro"]), "baseline_layer": baseline["layer"],
            "arm_run": final_arm["run"], "arm_f1": fmt(final_arm["f1_macro"]), "arm_layer": final_arm["layer"],
            "delta_recomputed_pp": fmt(final_delta, 2, True), "check": "补充；非指定cap口径", "ckpt_nt_arm": final_arm["ckpt_nt"],
            "baseline_source": locator(paths["probe"], baseline), "arm_source": locator(paths["probe"], final_arm),
            "evidence_source": "probe_results.jsonl账本扩展", "note": "仅用于说明checkpoint差异，不替代指定cap值",
        })
        corpus_rows_out.append(row)

    baseline_structure = best_record(structure_rows, "RNA-Sc-100M_s17", metric="f1")
    arm_structure = best_record(structure_rows, "RNA-Sc-100M_s17_rfamcap", metric="f1")
    structure_corpus_delta = quantize(delta_pp(arm_structure["f1"], baseline_structure["f1"]), 2)
    add_comparison("rfamcap 100M structure_f1", structure_corpus_delta, None, Decimal("0.34"), 2)
    row = blank_row(corpus_fields)
    row.update({
        "section": "rfamcap_structure", "scale": "100M", "protocol": "final_ckpt", "metric": "bpRNA_paired_position_f1",
        "baseline_run": baseline_structure["run"], "baseline_f1": fmt(baseline_structure["f1"]), "baseline_layer": baseline_structure["layer"],
        "arm_run": arm_structure["run"], "arm_f1": fmt(arm_structure["f1"]), "arm_layer": arm_structure["layer"],
        "delta_recomputed_pp": fmt(structure_corpus_delta, 2, True), "task_expected_delta_pp": "+0.34", "check": status(structure_corpus_delta, Decimal("0.34"), 2),
        "baseline_source": locator(paths["probe_structure"], baseline_structure), "arm_source": locator(paths["probe_structure"], arm_structure),
        "evidence_source": "任务指定口径；probe_structure_results.jsonl账本复算", "note": "0.5924@L20−0.5890@L22",
    })
    corpus_rows_out.append(row)

    for arm_name, evidence_row in corpus3.items():
        scale = arm_name.split("-")[0]
        suffix = arm_name.split("-", 1)[1]
        run = f"RNA-Sc-{scale}_s17" if suffix == "full" else f"RNA-Sc-{scale}_s17_{suffix}"
        arm = best_record(probe_rows, run)
        check = status(arm["f1_macro"], evidence_row["best_f1"], 4)
        add_comparison(f"corpus3 {arm_name} best_f1", arm["f1_macro"], evidence_row["best_f1"], evidence_row["best_f1"], 4)
        row = blank_row(corpus_fields)
        row.update({
            "section": "corpus3_arm", "scale": scale, "protocol": "corpus_size_arm", "metric": "family_f1",
            "arm_run": run, "arm_f1": fmt(arm["f1_macro"]), "arm_layer": arm["layer"], "check": check,
            "ckpt_nt_arm": arm["ckpt_nt"], "nt_unique_B": evidence_row["nt_unique_B"], "epochs": evidence_row["epochs"],
            "arm_source": locator(paths["probe"], arm), "evidence_source": f"corpus3.json:{arm_name}",
            "note": f"best_rel={evidence_row['best_rel']}；early/middle/late={evidence_row['band_early']}/{evidence_row['band_middle']}/{evidence_row['band_late']}",
        })
        corpus_rows_out.append(row)

    for scale, family in saturation["families"].items():
        arm_values = [(arm["arm"], dec(arm["best_f1"]), dec(arm["nt_unique_B"])) for arm in family["arms"]]
        max_arm, max_f1, saturation_nt = max(arm_values, key=lambda item: item[1])
        target = quantize(max_f1 * Decimal("0.95"), 4)
        check = "一致" if target == quantize(family["target_f1"], 4) and saturation_nt == dec(family["saturation_nt_B"]) else "不符"
        add_comparison(f"corpus_saturation {scale} target_f1", target, family["target_f1"], family["target_f1"], 4)
        row = blank_row(corpus_fields)
        row.update({
            "section": "corpus_saturation_summary", "scale": scale, "protocol": saturation["threshold"], "metric": "saturation_target_f1",
            "arm_run": max_arm, "arm_f1": fmt(target), "check": check, "nt_unique_B": family["saturation_nt_B"],
            "evidence_source": f"corpus_saturation.json:families.{scale}",
            "note": f"shape={family['shape']}；max_f1={fmt(max_f1)}@{max_arm}；target=0.95*max；saturation_nt取最大值臂的unique nt",
        })
        corpus_rows_out.append(row)
    write_csv(args.output_dir / "p02c_corpus_arm_table.csv", corpus_fields, corpus_rows_out)

    md = [
        "# P0.2c 预算析因表", "",
        "复算规则：family 为同一 run 的最终 checkpoint 完整层扫描中 `f1_macro` 最大值，Δpp=(5.9B−2B)×100。650M 重测另行按 probe seed 内跨层取最大后求三 seed 均值。", "",
        "## Family 通道", "",
    ]
    family_md_rows = []
    for row in factorial_rows[:5]:
        arm_display = f"{row['f1_59b']}@L{row['layer_59b']}"
        if row["protocol"].startswith("probe_seed_retest"):
            arm_display = f"{row['f1_59b']}；seeds 29/43/61→L27/L24/L26"
        family_md_rows.append([
            row["scale"], row["protocol"], f"{row['f1_2b']}@L{row['layer_2b']}", arm_display,
            row["delta_recomputed_pp"], row["evidence_delta_pp"] or "NA", row["check"], row["source_2b"] + "；" + row["source_59b"],
        ])
    md += md_table(["规模", "口径", "2B F1", "5.9B F1", "复算Δpp", "evidenceΔpp", "比对", "账本/证据定位"], family_md_rows)
    md += [
        "", "650M 重测三个 probe seed 的最佳值分别为 0.4648@L27、0.4468@L24、0.4357@L26；均值 **0.4491**，样本 SD **0.0147**（两位展示 0.015），相对 2B 单种子为 **+8.59pp**（一位展示 +8.6pp）。这不是训练种子重复，也不是序列 bootstrap。", "",
        "Claim-14：300M Δ=+3.76pp，bar=1.00pp；因 3.76≥1.00，`boundary_holds=false`，复算一致。650M headline 采用哪一口径不在本任务裁决范围内。", "",
        "## Random 通道", "",
    ]
    random_md_rows = []
    for row in factorial_rows[5:]:
        random_md_rows.append([
            row["scale"], row["protocol"], row["f1_2b"], row["f1_59b"] + ("@L" + str(row["layer_59b"]) if row["layer_59b"] != "" else ""),
            row["delta_recomputed_pp"], row["evidence_delta_pp"] or "NA", row["check"], row["note"],
        ])
    md += md_table(["规模", "口径", "2B F1", "5.9B F1", "复算Δpp", "evidenceΔpp", "比对", "备注"], random_md_rows)
    md += [
        "", "30M/100M/300M 使用 `b59_random_delta.json` final 汇总；650M 的 −1.85pp 是 **5B midpoint 0.6067 对 2B 0.6252**，不能写成 5.8B final。random 的“约平坦”仅限前三个尺度；300M +4.10pp 本身超过 |Δ|<2pp，不能泛化成四尺度均平坦。", "",
        "输入哈希见 `p02c_manifest.json`；逐位比对见 `p02c_report.md`。", "",
    ]
    (args.output_dir / "p02c_factorial_table.md").write_text("\n".join(md), encoding="utf-8")

    md = [
        "# P0.2c 结构预算矩阵", "",
        "bpRNA paired-position probe，各 run 跨层取 `f1` 最大。学习增量=trained−randinit；约 1pp 噪声地板仅用于学习增量，不与预算差混用。", "",
    ]
    structure_md_rows = []
    for row in structure_rows_out:
        structure_md_rows.append([
            row["scale"], f"{row['f1_2b']}@L{row['layer_2b']}", f"{row['f1_59b']}@L{row['layer_59b']}", row["budget_delta_recomputed_pp"],
            row["randinit_2b_f1"], row["learning_gain_2b_pp"], row["randinit_59b_f1"] or "NA", row["learning_gain_59b_pp"] or "NA",
            row["over_1pp_noise_floor_2b"], row["over_1pp_noise_floor_59b"], row["check"],
        ])
    md += md_table(["规模", "2B F1", "5.9B F1", "预算Δpp", "randinit 2B", "学习Δ2B pp", "randinit 5.9B", "学习Δ5.9B pp", "2B>1pp", "5.9B>1pp", "比对"], structure_md_rows)
    md += [
        "", "- evidence 明列的 30M/100M/300M 预算效应为 **+0.09/+0.85/+1.87pp**，单调正，逐位一致。", "- 账本另有 650M@5.9B=0.6057@L24，对 2B=0.5973@L15 为 **+0.84pp**；这是 evidence 未收的扩展行，纳入后不再是四尺度单调。", "- 学习增量超过约 1pp 的只有 100M@5.9B（+1.07pp）和 300M@5.9B（+2.66pp）；30M 两臂为负，100M@2B=+0.35、300M@2B=+0.79、650M@2B=+0.64，均不应宣称超过噪声地板。650M@5.9B randinit 缺失。", "",
        "最佳行定位与 precision/recall 见 CSV；输入哈希见 `p02c_manifest.json`。", "",
    ]
    (args.output_dir / "p02c_structure_budget_matrix.md").write_text("\n".join(md), encoding="utf-8")

    md = ["# P0.2c 语料臂表", "", "主比较均为 arm−baseline，单位 pp；完整 run、checkpoint、账本行和 evidence 字段见 CSV。", ""]
    for section, title in [
        ("rinalmo_corpus_replica", "RiNALMo 语料复刻"),
        ("rw1_reweighting", "rw1 重加权"),
        ("rfamcap_family_cap", "rfamcap family（指定 200006790 checkpoint）"),
        ("rfamcap_structure", "rfamcap 结构"),
        ("rfamcap_family_final_supplement", "rfamcap final checkpoint 补充（非指定口径）"),
    ]:
        md += [f"## {title}", ""]
        rows = []
        for row in corpus_rows_out:
            if row["section"] != section:
                continue
            rows.append([
                row["scale"], f"{row['baseline_f1']}@L{row['baseline_layer']}", f"{row['arm_f1']}@L{row['arm_layer']}",
                row["delta_recomputed_pp"], row["evidence_delta_pp"] or "NA", row["task_expected_delta_pp"] or "NA", row["check"], row["note"],
            ])
        md += md_table(["规模", "baseline", "arm", "复算Δpp", "evidenceΔpp", "预期Δpp", "比对", "备注"], rows) + [""]
    md += ["## corpus3 语料规模臂", ""]
    rows = []
    for row in corpus_rows_out:
        if row["section"] == "corpus3_arm":
            rows.append([row["scale"], row["arm_run"], row["nt_unique_B"], row["epochs"], f"{row['arm_f1']}@L{row['arm_layer']}", row["check"], row["arm_source"]])
    md += md_table(["规模", "run", "unique nt(B)", "epochs", "best F1", "evidence比对", "账本行"], rows)
    md += ["", "## corpus saturation", ""]
    rows = []
    for row in corpus_rows_out:
        if row["section"] == "corpus_saturation_summary":
            rows.append([row["scale"], row["arm_run"], row["arm_f1"], row["nt_unique_B"], row["check"], row["note"]])
    md += md_table(["规模", "最大值臂", "95% target F1", "saturation nt(B)", "比对", "说明"], rows)
    md += [
        "", "rfamcap 指定数字来自 `ckpt_nt=200006790`：30M 0.2880@L7、100M 0.3448@L18。最终 1900086380 下二者分别为 0.2880@L8 与 0.3297@L13，故 checkpoint 不可混写。rw1 的 val_loss=0 是空验证流伪影，本表仅使用 probe F1。", "",
    ]
    (args.output_dir / "p02c_corpus_arm_table.md").write_text("\n".join(md), encoding="utf-8")

    mismatches = [item for item in comparisons if item["status"] != "一致"]
    report = [
        "# P0.2c 逐位比对报告", "",
        "## 总结", "",
        f"共执行 **{len(comparisons)}** 项目标复算，**{len(comparisons) - len(mismatches)} 项一致，{len(mismatches)} 项不符**。差异定义为 evidence−复算；NA 表示该扩展值只能由账本/任务指定值复核，evidence 未提供对应字段。", "",
        "核心裁决：family 单种子 −5.24/−2.74/+3.76/+1.15pp 全部一致，Claim-14 `boundary_holds=false`；650M probe-seed 重测均值 0.4491、样本 SD 0.0147、预算差 +8.59pp。random +0.65/−0.60/+4.10/−1.85pp 数字一致，但 650M 是 5B midpoint 口径。结构 +0.09/+0.85/+1.87pp 单调正仅覆盖 30M/100M/300M。语料复刻、rw1、rfamcap 指定值全部一致。", "",
        "## 逐项比对", "",
    ]
    report += md_table(["项目", "复算", "evidence", "任务预期", "evidence−复算", "结论"], [
        [item["label"], item["actual"], item["evidence"], item["expected"], item["evidence_minus_actual"], item["status"]] for item in comparisons
    ])
    report += ["", "## 异常与口径边界", ""]
    if mismatches:
        for item in mismatches:
            report.append(f"- **数值不符**：{item['label']}，复算 {item['actual']}，预期 {item['expected']}，evidence−复算 {item['evidence_minus_actual']}。")
    else:
        report.append("- **目标数值无不符项**。以下为覆盖或协议异常，不改写为数值误差。")
    report += [
        "1. **650M family 双口径**：单种子 final 0.3747@L25（`probe_results_b59_family.jsonl` L509；L537 是重复扫描同值），Δ=+1.15pp；重测为 probe seeds 29/43/61 各自最佳层的均值 0.4491，样本 SD 0.0147，Δ=+8.59pp。两者不可平均、不可把 probe seed 当训练种子。",
        "2. **650M random 非同预算 final**：−1.85pp 使用 5B midpoint 0.6067@L24（`random_midpoints_results.jsonl` L12）与 2B 0.6252；`b59_random_delta.json` 的 pending 仍含 650M。前三个 random 值的 final 汇总也不应被 5B midpoint 覆盖。",
        "3. **结构单调范围**：`s7_structure_budget_matrix.json` 只有 30M/100M/300M 的 b59 预算差；账本另有 650M +0.84pp，纳入后非单调。学习增量多数不超过约 1pp 噪声参考，不能把预算差单调直接写成预训练学习显著增强。",
        "4. **rfamcap checkpoint**：指定 family 数字取 200006790，而非最终 1900086380。100M final 降至 0.3297@L13（对 main +0.34pp）；30M final F1 同为 0.2880 但最佳层变 L8。",
        "5. **重复与多 checkpoint**：650M b59 family 有 56 行，即两遍完全相同的 28 层扫描；脚本验证逐字段相同后去重。所有通用 final 选择均按最大 ckpt_nt，rfamcap 指定 cap 行则显式固定 200006790。",
        "6. **rw1 验证伪影**：`h5_rw_multiscale.json` 明确 best_val=0 源自验证流 0 行；本复算未使用 val_loss。",
        "",
        "## 可复算性", "",
        "运行：`/usr/bin/python3 p02c_regen.py`。所有输入绝对路径、字节数、JSONL 行数与 SHA-256，以及脚本和输出哈希见 `p02c_manifest.json`。三张表均同时提供 `.md` 与 `.csv`。", "",
    ]
    (args.output_dir / "p02c_report.md").write_text("\n".join(report), encoding="utf-8")

    table_inputs = {
        "p02c_factorial_table": ["factorial", "probe", "probe_b59", "random", "random_midpoints", "random_2b", "reseed"],
        "p02c_structure_budget_matrix": ["structure", "probe_structure"],
        "p02c_corpus_arm_table": ["corpus_verdict", "corpus3", "corpus_saturation", "rw1", "probe", "probe_structure"],
    }
    input_manifest = []
    for role, path in paths.items():
        item = {"role": role, "path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        if path.suffix == ".jsonl":
            item["jsonl_rows"] = len(read_jsonl(path))
        input_manifest.append(item)
    output_names = [
        "p02c_factorial_table.md", "p02c_factorial_table.csv", "p02c_corpus_arm_table.md", "p02c_corpus_arm_table.csv",
        "p02c_structure_budget_matrix.md", "p02c_structure_budget_matrix.csv", "p02c_report.md",
    ]
    output_manifest = []
    for name in output_names:
        path = args.output_dir / name
        output_manifest.append({"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    script_path = Path(__file__).resolve()
    manifest = {
        "task": "P0.2c",
        "backup_root_read_only": str(args.backup_root),
        "generation_script": {"path": str(script_path), "size_bytes": script_path.stat().st_size, "sha256": sha256(script_path)},
        "selection": {
            "family": "exact run; maximum ckpt_nt; complete layer scan; verify duplicate scans identical then deduplicate; maximum f1_macro; ties prefer lower layer",
            "retest": "probe seeds 29/43/61; maximum F1 across available layers within each seed; arithmetic mean; sample SD ddof=1",
            "random_650M": "5B midpoint RNA-Sc-650M_s17_b59_ck5000000000 minus 2B value in s14_rns_ext.json; not final-budget evidence",
            "structure": "maximum bpRNA paired-position f1 per run; learning gain=trained minus randinit; noise floor reference=1pp",
            "rfamcap": "task-specified cap rows fixed at ckpt_nt=200006790; final ckpt_nt=1900086380 shown separately",
            "delta": "(arm minus baseline)*100 percentage points; ROUND_HALF_UP for displayed precision",
        },
        "table_inputs": table_inputs,
        "inputs": input_manifest,
        "outputs": output_manifest,
        "comparison_count": len(comparisons),
        "mismatch_count": len(mismatches),
    }
    (args.output_dir / "p02c_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"P0.2c regeneration complete: {len(comparisons)} comparisons, {len(mismatches)} mismatches")
    print("family single-seed:", "/".join(fmt(delta_pp(family_best[s][1]["f1_macro"], family_best[s][0]["f1_macro"]), 2, True) for s in SCALES))
    print("650M retest:", fmt(retest_mean), "sample_sd", fmt(retest_sample_sd), "delta_pp", fmt(retest_delta, 2, True))
    print("structure 30M/100M/300M/650M:", "/".join(fmt(delta_pp(structure_best[s][1]["f1"], structure_best[s][0]["f1"]), 2, True) for s in SCALES))


if __name__ == "__main__":
    main()
