"""Validate and summarize a Week 3 grounding evaluation JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.grounding_dataset import (  # noqa: E402
    load_grounding_dataset,
    summarize_grounding_dataset,
)


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_DATASET = ROOT / "datasets" / "maps" / "grounding_holdout_synthetic_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "grounding_holdout_synthetic_v1_validation.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    records = load_grounding_dataset(args.dataset, locations)
    summary = summarize_grounding_dataset(records)

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"Wrote {args.summary_output}")


if __name__ == "__main__":
    main()
