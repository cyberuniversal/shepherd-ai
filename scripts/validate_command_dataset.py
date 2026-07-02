"""Validate and summarize a labeled Week 2 command JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import (  # noqa: E402
    load_labeled_commands,
    summarize_labeled_commands,
    validate_split_integrity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Path to labeled command JSONL.")
    parser.add_argument("--summary-output", help="Optional path to write summary JSON.")
    parser.add_argument(
        "--require-splits",
        help="Comma-separated split names that must be present, for example train,validation,test.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_labeled_commands(args.dataset)
    validate_split_integrity(records)
    summary = summarize_labeled_commands(records)
    if args.require_splits:
        required = {split.strip() for split in args.require_splits.split(",") if split.strip()}
        present = set(summary["split_counts"])
        missing = sorted(required - present)
        if missing:
            raise ValueError(f"missing required splits: {', '.join(missing)}")

    if args.summary_output:
        output = Path(args.summary_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
