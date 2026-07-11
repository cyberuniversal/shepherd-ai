"""Compare deterministic parser and trained span-to-intent paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_intent import compare_intent_paths_from_span_evaluation  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, help="Saved BIO/entity evaluation JSON.")
    parser.add_argument("--output", required=True, help="Path to write comparison JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))
    comparison = compare_intent_paths_from_span_evaluation(
        evaluation,
        metadata={"source_evaluation": args.evaluation},
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(comparison["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
