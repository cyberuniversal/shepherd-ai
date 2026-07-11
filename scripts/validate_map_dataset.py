"""Validate and summarize a Shepherd-AI map CSV dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.map_validation import render_map_validation_markdown, validate_map_locations  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "map_validation_shepherd_test_map_v1.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week3_map_validation_report.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    report = validate_map_locations(locations)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(
        render_map_validation_markdown(report, map_path=str(args.map)),
        encoding="utf-8",
    )

    print(json.dumps({"records": report.records, "warnings": len(report.warnings)}, indent=2, sort_keys=True))
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")


if __name__ == "__main__":
    main()
