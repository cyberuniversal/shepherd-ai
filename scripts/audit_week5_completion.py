"""Build the Week 5 completion-gate audit from generated scheduling artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week5_completion import (  # noqa: E402
    build_week5_completion_audit,
    render_week5_completion_markdown,
)


DEFAULT_SCHEDULE_COMPARISON = ROOT / "outputs" / "evaluations" / "week5_schedule_comparison_v1.json"
DEFAULT_ASSIGNMENT_CSV = ROOT / "outputs" / "tables" / "week5_assignments_least_loaded.csv"
DEFAULT_VISUALIZATION = ROOT / "outputs" / "visualizations" / "week5_drone_allocation_least_loaded.html"
DEFAULT_NOTEBOOK = ROOT / "notebooks" / "Notebook5_Scheduler.ipynb"
DEFAULT_ACCEPTANCE_CRITERIA = ROOT / "docs" / "week5_acceptance_criteria.json"
DEFAULT_RESEARCH_DEFERRALS = ROOT / "docs" / "week5_research_deferrals.json"
DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "week5_completion_gate_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week5_completion_gate_audit.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-comparison", type=Path, default=DEFAULT_SCHEDULE_COMPARISON)
    parser.add_argument("--assignment-csv", type=Path, default=DEFAULT_ASSIGNMENT_CSV)
    parser.add_argument("--allocation-visualization", type=Path, default=DEFAULT_VISUALIZATION)
    parser.add_argument("--scheduler-notebook", type=Path, default=DEFAULT_NOTEBOOK)
    parser.add_argument("--acceptance-criteria", type=Path, default=DEFAULT_ACCEPTANCE_CRITERIA)
    parser.add_argument("--research-deferrals", type=Path, default=DEFAULT_RESEARCH_DEFERRALS)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    audit = build_week5_completion_audit(
        schedule_comparison=_read_json(args.schedule_comparison),
        assignment_csv_text=args.assignment_csv.read_text(encoding="utf-8"),
        allocation_visualization_html=args.allocation_visualization.read_text(encoding="utf-8"),
        scheduler_notebook_text=args.scheduler_notebook.read_text(encoding="utf-8"),
        acceptance_criteria=_read_json(args.acceptance_criteria),
        research_deferrals=_read_json(args.research_deferrals),
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week5_completion_markdown(audit), encoding="utf-8")

    print(
        json.dumps(
            {
                "advancement_allowed": audit.advancement_allowed,
                "decision": audit.decision,
                "blockers": audit.blockers,
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
