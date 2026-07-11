"""Apply compact human-reviewed audio intent commands to a review packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_audio_intent_review_packet import summarize_review_packet


INTENT_FIELDS = ("action", "count", "location", "target", "constraints")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="Original audio intent review packet JSONL.")
    parser.add_argument("--commands-file", required=True, help="Compact reviewed JSONL commands file.")
    parser.add_argument("--output", required=True, help="Merged audio intent JSONL output.")
    parser.add_argument("--summary-output", required=True, help="Validation summary JSON output.")
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help="Exit non-zero unless the merged output is fully human-reviewed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    packet_records = _read_jsonl(Path(args.packet))
    commands = _read_jsonl(Path(args.commands_file))
    command_by_id = _index_commands(commands)
    merged, applied_ids = _apply_commands(packet_records, command_by_id)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output, merged)

    summary = summarize_review_packet(merged)
    summary["metadata"].update(
        {
            "packet": args.packet,
            "commands_file": args.commands_file,
            "output": args.output,
            "applied_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    summary["application"] = {
        "packet_records": len(packet_records),
        "commands": len(commands),
        "applied_records": len(applied_ids),
        "applied_ids": applied_ids,
    }
    summary_output = Path(args.summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({**summary["application"], **summary["summary"]}, indent=2, sort_keys=True))
    if args.require_reviewed and not summary["summary"]["ready_for_gold_evaluation"]:
        raise SystemExit(1)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {line_number}: invalid JSON") from exc
        records.append(record)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _index_commands(commands: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for line_number, command in enumerate(commands, start=1):
        record_id = str(command.get("id", ""))
        if not record_id:
            raise ValueError(f"commands line {line_number}: missing id")
        _validate_command(command, line_number=line_number)
        if record_id in by_id:
            duplicates.append(record_id)
        by_id[record_id] = command
    if duplicates:
        raise ValueError(f"duplicate command ids: {sorted(set(duplicates))}")
    return by_id


def _validate_command(command: dict[str, Any], *, line_number: int) -> None:
    missing = [field for field in ("id", *INTENT_FIELDS, "review_status", "data_type", "label_source") if field not in command]
    if missing:
        raise ValueError(f"commands line {line_number}: missing fields: {', '.join(missing)}")
    if not isinstance(command["constraints"], list):
        raise ValueError(f"commands line {line_number}: constraints must be a list")
    if command.get("review_notes") is not None and not isinstance(command.get("review_notes"), list):
        raise ValueError(f"commands line {line_number}: review_notes must be a list when provided")


def _apply_commands(
    packet_records: list[dict[str, Any]], command_by_id: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    packet_ids = [str(record["id"]) for record in packet_records]
    duplicate_packet_ids = _duplicates(packet_ids)
    if duplicate_packet_ids:
        raise ValueError(f"duplicate packet ids: {duplicate_packet_ids}")
    missing_packet_ids = sorted(set(command_by_id) - set(packet_ids))
    if missing_packet_ids:
        raise ValueError(f"command ids missing from packet: {missing_packet_ids}")

    merged: list[dict[str, Any]] = []
    applied_ids: list[str] = []
    for record in packet_records:
        record_id = str(record["id"])
        command = command_by_id.get(record_id)
        if command is None:
            merged.append(record)
            continue
        updated = dict(record)
        updated["expected_intent"] = {
            "action": command["action"],
            "count": command["count"],
            "location": command["location"],
            "target": command["target"],
            "constraints": command["constraints"],
        }
        updated["review_status"] = command["review_status"]
        updated["data_type"] = command["data_type"]
        updated["label_source"] = command["label_source"]
        updated["review_notes"] = command.get("review_notes", [])
        updated["reviewed_from_command_file"] = True
        merged.append(updated)
        applied_ids.append(record_id)
    return merged, applied_ids


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


if __name__ == "__main__":
    main()
