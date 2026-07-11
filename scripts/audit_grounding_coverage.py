"""Audit map coverage across Week 3 grounding evaluation datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.grounding_coverage import (  # noqa: E402
    build_grounding_coverage_report,
    render_grounding_coverage_markdown,
)
from shepherd_ai.grounding_dataset import load_grounding_dataset  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "grounding_map_coverage_v1.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week3_grounding_map_coverage.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--dataset", type=Path, action="append", required=True)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    datasets = [load_grounding_dataset(dataset_path, locations) for dataset_path in args.dataset]
    report = build_grounding_coverage_report(locations, datasets)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(
        render_grounding_coverage_markdown(report, map_path=str(args.map)),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "map_records": report.map_records,
                "covered_location_ids": len(report.covered_location_ids),
                "untested_location_ids": len(report.untested_location_ids),
                "warnings": len(report.warnings),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")


if __name__ == "__main__":
    main()
