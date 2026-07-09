"""Build a Week 2 audio manifest from a filled collection packet."""

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


READY_STATUS = "human_transcript_verified"
MANIFEST_FIELDS = ("id", "audio_path", "transcript", "source", "data_type", "split")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True, help="Filled packet JSONL.")
    parser.add_argument("--dataset-root", type=Path, default=Path("."))
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Skip blank/unready rows instead of failing. The resulting manifest is not a complete benchmark.",
    )
    args = parser.parse_args()

    packet_rows = _load_packet(args.packet)
    manifest_rows, skipped_rows = build_manifest_rows(packet_rows, dataset_root=args.dataset_root, allow_partial=args.allow_partial)
    _validate_manifest_rows(manifest_rows)

    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest_rows),
        encoding="utf-8",
    )
    records = load_audio_manifest(args.manifest_output, dataset_root=args.dataset_root)
    summary = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "packet": str(args.packet),
            "manifest_output": str(args.manifest_output),
            "ready_status_required": READY_STATUS,
            "allow_partial": args.allow_partial,
            "note": "Manifest builder only. Run the non-overlap audit before ASR or intent evaluation.",
        },
        "summary": summarize_audio_manifest(records),
        "skipped_rows": skipped_rows,
    }
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["summary"], indent=2, sort_keys=True))


def build_manifest_rows(
    packet_rows: list[dict[str, Any]],
    *,
    dataset_root: Path,
    allow_partial: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract manifest-ready rows from a filled collection packet."""

    manifest_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(packet_rows, start=1):
        record_id = str(row.get("id") or row.get("slot_id") or f"line_{line_number}")
        transcript = str(row.get("transcript", "")).strip()
        status = str(row.get("collection_status", "")).strip()
        if not transcript or status != READY_STATUS:
            skipped_rows.append(
                {
                    "line_number": line_number,
                    "id": record_id,
                    "reason": _skip_reason(transcript=transcript, status=status),
                }
            )
            continue
        manifest_row = {field: row.get(field) for field in MANIFEST_FIELDS}
        _validate_manifest_shape(manifest_row, line_number=line_number)
        _validate_audio_path(manifest_row, dataset_root=dataset_root, line_number=line_number)
        manifest_rows.append(manifest_row)

    if not allow_partial and skipped_rows:
        skipped = ", ".join(f"{row['id']}({row['reason']})" for row in skipped_rows[:10])
        raise ValueError(f"packet has unready rows; use --allow-partial only for temporary checks: {skipped}")
    if not manifest_rows:
        raise ValueError("no manifest-ready rows found")
    return manifest_rows, skipped_rows


def _load_packet(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"line {line_number}: packet row must be an object")
        rows.append(raw)
    if not rows:
        raise ValueError("packet is empty")
    return rows


def _validate_manifest_shape(row: dict[str, Any], *, line_number: int) -> None:
    missing = [field for field in MANIFEST_FIELDS if not isinstance(row.get(field), str) or not str(row[field]).strip()]
    if missing:
        raise ValueError(f"line {line_number}: missing manifest fields: {', '.join(missing)}")
    if row["data_type"] != "human_recorded_audio":
        raise ValueError(f"line {line_number}: data_type must be human_recorded_audio")
    if row["split"] not in {"validation", "test"}:
        raise ValueError(f"line {line_number}: post-development benchmark split must be validation or test")


def _validate_audio_path(row: dict[str, Any], *, dataset_root: Path, line_number: int) -> None:
    root = dataset_root.resolve()
    path = (root / str(row["audio_path"])).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"line {line_number}: audio_path must stay inside dataset_root")
    if path.suffix.lower() != ".wav":
        raise ValueError(f"line {line_number}: audio_path must point to a .wav file")
    if not path.exists():
        raise FileNotFoundError(f"line {line_number}: WAV file does not exist: {path}")


def _validate_manifest_rows(rows: list[dict[str, Any]]) -> None:
    ids = Counter(str(row["id"]) for row in rows)
    duplicates = sorted(record_id for record_id, count in ids.items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate audio ids: {', '.join(duplicates)}")
    by_transcript: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_transcript[_normalize_text(str(row["transcript"]))].append(str(row["id"]))
    duplicate_transcripts = {
        transcript: ids
        for transcript, ids in by_transcript.items()
        if transcript and len(ids) > 1
    }
    if duplicate_transcripts:
        first = next(iter(duplicate_transcripts.items()))
        raise ValueError(f"duplicate normalized transcript in manifest: {first[0]!r} -> {first[1]}")


def _skip_reason(*, transcript: str, status: str) -> str:
    if not transcript:
        return "blank_transcript"
    if status != READY_STATUS:
        return f"collection_status_not_{READY_STATUS}"
    return "unknown"


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


if __name__ == "__main__":
    main()
