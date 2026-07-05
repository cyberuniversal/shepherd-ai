"""Validate an audio intent review packet before using it as gold labels."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "id",
    "audio_id",
    "text",
    "split",
    "source",
    "data_type",
    "label_source",
    "review_status",
    "expected_intent",
)
INTENT_FIELDS = ("action", "count", "location", "target", "constraints")
REVIEWED_DATA_TYPE = "human_verified_audio_intent_command"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="Audio intent review packet JSONL.")
    parser.add_argument("--summary-output", required=True, help="Summary JSON output.")
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help="Exit non-zero unless every record is human-reviewed and has the reviewed data type.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_review_packet(args.packet)
    summary = summarize_review_packet(records)
    summary["metadata"]["packet"] = args.packet

    output = Path(args.summary_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary["summary"], indent=2, sort_keys=True))
    if args.require_reviewed and not summary["summary"]["ready_for_gold_evaluation"]:
        raise SystemExit(1)


def load_review_packet(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        _validate_record_shape(raw, line_number=line_number)
        records.append(raw)
    return records


def summarize_review_packet(records: list[dict[str, Any]]) -> dict[str, Any]:
    review_status_counts = Counter(str(record["review_status"]) for record in records)
    data_type_counts = Counter(str(record["data_type"]) for record in records)
    label_source_counts = Counter(str(record.get("label_source", "not stated")) for record in records)
    split_counts = Counter(str(record["split"]) for record in records)
    draft_records = [
        str(record["id"])
        for record in records
        if "draft" in str(record["data_type"]) or str(record.get("label_source", "")).endswith("_draft")
    ]
    not_reviewed_records = [
        str(record["id"])
        for record in records
        if record["review_status"] != "human_reviewed"
    ]
    wrong_data_type_records = [
        str(record["id"])
        for record in records
        if record["data_type"] != REVIEWED_DATA_TYPE
    ]
    ready = not draft_records and not not_reviewed_records and not wrong_data_type_records
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Review packet validation only. Records are ready for gold evaluation only when all labels "
                "are human-reviewed and no draft label sources remain."
            ),
        },
        "summary": {
            "records": len(records),
            "split_counts": dict(sorted(split_counts.items())),
            "review_status_counts": dict(sorted(review_status_counts.items())),
            "data_type_counts": dict(sorted(data_type_counts.items())),
            "label_source_counts": dict(sorted(label_source_counts.items())),
            "draft_records": len(draft_records),
            "not_reviewed_records": len(not_reviewed_records),
            "wrong_data_type_records": len(wrong_data_type_records),
            "ready_for_gold_evaluation": ready,
        },
        "blocking_records": {
            "draft_records": draft_records,
            "not_reviewed_records": not_reviewed_records,
            "wrong_data_type_records": wrong_data_type_records,
        },
    }


def _validate_record_shape(record: dict[str, Any], *, line_number: int) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"line {line_number}: missing required fields: {', '.join(missing)}")
    intent = record["expected_intent"]
    if not isinstance(intent, dict):
        raise ValueError(f"line {line_number}: expected_intent must be an object")
    missing_intent_fields = [field for field in INTENT_FIELDS if field not in intent]
    if missing_intent_fields:
        raise ValueError(
            f"line {line_number}: expected_intent missing fields: {', '.join(missing_intent_fields)}"
        )
    if not isinstance(intent["constraints"], list):
        raise ValueError(f"line {line_number}: expected_intent.constraints must be a list")


if __name__ == "__main__":
    main()
