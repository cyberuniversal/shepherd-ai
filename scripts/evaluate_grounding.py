"""Evaluate deterministic grounding on a labeled development JSONL file."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_DATASET = ROOT / "datasets" / "maps" / "grounding_examples_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "grounding_examples_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = evaluate(args.map, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


def evaluate(map_path: Path, dataset_path: Path) -> dict[str, Any]:
    locations = load_map_locations(map_path)
    records = _load_jsonl(dataset_path)
    rows: list[dict[str, Any]] = []
    total_references = 0
    matched_references = 0

    for record in records:
        intent = parse_intent(record["text"]).to_dict()
        grounded = ground_intent(intent, locations)
        references = {reference.field: reference for reference in grounded.references}
        field_matches: dict[str, bool] = {}
        for field_name in record["expected_grounding"]:
            expected = record["expected_grounding"][field_name]
            actual = references.get(field_name)
            actual_status = actual.status if actual else "missing_reference"
            actual_location_id = actual.location.id if actual and actual.location else None
            actual_candidate_ids = [candidate.id for candidate in actual.candidates] if actual else []
            matched = (
                expected["status"] == actual_status
                and expected.get("location_id") == actual_location_id
                and expected.get("candidate_ids", actual_candidate_ids) == actual_candidate_ids
            )
            field_matches[field_name] = matched
            total_references += 1
            matched_references += int(matched)

        rows.append(
            {
                "id": record["id"],
                "text": record["text"],
                "split": record.get("split"),
                "expected_grounding": record["expected_grounding"],
                "actual_grounding": {
                    field: {
                        "status": references[field].status if field in references else "missing_reference",
                        "location_id": references[field].location.id if field in references and references[field].location else None,
                        "candidate_ids": [candidate.id for candidate in references[field].candidates] if field in references else [],
                    }
                    for field in record["expected_grounding"]
                },
                "field_matches": field_matches,
                "all_fields_match": all(field_matches.values()),
                "ready_for_planning": grounded.ready_for_planning,
                "issues": list(grounded.issues),
            }
        )

    exact_records = sum(1 for row in rows if row["all_fields_match"])
    data_types = sorted(
        {
            str(record.get("data_type"))
            for record in records
            if record.get("data_type")
        }
    )
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(map_path),
            "dataset": str(dataset_path),
            "parser": DETERMINISTIC_PARSER_NAME,
            "dataset_note": _dataset_note(data_types),
            "data_types": data_types,
            "random_seed": None,
            "model_name": None,
            "model_version": None,
            "parameters": {"matching": "normalized_name_or_alias_exact_or_embedded_longest_match"},
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_records,
            "exact_record_accuracy": exact_records / len(rows) if rows else 0.0,
            "reference_matches": matched_references,
            "total_references": total_references,
            "reference_accuracy": matched_references / total_references if total_references else 0.0,
        },
        "records": rows,
    }


def _dataset_note(data_types: list[str]) -> str:
    if data_types and all("human" in data_type for data_type in data_types):
        return (
            "Human-written Week 3 grounding evaluation over the custom synthetic map. "
            "This is human command evidence, not real-world map evidence."
        )
    return (
        "Synthetic Week 3 grounding evaluation, not a real-world "
        "grounding benchmark or human-collected held-out set."
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if "text" not in record or "expected_grounding" not in record:
            raise ValueError(f"line {line_number}: missing text or expected_grounding")
        records.append(record)
    if not records:
        raise ValueError("grounding evaluation dataset is empty")
    return records


if __name__ == "__main__":
    main()
