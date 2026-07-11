"""Validate and summarize a Week 6 aerial-image manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import load_vision_manifest, summarize_vision_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Aerial-image manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root all manifest paths must stay within.")
    parser.add_argument("--summary-output", required=True, help="Path to write summary JSON.")
    args = parser.parse_args()

    records = load_vision_manifest(args.manifest, dataset_root=args.dataset_root)
    summary = {
        "metadata": {
            "manifest": str(Path(args.manifest)),
            "dataset_root": str(Path(args.dataset_root)),
            "research_note": (
                "Manifest validation checks provenance and file availability only. "
                "It is not detection-performance evidence."
            ),
        },
        "summary": summarize_vision_manifest(records),
    }

    output = Path(args.summary_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
