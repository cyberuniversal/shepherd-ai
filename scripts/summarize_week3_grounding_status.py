"""Summarize Week 3 grounding validation, evaluation, and clarification artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week3_status import (  # noqa: E402
    build_week3_grounding_status,
    render_week3_grounding_status_markdown,
)


DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "week3_grounding_status.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week3_grounding_status.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-validation", type=Path, required=True)
    parser.add_argument("--grounding-evaluation", type=Path, action="append", default=[])
    parser.add_argument("--clarification-report", type=Path, action="append", default=[])
    parser.add_argument("--applied-resolution", type=Path, action="append", default=[])
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    status = build_week3_grounding_status(
        map_validation=_read_json(args.map_validation),
        grounding_evaluations=[_read_json(path) for path in args.grounding_evaluation],
        clarification_reports=[_read_json(path) for path in args.clarification_report],
        applied_resolutions=[_read_json(path) for path in args.applied_resolution],
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(status.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.write_text(render_week3_grounding_status_markdown(status), encoding="utf-8")

    print(json.dumps(status.to_dict()["readiness"], indent=2, sort_keys=True))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_markdown}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
