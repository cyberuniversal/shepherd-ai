"""Evaluate the stateful Week 7 clarification dialogue on registered cases."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.clarification_dialogue import ClarificationSession  # noqa: E402
from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402


DEFAULT_CASES = ROOT / "datasets" / "safety" / "week7_clarification_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_clarification_development_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_clarification_development_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = _read_jsonl(args.cases)
    locations = load_map_locations(args.map)
    rows: list[dict[str, Any]] = []
    for case in cases:
        grounded = ground_intent(parse_intent(str(case["command"])), locations)
        session = ClarificationSession(grounded, locations)
        for event in case.get("events", []):
            _apply_event(session, event)
        result = session.snapshot()
        actual_events = [event["event_type"] for event in result["events"]]
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_week7_stateful_clarification_case",
                "case_input": case,
                "expected_status": str(case["expected_status"]),
                "actual_status": result["status"],
                "status_matches_expected": result["status"] == case["expected_status"],
                "expected_event_types": list(case["expected_event_types"]),
                "actual_event_types": actual_events,
                "event_types_match_expected": actual_events == case["expected_event_types"],
                "dialogue_result": result,
                "notes": list(case.get("notes", [])),
            }
        )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "deterministic_week7_stateful_clarification_evaluator_v1",
            "clarification_dialogue_mode": "stateful_multi_turn",
            "python_version": platform.python_version(),
            "random_seed": None,
            "data_scope": "synthetic_stateful_dialogue_development_evaluation",
            "input_sha256": {"cases": _sha256(args.cases), "map": _sha256(args.map)},
            "research_note": (
                "This evaluates deterministic dialogue state and choice validation. "
                "It is not a human-factors or usability study."
            ),
        },
        "summary": {
            "case_count": len(rows),
            "expected_status_matches": sum(row["status_matches_expected"] for row in rows),
            "expected_event_type_matches": sum(row["event_types_match_expected"] for row in rows),
        },
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_output}")


def _apply_event(session: ClarificationSession, event: dict[str, Any]) -> None:
    event_type = str(event.get("type"))
    if event_type == "choose":
        choices = event.get("choices", {})
        if not isinstance(choices, dict):
            raise ValueError("clarification choices must be an object")
        session.submit_choices({str(key): str(value) for key, value in choices.items()})
    elif event_type == "confirm":
        session.confirm()
    elif event_type == "cancel":
        session.cancel(str(event.get("reason", "operator_cancelled")))
    elif event_type == "timeout":
        session.timeout()
    else:
        raise ValueError(f"unsupported clarification event type: {event_type}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("clarification cases must contain at least one JSON object")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Clarification Dialogue Evaluation",
        "",
        "This is a synthetic dialogue-state evaluation, not a human-factors study.",
        "",
        "## Summary",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Expected status matches: `{summary['expected_status_matches']}`",
        f"- Expected event-sequence matches: `{summary['expected_event_type_matches']}`",
        "",
        "| Case | Expected | Actual | Events match |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['expected_status']} | {row['actual_status']} | "
            f"{row['event_types_match_expected']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
