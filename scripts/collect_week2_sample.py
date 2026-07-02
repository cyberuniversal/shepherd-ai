"""Collect one Week 2 text command and optional WAV recording.

This helper is intentionally collection-focused. It writes draft intent labels
from the deterministic parser so records are easy to review, but those labels
are not human-verified ground truth.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, summarize_audio_manifest  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.intent_training import EVAL_FIELDS, load_labeled_commands, validate_split_integrity  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="Human-provided command text or verified transcript.")
    parser.add_argument("--wav", help="Optional path to a WAV recording to copy into datasets/sample_audio.")
    parser.add_argument("--split", default="train", choices=("train", "validation", "test"))
    parser.add_argument("--source", default="manual_week2_collection_v1")
    parser.add_argument("--dataset-root", default=".")
    parser.add_argument("--command-output", default="datasets/commands/human_written_commands_draft.jsonl")
    parser.add_argument("--audio-dir", default="datasets/sample_audio")
    parser.add_argument("--audio-manifest", default="datasets/sample_audio/manifest.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root).resolve()
    command_output = _resolve_under_root(dataset_root, args.command_output)
    command_output.parent.mkdir(parents=True, exist_ok=True)

    command_id = _next_id(command_output, "human_cmd")
    command_record = _build_draft_command_record(
        command_id=command_id,
        text=args.text,
        split=args.split,
        source=args.source,
    )
    _append_jsonl(command_output, command_record)
    validate_split_integrity(load_labeled_commands(command_output))

    audio_record: dict[str, Any] | None = None
    if args.wav:
        audio_dir = _resolve_under_root(dataset_root, args.audio_dir)
        audio_manifest = _resolve_under_root(dataset_root, args.audio_manifest)
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_manifest.parent.mkdir(parents=True, exist_ok=True)
        audio_id = _next_id(audio_manifest, "audio")
        copied_audio = _copy_wav(Path(args.wav), audio_dir / f"{audio_id}.wav")
        audio_record = {
            "id": audio_id,
            "audio_path": _relative_posix(copied_audio, dataset_root),
            "transcript": args.text.strip(),
            "source": args.source,
            "data_type": "human_recorded_audio",
            "split": args.split,
        }
        _append_jsonl(audio_manifest, audio_record)
        summarize_audio_manifest(load_audio_manifest(audio_manifest, dataset_root=dataset_root))

    print(
        json.dumps(
            {
                "command_record": command_id,
                "command_output": str(command_output),
                "audio_record": audio_record["id"] if audio_record else None,
                "label_source": f"{DETERMINISTIC_PARSER_NAME}_draft",
                "note": "Draft intent labels must be reviewed before use as human-verified ground truth.",
            },
            indent=2,
            sort_keys=True,
        )
    )


def _build_draft_command_record(*, command_id: str, text: str, split: str, source: str) -> dict[str, Any]:
    intent = parse_intent(text).to_dict()
    return {
        "id": command_id,
        "text": text.strip(),
        "split": split,
        "source": source.strip(),
        "data_type": "human_written_command_draft_labeled",
        "label_source": f"{DETERMINISTIC_PARSER_NAME}_draft",
        "expected_intent": {field: intent[field] for field in EVAL_FIELDS},
    }


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _copy_wav(source: Path, destination: Path) -> Path:
    resolved_source = source.resolve()
    if resolved_source.suffix.lower() != ".wav":
        raise ValueError("--wav must point to a .wav file")
    if not resolved_source.exists():
        raise FileNotFoundError(f"WAV file does not exist: {resolved_source}")
    shutil.copy2(resolved_source, destination)
    return destination.resolve()


def _resolve_under_root(root: Path, raw_path: str) -> Path:
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"path must stay under dataset root: {candidate}")
    return candidate


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _next_id(path: Path, prefix: str) -> str:
    max_seen = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            record_id = str(raw.get("id", ""))
            if not record_id.startswith(f"{prefix}_"):
                continue
            suffix = record_id.rsplit("_", 1)[-1]
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
    return f"{prefix}_{max_seen + 1:03d}"


if __name__ == "__main__":
    main()
