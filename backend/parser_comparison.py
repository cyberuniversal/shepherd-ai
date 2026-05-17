import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

try:
    from backend.learned_parser import (
        DEFAULT_ARTIFACT_PATH,
        evaluate_artifact_on_splits,
        load_artifact,
        load_frozen_splits,
    )
    from backend.mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH, EVALUATED_INTENT_FIELDS
except ImportError:
    from learned_parser import DEFAULT_ARTIFACT_PATH, evaluate_artifact_on_splits, load_artifact, load_frozen_splits
    from mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH, EVALUATED_INTENT_FIELDS


COMPARISON_SCHEMA = "shepherd-parser-comparison/1.0"
DEFAULT_CANDIDATE_ARTIFACT_PATH = Path(".tmp_models/learned_parser_augmented.json")
DEFAULT_COMPARISON_PATH = Path(".tmp_models/parser_comparison.json")
DEFAULT_COMPARISON_MARKDOWN_PATH = Path(".tmp_models/parser_comparison.md")
DEFAULT_COMPARE_SPLITS = ("eval", "holdout", "adversarial")


def compare_artifacts(
    baseline_artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
    candidate_artifact_path: str | Path = DEFAULT_CANDIDATE_ARTIFACT_PATH,
    *,
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
    splits: Sequence[str] = DEFAULT_COMPARE_SPLITS,
    max_examples: int = 20,
) -> Dict:
    frozen_splits = load_frozen_splits(dataset_path, adversarial_path=adversarial_path)
    baseline_artifact = load_artifact(baseline_artifact_path)
    candidate_artifact = load_artifact(candidate_artifact_path)
    baseline_report = evaluate_artifact_on_splits(baseline_artifact, frozen_splits)
    candidate_report = evaluate_artifact_on_splits(candidate_artifact, frozen_splits)
    comparison = compare_reports(
        baseline_report,
        candidate_report,
        splits=splits,
        max_examples=max_examples,
    )
    comparison["sources"]["baseline"]["artifact_path"] = str(Path(baseline_artifact_path))
    comparison["sources"]["candidate"]["artifact_path"] = str(Path(candidate_artifact_path))
    comparison["sources"]["baseline"]["artifact_training"] = _artifact_training_source(baseline_artifact)
    comparison["sources"]["candidate"]["artifact_training"] = _artifact_training_source(candidate_artifact)
    comparison["sources"]["dataset_path"] = str(Path(dataset_path))
    comparison["sources"]["adversarial_path"] = str(Path(adversarial_path)) if adversarial_path else None
    return comparison


