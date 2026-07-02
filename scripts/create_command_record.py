"""Append one labeled Week 2 command record to a JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import load_labeled_commands, validate_split_integrity  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="JSONL file to append to.")
    parser.add_argument("--id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--source", required=True)
    parser.add_argument("--data-type", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--count", help="Integer, 'all', or omit for null.")
    parser.add_argument("--location", help="Normalized location, or omit for null.")
    parser.add_argument("--target", help="Normalized target, or omit for null.")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint phrase. Repeatable.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    record = {
        "id": args.id.strip(),
        "text": args.text.strip(),
        "split": args.split,
        "source": args.source.strip(),
        "data_type": args.data_type.strip(),
        "expected_intent": {
            "action": _nullable(args.action),
            "count": _parse_count(args.count),
            "location": _nullable(args.location),
            "target": _nullable(args.target),
            "constraints": [constraint.strip() for constraint in args.constraint if constraint.strip()],
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")

    records = load_labeled_commands(output)
    validate_split_integrity(records)
    print(json.dumps({"appended": record["id"], "records": len(records)}, indent=2, sort_keys=True))


def _nullable(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() in {"null", "none"}:
        return None
    return stripped


def _parse_count(value: str | None) -> int | str | None:
    parsed: Any = _nullable(value)
    if parsed is None:
        return None
    if parsed == "all":
        return "all"
    try:
        return int(parsed)
    except ValueError as exc:
        raise ValueError("--count must be an integer, 'all', or omitted") from exc


if __name__ == "__main__":
    main()
