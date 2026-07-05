"""Summarize transcript evaluation metrics by audio manifest split."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest JSONL containing split labels.")
    parser.add_argument("--dataset-root", required=True, help="Root directory audio paths must stay within.")
    parser.add_argument("--evaluation", required=True, help="Saved transcript evaluation JSON.")
    parser.add_argument("--output", required=True, help="Path to write split summary JSON.")
    parser.add_argument(
        "--split-policy",
        default="not stated",
        help="Human-readable split policy identifier to preserve in metadata.",
    )
    return parser.parse_args()


def summarize_by_split(records_by_id: dict[str, str], evaluation: dict[str, Any]) -> dict[str, Any]:
    rows_by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_manifest_ids: list[str] = []
    for row in evaluation.get("records", []):
        record_id = str(row.get("id", ""))
        split = records_by_id.get(record_id)
        if split is None:
            missing_manifest_ids.append(record_id)
            continue
        rows_by_split[split].append(row)

    if missing_manifest_ids:
        raise ValueError(f"evaluation records missing from manifest: {', '.join(sorted(missing_manifest_ids))}")

    split_summaries = {split: _summarize_rows(rows) for split, rows in sorted(rows_by_split.items())}
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_model_name": evaluation.get("metadata", {}).get("model_name"),
            "source_model_version": evaluation.get("metadata", {}).get("model_version"),
            "source_parameters": evaluation.get("metadata", {}).get("parameters", {}),
            "source_summary": evaluation.get("summary", {}),
        },
        "split_summaries": split_summaries,
    }


def main() -> None:
    args = parse_args()
    records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    records_by_id = {record.id: record.split for record in records}
    evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))
    summary = summarize_by_split(records_by_id, evaluation)
    summary["metadata"]["manifest"] = args.manifest
    summary["metadata"]["split_policy"] = args.split_policy
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary["split_summaries"], indent=2, sort_keys=True))


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact_matches = sum(1 for row in rows if row.get("exact_match", False))
    total_wer = sum(float(row.get("word_error_rate", 0.0)) for row in rows)
    return {
        "records": len(rows),
        "exact_matches": exact_matches,
        "exact_match_accuracy": exact_matches / len(rows) if rows else 0.0,
        "mean_word_error_rate": total_wer / len(rows) if rows else 0.0,
        "record_ids": sorted(str(row.get("id")) for row in rows),
    }


if __name__ == "__main__":
    main()
