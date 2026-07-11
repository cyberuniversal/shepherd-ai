"""Compare saved span tagger metric files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


METRIC_FIELDS = ("token_accuracy", "entity_precision", "entity_recall", "entity_f1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", action="append", required=True, help="Saved span tagger metrics JSON.")
    parser.add_argument("--output", required=True, help="Path to write comparison JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.metrics) < 2:
        raise ValueError("provide at least two --metrics files")
    comparison = compare_metrics([Path(path) for path in args.metrics])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "best_by_entity_f1": comparison["best_by_entity_f1"],
                "runs": list(comparison["runs"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


def compare_metrics(paths: list[Path]) -> dict:
    runs: dict[str, dict] = {}
    first_metrics: dict[str, float] | None = None
    for index, path in enumerate(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = dict(payload.get("metadata") or {})
        summary = dict(payload.get("summary") or {})
        model_name = str(metadata.get("model_name") or path.stem)
        metrics = {field: float(summary.get(field, 0.0)) for field in METRIC_FIELDS}
        if first_metrics is None:
            first_metrics = metrics
        runs[model_name] = {
            "path": str(path),
            "split": metadata.get("split"),
            "metrics": metrics,
            "delta_from_first": {
                field: metrics[field] - first_metrics[field]
                for field in METRIC_FIELDS
            },
        }
    best_by_entity_f1 = max(runs, key=lambda name: runs[name]["metrics"]["entity_f1"])
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metric_fields": list(METRIC_FIELDS),
        "best_by_entity_f1": best_by_entity_f1,
        "runs": runs,
    }


if __name__ == "__main__":
    main()
