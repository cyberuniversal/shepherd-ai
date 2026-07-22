"""Audit stored Week 8 evidence without rerunning models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_completion import (  # noqa: E402
    build_week8_completion_audit,
    render_week8_completion_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulation",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_roadmap_scenario_simulation.json",
    )
    parser.add_argument(
        "--asr-evidence",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_exact_scenario_asr.json",
    )
    parser.add_argument(
        "--intent-evaluation",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_exact_scenario_intent_evaluation.json",
    )
    parser.add_argument(
        "--vision-evaluation",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_mission_vision_evaluation.json",
    )
    parser.add_argument(
        "--evaluation-summary",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_end_to_end_evaluation.json",
    )
    parser.add_argument(
        "--telemetry",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_roadmap_scenario_telemetry.jsonl",
    )
    parser.add_argument(
        "--animated-map",
        type=Path,
        default=ROOT / "outputs/visualizations/week8_roadmap_scenario_simulation.html",
    )
    parser.add_argument("--mission-report", type=Path, default=ROOT / "reports/week8_mission_report.md")
    parser.add_argument("--demonstration-log", type=Path, default=ROOT / "reports/week8_demonstration.log")
    parser.add_argument(
        "--demonstration-screenshot",
        type=Path,
        default=ROOT / "reports/week8_demonstration.png",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_completion_gate_audit.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "reports/week8_completion_gate_audit.md",
    )
    args = parser.parse_args()

    audit = build_week8_completion_audit(
        simulation=_read_optional_json(args.simulation),
        asr_evidence=_read_optional_json(args.asr_evidence),
        intent_evaluation=_read_optional_json(args.intent_evaluation),
        vision_evaluation=_read_optional_json(args.vision_evaluation),
        evaluation_summary=_read_optional_json(args.evaluation_summary),
        artifact_status={
            "raw_run": args.simulation.is_file(),
            "telemetry": args.telemetry.is_file(),
            "animated_map": args.animated_map.is_file(),
            "evaluation_summary": args.evaluation_summary.is_file(),
            "mission_report": args.mission_report.is_file(),
            "demonstration_log": args.demonstration_log.is_file(),
            "demonstration_screenshot": args.demonstration_screenshot.is_file(),
        },
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_week8_completion_markdown(audit), encoding="utf-8")
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


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


if __name__ == "__main__":
    main()
