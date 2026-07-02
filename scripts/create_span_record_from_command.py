"""Create a span-labeled record from an existing command JSONL record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import build_spans_from_phrases, load_span_labeled_commands  # noqa: E402


SPAN_ARGUMENTS = (
    ("action", "action-span"),
    ("count", "count-span"),
    ("location", "location-span"),
    ("target", "target-span"),
    ("constraint", "constraint-span"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Existing command JSONL file.")
    parser.add_argument("--id", required=True, help="Existing command record id to label.")
    parser.add_argument("--output", required=True, help="Span-labeled JSONL file to append to.")
    parser.add_argument("--span-id", help="Optional id for the new span record. Defaults to --id.")
    parser.add_argument("--source", default="manual_week2_span_annotation_v1")
    parser.add_argument("--data-type", default="human_verified_span_command")
    parser.add_argument("--split", choices=("train", "validation", "test"), help="Override the source record split.")
    for _, argument in SPAN_ARGUMENTS:
        parser.add_argument(f"--{argument}", action="append", default=[], help="Exact phrase to label.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_record = _find_record_by_id(Path(args.input), args.id)
    text = _required_text(source_record.get("text"), "text")
    split = args.split or _required_text(source_record.get("split"), "split")
    record: dict[str, Any] = {
        "id": args.span_id.strip() if args.span_id else args.id.strip(),
        "base_command_id": args.id.strip(),
        "base_command_source": source_record.get("source"),
        "base_command_data_type": source_record.get("data_type"),
        "text": text,
        "split": split,
        "source": args.source.strip(),
        "data_type": args.data_type.strip(),
        "spans": build_spans_from_phrases(text, _iter_span_phrases(args)),
    }
    if "expected_intent" in source_record:
        record["expected_intent"] = source_record["expected_intent"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")

    load_span_labeled_commands(output)
    print(
        json.dumps(
            {
                "appended": record["id"],
                "base_command_id": record["base_command_id"],
                "spans": len(record["spans"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _find_record_by_id(path: Path, record_id: str) -> dict[str, Any]:
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("id") == record_id:
            return raw
    raise ValueError(f"record id not found in {path}: {record_id}")


def _iter_span_phrases(args: argparse.Namespace) -> list[tuple[str, str]]:
    field_phrases: list[tuple[str, str]] = []
    for field, argument in SPAN_ARGUMENTS:
        phrases = getattr(args, argument.replace("-", "_"))
        for phrase in phrases:
            field_phrases.append((field, phrase))
    return field_phrases


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"source record {field_name} must be a non-empty string")
    return value


if __name__ == "__main__":
    main()
