"""Evaluate saved Hugging Face transcript intent predictions against human labels."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.intent_training import EVAL_FIELDS  # noqa: E402
from shepherd_ai.span_intent import validate_assembled_intent  # noqa: E402


PREDICTION_SYSTEM_FIELDS = ("span_intent_assembly", "hybrid_span_parser")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, help="Saved transcript prediction JSON.")
    parser.add_argument("--gold-commands", required=True, help="Human-reviewed intent-label JSONL.")
    parser.add_argument("--output", required=True, help="Path to write evaluation JSON.")
    parser.add_argument(
        "--include-deterministic",
        action="store_true",
        help="Also evaluate the deterministic parser on the same transcript text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    gold_records = load_gold_commands(args.gold_commands)
    evaluation = evaluate_transcript_intent_predictions(
        predictions,
        gold_records,
        include_deterministic=args.include_deterministic,
        metadata={
            "predictions": args.predictions,
            "gold_commands": args.gold_commands,
        },
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluation, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evaluation["summary"], indent=2, sort_keys=True))


def load_gold_commands(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        _reject_nonfinal_gold_record(record, line_number=line_number)
        records.append(record)
    return records


def evaluate_transcript_intent_predictions(
    prediction_payload: dict[str, Any],
    gold_records: list[dict[str, Any]],
    *,
    include_deterministic: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gold_by_audio_id = _gold_by_audio_id(gold_records)
    rows: list[dict[str, Any]] = []
    unmatched_prediction_ids: list[str] = []

    for prediction in prediction_payload.get("records", []):
        prediction_id = str(prediction.get("id"))
        gold = gold_by_audio_id.get(prediction_id)
        if gold is None:
            unmatched_prediction_ids.append(prediction_id)
            continue
        expected_intent = _project_intent(gold["expected_intent"])
        transcript = str(prediction.get("transcript", ""))
        system_intents: dict[str, dict[str, Any]] = {
            system_name: _project_intent(prediction.get(system_name, {}))
            for system_name in PREDICTION_SYSTEM_FIELDS
        }
        if include_deterministic:
            system_intents[DETERMINISTIC_PARSER_NAME] = _project_intent(parse_intent(transcript).to_dict())

        for system_name, actual_intent in system_intents.items():
            field_matches = {
                field: expected_intent.get(field) == actual_intent.get(field)
                for field in EVAL_FIELDS
            }
            rows.append(
                {
                    "id": prediction_id,
                    "gold_record_id": str(gold.get("id")),
                    "split": gold.get("split", prediction.get("split", "not stated")),
                    "system": system_name,
                    "transcript_field": prediction.get("transcript_field", "not stated"),
                    "transcript": transcript,
                    "gold_text": gold.get("text"),
                    "expected_intent": expected_intent,
                    "actual_intent": actual_intent,
                    "actual_validation": validate_assembled_intent(actual_intent),
                    "field_matches": field_matches,
                    "all_fields_match": all(field_matches.values()),
                }
            )

    source_metadata = prediction_payload.get("metadata", {})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_prediction_model_dir": source_metadata.get("model_dir", "not stated"),
            "source_transcript_field": source_metadata.get("transcript_field", "not stated"),
            "source_input_jsonl": source_metadata.get("input_jsonl", "not stated"),
            "source_runtime": source_metadata.get("runtime", {}),
            "fields": list(EVAL_FIELDS),
            "systems": sorted({row["system"] for row in rows}),
            "unmatched_prediction_ids": unmatched_prediction_ids,
            "note": (
                "Intent-field evaluation for saved Hugging Face transcript predictions. Gold labels must "
                "be human-reviewed records matched by audio id. ASR and human-transcript prediction files "
                "must be evaluated separately."
            ),
            **(metadata or {}),
        },
        "summary": _summarize(rows),
        "records": rows,
    }


def _gold_by_audio_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        audio_id = record.get("audio_id")
        if audio_id is None:
            raise ValueError(f"gold record missing audio_id: {record.get('id')!r}")
        grouped[str(audio_id)].append(record)

    result: dict[str, dict[str, Any]] = {}
    for audio_id, matches in grouped.items():
        intents = [_project_intent(record["expected_intent"]) for record in matches]
        first_intent = intents[0]
        if any(intent != first_intent for intent in intents[1:]):
            raise ValueError(f"conflicting expected intents for audio id: {audio_id}")
        result[audio_id] = matches[0]
    return result


def _reject_nonfinal_gold_record(record: dict[str, Any], *, line_number: int) -> None:
    data_type = str(record.get("data_type", ""))
    label_source = str(record.get("label_source", ""))
    review_status = record.get("review_status")
    if "draft" in data_type or label_source.endswith("_draft"):
        raise ValueError(f"line {line_number}: draft labels cannot be used as gold commands")
    if review_status is not None and review_status != "human_reviewed":
        raise ValueError(f"line {line_number}: review_status must be 'human_reviewed'")
    if "expected_intent" not in record:
        raise ValueError(f"line {line_number}: missing expected_intent")
    for field in EVAL_FIELDS:
        if field not in record["expected_intent"]:
            raise ValueError(f"line {line_number}: expected_intent missing {field}")


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["system"])].append(row)
    return {system: _summarize_group(system_rows) for system, system_rows in sorted(grouped.items())}


def _summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    field_matches = 0
    total_fields = 0
    field_error_counts: Counter[str] = Counter()
    validation_issue_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        split = str(row.get("split", "not stated"))
        split_counts[split]["records"] += 1
        if row["all_fields_match"]:
            split_counts[split]["exact_record_matches"] += 1
        for field, matched in row["field_matches"].items():
            total_fields += 1
            if matched:
                field_matches += 1
            else:
                field_error_counts[field] += 1
        for issue in row.get("actual_validation", {}).get("issues", []):
            validation_issue_counts[str(issue.get("code"))] += 1

    exact_matches = sum(1 for row in rows if row["all_fields_match"])
    return {
        "records": len(rows),
        "exact_record_matches": exact_matches,
        "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
        "field_matches": field_matches,
        "total_fields": total_fields,
        "field_accuracy": field_matches / total_fields if total_fields else 0.0,
        "field_error_counts": dict(sorted(field_error_counts.items())),
        "validation_issue_counts": dict(sorted(validation_issue_counts.items())),
        "records_with_validation_issues": sum(
            1 for row in rows if row.get("actual_validation", {}).get("issues")
        ),
        "split_counts": {split: dict(counts) for split, counts in sorted(split_counts.items())},
    }


def _project_intent(intent: dict[str, Any]) -> dict[str, Any]:
    return {field: intent.get(field) for field in EVAL_FIELDS}


if __name__ == "__main__":
    main()
