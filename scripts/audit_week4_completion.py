"""Build the Week 4 completion-gate audit from generated planning artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week4_completion import (  # noqa: E402
    build_week4_completion_audit,
    render_week4_completion_markdown,
)


DEFAULT_HUMAN_PLANNING = ROOT / "outputs" / "evaluations" / "week4_planning_human_grounding_benchmark_v1.json"
DEFAULT_FOCUSED_PLANNING = ROOT / "outputs" / "evaluations" / "week4_planning_cases_v1.json"
DEFAULT_ACCEPTANCE_CRITERIA = ROOT / "docs" / "week4_acceptance_criteria.json"
DEFAULT_RESEARCH_DEFERRALS = ROOT / "docs" / "week4_research_deferrals.json"
DEFAULT_FLOW_DIAGRAM = ROOT / "outputs" / "diagrams" / "week4_plan_north_field_flow.md"
DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "week4_completion_gate_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week4_completion_gate_audit.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--human-planning-evaluation", type=Path, default=DEFAULT_HUMAN_PLANNING)
    parser.add_argument("--focused-planning-evaluation", type=Path, default=DEFAULT_FOCUSED_PLANNING)
    parser.add_argument("--acceptance-criteria", type=Path, default=DEFAULT_ACCEPTANCE_CRITERIA)
    parser.add_argument("--research-deferrals", type=Path, default=DEFAULT_RESEARCH_DEFERRALS)
    parser.add_argument("--flow-diagram", type=Path, default=DEFAULT_FLOW_DIAGRAM)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    audit = build_week4_completion_audit(
        human_benchmark_planning=_read_json(args.human_planning_evaluation),
        focused_planning_cases=_read_json(args.focused_planning_evaluation),
        flow_diagram_markdown=args.flow_diagram.read_text(encoding="utf-8"),
        acceptance_criteria=_read_json(args.acceptance_criteria),
        research_deferrals=_read_json(args.research_deferrals),
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week4_completion_markdown(audit), encoding="utf-8")

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
