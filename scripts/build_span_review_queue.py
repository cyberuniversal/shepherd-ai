"""Build a human review queue from held-out span prediction errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.hf_token_analysis import build_span_review_queue  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, help="Record-level evaluation JSON.")
    parser.add_argument("--output", required=True, help="JSONL path for review queue records.")
    parser.add_argument("--summary-output", required=True, help="JSON path for queue metadata and summary.")
    parser.add_argument(
        "--focus-field",
        action="append",
        default=[],
        help="Field to prioritize in review ordering. Repeatable; defaults to target and constraint.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluation_path = Path(args.evaluation)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    focus_fields = tuple(args.focus_field) if args.focus_field else ("target", "constraint")
    queue = build_span_review_queue(evaluation, focus_fields=focus_fields)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in queue["records"]),
        encoding="utf-8",
    )

    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_payload = {**queue["metadata"], **queue["summary"], "source_evaluation": str(evaluation_path)}
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(queue["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
