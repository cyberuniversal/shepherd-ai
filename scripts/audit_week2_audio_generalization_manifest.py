"""Audit a future Week 2 audio manifest for non-overlap with existing text data."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, summarize_audio_manifest  # noqa: E402
from shepherd_ai.intent_training import load_labeled_commands  # noqa: E402
from shepherd_ai.span_annotations import load_span_labeled_commands  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", required=True, help="Future audio manifest to audit.")
    parser.add_argument("--commands", required=True, help="Existing curated command JSONL.")
    parser.add_argument("--spans", required=True, help="Existing span-labeled command JSONL.")
    parser.add_argument("--existing-audio-manifest", required=True, help="Existing audio manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root used for audio path validation.")
    parser.add_argument("--output", required=True, help="Audit JSON output.")
    parser.add_argument(
        "--fail-on-overlap",
        action="store_true",
        help="Exit non-zero when candidate transcripts overlap existing data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate_records = load_audio_manifest(args.candidate_manifest, dataset_root=args.dataset_root)
    existing_index = _existing_text_index(
        commands_path=args.commands,
        spans_path=args.spans,
        existing_audio_manifest=args.existing_audio_manifest,
        dataset_root=args.dataset_root,
    )
    audit = audit_candidate_manifest(candidate_records, existing_index)
    audit["metadata"]["candidate_manifest"] = args.candidate_manifest
    audit["metadata"]["commands"] = args.commands
    audit["metadata"]["spans"] = args.spans
    audit["metadata"]["existing_audio_manifest"] = args.existing_audio_manifest

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit["summary"], indent=2, sort_keys=True))
    if args.fail_on_overlap and audit["summary"]["overlap_records"]:
        raise SystemExit(1)


def audit_candidate_manifest(candidate_records: list[Any], existing_index: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    duplicate_transcripts = _duplicates_within_candidate(candidate_records)
    overlaps: list[dict[str, Any]] = []
    for record in candidate_records:
        normalized = _normalize_text(record.transcript)
        matches = existing_index.get(normalized, [])
        if matches:
            overlaps.append(
                {
                    "id": record.id,
                    "split": record.split,
                    "transcript": record.transcript,
                    "normalized_transcript": normalized,
                    "matched_existing_records": matches,
                }
            )

    split_counts = summarize_audio_manifest(candidate_records)["split_counts"]
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Audio generalization manifest audit. A clean future evaluation batch should have no transcript "
                "overlap with existing command, span, or audio transcript text."
            ),
        },
        "summary": {
            "records": len(candidate_records),
            "split_counts": split_counts,
            "overlap_records": len(overlaps),
            "duplicate_transcripts_within_candidate": len(duplicate_transcripts),
            "passes_non_overlap_policy": not overlaps and not duplicate_transcripts,
        },
        "overlaps": overlaps,
        "duplicate_transcripts_within_candidate": duplicate_transcripts,
    }


def _existing_text_index(
    *,
    commands_path: str | Path,
    spans_path: str | Path,
    existing_audio_manifest: str | Path,
    dataset_root: str | Path,
) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in load_labeled_commands(commands_path):
        index[_normalize_text(record.text)].append({"source": "commands", "id": record.id, "split": record.split})
    for record in load_span_labeled_commands(spans_path):
        index[_normalize_text(record.text)].append({"source": "spans", "id": record.id, "split": record.split})
    for record in load_audio_manifest(existing_audio_manifest, dataset_root=dataset_root):
        index[_normalize_text(record.transcript)].append({"source": "audio", "id": record.id, "split": record.split})
    return dict(index)


def _duplicates_within_candidate(records: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        grouped[_normalize_text(record.transcript)].append(record)
    duplicates: list[dict[str, Any]] = []
    for normalized, matches in sorted(grouped.items()):
        if len(matches) > 1:
            duplicates.append(
                {
                    "normalized_transcript": normalized,
                    "ids": [record.id for record in matches],
                    "splits": sorted({record.split for record in matches}),
                }
            )
    return duplicates


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


if __name__ == "__main__":
    main()
