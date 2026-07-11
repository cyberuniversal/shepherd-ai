"""Evaluate a saved Week 2 intent model on a labeled command dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import (  # noqa: E402
    evaluate_intent_model,
    load_intent_model,
    load_labeled_commands,
    summarize_labeled_commands,
    validate_split_integrity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to saved trained intent model JSON.")
    parser.add_argument("--dataset", required=True, help="Path to labeled command JSONL.")
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--output", required=True, help="Path to write evaluation JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_intent_model(args.model)
    records = load_labeled_commands(args.dataset)
    validate_split_integrity(records)
    split_records = [record for record in records if record.split == args.split]
    if not split_records:
        raise ValueError(f"dataset has no records for split {args.split!r}")

    metrics = evaluate_intent_model(model, split_records, dataset_name=Path(args.dataset).name)
    metrics["metadata"]["split"] = args.split
    metrics["metadata"]["evaluation_mode"] = "saved_model"
    metrics["metadata"]["model_artifact"] = str(Path(args.model))
    metrics["metadata"]["dataset_summary"] = summarize_labeled_commands(records)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metrics["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
