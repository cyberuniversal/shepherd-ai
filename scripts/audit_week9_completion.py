"""Audit the Week 9 draft, bibliography, figures, tables, and evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week9_completion import (  # noqa: E402
    build_week9_completion_audit,
    render_week9_completion_markdown,
)


ARTIFACTS = {
    "architecture_figure": "reports/figures/week9_system_architecture.mmd",
    "evaluation_workflow": "reports/figures/week9_evaluation_workflow.mmd",
    "runtime_figure": "reports/figures/week9_stage_runtime.png",
    "metrics_table": "outputs/tables/week9_end_to_end_metrics.csv",
    "runtime_table": "outputs/tables/week9_runtime_stages.csv",
    "traceability_report": "reports/week9_evidence_traceability.md",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = json.loads(
        (root / "outputs/evaluations/week9_paper_evidence.json").read_text(encoding="utf-8")
    )
    audit = build_week9_completion_audit(
        paper_text=(root / "reports/shepherd_ai_paper_draft.md").read_text(encoding="utf-8"),
        bibliography_text=(root / "reports/week9_bibliography.md").read_text(encoding="utf-8"),
        notebook_text=(root / "notebooks/Notebook9_Evaluation.ipynb").read_text(encoding="utf-8"),
        evidence=evidence,
        artifact_status={name: (root / path).is_file() for name, path in ARTIFACTS.items()},
    )
    json_output = root / "outputs/evaluations/week9_completion_gate_audit.json"
    markdown_output = root / "reports/week9_completion_gate_audit.md"
    json_output.write_text(
        json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_output.write_text(render_week9_completion_markdown(audit), encoding="utf-8")
    print(
        json.dumps(
            {
                "completion_allowed": audit.completion_allowed,
                "decision": audit.decision,
                "blockers": list(audit.blockers),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
