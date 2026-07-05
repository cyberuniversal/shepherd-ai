"""Export compact editable JSONL commands for audio intent review."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


INTENT_FIELDS = ("action", "count", "location", "target", "constraints")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="Draft audio intent review packet JSONL.")
    parser.add_argument("--commands-output", required=True, help="Compact editable JSONL review file.")
    parser.add_argument("--report-output", required=True, help="Markdown review report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = _read_jsonl(Path(args.packet))
    commands = [_command_from_record(record) for record in records]

    commands_output = Path(args.commands_output)
    commands_output.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(commands_output, commands)

    report_output = Path(args.report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(_build_report(args, records, commands), encoding="utf-8")

    print(
        json.dumps(
            {
                "records": len(records),
                "commands_output": str(commands_output),
                "report_output": str(report_output),
                "review_status_counts": dict(sorted(Counter(command["review_status"] for command in commands).items())),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _command_from_record(record: dict[str, Any]) -> dict[str, Any]:
    intent = record.get("expected_intent", {})
    return {
        "id": record["id"],
        "audio_id": record.get("audio_id"),
        "text": record["text"],
        "split": record.get("split"),
        "action": intent.get("action"),
        "count": intent.get("count"),
        "location": intent.get("location"),
        "target": intent.get("target"),
        "constraints": intent.get("constraints", []),
        "review_status": "needs_human_review",
        "data_type": "human_recorded_audio_intent_draft",
        "label_source": "deterministic_v1_draft",
        "review_notes": [],
        "draft_review_flags": record.get("draft_review_flags", []),
    }


def _build_report(args: argparse.Namespace, records: list[dict[str, Any]], commands: list[dict[str, Any]]) -> str:
    flag_counts = Counter(flag for command in commands for flag in command.get("draft_review_flags", []))
    blocks = [
        "\n".join(
            [
                "# Week 2 Audio Intent Review Commands",
                "",
                "This is a human-review aid. The exported JSONL starts from deterministic parser drafts and is not gold data.",
                "",
                f"- Draft packet: `{args.packet}`",
                f"- Editable review file: `{args.commands_output}`",
                f"- Records: `{len(records)}`",
                "",
                "Workflow:",
                "",
                "1. Open the editable JSONL review file.",
                "2. For each line, compare `text` against the intent fields.",
                "3. Correct `action`, `count`, `location`, `target`, and `constraints`.",
                "4. Change `review_status` to `human_reviewed`, `data_type` to `human_verified_audio_intent_command`, and `label_source` to `human_reviewed_v1` only after review.",
                "5. Apply the reviewed file with `scripts/apply_audio_intent_review_commands.py`.",
                "",
                "Draft flag counts:",
                "",
                *[f"- `{flag}`: {count}" for flag, count in sorted(flag_counts.items())],
            ]
        )
    ]
    for record, command in zip(records, commands):
        blocks.append(_record_block(record, command))
    return "\n\n".join(blocks) + "\n"


def _record_block(record: dict[str, Any], command: dict[str, Any]) -> str:
    intent_summary = ", ".join(f"{field}={command.get(field)!r}" for field in INTENT_FIELDS)
    flags = ", ".join(command.get("draft_review_flags", [])) or "none"
    return "\n".join(
        [
            f"## {record['id']}",
            "",
            f"Text: `{record['text']}`",
            f"Split: `{record.get('split', 'not stated')}`",
            f"Draft flags: `{flags}`",
            f"Draft intent: {intent_summary}",
        ]
    )


if __name__ == "__main__":
    main()
