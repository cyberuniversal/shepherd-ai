"""Build the Week 3 completion-gate audit from generated artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week3_completion import (  # noqa: E402
    build_week3_completion_audit,
    render_week3_completion_markdown,
)


DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "week3_completion_gate_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week3_completion_gate_audit.md"
DEFAULT_ACCEPTANCE_CRITERIA = ROOT / "docs" / "week3_acceptance_criteria.json"
DEFAULT_RESEARCH_DEFERRALS = ROOT / "docs" / "week3_research_deferrals.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-validation", type=Path, required=True)
    parser.add_argument("--region-map-validation", type=Path, required=True)
    parser.add_argument("--grounding-evaluation", type=Path, action="append", required=True)
    parser.add_argument("--grounding-dataset-validation", type=Path, action="append", required=True)
    parser.add_argument("--coverage-report", type=Path, required=True)
    parser.add_argument("--week3-status", type=Path, required=True)
    parser.add_argument("--acceptance-criteria", type=Path, default=DEFAULT_ACCEPTANCE_CRITERIA)
    parser.add_argument("--research-deferrals", type=Path, default=DEFAULT_RESEARCH_DEFERRALS)
    parser.add_argument("--human-grounding-dataset-validation", type=Path)
    parser.add_argument("--human-grounding-evaluation", type=Path)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    audit = build_week3_completion_audit(
        map_validation=_read_json(args.map_validation),
        region_map_validation=_read_json(args.region_map_validation),
        grounding_evaluations=[_read_json(path) for path in args.grounding_evaluation],
        grounding_dataset_validations=[_read_json(path) for path in args.grounding_dataset_validation],
        coverage_report=_read_json(args.coverage_report),
        week3_status=_read_json(args.week3_status),
        acceptance_criteria=_read_json(args.acceptance_criteria),
        research_deferrals=_read_json(args.research_deferrals),
        human_grounding_dataset_validation=(
            _read_json(args.human_grounding_dataset_validation)
            if args.human_grounding_dataset_validation
            else None
        ),
        human_grounding_evaluation=(
            _read_json(args.human_grounding_evaluation)
            if args.human_grounding_evaluation
            else None
        ),
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week3_completion_markdown(audit), encoding="utf-8")

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
