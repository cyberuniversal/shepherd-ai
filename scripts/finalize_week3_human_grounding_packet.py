"""Finalize a filled Week 3 human grounding packet into a benchmark JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_PACKET = Path("reports") / "week3_human_grounding_packet.jsonl"
DEFAULT_OUTPUT = Path("datasets") / "maps" / "human_grounding_benchmark_v1.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--split", default="human_holdout")
    parser.add_argument("--source", default="manual_week3_grounding_benchmark_v1")
    parser.add_argument("--data-type", default="human_written_grounding_benchmark")
    args = parser.parse_args()

    records = _load_packet(args.packet)
    finalized = [
        _finalize_record(record, line_number=index, split=args.split, source=args.source, data_type=args.data_type)
        for index, record in enumerate(records, start=1)
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in finalized),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "records": len(finalized),
                "output": str(args.output),
                "data_type": args.data_type,
                "next_steps": [
                    "validate_grounding_dataset",
                    "evaluate_grounding",
                    "audit_week3_completion_with_human_evidence",
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_packet(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_number}: packet record must be a JSON object")
        records.append(payload)
    if not records:
        raise ValueError("packet is empty")
    return records


def _finalize_record(
    record: dict[str, Any],
    *,
    line_number: int,
    split: str,
    source: str,
    data_type: str,
) -> dict[str, Any]:
    record_id = _required_text(record, "id", line_number=line_number)
    text = _required_text(record, "text", line_number=line_number)
    expected_grounding = record.get("expected_grounding")
    if not isinstance(expected_grounding, dict) or not expected_grounding:
        raise ValueError(f"line {line_number}: expected_grounding must be a non-empty object")
    return {
        "id": record_id,
        "text": text,
        "split": split,
        "source": source,
        "data_type": data_type,
        "expected_grounding": expected_grounding,
    }


def _required_text(record: dict[str, Any], key: str, *, line_number: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {key} must be a non-empty string")
    return value.strip()


if __name__ == "__main__":
    main()
