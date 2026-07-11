"""Measure whether ASR transcript differences change span-assembled intent JSON."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import EVAL_FIELDS  # noqa: E402
from shepherd_ai.span_intent import (  # noqa: E402
    assemble_hybrid_intent_from_entities,
    assemble_intent_from_entities,
    validate_assembled_intent,
)


Assembler = Callable[[str, list[list[Any]]], dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--span-impact", required=True, help="ASR span-impact JSON from analyze_asr_span_impact.py.")
    parser.add_argument("--output", required=True, help="Path to write ASR span-intent impact JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    span_impact = json.loads(Path(args.span_impact).read_text(encoding="utf-8"))
    result = analyze_asr_span_intent_impact(span_impact, source_path=args.span_impact)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


def analyze_asr_span_intent_impact(span_impact: dict[str, Any], *, source_path: str) -> dict[str, Any]:
    """Compare span-assembled intents on human transcripts and ASR transcripts."""

    systems: dict[str, Assembler] = {
        "span_intent_assembly": assemble_intent_from_entities,
        "hybrid_span_parser": assemble_hybrid_intent_from_entities,
    }
    rows: list[dict[str, Any]] = []
    for record in span_impact.get("records", []):
        human_text = str(record.get("human_transcript", ""))
        asr_text = str(record.get("asr_transcript", ""))
        human_entities = _entity_records_to_tuples(record.get("human_predicted_entities", []))
        asr_entities = _entity_records_to_tuples(record.get("asr_predicted_entities", []))
        for system_name, assembler in systems.items():
            human_intent = assembler(human_text, human_entities)
            asr_intent = assembler(asr_text, asr_entities)
            field_matches = {field: human_intent.get(field) == asr_intent.get(field) for field in EVAL_FIELDS}
            rows.append(
                {
                    "id": str(record.get("id")),
                    "split": record.get("split", "not stated"),
                    "span_record_id": record.get("span_record_id"),
                    "system": system_name,
                    "human_transcript": human_text,
                    "asr_transcript": asr_text,
                    "raw_transcript_changed": bool(record.get("raw_transcript_changed")),
                    "normalized_word_changed": bool(record.get("normalized_word_changed")),
                    "semantic_span_prediction_changed": bool(record.get("semantic_span_prediction_changed")),
                    "human_intent": human_intent,
                    "asr_intent": asr_intent,
                    "human_validation": validate_assembled_intent(human_intent),
                    "asr_validation": validate_assembled_intent(asr_intent),
                    "field_matches": field_matches,
                    "intent_changed": not all(field_matches.values()),
                }
            )

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_span_impact": source_path,
            "source_model_name": span_impact.get("metadata", {}).get("model_name", "not stated"),
            "source_model_version": span_impact.get("metadata", {}).get("model_version", "not stated"),
            "evaluation_note": (
                "ASR-to-span-intent impact analysis. This compares intent JSON assembled from span-model "
                "predictions on human transcripts versus Whisper transcripts. It is not gold ASR intent "
                "accuracy because no human-verified span labels exist for the Whisper transcript text."
            ),
        },
        "summary": _summarize(rows),
        "records": rows,
    }


def _entity_records_to_tuples(entities: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [str(entity["field"]), int(entity["start"]), int(entity["end"])]
        for entity in entities
    ]


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["system"])].append(row)
    return {system: _summarize_system(system_rows) for system, system_rows in sorted(grouped.items())}


def _summarize_system(rows: list[dict[str, Any]]) -> dict[str, Any]:
    field_change_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    asr_validation_issue_counts: Counter[str] = Counter()
    for row in rows:
        split = str(row.get("split", "not stated"))
        split_counts[split]["records"] += 1
        if row["raw_transcript_changed"]:
            split_counts[split]["raw_transcript_changed"] += 1
        if row["normalized_word_changed"]:
            split_counts[split]["normalized_word_changed"] += 1
        if row["semantic_span_prediction_changed"]:
            split_counts[split]["semantic_span_prediction_changed"] += 1
        if row["intent_changed"]:
            split_counts[split]["intent_changed"] += 1
        for field, matched in row["field_matches"].items():
            if not matched:
                field_change_counts[field] += 1
        for issue in row["asr_validation"].get("issues", []):
            asr_validation_issue_counts[str(issue.get("code"))] += 1

    records = len(rows)
    changed_records = sum(1 for row in rows if row["intent_changed"])
    return {
        "records": records,
        "intent_changed_records": changed_records,
        "intent_changed_rate": changed_records / records if records else 0.0,
        "raw_transcript_changed_records": sum(1 for row in rows if row["raw_transcript_changed"]),
        "normalized_word_changed_records": sum(1 for row in rows if row["normalized_word_changed"]),
        "semantic_span_prediction_changed_records": sum(
            1 for row in rows if row["semantic_span_prediction_changed"]
        ),
        "unchanged_intent_when_normalized_word_changed": sum(
            1 for row in rows if row["normalized_word_changed"] and not row["intent_changed"]
        ),
        "field_change_counts": dict(sorted(field_change_counts.items())),
        "asr_validation_issue_counts": dict(sorted(asr_validation_issue_counts.items())),
        "split_counts": {split: dict(counts) for split, counts in sorted(split_counts.items())},
    }


if __name__ == "__main__":
    main()
