"""Evaluate event-driven Week 7 mission supervision on registered scenarios."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission  # noqa: E402
from shepherd_ai.mission_supervision import MissionSupervisor  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.scheduling import (  # noqa: E402
    DroneState,
    extract_tasks_from_plan_payloads,
    load_drones,
    schedule_tasks,
)


DEFAULT_CASES = ROOT / "datasets" / "safety" / "week7_supervision_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_supervision_development_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_supervision_development_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = _read_jsonl(args.cases)
    locations = load_map_locations(args.map)
    location_index = {location.id: location for location in locations}
    fleet = json.loads(args.fleet.read_text(encoding="utf-8"))
    policy = load_safety_policy(args.policy)
    rows: list[dict[str, Any]] = []
    for case in cases:
        drones = load_drones(fleet, location_index)
        grounded = ground_intent(parse_intent(str(case["command"])), locations)
        plan = plan_grounded_mission(grounded)
        tasks = extract_tasks_from_plan_payloads([{"mission_plan": plan.to_dict()}])
        schedule = schedule_tasks(tasks, drones, strategy="least_loaded")
        supervisor = MissionSupervisor(
            schedule,
            drones,
            location_index,
            policy,
            mission_altitude_m=float(case.get("mission_altitude_m", policy.default_mission_altitude_m)),
        )
        current_drones = drones
        for event in case.get("events", []):
            current_drones = _apply_event(supervisor, current_drones, event)
        result = supervisor.snapshot()
        actual_event_types = [event["event_type"] for event in result["events"]]
        actual_interventions = [
            event["intervention"] for event in result["events"] if event.get("intervention")
        ]
        expected_intervention = case.get("expected_intervention")
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_week7_supervision_evaluation_case",
                "case_input": case,
                "expected_final_status": str(case["expected_final_status"]),
                "actual_final_status": result["mission_status"],
                "final_status_matches_expected": result["mission_status"] == case["expected_final_status"],
                "expected_event_types": list(case["expected_event_types"]),
                "actual_event_types": actual_event_types,
                "event_types_match_expected": actual_event_types == case["expected_event_types"],
                "expected_intervention": expected_intervention,
                "actual_interventions": actual_interventions,
                "intervention_matches_expected": (
                    expected_intervention is None or expected_intervention in actual_interventions
                ),
                "supervision_result": result,
                "notes": list(case.get("notes", [])),
            }
        )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "deterministic_week7_event_supervision_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "data_scope": "synthetic_event_driven_development_evaluation",
            "safety_capabilities": [
                "runtime_battery",
                "runtime_availability",
                "inter_drone_separation"
            ],
            "input_sha256": {
                "cases": _sha256(args.cases),
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
            },
            "research_note": (
                "This evaluates deterministic simulated state transitions and intervention requests. "
                "It is not vehicle-dynamics, collision-avoidance, or physical-flight evidence."
            ),
        },
        "summary": {
            "case_count": len(rows),
            "expected_final_status_matches": sum(row["final_status_matches_expected"] for row in rows),
            "expected_event_type_matches": sum(row["event_types_match_expected"] for row in rows),
            "expected_intervention_matches": sum(row["intervention_matches_expected"] for row in rows),
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


def _apply_event(
    supervisor: MissionSupervisor,
    drones: tuple[DroneState, ...],
    event: dict[str, Any],
) -> tuple[DroneState, ...]:
    event_type = str(event.get("type"))
    if event_type == "confirm":
        supervisor.confirm_and_start(drones)
    elif event_type == "complete_all":
        for task_id, task in supervisor.snapshot()["tasks"].items():
            if task["status"] == "running":
                supervisor.complete_task(task_id)
    elif event_type == "telemetry_assigned":
        assigned = {task["drone_id"] for task in supervisor.snapshot()["tasks"].values()}
        updates = event.get("updates", {})
        if not isinstance(updates, dict):
            raise ValueError("telemetry_assigned updates must be an object")
        drones = tuple(
            replace(drone, **updates) if drone.drone_id in assigned else drone for drone in drones
        )
        supervisor.apply_telemetry(drones)
    elif event_type == "telemetry_by_drone":
        updates_by_drone = event.get("updates", {})
        if not isinstance(updates_by_drone, dict):
            raise ValueError("telemetry_by_drone updates must be an object")
        drones = tuple(
            replace(drone, **updates_by_drone[drone.drone_id])
            if drone.drone_id in updates_by_drone
            else drone
            for drone in drones
        )
        supervisor.apply_telemetry(drones)
    elif event_type == "pause":
        supervisor.pause(str(event.get("reason", "operator_pause")))
    elif event_type == "resume":
        supervisor.resume(drones)
    elif event_type == "cancel":
        supervisor.cancel(str(event.get("reason", "operator_cancel")))
    else:
        raise ValueError(f"unsupported supervision event type: {event_type}")
    return drones


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("supervision cases must contain at least one JSON object")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Mission Supervision Evaluation",
        "",
        "This is a synthetic event-driven lifecycle evaluation, not physical-flight safety evidence.",
        "",
        "## Summary",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Expected final-status matches: `{summary['expected_final_status_matches']}`",
        f"- Expected event-sequence matches: `{summary['expected_event_type_matches']}`",
        f"- Expected intervention matches: `{summary['expected_intervention_matches']}`",
        "",
        "## Cases",
        "",
        "| Case | Expected | Actual | Events match | Interventions |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        interventions = ", ".join(row["actual_interventions"]) or "none"
        lines.append(
            f"| {row['case_id']} | {row['expected_final_status']} | {row['actual_final_status']} | "
            f"{row['event_types_match_expected']} | {interventions} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Events and telemetry snapshots are synthetic registered inputs.",
            "- Intervention requests do not execute return or hold trajectories.",
            "- Route geometry, collision avoidance, communications, and dynamics remain unevaluated.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
