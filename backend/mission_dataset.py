import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List


DEFAULT_DATASET_PATH = Path("data/mission_commands/seed.jsonl")
SUPPORTED_LANGUAGES = {"en", "ar"}
SUPPORTED_SPLITS = {"train", "eval", "holdout"}
REQUIRED_FIELDS = {
    "id",
    "language",
    "split",
    "command",
    "expected_intent",
    "expected_constraints",
    "should_clarify",
    "notes",
}
REQUIRED_INTENT_FIELDS = {"action", "target_zone", "drone_count", "pattern"}
REQUIRED_CONSTRAINT_FIELDS = {"confirmation_required", "nav_mode"}
EVALUATED_INTENT_FIELDS = ["action", "target_zone", "target_reference", "drone_count", "pattern", "priority"]


def load_examples(path: str | Path = DEFAULT_DATASET_PATH) -> List[Dict]:
    dataset_path = Path(path)
    examples = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                example = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{dataset_path}:{line_number}: invalid JSON: {exc}") from exc
            example["_line_number"] = line_number
            examples.append(example)
    return examples


def validate_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> Dict:
    dataset_path = Path(path)
    examples = load_examples(dataset_path)
    errors = []
    seen_ids = set()
    language_counts = {language: 0 for language in sorted(SUPPORTED_LANGUAGES)}
    split_counts = {split: 0 for split in sorted(SUPPORTED_SPLITS)}

    for index, example in enumerate(examples, 1):
        errors.extend(_validate_example(dataset_path, index, example, seen_ids, language_counts, split_counts))

    return {
        "dataset": str(dataset_path),
        "valid": len(errors) == 0,
        "summary": {
            "total": len(examples),
            "language_counts": language_counts,
            "split_counts": split_counts,
            "unique_ids": len(seen_ids),
        },
        "errors": errors,
    }


def export_training_rows(path: str | Path = DEFAULT_DATASET_PATH) -> List[Dict]:
    rows = []
    for example in load_examples(path):
        target = {
            "intent": example["expected_intent"],
            "constraints": example["expected_constraints"],
        }
        rows.append({
            "id": example["id"],
            "language": example["language"],
            "split": example["split"],
            "input": example["command"],
            "should_clarify": bool(example["should_clarify"]),
            "target_json": json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        })
    return rows


async def evaluate_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> Dict:
    validation = validate_dataset(path)
    if not validation["valid"]:
        return {
            "dataset": validation["dataset"],
            "valid": False,
            "summary": validation["summary"],
            "errors": validation["errors"],
            "results": [],
        }

    try:
        from backend.brain import MissionParser
    except ImportError:
        from brain import MissionParser

    parser = MissionParser()
    parser._ollama_available = False
    examples = load_examples(path)
    results = []
    field_totals = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    field_matches = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    clarify_matches = 0

    for example in examples:
        parsed = await parser.parse_intent(example["command"])
        expected = example["expected_intent"]
        field_results = {}
        for field in EVALUATED_INTENT_FIELDS:
            if field not in expected:
                continue
            expected_value = expected.get(field)
            parsed_value = parsed.get(field)
            matched = _normalize_value(parsed_value) == _normalize_value(expected_value)
            field_totals[field] += 1
            if matched:
                field_matches[field] += 1
            field_results[field] = {
                "expected": expected_value,
                "parsed": parsed_value,
                "matched": matched,
            }

        expected_clarify = bool(example.get("should_clarify"))
        parsed_clarify = _parsed_should_clarify(parsed)
        if expected_clarify == parsed_clarify:
            clarify_matches += 1

        results.append({
            "id": example["id"],
            "language": example["language"],
            "split": example["split"],
            "command": example["command"],
            "field_results": field_results,
            "should_clarify": {
                "expected": expected_clarify,
                "parsed": parsed_clarify,
                "matched": expected_clarify == parsed_clarify,
            },
            "parsed_intent": parsed,
            "subset_match": all(result["matched"] for result in field_results.values()),
        })

    field_metrics = {
        field: {
            "matched": field_matches[field],
            "total": field_totals[field],
            "accuracy": round(field_matches[field] / field_totals[field], 3) if field_totals[field] else None,
        }
        for field in EVALUATED_INTENT_FIELDS
    }

    return {
        "dataset": str(Path(path)),
        "valid": True,
        "summary": {
            **validation["summary"],
            "evaluated": len(results),
            "subset_matches": len([result for result in results if result["subset_match"]]),
            "clarification_matches": clarify_matches,
            "field_metrics": field_metrics,
        },
        "errors": [],
        "results": results,
    }


