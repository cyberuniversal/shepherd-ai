"""Evaluate straight-line restricted-area checks on registered route geometry."""

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

from shepherd_ai.grounding import MapLocation  # noqa: E402
from shepherd_ai.safety import load_safety_policy, validate_schedule_safety  # noqa: E402
from shepherd_ai.scheduling import Assignment, DroneState, ScheduleResult  # noqa: E402


DEFAULT_CASES = ROOT / "datasets" / "safety" / "week7_route_safety_cases_v1.jsonl"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_route_safety_development_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_route_safety_development_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = _read_jsonl(args.cases)
    policy = load_safety_policy(args.policy)
    rows: list[dict[str, Any]] = []
    for case in cases:
        start = case["start"]
        target_payload = case["target"]
        target = MapLocation(
            id="target",
            name="Target",
            category="mission_area",
            latitude=float(target_payload["latitude"]),
            longitude=float(target_payload["longitude"]),
            radius_m=1.0,
        )
        restricted = tuple(_restricted_location(payload) for payload in case["restricted_locations"])
        locations = {location.id: location for location in (target, *restricted)}
        drone = DroneState(
            drone_id="drone_1",
            status="idle",
            current_location_id="synthetic_start",
            current_latitude=float(start["latitude"]),
            current_longitude=float(start["longitude"]),
            available_at_min=0.0,
            battery_percent=100.0,
            speed_m_per_min=300.0,
        )
        schedule = ScheduleResult(
            strategy="registered_route_case",
            assignments=(
                Assignment(
                    task_id="task_1",
                    drone_id="drone_1",
                    strategy="registered_route_case",
                    start_min=0.0,
                    end_min=1.0,
                    duration_min=1.0,
                    travel_distance_m=0.0,
                    target_location_id="target",
                    target_name="Target",
                    action="inspect",
                ),
            ),
            unassigned_tasks=(),
            metrics={},
        )
        report = validate_schedule_safety(
            schedule,
            (drone,),
            locations,
            policy,
            mission_altitude_m=policy.default_mission_altitude_m,
        )
        route_check = next(
            check
            for check in report.assignment_results[0].checks
            if check.category == "restricted_area"
        )
        actual_intersections = sorted(
            item["location_id"] for item in route_check.evidence.get("route_intersections", [])
        )
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_week7_route_safety_case",
                "case_input": case,
                "expected_decision": str(case["expected_decision"]),
                "actual_decision": report.status,
                "decision_matches_expected": report.status == case["expected_decision"],
                "expected_intersections": sorted(case.get("expected_intersections", [])),
                "actual_intersections": actual_intersections,
                "intersections_match_expected": actual_intersections
                == sorted(case.get("expected_intersections", [])),
                "safety_report": report.to_dict(),
                "notes": list(case.get("notes", [])),
            }
        )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "deterministic_week7_straight_line_route_safety_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "data_scope": "synthetic_route_geometry_development_evaluation",
            "route_model": "straight_line_center_to_center",
            "safety_capabilities": ["route_restricted_area_intersection"],
            "input_sha256": {"cases": _sha256(args.cases), "policy": _sha256(args.policy)},
            "research_note": (
                "This is a straight-line geometric baseline over synthetic circles and polygons. "
                "It is not trajectory optimization or continuous geofence enforcement."
            ),
        },
        "summary": {
            "case_count": len(rows),
            "expected_decision_matches": sum(row["decision_matches_expected"] for row in rows),
            "expected_intersection_matches": sum(row["intersections_match_expected"] for row in rows),
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


def _restricted_location(payload: dict[str, Any]) -> MapLocation:
    boundary = tuple(
        (float(point["latitude"]), float(point["longitude"]))
        for point in payload.get("boundary", [])
    )
    return MapLocation(
        id=str(payload["id"]),
        name=str(payload["name"]),
        category="restricted_area",
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        radius_m=float(payload["radius_m"]),
        geometry_type=str(payload["geometry_type"]),
        map_role="restricted_area",
        flyable=False,
        requires_clearance=True,
        boundary=boundary,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("route cases must contain at least one JSON object")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Route Safety Evaluation",
        "",
        "This is a synthetic straight-line geometry evaluation, not trajectory optimization.",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Expected decision matches: `{summary['expected_decision_matches']}`",
        f"- Expected intersection matches: `{summary['expected_intersection_matches']}`",
        "",
        "| Case | Expected | Actual | Intersections |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        intersections = ", ".join(row["actual_intersections"]) or "none"
        lines.append(
            f"| {row['case_id']} | {row['expected_decision']} | {row['actual_decision']} | {intersections} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
