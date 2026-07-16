"""Evaluate the Week 7 integrated workflow on registered synthetic cases."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.integration import run_integrated_workflow  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402


DEFAULT_CASES = ROOT / "datasets" / "safety" / "week7_safety_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_safety_development_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_safety_development_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--strategy", default="least_loaded")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = _read_jsonl(args.cases)
    locations = load_map_locations(args.map)
    base_fleet = _read_json(args.fleet)
    policy = load_safety_policy(args.policy)
    rows: list[dict[str, Any]] = []
    for case in cases:
        scheduling_fleet = _set_all_drones(base_fleet, case.get("scheduling_fleet_set_all"))
        current_fleet = _set_all_drones(scheduling_fleet, case.get("current_fleet_set_all"))
        result = run_integrated_workflow(
            str(case["command"]),
            locations=locations,
            fleet_payload=scheduling_fleet,
            current_fleet_payload=current_fleet,
            safety_policy=policy,
            strategy=args.strategy,
            mission_altitude_m=case.get("mission_altitude_m"),
        )
        failed_categories = _failed_categories(result.to_dict())
        expected_failed = sorted(str(value) for value in case.get("expected_failed_categories", []))
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_week7_safety_evaluation_case",
                "case_input": case,
                "command": str(case["command"]),
                "expected_workflow_status": str(case["expected_workflow_status"]),
                "actual_workflow_status": result.status,
                "status_matches_expected": result.status == case["expected_workflow_status"],
                "expected_failed_categories": expected_failed,
                "actual_failed_categories": failed_categories,
                "failed_categories_match_expected": failed_categories == expected_failed,
                "workflow_result": result.to_dict(),
                "notes": list(case.get("notes", [])),
            }
        )

    status_counts = Counter(row["actual_workflow_status"] for row in rows)
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "cases": str(args.cases),
            "map": str(args.map),
            "fleet": str(args.fleet),
            "policy": str(args.policy),
            "strategy": args.strategy,
            "evaluator": "deterministic_week7_safety_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "input_sha256": {
                "cases": _sha256(args.cases),
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
            },
            "data_scope": "synthetic_development_evaluation",
            "research_note": (
                "Registered synthetic Week 7 safety and feedback evaluation. "
                "This is not physical-flight safety evidence or Week 8 end-to-end mission success."
            ),
        },
        "summary": {
            "case_count": len(rows),
            "expected_status_matches": sum(row["status_matches_expected"] for row in rows),
            "expected_status_accuracy": (
                sum(row["status_matches_expected"] for row in rows) / len(rows) if rows else 0.0
            ),
            "expected_failed_category_matches": sum(
                row["failed_categories_match_expected"] for row in rows
            ),
            "workflow_status_counts": dict(sorted(status_counts.items())),
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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("cases JSONL must contain at least one object")
    return rows


def _set_all_drones(payload: dict[str, Any], updates: Any) -> dict[str, Any]:
    result = deepcopy(payload)
    if updates is None:
        return result
    if not isinstance(updates, dict):
        raise ValueError("fleet set-all updates must be an object")
    for drone in result.get("drones", []):
        drone.update(updates)
    return result


def _failed_categories(payload: dict[str, Any]) -> list[str]:
    report = payload.get("safety_report")
    if not isinstance(report, dict):
        return []
    return sorted(
        {
            str(check["category"])
            for assignment in report.get("assignment_results", [])
            for check in assignment.get("checks", [])
            if check.get("status") == "failed"
        }
    )


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Safety Development Evaluation",
        "",
        "This is a synthetic pre-execution development evaluation, not physical-flight safety evidence or a Week 8 end-to-end result.",
        "",
        "## Summary",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Expected status matches: `{summary['expected_status_matches']}`",
        f"- Expected status accuracy: `{summary['expected_status_accuracy']}`",
        f"- Expected failed-category matches: `{summary['expected_failed_category_matches']}`",
        "",
        "## Cases",
        "",
        "| Case | Expected status | Actual status | Status match | Failed categories |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        failed = ", ".join(row["actual_failed_categories"]) or "none"
        lines.append(
            f"| {row['case_id']} | {row['expected_workflow_status']} | "
            f"{row['actual_workflow_status']} | {row['status_matches_expected']} | {failed} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Thresholds are explicit synthetic development assumptions.",
            "- Routes use a straight-line geometry baseline; active collision avoidance, weather, communications, and dynamics are not evaluated.",
            "- Mission-specific vision execution and full mission reports remain Week 8 work.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
