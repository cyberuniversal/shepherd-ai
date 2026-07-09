"""Analyze transcript-intent failures for imported Hugging Face predictions."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--human-evaluation", required=True, help="Human/reference transcript intent evaluation JSON.")
    parser.add_argument("--asr-evaluation", required=True, help="ASR/Whisper transcript intent evaluation JSON.")
    parser.add_argument("--json-output", required=True, help="Path to write machine-readable analysis.")
    parser.add_argument("--markdown-output", required=True, help="Path to write Markdown analysis.")
    parser.add_argument("--max-examples", type=int, default=5, help="Maximum examples per system.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analysis = analyze_errors(
        human_evaluation=_load_json(args.human_evaluation),
        asr_evaluation=_load_json(args.asr_evaluation),
        metadata={
            "human_evaluation": args.human_evaluation,
            "asr_evaluation": args.asr_evaluation,
            "max_examples": args.max_examples,
        },
        max_examples=args.max_examples,
    )
    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps(analysis["summary"], indent=2, sort_keys=True))


def analyze_errors(
    *,
    human_evaluation: dict[str, Any],
    asr_evaluation: dict[str, Any],
    metadata: dict[str, Any],
    max_examples: int,
) -> dict[str, Any]:
    human_records = list(human_evaluation.get("records", []))
    asr_records = list(asr_evaluation.get("records", []))
    systems = sorted({str(record.get("system")) for record in human_records + asr_records})
    human_by_key = _records_by_system_id(human_records)
    asr_by_key = _records_by_system_id(asr_records)

    system_rows: dict[str, dict[str, Any]] = {}
    for system in systems:
        human_system = [record for record in human_records if record.get("system") == system]
        asr_system = [record for record in asr_records if record.get("system") == system]
        system_rows[system] = {
            "human_transcript": _summarize_records(human_system, max_examples=max_examples),
            "asr_transcript": _summarize_records(asr_system, max_examples=max_examples),
            "asr_added_failures": _asr_added_failures(
                system,
                human_by_key,
                asr_by_key,
                max_examples=max_examples,
            ),
        }

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Failure analysis for transcript-intent evaluations. Human/reference transcript failures "
                "mostly reflect model or assembly behavior; ASR-added failures are records correct on the "
                "human transcript and incorrect on the Whisper transcript for the same system."
            ),
            **metadata,
        },
        "summary": {
            system: {
                "human_error_records": rows["human_transcript"]["error_records"],
                "asr_error_records": rows["asr_transcript"]["error_records"],
                "asr_added_failure_records": rows["asr_added_failures"]["records"],
                "human_field_errors": rows["human_transcript"]["field_error_counts"],
                "asr_field_errors": rows["asr_transcript"]["field_error_counts"],
            }
            for system, rows in system_rows.items()
        },
        "systems": system_rows,
    }


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Week 2 Transformer Transcript Intent Error Analysis",
        "",
        analysis["metadata"]["note"],
        "",
        "## Summary",
        "",
        "| System | Human errors | ASR errors | ASR-added failures | Human field errors | ASR field errors |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for system, summary in analysis["summary"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{system}`",
                    str(summary["human_error_records"]),
                    str(summary["asr_error_records"]),
                    str(summary["asr_added_failure_records"]),
                    f"`{json.dumps(summary['human_field_errors'], sort_keys=True)}`",
                    f"`{json.dumps(summary['asr_field_errors'], sort_keys=True)}`",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Examples", ""])
    for system, rows in analysis["systems"].items():
        lines.extend([f"### `{system}`", ""])
        for label, section in (
            ("Human/reference transcript errors", rows["human_transcript"]),
            ("ASR/Whisper transcript errors", rows["asr_transcript"]),
            ("ASR-added failures", rows["asr_added_failures"]),
        ):
            lines.extend([f"#### {label}", ""])
            examples = section.get("examples", [])
            if not examples:
                lines.append("- none")
            else:
                for example in examples:
                    lines.append(
                        "- "
                        f"`{example['id']}` fields `{json.dumps(example['failed_fields'], sort_keys=True)}`; "
                        f"transcript: {example['transcript']!r}"
                    )
            lines.append("")
    return "\n".join(lines)


def _summarize_records(records: list[dict[str, Any]], *, max_examples: int) -> dict[str, Any]:
    field_errors: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    error_records = 0
    for record in records:
        failed_fields = _failed_fields(record)
        if not failed_fields:
            continue
        error_records += 1
        field_errors.update(failed_fields)
        if len(examples) < max_examples:
            examples.append(_example(record, failed_fields))
    return {
        "records": len(records),
        "error_records": error_records,
        "field_error_counts": dict(sorted(field_errors.items())),
        "examples": examples,
    }


def _asr_added_failures(
    system: str,
    human_by_key: dict[tuple[str, str], dict[str, Any]],
    asr_by_key: dict[tuple[str, str], dict[str, Any]],
    *,
    max_examples: int,
) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    field_errors: Counter[str] = Counter()
    records = 0
    for key, asr_record in sorted(asr_by_key.items()):
        if key[0] != system:
            continue
        human_record = human_by_key.get(key)
        if human_record is None or not human_record.get("all_fields_match"):
            continue
        failed_fields = _failed_fields(asr_record)
        if not failed_fields:
            continue
        records += 1
        field_errors.update(failed_fields)
        if len(examples) < max_examples:
            examples.append(_example(asr_record, failed_fields))
    return {
        "records": records,
        "field_error_counts": dict(sorted(field_errors.items())),
        "examples": examples,
    }


def _records_by_system_id(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(record.get("system")), str(record.get("id"))): record for record in records}


def _failed_fields(record: dict[str, Any]) -> list[str]:
    return [field for field, matched in dict(record.get("field_matches") or {}).items() if not matched]


def _example(record: dict[str, Any], failed_fields: list[str]) -> dict[str, Any]:
    return {
        "id": str(record.get("id")),
        "failed_fields": failed_fields,
        "transcript": str(record.get("transcript", "")),
        "expected_intent": record.get("expected_intent", {}),
        "actual_intent": record.get("actual_intent", {}),
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
