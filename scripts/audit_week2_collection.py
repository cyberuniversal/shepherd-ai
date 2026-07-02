"""Audit collected Week 2 command and audio records before training."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, summarize_audio_manifest  # noqa: E402
from shepherd_ai.intent_training import load_labeled_commands, summarize_labeled_commands  # noqa: E402


REQUIRED_SPLITS = ("train", "validation", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", required=True, help="Path to collected command JSONL.")
    parser.add_argument("--audio-manifest", help="Optional path to audio manifest JSONL.")
    parser.add_argument("--dataset-root", default=".", help="Root used for audio manifest path validation.")
    parser.add_argument("--output", required=True, help="Path to write audit JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commands_path = Path(args.commands)
    command_records = load_labeled_commands(commands_path)
    command_summary = summarize_labeled_commands(command_records)

    audio_summary: dict[str, Any] | None = None
    if args.audio_manifest and Path(args.audio_manifest).exists():
        audio_records = load_audio_manifest(args.audio_manifest, dataset_root=args.dataset_root)
        audio_summary = summarize_audio_manifest(audio_records)

    audit = {
        "metadata": {
            "commands": str(commands_path),
            "audio_manifest": str(Path(args.audio_manifest)) if args.audio_manifest else None,
            "note": "Audit only. Draft labels and collected records still require human review before research claims.",
        },
        "commands": command_summary,
        "audio": audio_summary,
        "warnings": _build_warnings(command_records, audio_summary),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


def _build_warnings(records: list[Any], audio_summary: dict[str, Any] | None) -> dict[str, Any]:
    split_counts = Counter(record.split for record in records)
    text_to_ids: dict[str, list[str]] = defaultdict(list)
    draft_labeled_records = 0
    null_field_counts: Counter[str] = Counter()

    for record in records:
        text_to_ids[_normalize_for_audit(record.text)].append(record.id)
        if record.data_type.endswith("_draft_labeled"):
            draft_labeled_records += 1
        for field, value in record.expected_intent.items():
            if value is None:
                null_field_counts[field] += 1

    duplicate_command_texts = [
        {"normalized_text": text, "ids": ids, "count": len(ids)}
        for text, ids in sorted(text_to_ids.items())
        if len(ids) > 1
    ]

    return {
        "missing_command_splits": [split for split in REQUIRED_SPLITS if split_counts.get(split, 0) == 0],
        "duplicate_command_texts": duplicate_command_texts,
        "draft_labeled_records": draft_labeled_records,
        "null_field_counts": dict(sorted(null_field_counts.items())),
        "audio_records": audio_summary["records"] if audio_summary else 0,
        "note": "Warnings identify review needs; they do not automatically make the data unusable.",
    }


def _normalize_for_audit(text: str) -> str:
    return " ".join(text.lower().split())


if __name__ == "__main__":
    main()
