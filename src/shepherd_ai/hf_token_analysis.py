"""Evaluation helpers for Hugging Face BIO token-classifier outputs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def evaluate_hf_token_predictions(
    records: list[dict[str, Any]],
    predictions_by_id: dict[str, list[str]],
    *,
    dataset_name: str,
    model_name: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a span-tagger-compatible evaluation JSON payload.

    The returned shape intentionally matches `evaluate_span_tagger()` records so
    the existing BIO error analyzer can be reused for transformer outputs.
    """

    rows: list[dict[str, Any]] = []
    total_tokens = 0
    matched_tokens = 0
    expected_entities_total = 0
    predicted_entities_total = 0
    matched_entities_total = 0
    data_types: set[str] = set()
    for record in records:
        record_id = str(record["id"])
        expected_tags = [str(tag) for tag in record["labels"]]
        predicted_tags = predictions_by_id[record_id]
        if len(expected_tags) != len(predicted_tags):
            raise ValueError(
                f"{record_id}: expected {len(expected_tags)} predicted tags, got {len(predicted_tags)}"
            )
        tokens = [str(token) for token in record["tokens"]]
        offsets = [[int(start), int(end)] for start, end in record["offsets"]]
        token_matches = [expected == actual for expected, actual in zip(expected_tags, predicted_tags)]
        expected_entities = set(entities_from_bio(expected_tags, offsets))
        predicted_entities = set(entities_from_bio(predicted_tags, offsets))
        matched_entities = expected_entities & predicted_entities
        total_tokens += len(expected_tags)
        matched_tokens += sum(1 for matched in token_matches if matched)
        expected_entities_total += len(expected_entities)
        predicted_entities_total += len(predicted_entities)
        matched_entities_total += len(matched_entities)
        data_types.add(str(record.get("data_type", "not stated")))
        rows.append(
            {
                "id": record_id,
                "split": record.get("split"),
                "text": record.get("text"),
                "tokens": tokens,
                "offsets": offsets,
                "expected_tags": expected_tags,
                "predicted_tags": predicted_tags,
                "token_matches": token_matches,
                "expected_entities": [list(entity) for entity in sorted(expected_entities)],
                "predicted_entities": [list(entity) for entity in sorted(predicted_entities)],
            }
        )
    precision = matched_entities_total / predicted_entities_total if predicted_entities_total else 0.0
    recall = matched_entities_total / expected_entities_total if expected_entities_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "dataset": dataset_name,
            "data_types": sorted(data_types),
            "note": "Human-verified span command evaluation; not ASR or end-to-end mission performance.",
            **(metadata or {}),
        },
        "summary": {
            "records": len(rows),
            "tokens": total_tokens,
            "token_matches": matched_tokens,
            "token_accuracy": matched_tokens / total_tokens if total_tokens else 0.0,
            "expected_entities": expected_entities_total,
            "predicted_entities": predicted_entities_total,
            "matched_entities": matched_entities_total,
            "entity_precision": precision,
            "entity_recall": recall,
            "entity_f1": f1,
        },
        "records": rows,
    }


def summarize_hf_token_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    summary = dict(evaluation["summary"])
    summary["records_with_errors"] = sum(
        1 for row in evaluation.get("records", []) if not all(row.get("token_matches", []))
    )
    field_counts: Counter[str] = Counter()
    for row in evaluation.get("records", []):
        expected_entities = {_tuple_entity(entity) for entity in row.get("expected_entities", [])}
        predicted_entities = {_tuple_entity(entity) for entity in row.get("predicted_entities", [])}
        for field, _, _ in expected_entities - predicted_entities:
            field_counts[field] += 1
    summary["false_negative_entity_counts"] = dict(sorted(field_counts.items()))
    return summary


def entities_from_bio(tags: list[str], offsets: list[list[int]]) -> list[tuple[str, int, int]]:
    entities: list[tuple[str, int, int]] = []
    active_field: str | None = None
    active_start: int | None = None
    active_end: int | None = None
    for tag, offset in zip(tags, offsets):
        if tag == "O":
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append((active_field, active_start, active_end))
            active_field = None
            active_start = None
            active_end = None
            continue
        prefix, field = tag.split("-", 1)
        if prefix == "B" or active_field != field:
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append((active_field, active_start, active_end))
            active_field = field
            active_start = int(offset[0])
            active_end = int(offset[1])
        else:
            active_end = int(offset[1])
    if active_field is not None and active_start is not None and active_end is not None:
        entities.append((active_field, active_start, active_end))
    return entities


def _tuple_entity(entity: Any) -> tuple[str, int, int]:
    field, start, end = entity
    return str(field), int(start), int(end)
