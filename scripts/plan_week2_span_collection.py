"""Plan targeted Week 2 span-data collection from token-classifier errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import load_span_labeled_commands, summarize_span_labeled_commands  # noqa: E402
from shepherd_ai.week2_collection_planning import (  # noqa: E402
    build_week2_collection_plan,
    render_week2_collection_plan_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--span-dataset", required=True, help="Human-verified span command JSONL dataset.")
    parser.add_argument("--evaluation", required=True, help="Record-level transformer evaluation JSON.")
    parser.add_argument("--error-analysis", required=True, help="Transformer BIO error-analysis JSON.")
    parser.add_argument("--json-output", required=True, help="Machine-readable collection plan JSON output.")
    parser.add_argument("--markdown-output", required=True, help="Human-readable collection plan Markdown output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    span_dataset_path = Path(args.span_dataset)
    evaluation_path = Path(args.evaluation)
    error_analysis_path = Path(args.error_analysis)

    span_records = load_span_labeled_commands(span_dataset_path)
    span_summary = summarize_span_labeled_commands(span_records)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    error_analysis = json.loads(error_analysis_path.read_text(encoding="utf-8"))

    plan = build_week2_collection_plan(
        span_summary=span_summary,
        evaluation_summary=dict(evaluation.get("summary", {})),
        error_analysis=error_analysis,
        source_paths={
            "span_dataset": str(span_dataset_path),
            "evaluation": str(evaluation_path),
            "error_analysis": str(error_analysis_path),
        },
    )

    json_output_path = Path(args.json_output)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    markdown_output_path = Path(args.markdown_output)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_week2_collection_plan_markdown(plan), encoding="utf-8")

    print(
        json.dumps(
            {
                "minimum_human_written_span_records": plan["recommended_next_batch"][
                    "minimum_human_written_span_records"
                ],
                "json_output": str(json_output_path),
                "markdown_output": str(markdown_output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
