"""Build the Week 2 completion-gate audit from current and fresh benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week2_completion import (  # noqa: E402
    build_week2_completion_audit,
    render_week2_completion_markdown,
)


DEFAULT_STATUS = ROOT / "outputs" / "evaluations" / "week2_status_summary.json"
DEFAULT_RISK = ROOT / "outputs" / "evaluations" / "week2_performance_risk_audit.json"
DEFAULT_HANDOFF = ROOT / "outputs" / "evaluations" / "week2_to_week3_nlp_handoff.json"
DEFAULT_FRESH_MANIFEST_AUDIT = ROOT / "outputs" / "evaluations" / "week2_post_development_manifest_audit.json"
DEFAULT_FRESH_REVIEW = ROOT / "outputs" / "evaluations" / "week2_post_development_intent_review_summary.json"
DEFAULT_FRESH_ASR = ROOT / "outputs" / "evaluations" / "week2_post_development_asr_evaluation.json"
DEFAULT_FRESH_INTENT = ROOT / "outputs" / "evaluations" / "week2_post_development_intent_accuracy.json"
DEFAULT_CRITERIA = ROOT / "docs" / "week2_completion_criteria.json"
DEFAULT_JSON = ROOT / "outputs" / "evaluations" / "week2_completion_gate_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week2_completion_gate_audit.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-summary", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--performance-risk-audit", type=Path, default=DEFAULT_RISK)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--fresh-manifest-audit", type=Path, default=DEFAULT_FRESH_MANIFEST_AUDIT)
    parser.add_argument("--fresh-intent-review-summary", type=Path, default=DEFAULT_FRESH_REVIEW)
    parser.add_argument("--fresh-asr-evaluation", type=Path, default=DEFAULT_FRESH_ASR)
    parser.add_argument("--fresh-intent-evaluation", type=Path, default=DEFAULT_FRESH_INTENT)
    parser.add_argument("--acceptance-criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    audit = build_week2_completion_audit(
        status_summary=_read_json_if_exists(args.status_summary),
        performance_risk_audit=_read_json_if_exists(args.performance_risk_audit),
        handoff=_read_json_if_exists(args.handoff),
        fresh_manifest_audit=_read_json_if_exists(args.fresh_manifest_audit),
        fresh_intent_review_summary=_read_json_if_exists(args.fresh_intent_review_summary),
        fresh_asr_evaluation=_read_json_if_exists(args.fresh_asr_evaluation),
        fresh_intent_evaluation=_read_json_if_exists(args.fresh_intent_evaluation),
        acceptance_criteria=_read_json_if_exists(args.acceptance_criteria),
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week2_completion_markdown(audit), encoding="utf-8")

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


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