def _validate_example(
    dataset_path: Path,
    index: int,
    example: Dict,
    seen_ids: set,
    language_counts: Dict[str, int],
    split_counts: Dict[str, int],
) -> List[str]:
    label = f"{dataset_path}:{example.get('_line_number', index)}"
    errors = []
    missing = sorted(REQUIRED_FIELDS - set(example))
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
        return errors

    example_id = example.get("id")
    if not isinstance(example_id, str) or not example_id:
        errors.append(f"{label}: id must be a non-empty string")
    elif example_id in seen_ids:
        errors.append(f"{label}: duplicate id {example_id}")
    else:
        seen_ids.add(example_id)

    language = example.get("language")
    if language not in SUPPORTED_LANGUAGES:
        errors.append(f"{label}: unsupported language {language}")
    else:
        language_counts[language] += 1

    split = example.get("split")
    if split not in SUPPORTED_SPLITS:
        errors.append(f"{label}: unsupported split {split}")
    else:
        split_counts[split] += 1

    command = example.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append(f"{label}: command must be a non-empty string")

    if not isinstance(example.get("should_clarify"), bool):
        errors.append(f"{label}: should_clarify must be a boolean")

    intent = example.get("expected_intent")
    if not isinstance(intent, dict):
        errors.append(f"{label}: expected_intent must be an object")
    else:
        missing_intent = sorted(REQUIRED_INTENT_FIELDS - set(intent))
        if missing_intent:
            errors.append(f"{label}: expected_intent missing fields: {', '.join(missing_intent)}")
        if not isinstance(intent.get("drone_count"), int) or intent.get("drone_count", 0) < 1:
            errors.append(f"{label}: expected_intent.drone_count must be a positive integer")

    constraints = example.get("expected_constraints")
    if not isinstance(constraints, dict):
        errors.append(f"{label}: expected_constraints must be an object")
    else:
        missing_constraints = sorted(REQUIRED_CONSTRAINT_FIELDS - set(constraints))
        if missing_constraints:
            errors.append(f"{label}: expected_constraints missing fields: {', '.join(missing_constraints)}")

    return errors


def _normalize_value(value):
    if isinstance(value, str):
        return " ".join(value.lower().strip().split())
    return value


def _parsed_should_clarify(parsed: Dict) -> bool:
    target_zone = _normalize_value(parsed.get("target_zone"))
    if target_zone in {"unknown", "", None, "undefined"}:
        return True
    try:
        confidence = float(parsed.get("confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0
    return bool(parsed.get("clarifying_question")) and confidence <= 0.5


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Validate or export Shepherd-AI mission-command dataset rows.")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate the dataset schema.")
    validate_parser.add_argument("--path", default=str(DEFAULT_DATASET_PATH), help="JSONL dataset path.")

    export_parser = subparsers.add_parser("export", help="Export input/target rows for parser training.")
    export_parser.add_argument("--path", default=str(DEFAULT_DATASET_PATH), help="JSONL dataset path.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate the offline heuristic parser against the dataset.")
    evaluate_parser.add_argument("--path", default=str(DEFAULT_DATASET_PATH), help="JSONL dataset path.")
    evaluate_parser.add_argument("--summary-only", action="store_true", help="Omit per-row parser results.")

    args = parser.parse_args()
    command = args.command or "validate"
    if command == "export":
        print(json.dumps({"rows": export_training_rows(args.path)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if command == "evaluate":
        result = asyncio.run(evaluate_dataset(args.path))
        if args.summary_only:
            result = {key: value for key, value in result.items() if key != "results"}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["valid"] else 1

    result = validate_dataset(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
