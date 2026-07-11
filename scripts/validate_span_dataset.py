"""Validate a Week 2 span-labeled command dataset and export BIO rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import (  # noqa: E402
    load_span_labeled_commands,
    spans_to_bio_tags,
    summarize_span_labeled_commands,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Span-labeled command JSONL dataset.")
    parser.add_argument("--summary-output", help="Optional path for a summary JSON file.")
    parser.add_argument("--bio-output", help="Optional path for a BIO-token JSONL export.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_span_labeled_commands(args.dataset)
    summary = summarize_span_labeled_commands(records)

    if args.summary_output:
        summary_output = Path(args.summary_output)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if args.bio_output:
        bio_output = Path(args.bio_output)
        bio_output.parent.mkdir(parents=True, exist_ok=True)
        with bio_output.open("w", encoding="utf-8") as handle:
            for record in records:
                tagged = spans_to_bio_tags(record.text, record.spans)
                handle.write(
                    json.dumps(
                        {
                            "id": record.id,
                            "text": record.text,
                            "split": record.split,
                            "source": record.source,
                            "data_type": record.data_type,
                            "tokens": [token.text for token, _ in tagged],
                            "offsets": [[token.start, token.end] for token, _ in tagged],
                            "tags": [tag for _, tag in tagged],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
