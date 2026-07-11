"""Create a blank Week 2 audio generalization collection packet.

The packet does not generate command text or audio. It pre-registers record
IDs, splits, and non-overlap requirements for a future audio batch so the next
ASR evaluation is not just a repeat of existing command/span text.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402
from shepherd_ai.intent_training import load_labeled_commands  # noqa: E402
from shepherd_ai.span_annotations import load_span_labeled_commands  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", required=True, help="Existing curated command JSONL.")
    parser.add_argument("--spans", required=True, help="Existing span-labeled command JSONL.")
    parser.add_argument(
        "--existing-audio-manifest",
        action="append",
        required=True,
        help="Existing audio manifest JSONL. Repeat to block overlap with multiple prior audio sets.",
    )
    parser.add_argument("--dataset-root", required=True, help="Root used for existing audio path validation.")
    parser.add_argument("--jsonl-output", required=True, help="Blank packet JSONL output.")
    parser.add_argument("--markdown-output", required=True, help="Human-readable packet output.")
    parser.add_argument("--record-prefix", default="audio_generalization", help="Prefix for new audio IDs.")
    parser.add_argument("--source", default="manual_week2_audio_generalization_v1", help="Source for future records.")
    parser.add_argument("--validation-count", type=int, default=10, help="Number of validation slots.")
    parser.add_argument("--test-count", type=int, default=20, help="Number of test slots.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    existing_texts = _existing_text_profile(
        commands_path=args.commands,
        spans_path=args.spans,
        existing_audio_manifests=args.existing_audio_manifest,
        dataset_root=args.dataset_root,
    )
    packet = build_audio_generalization_packet(
        validation_count=args.validation_count,
        test_count=args.test_count,
        record_prefix=args.record_prefix,
        source=args.source,
        existing_texts=existing_texts,
    )

    jsonl_output = Path(args.jsonl_output)
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet["slots"]),
        encoding="utf-8",
    )

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_audio_generalization_packet_markdown(packet), encoding="utf-8")

    print(json.dumps(packet["summary"], indent=2, sort_keys=True))


def build_audio_generalization_packet(
    *,
    validation_count: int,
    test_count: int,
    record_prefix: str,
    source: str,
    existing_texts: dict[str, Any],
) -> dict[str, Any]:
    if validation_count < 0 or test_count < 0:
        raise ValueError("slot counts must be non-negative")
    if validation_count + test_count == 0:
        raise ValueError("at least one validation or test slot is required")

    slots: list[dict[str, Any]] = []
    slot_index = 1
    for split, count in (("validation", validation_count), ("test", test_count)):
        for _ in range(count):
            audio_id = f"{record_prefix}_{slot_index:03d}"
            slots.append(
                {
                    "slot_id": audio_id,
                    "id": audio_id,
                    "split": split,
                    "audio_path": f"datasets/sample_audio/{audio_id}.wav",
                    "transcript": "",
                    "source": source,
                    "data_type": "human_recorded_audio",
                    "collection_status": "blank_slot_not_collected",
                    "required_checks": [
                        "record a real WAV file before adding this slot to the manifest",
                        "enter a human-verified transcript after listening to the recording",
                        "transcript must not normalize-match any existing command text, span text, or audio transcript",
                        "do not run ASR before the split and transcript are recorded",
                    ],
                }
            )
            slot_index += 1

    split_counts = Counter(slot["split"] for slot in slots)
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Blank pre-registration packet only. It contains no collected audio, no transcripts, "
                "and no evaluation result."
            ),
        },
        "summary": {
            "slots": len(slots),
            "split_counts": dict(sorted(split_counts.items())),
            "existing_unique_normalized_texts": len(existing_texts["normalized_texts"]),
            "non_overlap_required": True,
        },
        "existing_text_profile": existing_texts["summary"],
        "slots": slots,
    }


def render_audio_generalization_packet_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# Week 2 Audio Generalization Collection Packet",
        "",
        packet["metadata"]["note"],
        "",
        "## Purpose",
        "",
        "Collect a fresh audio batch whose transcripts do not overlap existing Week 2 command or span text.",
        "This is intended to produce stronger ASR and speech-to-intent evidence than prior audio samples.",
        "",
        "## Summary",
        "",
        f"- Blank slots: {summary['slots']}",
        f"- Split counts: `{json.dumps(summary['split_counts'], sort_keys=True)}`",
        f"- Existing normalized texts blocked for overlap: {summary['existing_unique_normalized_texts']}",
        "- Non-overlap required: true",
        "",
        "## Collection Rules",
        "",
        "- Record the WAV before running ASR.",
        "- Write the human-verified transcript before running ASR.",
        "- Do not reuse existing command, span, or audio transcript text.",
        "- Keep WAV files private unless consent/privacy requirements allow publication.",
        "- Preserve failures and rejected recordings in notes rather than deleting them silently.",
        "",
        "## Blank Slots",
        "",
        "| Slot | Split | Future audio path | Transcript |",
        "| --- | --- | --- | --- |",
    ]
    for slot in packet["slots"]:
        lines.append(f"| `{slot['id']}` | `{slot['split']}` | `{slot['audio_path']}` | blank |")
    lines.append("")
    return "\n".join(lines)


def _existing_text_profile(
    *,
    commands_path: str | Path,
    spans_path: str | Path,
    existing_audio_manifests: list[str | Path],
    dataset_root: str | Path,
) -> dict[str, Any]:
    command_records = load_labeled_commands(commands_path)
    span_records = load_span_labeled_commands(spans_path)
    audio_records = [
        record
        for manifest_path in existing_audio_manifests
        for record in load_audio_manifest(manifest_path, dataset_root=dataset_root)
    ]
    normalized_sources: dict[str, set[str]] = {}
    for source_name, records, text_attr in (
        ("commands", command_records, "text"),
        ("spans", span_records, "text"),
        ("audio", audio_records, "transcript"),
    ):
        for record in records:
            normalized = _normalize_text(getattr(record, text_attr))
            normalized_sources.setdefault(normalized, set()).add(source_name)
    source_counts: Counter[str] = Counter()
    for sources in normalized_sources.values():
        for source in sources:
            source_counts[source] += 1
    return {
        "normalized_texts": set(normalized_sources),
        "summary": {
            "unique_normalized_texts": len(normalized_sources),
            "source_counts": dict(sorted(source_counts.items())),
        },
    }


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


if __name__ == "__main__":
    main()