def compare_reports(
    baseline_report: Dict,
    candidate_report: Dict,
    *,
    splits: Sequence[str] = DEFAULT_COMPARE_SPLITS,
    max_examples: int = 20,
) -> Dict:
    split_scope = tuple(splits)
    baseline_rows = _rows_by_id(baseline_report, split_scope)
    candidate_rows = _rows_by_id(candidate_report, split_scope)
    common_ids = sorted(set(baseline_rows) & set(candidate_rows))
    compared = [
        _compare_row(baseline_rows[row_id], candidate_rows[row_id])
        for row_id in common_ids
    ]
    improvements = [row for row in compared if row["status"] == "improved"]
    regressions = [row for row in compared if row["status"] == "regressed"]
    changed = [row for row in compared if row["fixed_fields"] or row["new_failed_fields"]]
    baseline_metrics = _metrics(baseline_rows[row_id] for row_id in common_ids)
    candidate_metrics = _metrics(candidate_rows[row_id] for row_id in common_ids)
    split_deltas = _group_deltas(baseline_rows, candidate_rows, common_ids, "split")
    language_deltas = _group_deltas(baseline_rows, candidate_rows, common_ids, "language")
    field_deltas = _field_deltas(baseline_metrics["field_metrics"], candidate_metrics["field_metrics"])

    return {
        "schema": COMPARISON_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "baseline": _report_source(baseline_report),
            "candidate": _report_source(candidate_report),
        },
        "scope": {
            "splits": list(split_scope),
            "baseline_total_rows": len(_rows_by_id(baseline_report, None)),
            "candidate_total_rows": len(_rows_by_id(candidate_report, None)),
            "compared_ids": len(common_ids),
            "baseline_only_ids": sorted(set(baseline_rows) - set(candidate_rows)),
            "candidate_only_ids": sorted(set(candidate_rows) - set(baseline_rows)),
        },
        "summary": {
            "compared_examples": len(compared),
            "baseline_failed": baseline_metrics["failed_examples"],
            "candidate_failed": candidate_metrics["failed_examples"],
            "failure_delta": candidate_metrics["failed_examples"] - baseline_metrics["failed_examples"],
            "baseline_subset_accuracy": baseline_metrics["subset_accuracy"],
            "candidate_subset_accuracy": candidate_metrics["subset_accuracy"],
            "subset_accuracy_delta": _delta(
                baseline_metrics["subset_accuracy"],
                candidate_metrics["subset_accuracy"],
            ),
            "improved_examples": len(improvements),
            "regressed_examples": len(regressions),
            "unchanged_pass": len([row for row in compared if row["status"] == "unchanged_pass"]),
            "unchanged_fail": len([row for row in compared if row["status"] == "unchanged_fail"]),
            "changed_examples": len(changed),
        },
        "field_deltas": field_deltas,
        "split_deltas": split_deltas,
        "language_deltas": language_deltas,
        "improvements": [_example_delta(row) for row in improvements[:max_examples]],
        "regressions": [_example_delta(row) for row in regressions[:max_examples]],
        "changed_examples": [_example_delta(row) for row in changed[:max_examples]],
        "recommendations": _recommendations(field_deltas, split_deltas, language_deltas, regressions),
    }


def load_report(path: str | Path) -> Dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_comparison(comparison: Dict, output_path: str | Path) -> str:
    return _write_json(comparison, output_path)


