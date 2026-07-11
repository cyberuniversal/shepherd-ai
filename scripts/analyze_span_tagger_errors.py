"""Analyze BIO span tagger errors from a saved evaluation JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_training import analyze_span_tagger_errors  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, help="Saved span tagger evaluation JSON.")
    parser.add_argument("--output", required=True, help="Path to write error analysis JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))
    analysis = analyze_span_tagger_errors(evaluation)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(_summary(analysis), indent=2, sort_keys=True))


def _summary(analysis: dict) -> dict:
    return {
        "false_negative_entity_counts": analysis["false_negative_entity_counts"],
        "false_positive_entity_counts": analysis["false_positive_entity_counts"],
        "token_confusion_labels": len(analysis["token_confusion"]),
        "worst_records": len(analysis["worst_records"]),
    }


if __name__ == "__main__":
    main()
