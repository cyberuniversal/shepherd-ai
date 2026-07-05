"""Evaluate intent extraction on human and ASR transcripts with matched command labels."""

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

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.intent_training import EVAL_FIELDS, load_intent_model  # noqa: E402
from shepherd_ai.whisper_asr import load_whisper_predictions  # noqa: E402


Predictor = Callable[[str], dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest JSONL containing split labels.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--predictions", required=True, help="Whisper prediction JSONL.")
    parser.add_argument("--gold-commands", required=True, help="Labeled command JSONL used for expected intents.")
    parser.add_argument("--output", required=True, help="Path to write evaluation JSON.")
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
    predictions = load_whisper_predictions(args.predictions)
    gold_index = build_gold_index(load_gold_commands(args.gold_commands))
    systems = _load_systems(args.model)
    evaluation = evaluate_audio_intent_accuracy(
        manifest_records={record.id: record.split for record in manifest_records},
        predictions=predictions,
        gold_index=gold_index,
        systems=systems,
    )
    evaluation["metadata"]["manifest"] = args.manifest
    evaluation["metadata"]["predictions"] = args.predictions
    evaluation["metadata"]["gold_commands"] = args.gold_commands
    evaluation["metadata"]["model_artifacts"] = [str(Path(model)) for model in args.model]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluation, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evaluation["summary"], indent=2, sort_keys=True))


def load_gold_commands(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if line.strip():
            record = json.loads(line)
            _reject_draft_gold_record(record, line_number=line_number)
            records.append(record)
    return records


def _reject_draft_gold_record(record: dict[str, Any], *, line_number: int) -> None:
    data_type = str(record.get("data_type", ""))
    label_source = str(record.get("label_source", ""))
    review_status = record.get("review_status")
    if "draft" in data_type or label_source.endswith("_draft"):
        raise ValueError(
            f"line {line_number}: draft labels cannot be used as gold commands for intent accuracy"
        )
    if review_status is not None and review_status != "human_reviewed":
        raise ValueError(
            f"line {line_number}: review_status must be 'human_reviewed' before intent accuracy evaluation"
        )


def build_gold_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_normalize_text(str(record["text"]))].append(record)

    index: dict[str, dict[str, Any]] = {}
    for normalized_text, matching_records in grouped.items():
        intents = [dict(record["expected_intent"]) for record in matching_records]
        first_intent = intents[0]
        if any(intent != first_intent for intent in intents[1:]):
            continue
        index[normalized_text] = {
            "expected_intent": first_intent,
            "gold_record_ids": [str(record["id"]) for record in matching_records],
            "gold_sources": sorted({str(record["source"]) for record in matching_records}),
            "gold_data_types": sorted({str(record["data_type"]) for record in matching_records}),
            "gold_label_sources": sorted({str(record.get("label_source", "not stated")) for record in matching_records}),
        }
    return index


def evaluate_audio_intent_accuracy(
    *,
    manifest_records: dict[str, str],
    predictions: list[dict[str, Any]],
    gold_index: dict[str, dict[str, Any]],
    systems: dict[str, Predictor],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    unmatched_audio_ids: list[str] = []
    for prediction in predictions:
        record_id = str(prediction["id"])
        expected_transcript = str(prediction.get("expected_transcript", ""))
        gold = gold_index.get(_normalize_text(expected_transcript))
        if gold is None:
            unmatched_audio_ids.append(record_id)
            continue
        for system_name, predictor in systems.items():
            for transcript_kind, transcript in (
                ("human_transcript", expected_transcript),
                ("asr_transcript", str(prediction.get("predicted_transcript", ""))),
            ):
                actual_intent = _project_intent(predictor(transcript))
                expected_intent = _project_intent(gold["expected_intent"])
                field_matches = {
                    field: actual_intent[field] == expected_intent[field]
                    for field in EVAL_FIELDS
                }
                rows.append(
                    {
                        "id": record_id,
                        "split": manifest_records.get(record_id, "not stated"),
                        "system": system_name,
                        "transcript_kind": transcript_kind,
                        "transcript": transcript,
                        "expected_transcript": expected_transcript,
                        "expected_intent": expected_intent,
                        "actual_intent": actual_intent,
                        "field_matches": field_matches,
                        "all_fields_match": all(field_matches.values()),
                        "gold_record_ids": gold["gold_record_ids"],
                        "gold_sources": gold["gold_sources"],
                        "gold_data_types": gold["gold_data_types"],
                        "gold_label_sources": gold["gold_label_sources"],
                    }
                )

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluation_note": (
                "Intent accuracy on audio-linked transcripts whose expected transcript exactly matches a labeled "
                "record in --gold-commands. Draft labels and non-human-reviewed labels are rejected before "
                "evaluation."
            ),
            "fields": list(EVAL_FIELDS),
            "systems": list(systems),
            "unmatched_audio_ids": unmatched_audio_ids,
        },
        "summary": _summarize(rows),
        "records": rows,
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


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["system"], row["transcript_kind"])].append(row)
    return {
        f"{system}:{transcript_kind}": _summarize_group(group_rows)
        for (system, transcript_kind), group_rows in sorted(grouped.items())
    }


def _summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    field_matches = 0
    total_fields = 0
    field_error_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        split_counts[row["split"]]["records"] += 1
        if row["all_fields_match"]:
            split_counts[row["split"]]["exact_record_matches"] += 1
        for field, matched in row["field_matches"].items():
            total_fields += 1
            if matched:
                field_matches += 1
            else:
                field_error_counts[field] += 1
    exact_matches = sum(1 for row in rows if row["all_fields_match"])
    return {
        "records": len(rows),
        "exact_record_matches": exact_matches,
        "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
        "field_matches": field_matches,
        "total_fields": total_fields,
        "field_accuracy": field_matches / total_fields if total_fields else 0.0,
        "field_error_counts": dict(sorted(field_error_counts.items())),
        "split_counts": {
            split: dict(counts)
            for split, counts in sorted(split_counts.items())
        },
    }


def _project_intent(intent: dict[str, Any]) -> dict[str, Any]:
    return {field: intent.get(field) for field in EVAL_FIELDS}


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace(".", " ").replace(",", " ").split())


if __name__ == "__main__":
    main()
