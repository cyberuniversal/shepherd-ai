"""Analyze transcript errors from a saved ASR evaluation JSON file."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import word_error_details  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, help="Saved transcript evaluation JSON.")
    parser.add_argument("--output", required=True, help="Path to write ASR error analysis JSON.")
    return parser.parse_args()


def analyze_asr_errors(evaluation: dict[str, Any]) -> dict[str, Any]:
    operation_counts: Counter[str] = Counter()
    substitution_counts: Counter[str] = Counter()
    error_records: list[dict[str, Any]] = []

    for record in evaluation.get("records", []):
        details = word_error_details(str(record.get("expected", "")), str(record.get("predicted", "")))
        for operation in details["operations"]:
            operation_counts[operation["operation"]] += 1
            if operation["operation"] == "substitute":
                key = f"{operation['reference']} -> {operation['hypothesis']}"
                substitution_counts[key] += 1

        if not record.get("exact_match", False) or details["edit_distance"]:
            error_records.append(
                {
                    "id": record.get("id"),
                    "expected": record.get("expected", ""),
                    "predicted": record.get("predicted", ""),
                    "word_error_rate": details["word_error_rate"],
                    "edit_distance": details["edit_distance"],
                    "non_equal_operations": [
                        operation for operation in details["operations"] if operation["operation"] != "equal"
                    ],
                }
            )

    error_records.sort(key=lambda row: (row["word_error_rate"], row["edit_distance"], str(row["id"])), reverse=True)
    return {
        "metadata": {
            "source_model_name": evaluation.get("metadata", {}).get("model_name"),
            "source_model_version": evaluation.get("metadata", {}).get("model_version"),
            "source_parameters": evaluation.get("metadata", {}).get("parameters", {}),
            "source_summary": evaluation.get("summary", {}),
        },
        "operation_counts": dict(sorted(operation_counts.items())),
        "substitution_counts": dict(sorted(substitution_counts.items())),
        "error_record_count": len(error_records),
        "error_records": error_records,
    }


def main() -> None:
    args = parse_args()
    evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))
    analysis = analyze_asr_errors(evaluation)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(_summary(analysis), indent=2, sort_keys=True))


def _summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "error_record_count": analysis["error_record_count"],
        "operation_counts": analysis["operation_counts"],
        "substitution_counts": analysis["substitution_counts"],
    }


if __name__ == "__main__":
    main()
