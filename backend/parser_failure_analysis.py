import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

try:
    from backend.learned_parser import DEFAULT_ARTIFACT_PATH, evaluate_artifact_on_splits, load_artifact, load_frozen_splits
    from backend.mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH, EVALUATED_INTENT_FIELDS
except ImportError:
    from learned_parser import DEFAULT_ARTIFACT_PATH, evaluate_artifact_on_splits, load_artifact, load_frozen_splits
    from mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH, EVALUATED_INTENT_FIELDS


FAILURE_ANALYSIS_SCHEMA = "shepherd-parser-failure-analysis/1.0"
DEFAULT_FAILURE_ANALYSIS_PATH = Path(".tmp_models/parser_failure_analysis.json")
DEFAULT_FAILURE_MARKDOWN_PATH = Path(".tmp_models/parser_failure_analysis.md")


def analyze_report(report: Dict, *, max_examples_per_group: int = 8) -> Dict:
    rows = _flatten_results(report)
    failures = [row for row in rows if row["failed_fields"]]
    split_counts = Counter(row["split"] for row in rows)
    split_failures = Counter(row["split"] for row in failures)
    language_counts = Counter(row["language"] for row in rows)
    language_failures = Counter(row["language"] for row in failures)
    field_failures = Counter(field for row in failures for field in row["failed_fields"])
    category_counts = Counter(category for row in rows for category in row["categories"])
    category_failures = Counter(category for row in failures for category in row["categories"])

    by_split = {
        split: _rate_group(split_counts[split], split_failures[split])
        for split in sorted(split_counts)
    }
    by_language = {
        language: _rate_group(language_counts[language], language_failures[language])
        for language in sorted(language_counts)
    }
    by_category = {
        category: _rate_group(category_counts[category], category_failures[category])
        for category in sorted(category_counts)
    }
    field_details = {
        field: _field_detail(field, failures, max_examples_per_group)
        for field in EVALUATED_INTENT_FIELDS
        if field_failures[field]
    }
    highest_risk_examples = sorted(
        (_example_summary(row) for row in failures),
        key=lambda item: (-len(item["failed_fields"]), item["split"], item["language"], item["id"]),
    )[:25]

    return {
        "schema": FAILURE_ANALYSIS_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "schema": report.get("schema"),
            "dataset": report.get("dataset"),
            "model_id": report.get("model_id"),
            "artifact_digest": report.get("artifact_digest"),
        },
        "summary": {
            "total_examples": len(rows),
            "failed_examples": len(failures),
            "failure_rate": round(len(failures) / len(rows), 3) if rows else 0.0,
            "field_failure_counts": dict(field_failures),
            "top_failed_fields": field_failures.most_common(),
            "top_failed_categories": category_failures.most_common(),
        },
        "by_split": by_split,
        "by_language": by_language,
        "by_category": by_category,
        "field_details": field_details,
        "highest_risk_examples": highest_risk_examples,
        "recommendations": _recommendations(field_failures, category_failures, by_language),
    }


def analyze_learned_artifact(
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
    *,
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
    max_examples_per_group: int = 8,
) -> Dict:
    artifact = load_artifact(artifact_path)
    splits = load_frozen_splits(dataset_path, adversarial_path=adversarial_path)
    report = evaluate_artifact_on_splits(artifact, splits)
    analysis = analyze_report(report, max_examples_per_group=max_examples_per_group)
    analysis["source"]["artifact_path"] = str(Path(artifact_path))
    return analysis


def load_report(path: str | Path) -> Dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_analysis(analysis: Dict, output_path: str | Path) -> str:
    return _write_json(analysis, output_path)


