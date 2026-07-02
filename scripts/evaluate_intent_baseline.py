"""Evaluate the deterministic intent baseline on roadmap-derived samples."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402

DATASET_PATH = ROOT / "datasets" / "commands" / "roadmap_examples.jsonl"
OUTPUT_PATH = ROOT / "outputs" / "evaluations" / "intent_baseline_roadmap_examples.json"
FIELDS = ("action", "count", "location", "target", "constraints")


def load_examples(path: Path) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            record = json.loads(line)
            record["_line_number"] = line_number
            examples.append(record)
    return examples


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, bool]:
    return {field: expected.get(field) == actual.get(field) for field in FIELDS}


def evaluate() -> dict[str, Any]:
    examples = load_examples(DATASET_PATH)
    rows: list[dict[str, Any]] = []
    total_fields = 0
    matched_fields = 0

    for example in examples:
        parsed = parse_intent(example["text"]).to_dict()
        field_matches = compare(example["expected_intent"], parsed)
        total_fields += len(field_matches)
        matched_fields += sum(1 for matched in field_matches.values() if matched)
        rows.append(
            {
                "id": example["id"],
                "source": example["source"],
                "data_type": example["data_type"],
                "text": example["text"],
                "expected_intent": example["expected_intent"],
                "actual_intent": {field: parsed[field] for field in FIELDS},
                "field_matches": field_matches,
                "all_fields_match": all(field_matches.values()),
            }
        )

    exact_records = sum(1 for row in rows if row["all_fields_match"])
    result = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "parser": DETERMINISTIC_PARSER_NAME,
            "dataset": str(DATASET_PATH.relative_to(ROOT)),
            "dataset_note": "Roadmap-derived synthetic smoke sample, not a research benchmark.",
            "random_seed": None,
            "model_name": None,
            "model_version": None,
            "parameters": {},
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_records,
            "exact_record_accuracy": exact_records / len(rows) if rows else 0.0,
            "field_matches": matched_fields,
            "total_fields": total_fields,
            "field_accuracy": matched_fields / total_fields if total_fields else 0.0,
        },
        "records": rows,
    }
    return result


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = evaluate()
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
