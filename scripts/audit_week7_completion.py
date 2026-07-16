"""Build the Week 7 completion audit from stored development evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week7_completion import (  # noqa: E402
    build_week7_completion_audit,
    render_week7_completion_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, default=ROOT / "outputs/evaluations/week7_safety_development_v1.json")
    parser.add_argument("--policy", type=Path, default=ROOT / "datasets/safety/week7_safety_policy_v1.json")
    parser.add_argument("--acceptance-criteria", type=Path, default=ROOT / "docs/week7_acceptance_criteria.json")
    parser.add_argument("--research-deferrals", type=Path, default=ROOT / "docs/week7_research_deferrals.json")
    parser.add_argument("--notebook", type=Path, default=ROOT / "notebooks/Notebook7_Safety.ipynb")
    parser.add_argument("--json-output", type=Path, default=ROOT / "outputs/evaluations/week7_completion_gate_audit.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "reports/week7_completion_gate_audit.md")
    args = parser.parse_args()

    audit = build_week7_completion_audit(
        evaluation=_read_json(args.evaluation),
        policy=_read_json(args.policy),
        acceptance_criteria=_read_json(args.acceptance_criteria),
        research_deferrals=_read_json(args.research_deferrals),
        notebook_text=args.notebook.read_text(encoding="utf-8"),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week7_completion_markdown(audit), encoding="utf-8")
    print(json.dumps({"advancement_allowed": audit.advancement_allowed, "decision": audit.decision, "blockers": list(audit.blockers)}, indent=2, sort_keys=True))
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
