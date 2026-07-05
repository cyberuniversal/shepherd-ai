"""Measure whether ASR transcript differences change downstream intent extraction."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, word_error_details  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, NUMBER_WORDS, parse_intent  # noqa: E402
from shepherd_ai.intent_training import EVAL_FIELDS, load_intent_model  # noqa: E402
from shepherd_ai.whisper_asr import load_whisper_predictions  # noqa: E402


Predictor = Callable[[str], dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest JSONL containing split labels.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--predictions", required=True, help="Whisper prediction JSONL.")
    parser.add_argument("--output", required=True, help="Path to write intent-impact JSON.")
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="Optional saved trained intent model JSON. May be passed more than once.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    splits_by_id = {record.id: record.split for record in manifest_records}
    predictions = load_whisper_predictions(args.predictions)
    systems = _load_systems(args.model)
    analysis = analyze_impact(predictions, splits_by_id=splits_by_id, systems=systems)
    analysis["metadata"]["manifest"] = args.manifest
    analysis["metadata"]["predictions"] = args.predictions
    analysis["metadata"]["model_artifacts"] = [str(Path(model)) for model in args.model]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(analysis["summary"], indent=2, sort_keys=True))


def analyze_impact(
    predictions: list[dict[str, Any]],
    *,
    splits_by_id: dict[str, str],
    systems: dict[str, Predictor],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    system_summaries: dict[str, dict[str, Any]] = {}
    for system_name, predictor in systems.items():
        rows = []
        for prediction in predictions:
            record_id = str(prediction["id"])
            human_transcript = str(prediction.get("expected_transcript", ""))
            asr_transcript = str(prediction.get("predicted_transcript", ""))
            transcript_details = word_error_details(human_transcript, asr_transcript)
            human_intent = _project_intent(predictor(human_transcript))
            asr_intent = _project_intent(predictor(asr_transcript))
            field_changes = {
                field: {"human": human_intent[field], "asr": asr_intent[field]}
                for field in EVAL_FIELDS
                if human_intent[field] != asr_intent[field]
            }
            normalized_human_intent = _normalize_intent_for_comparison(human_intent)
            normalized_asr_intent = _normalize_intent_for_comparison(asr_intent)
            normalized_field_changes = {
                field: {"human": normalized_human_intent[field], "asr": normalized_asr_intent[field]}
                for field in EVAL_FIELDS
                if normalized_human_intent[field] != normalized_asr_intent[field]
            }
            rows.append(
                {
                    "id": record_id,
                    "split": splits_by_id.get(record_id, "not stated"),
                    "system": system_name,
                    "human_transcript": human_transcript,
                    "asr_transcript": asr_transcript,
                    "raw_transcript_changed": human_transcript != asr_transcript,
                    "normalized_word_changed": transcript_details["edit_distance"] > 0,
                    "transcript_edit_distance": transcript_details["edit_distance"],
                    "transcript_word_error_rate": transcript_details["word_error_rate"],
                    "human_intent": human_intent,
                    "asr_intent": asr_intent,
                    "intent_changed": bool(field_changes),
                    "field_changes": field_changes,
                    "normalized_human_intent": normalized_human_intent,
                    "normalized_asr_intent": normalized_asr_intent,
                    "semantic_intent_changed": bool(normalized_field_changes),
                    "normalized_field_changes": normalized_field_changes,
                }
            )
        system_summaries[system_name] = _summarize_rows(rows)
        records.extend(rows)

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluation_note": (
                "ASR-to-intent impact analysis only. This compares extractor outputs on human transcripts "
                "and ASR transcripts; it is not intent accuracy because no gold intent labels are used."
            ),
            "fields": list(EVAL_FIELDS),
            "systems": list(systems),
        },
        "summary": system_summaries,
        "records": records,
    }


def _load_systems(model_paths: list[str]) -> dict[str, Predictor]:
    systems: dict[str, Predictor] = {
        DETERMINISTIC_PARSER_NAME: lambda text: parse_intent(text).to_dict(),
    }
    for model_path in model_paths:
        model = load_intent_model(model_path)
        system_name = model.model_name
        if system_name in systems:
            system_name = f"{system_name}:{Path(model_path).stem}"
        systems[system_name] = lambda text, loaded_model=model: loaded_model.predict(text).to_dict()
    return systems


def _project_intent(intent: dict[str, Any]) -> dict[str, Any]:
    return {field: intent.get(field) for field in EVAL_FIELDS}


def _normalize_intent_for_comparison(intent: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(intent)
    constraints = normalized.get("constraints")
    if isinstance(constraints, list):
        normalized["constraints"] = [_normalize_constraint_text(str(constraint)) for constraint in constraints]
    return normalized


def _normalize_constraint_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("metres", "meters")
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
        normalized = _replace_word(normalized, word, str(value))
    return " ".join(normalized.split())


def _replace_word(text: str, word: str, replacement: str) -> str:
    return re.sub(rf"\b{re.escape(word)}\b", replacement, text)


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changed_field_counts: Counter[str] = Counter()
    normalized_changed_field_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        split = row["split"]
        split_counts[split]["records"] += 1
        if row["raw_transcript_changed"]:
            split_counts[split]["raw_transcript_changed"] += 1
        if row["normalized_word_changed"]:
            split_counts[split]["normalized_word_changed"] += 1
        if row["intent_changed"]:
            split_counts[split]["intent_changed"] += 1
        if row["semantic_intent_changed"]:
            split_counts[split]["semantic_intent_changed"] += 1
        for field in row["field_changes"]:
            changed_field_counts[field] += 1
        for field in row["normalized_field_changes"]:
            normalized_changed_field_counts[field] += 1

    records = len(rows)
    raw_transcript_changed = sum(1 for row in rows if row["raw_transcript_changed"])
    normalized_word_changed = sum(1 for row in rows if row["normalized_word_changed"])
    intent_changed = sum(1 for row in rows if row["intent_changed"])
    semantic_intent_changed = sum(1 for row in rows if row["semantic_intent_changed"])
    return {
        "records": records,
        "raw_transcript_changed_records": raw_transcript_changed,
        "raw_transcript_changed_rate": raw_transcript_changed / records if records else 0.0,
        "normalized_word_changed_records": normalized_word_changed,
        "normalized_word_changed_rate": normalized_word_changed / records if records else 0.0,
        "intent_changed_records": intent_changed,
        "intent_changed_rate": intent_changed / records if records else 0.0,
        "semantic_intent_changed_records": semantic_intent_changed,
        "semantic_intent_changed_rate": semantic_intent_changed / records if records else 0.0,
        "unchanged_intent_when_normalized_word_changed": sum(
            1 for row in rows if row["normalized_word_changed"] and not row["intent_changed"]
        ),
        "unchanged_semantic_intent_when_normalized_word_changed": sum(
            1 for row in rows if row["normalized_word_changed"] and not row["semantic_intent_changed"]
        ),
        "changed_field_counts": dict(sorted(changed_field_counts.items())),
        "normalized_changed_field_counts": dict(sorted(normalized_changed_field_counts.items())),
        "split_counts": {
            split: dict(counts)
            for split, counts in sorted(split_counts.items())
        },
    }


if __name__ == "__main__":
    main()
