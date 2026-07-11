"""Create a human-review packet for audio-transcript intent labels.

This script drafts intent labels from verified audio transcripts so a reviewer
can correct them before the records become gold labels. It does not create a
training/evaluation dataset and does not mark draft labels as human-verified.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.intent_training import EVAL_FIELDS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest with human-verified transcripts.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--jsonl-output", required=True, help="Draft review packet JSONL output.")
    parser.add_argument("--markdown-output", required=True, help="Human-readable review packet output.")
    parser.add_argument(
        "--review-source",
        default="manual_week2_audio_generalization_intent_review_v1",
        help="Source value to use once records are human-reviewed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    packet = build_audio_intent_review_packet(records, review_source=args.review_source)

    jsonl_output = Path(args.jsonl_output)
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet["records"]),
        encoding="utf-8",
    )

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_audio_intent_review_markdown(packet), encoding="utf-8")

    print(json.dumps(packet["summary"], indent=2, sort_keys=True))


def build_audio_intent_review_packet(records: list[Any], *, review_source: str) -> dict[str, Any]:
    review_records = [_draft_review_record(record, review_source=review_source) for record in records]
    split_counts = Counter(record["split"] for record in review_records)
    flag_counts: Counter[str] = Counter()
    for record in review_records:
        flag_counts.update(record["draft_review_flags"])
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Draft intent-label review packet only. Labels come from the deterministic parser and must be "
                "human-reviewed before training, evaluation, or accuracy claims."
            ),
            "draft_label_source": f"{DETERMINISTIC_PARSER_NAME}_draft",
            "review_source": review_source,
        },
        "summary": {
            "records": len(review_records),
            "split_counts": dict(sorted(split_counts.items())),
            "review_status_counts": dict(Counter(record["review_status"] for record in review_records)),
            "draft_review_flag_counts": dict(sorted(flag_counts.items())),
        },
        "records": review_records,
    }


def render_audio_intent_review_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# Week 2 Audio Intent Review Packet",
        "",
        packet["metadata"]["note"],
        "",
        "## Summary",
        "",
        f"- Records: {summary['records']}",
        f"- Split counts: `{json.dumps(summary['split_counts'], sort_keys=True)}`",
        f"- Draft label source: `{packet['metadata']['draft_label_source']}`",
        f"- Draft review flag counts: `{json.dumps(summary['draft_review_flag_counts'], sort_keys=True)}`",
        "",
        "## Review Instructions",
        "",
        "- Listen to the WAV file if there is any transcript doubt.",
        "- Correct `action`, `count`, `location`, `target`, and `constraints` in the JSONL packet.",
        "- Keep `review_status` as `needs_human_review` until a human has checked the record.",
        "- After review, change `review_status` to `human_reviewed` and set `data_type` to `human_verified_audio_intent_command`.",
        "- Do not use draft records for training or accuracy reporting.",
        "",
        "## Draft Records",
        "",
        "| ID | Split | Transcript | Draft flags | Draft intent |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in packet["records"]:
        intent = {field: record["expected_intent"][field] for field in EVAL_FIELDS}
        lines.append(
            f"| `{record['id']}` | `{record['split']}` | {record['text']} | "
            f"`{', '.join(record['draft_review_flags']) or 'none'}` | "
            f"`{json.dumps(intent, sort_keys=True)}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _draft_review_record(record: Any, *, review_source: str) -> dict[str, Any]:
    intent = parse_intent(record.transcript).to_dict()
    expected_intent = {field: intent[field] for field in EVAL_FIELDS}
    return {
        "id": f"{record.id}_intent",
        "audio_id": record.id,
        "audio_path": _as_posix(record.audio_path),
        "text": record.transcript,
        "split": record.split,
        "source": review_source,
        "data_type": "human_recorded_audio_intent_draft",
        "label_source": f"{DETERMINISTIC_PARSER_NAME}_draft",
        "parser": intent["parser"],
        "review_status": "needs_human_review",
        "expected_intent": expected_intent,
        "draft_parser_notes": intent.get("notes", []),
        "draft_review_flags": _draft_review_flags(expected_intent, intent.get("notes", [])),
        "review_notes": [],
    }


def _as_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _draft_review_flags(expected_intent: dict[str, Any], parser_notes: list[str]) -> list[str]:
    flags = list(parser_notes)
    if expected_intent.get("action") is None:
        flags.append("action_missing_or_unsupported")
    if expected_intent.get("target") is None:
        flags.append("target_missing")
    if expected_intent.get("target") == "area":
        flags.append("generic_target_area")
    if expected_intent.get("count") is None:
        flags.append("count_missing")
    if expected_intent.get("constraints"):
        flags.append("constraint_review_needed")
    return sorted(set(flags))


if __name__ == "__main__":
    main()
