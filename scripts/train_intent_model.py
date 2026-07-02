"""Train and evaluate the Week 2 intent extraction baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import (  # noqa: E402
    compare_with_deterministic_baseline,
    evaluate_intent_model,
    load_labeled_commands,
    save_intent_model,
    summarize_labeled_commands,
    train_intent_model,
    validate_split_integrity,
    with_training_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Path to labeled command JSONL.")
    parser.add_argument("--model-output", required=True, help="Path to write trained model JSON.")
    parser.add_argument("--metrics-output", required=True, help="Path to write trained model test metrics JSON.")
    parser.add_argument("--comparison-output", required=True, help="Path to write baseline comparison JSON.")
    parser.add_argument("--validation-output", help="Optional path to write validation metrics JSON.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model-name", default="trained_nb_v0")
    parser.add_argument("--model-version", default="0.1")
    parser.add_argument("--include-bigrams", action="store_true")
    parser.add_argument("--include-alias-features", action="store_true")
    parser.add_argument("--alias-feature-weight", type=int, default=3)
    parser.add_argument("--use-rule-overrides", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    records = load_labeled_commands(args.dataset)
    validate_split_integrity(records)
    train_records = [record for record in records if record.split == "train"]
    validation_records = [record for record in records if record.split == "validation"]
    test_records = [record for record in records if record.split == "test"]
    if not test_records:
        raise ValueError("dataset must include at least one test record")

    model = train_intent_model(
        train_records,
        model_name=args.model_name,
        model_version=args.model_version,
        include_bigrams=args.include_bigrams,
        include_alias_features=args.include_alias_features,
        alias_feature_weight=args.alias_feature_weight,
        use_rule_overrides=args.use_rule_overrides,
    )
    metrics = evaluate_intent_model(model, test_records, dataset_name=Path(args.dataset).name)
    metrics["metadata"]["split"] = "test"
    metrics["metadata"]["random_seed"] = args.seed
    comparison = compare_with_deterministic_baseline(
        model,
        test_records,
        dataset_name=Path(args.dataset).name,
    )
    comparison["metadata"]["random_seed"] = args.seed
    validation_metrics = None
    if args.validation_output:
        validation_metrics = evaluate_intent_model(
            model,
            validation_records,
            dataset_name=Path(args.dataset).name,
        )
        validation_metrics["metadata"]["split"] = "validation"
        validation_metrics["metadata"]["random_seed"] = args.seed

    model = with_training_metadata(
        model,
        {
            "dataset": str(Path(args.dataset)),
            "random_seed": args.seed,
            "split_counts": _split_counts(records),
            "dataset_summary": summarize_labeled_commands(records),
            "evaluation_artifacts": {
                "metrics": str(Path(args.metrics_output)),
                "comparison": str(Path(args.comparison_output)),
                **({"validation": str(Path(args.validation_output))} if args.validation_output else {}),
            },
        },
    )
    save_intent_model(model, args.model_output)
    _write_json(metrics, args.metrics_output)
    _write_json(comparison, args.comparison_output)
    if validation_metrics is not None:
        _write_json(validation_metrics, args.validation_output)
    print(
        json.dumps(
            {
                "train_records": len(train_records),
                "validation_records": len(validation_records),
                "test_records": len(test_records),
                "field_accuracy": metrics["summary"]["field_accuracy"],
                "exact_record_accuracy": metrics["summary"]["exact_record_accuracy"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _write_json(payload: dict, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _split_counts(records: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.split] = counts.get(record.split, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()
