"""Append one human-reviewed Week 2 span-labeled command record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

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
    parser.add_argument("--output", required=True, help="Span-labeled JSONL file to append to.")
    parser.add_argument("--id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--source", default="manual_week2_span_annotation_v1")
    parser.add_argument("--data-type", default="human_verified_span_command")
    for _, argument in SPAN_ARGUMENTS:
        parser.add_argument(f"--{argument}", action="append", default=[], help="Exact phrase to label.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text = args.text.strip()
    if not text:
        raise ValueError("--text must not be empty")
    record = {
        "id": args.id.strip(),
        "text": text,
        "split": args.split,
        "source": args.source.strip(),
        "data_type": args.data_type.strip(),
        "spans": build_spans_from_phrases(text, _iter_span_phrases(args)),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")

    load_span_labeled_commands(output)
    print(json.dumps({"appended": record["id"], "spans": len(record["spans"])}, indent=2, sort_keys=True))


def _iter_span_phrases(args: argparse.Namespace) -> list[tuple[str, str]]:
    field_phrases: list[tuple[str, str]] = []
    for field, argument in SPAN_ARGUMENTS:
        phrases = getattr(args, argument.replace("-", "_"))
        for phrase in phrases:
            field_phrases.append((field, phrase))
    return field_phrases


if __name__ == "__main__":
    main()
