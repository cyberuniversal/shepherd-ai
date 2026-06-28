"""Generate transcript output from an audio manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402
from shepherd_ai.transcription import (  # noqa: E402
    CachedTranscriptTranscriber,
    transcribe_records,
    write_transcription_output,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to audio manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root directory used to resolve audio paths.")
    parser.add_argument("--backend", choices=("cached",), default="cached")
    parser.add_argument("--output", required=True, help="Path for raw transcript output JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    transcriber = CachedTranscriptTranscriber.from_records(records)
    output = transcribe_records(records, transcriber)
    write_transcription_output(output, args.output)
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