def write_markdown_comparison(comparison: Dict, output_path: str | Path) -> str:
    summary = comparison["summary"]
    lines = [
        "# Shepherd-AI Parser Comparison",
        "",
        f"- Compared examples: `{summary['compared_examples']}`",
        f"- Baseline failed: `{summary['baseline_failed']}`",
        f"- Candidate failed: `{summary['candidate_failed']}`",
        f"- Failure delta: `{summary['failure_delta']}`",
        f"- Baseline subset accuracy: `{summary['baseline_subset_accuracy']}`",
        f"- Candidate subset accuracy: `{summary['candidate_subset_accuracy']}`",
        f"- Subset accuracy delta: `{summary['subset_accuracy_delta']}`",
        f"- Improved examples: `{summary['improved_examples']}`",
        f"- Regressed examples: `{summary['regressed_examples']}`",
        "",
        "## Field Deltas",
        "",
        "| Field | Baseline Accuracy | Candidate Accuracy | Delta | Baseline Failures | Candidate Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field, item in comparison.get("field_deltas", {}).items():
        lines.append(
            f"| {field} | {item['baseline_accuracy']} | {item['candidate_accuracy']} | "
            f"{item['accuracy_delta']} | {item['baseline_failures']} | {item['candidate_failures']} |"
        )

    lines.extend(["", "## Split Deltas", "", "| Split | Baseline Accuracy | Candidate Accuracy | Delta |", "| --- | ---: | ---: | ---: |"])
    for split, item in comparison.get("split_deltas", {}).items():
        lines.append(f"| {split} | {item['baseline_subset_accuracy']} | {item['candidate_subset_accuracy']} | {item['subset_accuracy_delta']} |")

    lines.extend(["", "## Regressions", ""])
    regressions = comparison.get("regressions", [])
    if regressions:
        for example in regressions:
            lines.append(f"- `{example['id']}` ({example['language']}/{example['split']}): {', '.join(example['new_failed_fields'])}")
    else:
        lines.append("- None in compared scope.")

    lines.extend(["", "## Improvements", ""])
    improvements = comparison.get("improvements", [])
    if improvements:
        for example in improvements:
            lines.append(f"- `{example['id']}` ({example['language']}/{example['split']}): {', '.join(example['fixed_fields'])}")
    else:
        lines.append("- None in compared scope.")

    lines.extend(["", "## Recommendations", ""])
    for recommendation in comparison.get("recommendations", []):
        lines.append(f"- {recommendation}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _rows_by_id(report: Dict, splits: Sequence[str] | None) -> Dict[str, Dict]:
    rows = {}
    split_filter = set(splits) if splits else None
    for split_name, split_report in report.get("split_reports", {}).items():
        if split_filter is not None and split_name not in split_filter:
            continue
        for result in split_report.get("results", []):
            row = _normalize_row(result, fallback_split=split_name)
            rows[row["id"]] = row
    if report.get("results"):
        for result in report.get("results", []):
            row = _normalize_row(result, fallback_split=result.get("split", "unknown"))
            if split_filter is None or row["split"] in split_filter:
                rows[row["id"]] = row
    return rows


def _normalize_row(result: Dict, *, fallback_split: str) -> Dict:
    field_results = {}
    failed_fields = []
    for field, field_result in result.get("field_results", {}).items():
        expected = field_result.get("expected")
        predicted = field_result.get("predicted", field_result.get("parsed"))
        matched = bool(field_result.get("matched"))
        field_results[field] = {
            "expected": expected,
            "predicted": predicted,
            "matched": matched,
        }
        if not matched:
            failed_fields.append(field)
    return {
        "id": result.get("id", "unknown"),
        "language": result.get("language", "unknown"),
        "split": result.get("split") or fallback_split,
        "command": result.get("command", ""),
        "field_results": field_results,
        "failed_fields": sorted(failed_fields),
    }


def _compare_row(baseline: Dict, candidate: Dict) -> Dict:
    baseline_failed = set(baseline["failed_fields"])
    candidate_failed = set(candidate["failed_fields"])
    if not baseline_failed and not candidate_failed:
        status = "unchanged_pass"
    elif baseline_failed and not candidate_failed:
        status = "improved"
    elif not baseline_failed and candidate_failed:
        status = "regressed"
    elif len(candidate_failed) < len(baseline_failed):
        status = "partially_improved"
    elif len(candidate_failed) > len(baseline_failed):
        status = "partially_regressed"
    else:
        status = "unchanged_fail"
    return {
        "id": baseline["id"],
        "language": baseline["language"],
        "split": baseline["split"],
        "command": baseline["command"],
        "status": status,
        "baseline_failed_fields": sorted(baseline_failed),
        "candidate_failed_fields": sorted(candidate_failed),
        "fixed_fields": sorted(baseline_failed - candidate_failed),
        "new_failed_fields": sorted(candidate_failed - baseline_failed),
    }


def _metrics(rows: Iterable[Dict]) -> Dict:
    row_list = list(rows)
    field_totals = Counter()
    field_matches = Counter()
    failed_examples = 0
    for row in row_list:
        if row["failed_fields"]:
            failed_examples += 1
        for field, field_result in row["field_results"].items():
            field_totals[field] += 1
            if field_result["matched"]:
                field_matches[field] += 1
    return {
        "total": len(row_list),
        "failed_examples": failed_examples,
        "subset_matches": len(row_list) - failed_examples,
        "subset_accuracy": round((len(row_list) - failed_examples) / len(row_list), 3) if row_list else None,
        "field_metrics": {
            field: {
                "matched": field_matches[field],
                "total": field_totals[field],
                "failures": field_totals[field] - field_matches[field],
                "accuracy": round(field_matches[field] / field_totals[field], 3) if field_totals[field] else None,
            }
            for field in sorted(field_totals)
        },
    }


def _group_deltas(baseline_rows: Dict[str, Dict], candidate_rows: Dict[str, Dict], row_ids: Sequence[str], group_key: str) -> Dict:
    groups = defaultdict(list)
    for row_id in row_ids:
        groups[baseline_rows[row_id].get(group_key, "unknown")].append(row_id)
    return {
        group: _metric_delta(
            _metrics(baseline_rows[row_id] for row_id in ids),
            _metrics(candidate_rows[row_id] for row_id in ids),
        )
        for group, ids in sorted(groups.items())
    }


def _metric_delta(baseline: Dict, candidate: Dict) -> Dict:
    return {
        "total": baseline["total"],
        "baseline_failures": baseline["failed_examples"],
        "candidate_failures": candidate["failed_examples"],
        "failure_delta": candidate["failed_examples"] - baseline["failed_examples"],
        "baseline_subset_accuracy": baseline["subset_accuracy"],
        "candidate_subset_accuracy": candidate["subset_accuracy"],
        "subset_accuracy_delta": _delta(baseline["subset_accuracy"], candidate["subset_accuracy"]),
    }


def _field_deltas(baseline_fields: Dict, candidate_fields: Dict) -> Dict:
    deltas = {}
    for field in sorted(set(EVALUATED_INTENT_FIELDS) | set(baseline_fields) | set(candidate_fields)):
        baseline = baseline_fields.get(field, {})
        candidate = candidate_fields.get(field, {})
        baseline_failures = baseline.get("failures")
        candidate_failures = candidate.get("failures")
        deltas[field] = {
            "baseline_accuracy": baseline.get("accuracy"),
            "candidate_accuracy": candidate.get("accuracy"),
            "accuracy_delta": _delta(baseline.get("accuracy"), candidate.get("accuracy")),
            "baseline_failures": baseline_failures,
            "candidate_failures": candidate_failures,
            "failure_delta": (
                candidate_failures - baseline_failures
                if isinstance(candidate_failures, int) and isinstance(baseline_failures, int)
                else None
            ),
        }
    return deltas


def _example_delta(row: Dict) -> Dict:
    return {
        "id": row["id"],
        "language": row["language"],
        "split": row["split"],
        "command": row["command"],
        "status": row["status"],
        "baseline_failed_fields": row["baseline_failed_fields"],
        "candidate_failed_fields": row["candidate_failed_fields"],
        "fixed_fields": row["fixed_fields"],
        "new_failed_fields": row["new_failed_fields"],
    }


def _report_source(report: Dict) -> Dict:
    return {
        "schema": report.get("schema"),
        "model_id": report.get("model_id"),
        "artifact_digest": report.get("artifact_digest"),
        "summary": {
            "train_count": report.get("summary", {}).get("train_count"),
            "augmentation_count": report.get("summary", {}).get("augmentation_count"),
            "eval_count": report.get("summary", {}).get("eval_count"),
            "holdout_count": report.get("summary", {}).get("holdout_count"),
            "adversarial_count": report.get("summary", {}).get("adversarial_count"),
            "adversarial_used_for_training": report.get("summary", {}).get("adversarial_used_for_training"),
        },
    }


def _artifact_training_source(artifact: Dict) -> Dict:
    dataset = artifact.get("dataset", {})
    train_ids = dataset.get("train_ids") or []
    augmentation_ids = dataset.get("augmentation_ids") or []
    adversarial_ids = dataset.get("adversarial_ids") or []
    return {
        "dataset_path": dataset.get("path"),
        "augmentation_path": dataset.get("augmentation_path"),
        "adversarial_path": dataset.get("adversarial_path"),
        "train_count": len(train_ids),
        "augmentation_count": len(augmentation_ids),
        "adversarial_count": len(adversarial_ids),
        "adversarial_used_for_training": bool(set(train_ids) & set(adversarial_ids)) if train_ids and adversarial_ids else None,
    }


def _recommendations(field_deltas: Dict, split_deltas: Dict, language_deltas: Dict, regressions: Sequence[Dict]) -> List[str]:
    recommendations = []
    if regressions:
        recommendations.append("Review regressed held-out examples before expanding training further.")
    weak_fields = [
        field
        for field, delta in field_deltas.items()
        if delta.get("candidate_accuracy") is not None and delta["candidate_accuracy"] < 0.75
    ]
    if weak_fields:
        recommendations.append(f"Prioritize more training rows and parser features for weak fields: {', '.join(weak_fields)}.")
    worse_fields = [
        field
        for field, delta in field_deltas.items()
        if delta.get("accuracy_delta") is not None and delta["accuracy_delta"] < 0
    ]
    if worse_fields:
        recommendations.append(f"Inspect augmentation for negative field transfer in: {', '.join(worse_fields)}.")
    if split_deltas.get("adversarial", {}).get("candidate_subset_accuracy", 0) < 0.35:
        recommendations.append("Keep adversarial holdout as a pressure test; do not train on it directly.")
    if language_deltas.get("ar", {}).get("candidate_subset_accuracy", 1.0) < language_deltas.get("en", {}).get("candidate_subset_accuracy", 0.0):
        recommendations.append("Add more Arabic and mixed Arabic/English train rows for the weakest fields.")
    return recommendations or ["No comparison-specific risk found; proceed to the parser promotion gate or next dataset expansion."]


def _delta(baseline, candidate):
    if baseline is None or candidate is None:
        return None
    return round(candidate - baseline, 3)


def _write_json(payload: Dict, path: str | Path) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return str(output_path)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Compare Shepherd-AI parser reports or learned-parser artifacts.")
    parser.add_argument("--baseline-report", default=None, help="Baseline parser report JSON with per-row results.")
    parser.add_argument("--candidate-report", default=None, help="Candidate parser report JSON with per-row results.")
    parser.add_argument("--baseline-artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Baseline learned parser artifact.")
    parser.add_argument("--candidate-artifact", default=str(DEFAULT_CANDIDATE_ARTIFACT_PATH), help="Candidate learned parser artifact.")
    parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    parser.add_argument("--splits", nargs="+", default=list(DEFAULT_COMPARE_SPLITS), help="Splits to compare.")
    parser.add_argument("--output", default=str(DEFAULT_COMPARISON_PATH), help="Output JSON comparison path.")
    parser.add_argument("--markdown", default=None, help="Optional Markdown comparison path.")
    parser.add_argument("--max-examples", type=int, default=20, help="Max examples per changed-example section.")
    parser.add_argument("--summary-only", action="store_true", help="Omit example lists from stdout.")
    args = parser.parse_args()

    if args.baseline_report or args.candidate_report:
        if not (args.baseline_report and args.candidate_report):
            parser.error("--baseline-report and --candidate-report must be provided together.")
        comparison = compare_reports(
            load_report(args.baseline_report),
            load_report(args.candidate_report),
            splits=args.splits,
            max_examples=args.max_examples,
        )
        comparison["sources"]["baseline"]["report_path"] = str(Path(args.baseline_report))
        comparison["sources"]["candidate"]["report_path"] = str(Path(args.candidate_report))
    else:
        comparison = compare_artifacts(
            args.baseline_artifact,
            args.candidate_artifact,
            dataset_path=args.dataset,
            adversarial_path=args.adversarial,
            splits=args.splits,
            max_examples=args.max_examples,
        )

    comparison_path = write_comparison(comparison, args.output)
    comparison["comparison_path"] = comparison_path
    if args.markdown:
        comparison["markdown_path"] = write_markdown_comparison(comparison, args.markdown)
    if args.summary_only:
        comparison = {
            key: value
            for key, value in comparison.items()
            if key not in {"improvements", "regressions", "changed_examples"}
        }
    print(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
