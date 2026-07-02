"""Validate and summarize a Week 2 audio manifest JSONL file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest, summarize_audio_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to audio manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--summary-output", help="Optional path to write summary JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    summary = summarize_audio_manifest(records)
    if args.summary_output:
        output = Path(args.summary_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
