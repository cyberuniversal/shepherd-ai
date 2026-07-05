"""Measure whether ASR transcript differences change downstream BIO span extraction."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, word_error_details  # noqa: E402
from shepherd_ai.intent import NUMBER_WORDS  # noqa: E402
from shepherd_ai.span_annotations import spans_to_bio_tags  # noqa: E402
from shepherd_ai.span_training import (  # noqa: E402
    SpanTagRecord,
    evaluate_span_tagger,
    load_span_tagger,
    records_from_span_commands,
)
from shepherd_ai.whisper_asr import load_whisper_predictions  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest JSONL containing split labels.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--predictions", required=True, help="Whisper prediction JSONL.")
    parser.add_argument("--span-dataset", required=True, help="Human-verified span-label JSONL.")
    parser.add_argument("--model", required=True, help="Saved span tagger JSON artifact.")
    parser.add_argument("--output", required=True, help="Path to write ASR span-impact JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    splits_by_id = {record.id: record.split for record in manifest_records}
    predictions = load_whisper_predictions(args.predictions)
    span_records = records_from_span_commands(args.span_dataset)
    model = load_span_tagger(args.model)

    analysis = analyze_span_impact(
        predictions,
        splits_by_id=splits_by_id,
        span_records=span_records,
        model=model,
    )
    analysis["metadata"]["manifest"] = args.manifest
    analysis["metadata"]["predictions"] = args.predictions
    analysis["metadata"]["span_dataset"] = args.span_dataset
    analysis["metadata"]["model_artifact"] = args.model

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(analysis["summary"], indent=2, sort_keys=True))


def analyze_span_impact(
    predictions: list[dict[str, Any]],
    *,
    splits_by_id: dict[str, str],
    span_records: list[SpanTagRecord],
    model: Any,
) -> dict[str, Any]:
    span_index = _build_unambiguous_text_index(span_records)
    records: list[dict[str, Any]] = []
    matched_human_records: list[SpanTagRecord] = []
    unmatched_audio_ids: list[str] = []
    ambiguous_audio_ids: list[str] = []

    for prediction in predictions:
        record_id = str(prediction["id"])
        human_transcript = str(prediction.get("expected_transcript", ""))
        asr_transcript = str(prediction.get("predicted_transcript", ""))
        match_status, matched_record = _lookup_span_record(span_index, human_transcript)
        if match_status == "unmatched":
            unmatched_audio_ids.append(record_id)
            continue
        if match_status == "ambiguous":
            ambiguous_audio_ids.append(record_id)
            continue
        assert matched_record is not None
        matched_human_records.append(matched_record)

        transcript_details = word_error_details(human_transcript, asr_transcript)
        human_prediction = _predict_entities(model, human_transcript)
        asr_prediction = _predict_entities(model, asr_transcript)
        human_signatures = _entity_signatures(human_prediction["entities"])
        asr_signatures = _entity_signatures(asr_prediction["entities"])
        semantic_human_signatures = _semantic_entity_signatures(human_prediction["entities"])
        semantic_asr_signatures = _semantic_entity_signatures(asr_prediction["entities"])
        removed_signatures = sorted(human_signatures - asr_signatures)
        added_signatures = sorted(asr_signatures - human_signatures)
        semantic_removed_signatures = sorted(semantic_human_signatures - semantic_asr_signatures)
        semantic_added_signatures = sorted(semantic_asr_signatures - semantic_human_signatures)
        records.append(
            {
                "id": record_id,
                "split": splits_by_id.get(record_id, "not stated"),
                "span_record_id": matched_record.id,
                "human_transcript": human_transcript,
                "asr_transcript": asr_transcript,
                "raw_transcript_changed": human_transcript != asr_transcript,
                "normalized_word_changed": transcript_details["edit_distance"] > 0,
                "transcript_edit_distance": transcript_details["edit_distance"],
                "transcript_word_error_rate": transcript_details["word_error_rate"],
                "human_predicted_tokens": human_prediction["tokens"],
                "human_predicted_tags": human_prediction["tags"],
                "human_predicted_entities": human_prediction["entities"],
                "asr_predicted_tokens": asr_prediction["tokens"],
                "asr_predicted_tags": asr_prediction["tags"],
                "asr_predicted_entities": asr_prediction["entities"],
                "span_prediction_changed": bool(removed_signatures or added_signatures),
                "removed_entity_signatures": [list(signature) for signature in removed_signatures],
                "added_entity_signatures": [list(signature) for signature in added_signatures],
                "semantic_span_prediction_changed": bool(
                    semantic_removed_signatures or semantic_added_signatures
                ),
                "semantic_removed_entity_signatures": [
                    list(signature) for signature in semantic_removed_signatures
                ],
                "semantic_added_entity_signatures": [
                    list(signature) for signature in semantic_added_signatures
                ],
            }
        )

    human_accuracy = evaluate_span_tagger(
        model,
        matched_human_records,
        dataset_name="audio_matched_human_transcripts",
    )

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": getattr(model, "model_name", "not stated"),
            "model_version": getattr(model, "model_version", "not stated"),
            "evaluation_note": (
                "ASR-to-span impact analysis. Human transcript span accuracy is computed only where the "
                "audio transcript exactly matches a human-verified span-labeled command. ASR transcript "
                "rows compare model predictions on human versus Whisper transcripts; they are not ASR span "
                "accuracy because no human gold spans exist for the ASR text. Semantic span comparison "
                "normalizes simple number-word variants such as fifty and 50."
            ),
        },
        "summary": _summarize_rows(records)
        | {
            "matched_audio_records": len(matched_human_records),
            "unmatched_audio_ids": unmatched_audio_ids,
            "ambiguous_audio_ids": ambiguous_audio_ids,
            "human_transcript_span_accuracy": human_accuracy["summary"],
        },
        "records": records,
    }


def _build_unambiguous_text_index(records: list[SpanTagRecord]) -> dict[str, list[SpanTagRecord]]:
    index: dict[str, list[SpanTagRecord]] = defaultdict(list)
    for record in records:
        index[_normalize_text(record.text)].append(record)
    return dict(index)


def _lookup_span_record(index: dict[str, list[SpanTagRecord]], text: str) -> tuple[str, SpanTagRecord | None]:
    matches = index.get(_normalize_text(text), [])
    if not matches:
        return "unmatched", None
    signatures = {_gold_record_signature(record) for record in matches}
    if len(signatures) > 1:
        return "ambiguous", None
    return "matched", matches[0]


def _gold_record_signature(record: SpanTagRecord) -> tuple[tuple[str, str], ...]:
    entities = _entities_from_bio(record.tags, record.offsets, record.text)
    return tuple(sorted((entity["field"], _normalize_entity_text(entity["text"])) for entity in entities))


def _predict_entities(model: Any, text: str) -> dict[str, Any]:
    tagged = spans_to_bio_tags(text, [])
    tokens = [token.text for token, _ in tagged]
    offsets = [[token.start, token.end] for token, _ in tagged]
    tags = model.predict(tokens)
    entities = _entities_from_bio(tags, offsets, text)
    return {"tokens": tokens, "tags": tags, "entities": entities}


def _entities_from_bio(tags: list[str], offsets: list[list[int]], text: str) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    active_field: str | None = None
    active_start: int | None = None
    active_end: int | None = None
    for tag, offset in zip(tags, offsets):
        if tag == "O":
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append(_entity_dict(active_field, active_start, active_end, text))
            active_field = None
            active_start = None
            active_end = None
            continue
        prefix, field = tag.split("-", 1)
        if prefix == "B" or active_field != field:
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append(_entity_dict(active_field, active_start, active_end, text))
            active_field = field
            active_start = offset[0]
            active_end = offset[1]
        else:
            active_end = offset[1]
    if active_field is not None and active_start is not None and active_end is not None:
        entities.append(_entity_dict(active_field, active_start, active_end, text))
    return entities


def _entity_dict(field: str, start: int, end: int, text: str) -> dict[str, Any]:
    return {"field": field, "start": start, "end": end, "text": text[start:end]}


def _entity_signatures(entities: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(entity["field"]), _normalize_entity_text(str(entity["text"])))
        for entity in entities
    }


def _semantic_entity_signatures(entities: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(entity["field"]), _normalize_entity_text_semantic(str(entity["text"])))
        for entity in entities
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    changed_field_counts: Counter[str] = Counter()
    semantic_changed_field_counts: Counter[str] = Counter()
    for row in rows:
        split = row["split"]
        split_counts[split]["records"] += 1
        if row["raw_transcript_changed"]:
            split_counts[split]["raw_transcript_changed"] += 1
        if row["normalized_word_changed"]:
            split_counts[split]["normalized_word_changed"] += 1
        if row["span_prediction_changed"]:
            split_counts[split]["span_prediction_changed"] += 1
        if row["semantic_span_prediction_changed"]:
            split_counts[split]["semantic_span_prediction_changed"] += 1
        for field, _ in row["removed_entity_signatures"] + row["added_entity_signatures"]:
            changed_field_counts[field] += 1
        for field, _ in row["semantic_removed_entity_signatures"] + row["semantic_added_entity_signatures"]:
            semantic_changed_field_counts[field] += 1

    records = len(rows)
    raw_transcript_changed = sum(1 for row in rows if row["raw_transcript_changed"])
    normalized_word_changed = sum(1 for row in rows if row["normalized_word_changed"])
    span_prediction_changed = sum(1 for row in rows if row["span_prediction_changed"])
    semantic_span_prediction_changed = sum(1 for row in rows if row["semantic_span_prediction_changed"])
    return {
        "evaluated_records": records,
        "raw_transcript_changed_records": raw_transcript_changed,
        "raw_transcript_changed_rate": raw_transcript_changed / records if records else 0.0,
        "normalized_word_changed_records": normalized_word_changed,
        "normalized_word_changed_rate": normalized_word_changed / records if records else 0.0,
        "span_prediction_changed_records": span_prediction_changed,
        "span_prediction_changed_rate": span_prediction_changed / records if records else 0.0,
        "semantic_span_prediction_changed_records": semantic_span_prediction_changed,
        "semantic_span_prediction_changed_rate": semantic_span_prediction_changed / records if records else 0.0,
        "unchanged_span_prediction_when_normalized_word_changed": sum(
            1 for row in rows if row["normalized_word_changed"] and not row["span_prediction_changed"]
        ),
        "unchanged_semantic_span_prediction_when_normalized_word_changed": sum(
            1 for row in rows if row["normalized_word_changed"] and not row["semantic_span_prediction_changed"]
        ),
        "changed_entity_field_counts": dict(sorted(changed_field_counts.items())),
        "semantic_changed_entity_field_counts": dict(sorted(semantic_changed_field_counts.items())),
        "split_counts": {
            split: dict(counts)
            for split, counts in sorted(split_counts.items())
        },
    }


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _normalize_entity_text(text: str) -> str:
    return _normalize_text(text)


def _normalize_entity_text_semantic(text: str) -> str:
    normalized = _normalize_text(text).replace("metres", "meters")
    number_words = {
        **NUMBER_WORDS,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
    }
    for word, value in sorted(number_words.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = re.sub(rf"\b{re.escape(word)}\b", str(value), normalized)
    return " ".join(normalized.split())


if __name__ == "__main__":
    main()
