"""Export editable span-label commands for records in a review queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import load_span_labeled_commands  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--span-dataset", required=True, help="Current human-verified span JSONL dataset.")
    parser.add_argument("--review-queue", required=True, help="JSONL review queue from build_span_review_queue.py.")
    parser.add_argument("--commands-output", required=True, help="Editable command file to write.")
    parser.add_argument("--report-output", required=True, help="Markdown review report to write.")
    parser.add_argument(
        "--source-command-dataset",
        default="datasets/commands/human_written_commands_curated_v1.jsonl",
        help="Command dataset path used by create_span_record_from_command.py.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    span_records = {record.id: record for record in load_span_labeled_commands(args.span_dataset)}
    review_records = _read_jsonl(Path(args.review_queue))
    commands = []
    report_blocks = [_report_header(args)]
    missing_ids = []
    for review in review_records:
        record_id = str(review["id"])
        span_record = span_records.get(record_id)
        if span_record is None:
            missing_ids.append(record_id)
            continue
        commands.append(_command_for_record(span_record, args.source_command_dataset))
        report_blocks.append(_report_block(review, span_record))
    if missing_ids:
        raise ValueError(f"review queue ids missing from span dataset: {missing_ids}")

    commands_output = Path(args.commands_output)
    commands_output.parent.mkdir(parents=True, exist_ok=True)
    commands_output.write_text("\n".join(commands) + ("\n" if commands else ""), encoding="utf-8")

    report_output = Path(args.report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text("\n\n".join(report_blocks) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "commands": len(commands),
                "commands_output": str(commands_output),
                "report_output": str(report_output),
                "review_queue": args.review_queue,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _command_for_record(record, source_command_dataset: str) -> str:
    parts = [
        "python",
        "scripts/create_span_record_from_command.py",
        "--input",
        source_command_dataset,
        "--id",
        record.id,
        "--output",
        "datasets/commands/human_verified_span_commands.jsonl",
    ]
    for span in sorted(record.spans, key=lambda item: (item.start, item.end, item.field)):
        parts.extend([f"--{span.field}-span", span.text])
    return " ".join(shlex.quote(part) for part in parts)


def _report_header(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            "# Week 2 Span Review Commands",
            "",
            "This file is a review aid. The command file starts from the current gold spans, and model predictions are not gold labels.",
            "",
            f"- Span dataset: `{args.span_dataset}`",
            f"- Review queue: `{args.review_queue}`",
            f"- Editable command file: `{args.commands_output}`",
            "",
            "Workflow:",
            "",
            "1. Open the editable command file.",
            "2. For each record below, compare the current span arguments with the original command text and error context.",
            "3. Edit only spans that are actually wrong after human review.",
            "4. Rebuild with `scripts/rebuild_span_dataset_from_commands.py` when the command file has been reviewed.",
        ]
    )


def _report_block(review: dict[str, Any], span_record) -> str:
    current_spans = ", ".join(f"{span.field}={span.text!r}" for span in span_record.spans)
    false_negatives = ", ".join(_entity_summary(entity) for entity in review.get("false_negative_entities", []))
    false_positives = ", ".join(_entity_summary(entity) for entity in review.get("false_positive_entities", []))
    return "\n".join(
        [
            f"## {review['id']}",
            "",
            f"Text: `{review.get('text', span_record.text)}`",
            "",
            f"Review fields: `{', '.join(review.get('review_fields', []))}`",
            f"Focus errors: `{review.get('focus_error_count', 0)}`; token errors: `{review.get('token_error_count', 0)}`",
            f"Current gold span arguments: {current_spans or 'none'}",
            f"False negatives from model comparison: {false_negatives or 'none'}",
            f"False positives from model comparison: {false_positives or 'none'}",
        ]
    )


def _entity_summary(entity: dict[str, Any]) -> str:
    return f"{entity.get('field')}={entity.get('text')!r}"


if __name__ == "__main__":
    main()
