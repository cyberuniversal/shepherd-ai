"""Evaluate decision sensitivity to the synthetic Week 7 policy thresholds."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from math import cos, degrees
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import MapLocation  # noqa: E402
from shepherd_ai.safety import (  # noqa: E402
    SafetyPolicy,
    load_safety_policy,
    validate_inter_drone_separation,
    validate_schedule_safety,
)
from shepherd_ai.scheduling import Assignment, DroneState, ScheduleResult  # noqa: E402


DEFAULT_CONFIG = ROOT / "datasets" / "safety" / "week7_policy_sensitivity_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_policy_sensitivity_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_policy_sensitivity_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    config = _read_json(args.config)
    base_policy = load_safety_policy(args.policy)
    evaluators = {
        "minimum_battery_percent": _battery_decision,
        "maximum_altitude_m": _altitude_decision,
        "route_clearance_margin_m": _route_decision,
        "minimum_inter_drone_separation_m": _separation_decision,
    }
    rows: list[dict[str, Any]] = []
    for name, evaluator in evaluators.items():
        dimension = config["dimensions"][name]
        decisions = [evaluator(base_policy, float(value), dimension) for value in dimension["values"]]
        expected = list(dimension["expected_decisions"])
        rows.append(
            {
                "dimension": name,
                "values": list(dimension["values"]),
                "fixed_observation": {
                    key: value for key, value in dimension.items() if key not in {"values", "expected_decisions"}
                },
                "expected_decisions": expected,
                "actual_decisions": decisions,
                "expected_sequence_matches": decisions == expected,
                "monotonicity_passed": _monotonic(name, decisions),
            }
        )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "deterministic_week7_policy_sensitivity_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "data_scope": "synthetic_policy_sensitivity",
            "dimensions": sorted(evaluators),
            "input_sha256": {"config": _sha256(args.config), "policy": _sha256(args.policy)},
            "research_note": (
                "This study tests how synthetic decisions change with thresholds. It does not "
                "identify legal limits, hardware specifications, or a physically safe policy."
            ),
        },
        "summary": {
            "dimension_count": len(rows),
            "expected_sequence_matches": sum(row["expected_sequence_matches"] for row in rows),
            "monotonicity_checks_passed": sum(row["monotonicity_passed"] for row in rows),
        },
        "dimensions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_output}")


def _battery_decision(policy: SafetyPolicy, value: float, dimension: dict[str, Any]) -> str:
    report = _single_assignment_report(
        replace(policy, minimum_battery_percent=value),
        battery_percent=float(dimension["fixed_observation"]),
        mission_altitude_m=30.0,
    )
    return report.status


def _altitude_decision(policy: SafetyPolicy, value: float, dimension: dict[str, Any]) -> str:
    adjusted = replace(
        policy,
        maximum_altitude_m=value,
        default_mission_altitude_m=min(policy.default_mission_altitude_m, value),
    )
    report = _single_assignment_report(
        adjusted,
        battery_percent=100.0,
        mission_altitude_m=float(dimension["fixed_observation"]),
    )
    return report.status


def _route_decision(policy: SafetyPolicy, value: float, dimension: dict[str, Any]) -> str:
    origin_lat = 24.0
    origin_lon = 46.0
    offset_lat = degrees(float(dimension["fixed_obstacle_offset_m"]) / 6_371_000.0)
    target = MapLocation("target", "Target", "field", origin_lat, 46.002, 1.0)
    obstacle = MapLocation(
        "obstacle",
        "Obstacle",
        "restricted_area",
        origin_lat + offset_lat,
        46.001,
        float(dimension["obstacle_radius_m"]),
        map_role="restricted_area",
        flyable=False,
        requires_clearance=True,
    )
    report = _single_assignment_report(
        replace(policy, route_clearance_margin_m=value),
        battery_percent=100.0,
        mission_altitude_m=30.0,
        start=(origin_lat, origin_lon),
        target=target,
        extra_locations=(obstacle,),
    )
    return report.status


def _separation_decision(policy: SafetyPolicy, value: float, dimension: dict[str, Any]) -> str:
    origin_lat = 24.0
    origin_lon = 46.0
    distance_m = float(dimension["fixed_pair_distance_m"])
    longitude_delta = degrees(distance_m / (6_371_000.0 * cos(origin_lat * 3.141592653589793 / 180.0)))
    first = _drone("drone_1", origin_lat, origin_lon, 100.0)
    second = _drone("drone_2", origin_lat, origin_lon + longitude_delta, 100.0)
    check = validate_inter_drone_separation(
        (first, second),
        replace(policy, minimum_inter_drone_separation_m=value),
    )
    return "approved" if check.status == "passed" else "rejected"


def _single_assignment_report(
    policy: SafetyPolicy,
    *,
    battery_percent: float,
    mission_altitude_m: float,
    start: tuple[float, float] = (24.0, 46.0),
    target: MapLocation | None = None,
    extra_locations: tuple[MapLocation, ...] = (),
):
    target = target or MapLocation("target", "Target", "field", 24.001, 46.0, 1.0)
    schedule = ScheduleResult(
        strategy="sensitivity",
        assignments=(Assignment("task", "drone", "sensitivity", 0.0, 1.0, 1.0, 0.0, target.id, target.name, "inspect"),),
        unassigned_tasks=(),
        metrics={},
    )
    locations = {location.id: location for location in (target, *extra_locations)}
    return validate_schedule_safety(
        schedule,
        (_drone("drone", start[0], start[1], battery_percent),),
        locations,
        policy,
        mission_altitude_m=mission_altitude_m,
    )


def _drone(drone_id: str, latitude: float, longitude: float, battery: float) -> DroneState:
    return DroneState(drone_id, "idle", "synthetic", latitude, longitude, 0.0, battery, 300.0)


def _monotonic(name: str, decisions: list[str]) -> bool:
    encoded = [1 if decision == "approved" else 0 for decision in decisions]
    if name in {"minimum_battery_percent", "route_clearance_margin_m", "minimum_inter_drone_separation_m"}:
        return encoded == sorted(encoded, reverse=True)
    return encoded == sorted(encoded)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Policy Sensitivity Evaluation",
        "",
        "This is a synthetic decision-sensitivity study, not physical safety calibration.",
        "",
        f"- Dimensions: `{summary['dimension_count']}`",
        f"- Expected sequence matches: `{summary['expected_sequence_matches']}`",
        f"- Monotonicity checks passed: `{summary['monotonicity_checks_passed']}`",
        "",
        "| Dimension | Values | Decisions | Monotonic |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["dimensions"]:
        lines.append(
            f"| {row['dimension']} | {row['values']} | {row['actual_decisions']} | {row['monotonicity_passed']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