def write_markdown_analysis(analysis: Dict, output_path: str | Path) -> str:
    lines = [
        "# Shepherd-AI Parser Failure Analysis",
        "",
        f"- Source schema: `{analysis.get('source', {}).get('schema')}`",
        f"- Model: `{analysis.get('source', {}).get('model_id')}`",
        f"- Total examples: `{analysis['summary']['total_examples']}`",
        f"- Failed examples: `{analysis['summary']['failed_examples']}`",
        f"- Failure rate: `{analysis['summary']['failure_rate']}`",
        "",
        "## Failed Fields",
        "",
        "| Field | Failures |",
        "| --- | ---: |",
    ]
    for field, count in analysis["summary"]["top_failed_fields"]:
        lines.append(f"| {field} | {count} |")

    lines.extend(["", "## Splits", "", "| Split | Total | Failures | Failure Rate |", "| --- | ---: | ---: | ---: |"])
    for split, group in analysis.get("by_split", {}).items():
        lines.append(f"| {split} | {group['total']} | {group['failures']} | {group['failure_rate']} |")

    lines.extend(["", "## Languages", "", "| Language | Total | Failures | Failure Rate |", "| --- | ---: | ---: | ---: |"])
    for language, group in analysis.get("by_language", {}).items():
        lines.append(f"| {language} | {group['total']} | {group['failures']} | {group['failure_rate']} |")

    lines.extend(["", "## Categories", "", "| Category | Total | Failures | Failure Rate |", "| --- | ---: | ---: | ---: |"])
    for category, group in analysis.get("by_category", {}).items():
        lines.append(f"| {category} | {group['total']} | {group['failures']} | {group['failure_rate']} |")

    lines.extend(["", "## Field Details", ""])
    for field, detail in analysis.get("field_details", {}).items():
        lines.append(f"### {field}")
        lines.append("")
        lines.append("| Expected | Predicted | Count |")
        lines.append("| --- | --- | ---: |")
        for item in detail.get("top_confusions", []):
            lines.append(f"| `{item['expected']}` | `{item['predicted']}` | {item['count']} |")
        if detail.get("examples"):
            lines.append("")
            lines.append("Examples:")
            for example in detail["examples"]:
                lines.append(f"- `{example['id']}` ({example['language']}/{example['split']}): {example['command']}")
        lines.append("")

    lines.extend(["## Highest Risk Examples", ""])
    for example in analysis.get("highest_risk_examples", []):
        failed = ", ".join(example["failed_fields"])
        lines.append(f"- `{example['id']}` ({example['language']}/{example['split']}): {failed}")

    lines.extend(["", "## Recommendations", ""])
    for recommendation in analysis.get("recommendations", []):
        lines.append(f"- {recommendation}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _flatten_results(report: Dict) -> List[Dict]:
    if "split_reports" in report:
        rows = []
        for split_name, split_report in report.get("split_reports", {}).items():
            for result in split_report.get("results", []):
                rows.append(_normalize_result_row(result, fallback_split=split_name))
        return rows
    return [_normalize_result_row(result, fallback_split=result.get("split", "unknown")) for result in report.get("results", [])]


def _normalize_result_row(result: Dict, *, fallback_split: str) -> Dict:
    field_results = result.get("field_results", {})
    failed_fields = []
    normalized_fields = {}
    for field, field_result in field_results.items():
        expected = field_result.get("expected")
        predicted = field_result.get("predicted", field_result.get("parsed"))
        matched = bool(field_result.get("matched"))
        normalized_fields[field] = {
            "expected": expected,
            "predicted": predicted,
            "matched": matched,
        }
        if not matched:
            failed_fields.append(field)

    command = result.get("command", "")
    split = result.get("split") or fallback_split
    language = result.get("language", "unknown")
    return {
        "id": result.get("id", "unknown"),
        "language": language,
        "split": split,
        "command": command,
        "field_results": normalized_fields,
        "failed_fields": failed_fields,
        "categories": _categories_for_result(command, normalized_fields, split),
    }


def _categories_for_result(command: str, field_results: Dict, split: str) -> List[str]:
    lower = command.lower()
    expected_target = _normalize_value(field_results.get("target_zone", {}).get("expected"))
    expected_action = _normalize_value(field_results.get("action", {}).get("expected"))
    expected_reference = _normalize_value(field_results.get("target_reference", {}).get("expected"))
    categories = [f"split:{split}"]
    if expected_target == "unknown":
        categories.append("ambiguous_target")
    if expected_target == "coordinates" or any(char.isdigit() for char in lower):
        categories.append("coordinates")
    if expected_target in {"multi_target", "route_between_known_zones"}:
        categories.append("multi_target")
    if expected_reference in {"operator", "operator_relative"}:
        categories.append("operator_reference")
    if expected_action in {"return", "rendezvous", "hold", "land", "cancel", "patrol"}:
        categories.append(f"action:{expected_action}")
    if any(term in lower for term in ["urgent", "fast", "emergency", "عاجل", "بسرعة"]):
        categories.append("priority_or_urgency")
    if any(term in lower for term in ["don't", "do not", "لا "]):
        categories.append("negation")
    if any(term in lower for term in ["if", "unless", "إذا", "اذا"]):
        categories.append("conditional")
    if any(term in lower for term in ["there", "that", "same", "last", "yesterday", "هناك", "نفس", "آخر"]):
        categories.append("deictic_or_memory_reference")
    return sorted(set(categories))


def _field_detail(field: str, failures: Iterable[Dict], max_examples_per_group: int) -> Dict:
    confusion = Counter()
    examples = []
    for row in failures:
        if field not in row["failed_fields"]:
            continue
        field_result = row["field_results"][field]
        expected = _render_value(field_result.get("expected"))
        predicted = _render_value(field_result.get("predicted"))
        confusion[(expected, predicted)] += 1
        if len(examples) < max_examples_per_group:
            examples.append(_example_summary(row))
    return {
        "top_confusions": [
            {"expected": expected, "predicted": predicted, "count": count}
            for (expected, predicted), count in confusion.most_common(15)
        ],
        "examples": examples,
    }


def _example_summary(row: Dict) -> Dict:
    return {
        "id": row["id"],
        "language": row["language"],
        "split": row["split"],
        "command": row["command"],
        "failed_fields": row["failed_fields"],
        "categories": row["categories"],
    }


def _rate_group(total: int, failures: int) -> Dict:
    return {
        "total": total,
        "failures": failures,
        "failure_rate": round(failures / total, 3) if total else 0.0,
    }


def _recommendations(field_failures: Counter, category_failures: Counter, by_language: Dict) -> List[str]:
    recommendations = []
    if field_failures.get("target_zone", 0):
        recommendations.append("Prioritize canonical target-zone labels, aliases, and target extraction examples.")
    if field_failures.get("drone_count", 0):
        recommendations.append("Add count-focused examples for digits, number words, implicit pairs, and fleet-wide commands.")
    if field_failures.get("action", 0):
        recommendations.append("Add action-disambiguation examples for return, hold, cancel, land, patrol, inspect, and scout.")
    if field_failures.get("pattern", 0):
        recommendations.append("Expand pattern labels with direct, perimeter, grid, corridor, search, circle, and stationary examples.")
    if category_failures.get("operator_reference", 0):
        recommendations.append("Add operator-relative commands with explicit labels for operator and operator_relative references.")
    if category_failures.get("ambiguous_target", 0):
        recommendations.append("Keep ambiguous/deictic commands in evaluation and add clarification-focused training rows.")
    if category_failures.get("conditional", 0) or category_failures.get("negation", 0):
        recommendations.append("Separate negation and conditional commands into explicit clarify/cancel/blocked-intent examples.")
    if by_language.get("ar", {}).get("failure_rate", 0) > by_language.get("en", {}).get("failure_rate", 0):
        recommendations.append("Increase Arabic and mixed Arabic/English rows for the highest-failing fields.")
    return recommendations or ["No dominant failure class found; inspect highest-risk examples manually."]


def _normalize_value(value):
    if isinstance(value, str):
        return " ".join(value.lower().strip().split())
    return value


def _render_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


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

    parser = argparse.ArgumentParser(description="Analyze Shepherd-AI parser evaluation failures.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--report", help="Existing parser evaluation report JSON with per-row results.")
    source.add_argument("--artifact", help="Learned parser artifact to evaluate and analyze.")
    parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    parser.add_argument("--output", default=str(DEFAULT_FAILURE_ANALYSIS_PATH), help="Output JSON analysis path.")
    parser.add_argument("--markdown", default=None, help="Optional Markdown analysis path.")
    parser.add_argument("--max-examples", type=int, default=8, help="Max examples to include per field group.")
    args = parser.parse_args()

    if args.report:
        analysis = analyze_report(load_report(args.report), max_examples_per_group=args.max_examples)
    else:
        analysis = analyze_learned_artifact(
            args.artifact,
            dataset_path=args.dataset,
            adversarial_path=args.adversarial,
            max_examples_per_group=args.max_examples,
        )

    analysis_path = write_analysis(analysis, args.output)
    analysis["analysis_path"] = analysis_path
    if args.markdown:
        analysis["markdown_path"] = write_markdown_analysis(analysis, args.markdown)
    print(json.dumps(analysis, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
