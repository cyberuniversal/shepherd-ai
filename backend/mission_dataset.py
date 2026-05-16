import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


DEFAULT_DATASET_PATH = Path("data/mission_commands/seed.jsonl")
SUPPORTED_LANGUAGES = {"en", "ar"}
REQUIRED_FIELDS = {
    "id",
    "language",
    "command",
    "expected_intent",
    "expected_constraints",
    "notes",
}
REQUIRED_INTENT_FIELDS = {"action", "drone_count", "pattern"}
REQUIRED_CONSTRAINT_FIELDS = {"confirmation_required", "nav_mode"}


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

    for index, example in enumerate(examples, 1):
        errors.extend(_validate_example(dataset_path, index, example, seen_ids, language_counts))

    return {
        "dataset": str(dataset_path),
        "valid": len(errors) == 0,
        "summary": {
            "total": len(examples),
            "language_counts": language_counts,
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
            "input": example["command"],
            "target_json": json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        })
    return rows


def _validate_example(
    dataset_path: Path,
    index: int,
    example: Dict,
    seen_ids: set,
    language_counts: Dict[str, int],
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

    command = example.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append(f"{label}: command must be a non-empty string")

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


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Validate or export Shepherd-AI mission-command dataset rows.")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate the dataset schema.")
    validate_parser.add_argument("--path", default=str(DEFAULT_DATASET_PATH), help="JSONL dataset path.")

    export_parser = subparsers.add_parser("export", help="Export input/target rows for parser training.")
    export_parser.add_argument("--path", default=str(DEFAULT_DATASET_PATH), help="JSONL dataset path.")

    args = parser.parse_args()
    command = args.command or "validate"
    if command == "export":
        print(json.dumps({"rows": export_training_rows(args.path)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    result = validate_dataset(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
