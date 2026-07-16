"""Deterministic pre-execution safety validation for Week 7 simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import MapLocation
from shepherd_ai.scheduling import Assignment, DroneState, ScheduleResult


SAFETY_VALIDATOR_NAME = "deterministic_week7_safety_v1"
ROADMAP_CHECK_CATEGORIES = ("availability", "battery", "altitude", "restricted_area")


@dataclass(frozen=True)
class SafetyPolicy:
    """Versioned thresholds and allowlists for a simulated safety gate."""

    policy_id: str
    data_type: str
    source: str
    minimum_battery_percent: float
    maximum_altitude_m: float
    default_mission_altitude_m: float
    allowed_drone_statuses: tuple[str, ...]
    blocked_map_roles: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_drone_statuses"] = list(self.allowed_drone_statuses)
        payload["blocked_map_roles"] = list(self.blocked_map_roles)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class SafetyCheck:
    """One evidence-bearing pass, failure, or unavailable check."""

    category: str
    status: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssignmentSafetyResult:
    """Safety decision for one scheduled drone-task assignment."""

    task_id: str
    drone_id: str
    decision: str
    checks: tuple[SafetyCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "drone_id": self.drone_id,
            "decision": self.decision,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class SafetyReport:
    """Aggregate pre-execution decision for a simulated schedule."""

    status: str
    safe_to_execute: bool
    validator: str
    policy: dict[str, Any]
    mission_altitude_m: float
    altitude_source: str
    command_altitude_ceiling_m: float | None
    assignment_results: tuple[AssignmentSafetyResult, ...]
    summary: dict[str, int]
    issues: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "safe_to_execute": self.safe_to_execute,
            "validator": self.validator,
            "policy": self.policy,
            "mission_altitude_m": self.mission_altitude_m,
            "altitude_source": self.altitude_source,
            "command_altitude_ceiling_m": self.command_altitude_ceiling_m,
            "assignment_results": [result.to_dict() for result in self.assignment_results],
            "summary": self.summary,
            "issues": list(self.issues),
            "limitations": list(self.limitations),
        }


def load_safety_policy(path: str | Path) -> SafetyPolicy:
    """Load a versioned simulation policy from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("safety policy must contain a JSON object")
    required = {
        "policy_id",
        "data_type",
        "source",
        "minimum_battery_percent",
        "maximum_altitude_m",
        "default_mission_altitude_m",
        "allowed_drone_statuses",
        "blocked_map_roles",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"safety policy is missing required fields: {', '.join(missing)}")
    minimum_battery = float(payload["minimum_battery_percent"])
    maximum_altitude = float(payload["maximum_altitude_m"])
    default_altitude = float(payload["default_mission_altitude_m"])
    if not 0.0 <= minimum_battery <= 100.0:
        raise ValueError("minimum_battery_percent must be between 0 and 100")
    if maximum_altitude <= 0.0:
        raise ValueError("maximum_altitude_m must be positive")
    if not 0.0 < default_altitude <= maximum_altitude:
        raise ValueError("default_mission_altitude_m must be positive and within the maximum")
    statuses = _nonempty_text_tuple(payload["allowed_drone_statuses"], "allowed_drone_statuses")
    blocked_roles = _nonempty_text_tuple(payload["blocked_map_roles"], "blocked_map_roles")
    return SafetyPolicy(
        policy_id=str(payload["policy_id"]),
        data_type=str(payload["data_type"]),
        source=str(payload["source"]),
        minimum_battery_percent=minimum_battery,
        maximum_altitude_m=maximum_altitude,
        default_mission_altitude_m=default_altitude,
        allowed_drone_statuses=statuses,
        blocked_map_roles=blocked_roles,
        notes=tuple(str(note) for note in payload.get("notes", [])),
    )


def validate_schedule_safety(
    schedule: ScheduleResult,
    drones: Iterable[DroneState],
    map_locations: Mapping[str, MapLocation],
    policy: SafetyPolicy,
    *,
    mission_altitude_m: float | None = None,
    command_altitude_ceiling_m: float | None = None,
) -> SafetyReport:
    """Apply the four roadmap safety checks to every current assignment."""

    altitude = policy.default_mission_altitude_m if mission_altitude_m is None else float(mission_altitude_m)
    altitude_source = "policy_default" if mission_altitude_m is None else "operator_or_workflow_input"
    drone_index = {drone.drone_id: drone for drone in drones}
    results = tuple(
        _validate_assignment(
            assignment,
            drone_index,
            map_locations,
            policy,
            altitude,
            command_altitude_ceiling_m,
        )
        for assignment in schedule.assignments
    )
    checks = [check for result in results for check in result.checks]
    passed = sum(check.status == "passed" for check in checks)
    failed = sum(check.status == "failed" for check in checks)
    not_evaluated = sum(check.status == "not_evaluated" for check in checks)
    issues: list[str] = []
    if schedule.unassigned_tasks:
        issues.append("schedule_contains_unassigned_tasks")
    if not schedule.assignments:
        issues.append("schedule_contains_no_assignments")
    if not_evaluated or issues:
        status = "incomplete"
    elif failed:
        status = "rejected"
    else:
        status = "approved"
    return SafetyReport(
        status=status,
        safe_to_execute=status == "approved",
        validator=SAFETY_VALIDATOR_NAME,
        policy=policy.to_dict(),
        mission_altitude_m=altitude,
        altitude_source=altitude_source,
        command_altitude_ceiling_m=command_altitude_ceiling_m,
        assignment_results=results,
        summary={
            "assignments": len(results),
            "roadmap_checks_per_assignment": len(ROADMAP_CHECK_CATEGORIES),
            "passed_checks": passed,
            "failed_checks": failed,
            "not_evaluated_checks": not_evaluated,
        },
        issues=tuple(issues),
        limitations=(
            "Pre-execution simulation gate only; this is not a physical-flight safety guarantee.",
            "Route intersection, collision avoidance, weather, communications, and flight dynamics are not evaluated.",
        ),
    )


def _validate_assignment(
    assignment: Assignment,
    drones: Mapping[str, DroneState],
    locations: Mapping[str, MapLocation],
    policy: SafetyPolicy,
    altitude_m: float,
    command_altitude_ceiling_m: float | None,
) -> AssignmentSafetyResult:
    drone = drones.get(assignment.drone_id)
    location = locations.get(assignment.target_location_id)
    checks = (
        _availability_check(assignment, drone, policy),
        _battery_check(assignment, drone, policy),
        _altitude_check(altitude_m, policy, command_altitude_ceiling_m),
        _restricted_area_check(assignment, location, policy),
    )
    if any(check.status == "not_evaluated" for check in checks):
        decision = "incomplete"
    elif any(check.status == "failed" for check in checks):
        decision = "rejected"
    else:
        decision = "approved"
    return AssignmentSafetyResult(
        task_id=assignment.task_id,
        drone_id=assignment.drone_id,
        decision=decision,
        checks=checks,
    )


def _availability_check(
    assignment: Assignment,
    drone: DroneState | None,
    policy: SafetyPolicy,
) -> SafetyCheck:
    if drone is None:
        return SafetyCheck(
            category="availability",
            status="not_evaluated",
            reason="assigned_drone_missing_from_current_state",
            evidence={"drone_id": assignment.drone_id},
        )
    allowed = drone.status in policy.allowed_drone_statuses
    return SafetyCheck(
        category="availability",
        status="passed" if allowed else "failed",
        reason="drone_status_allowed" if allowed else "drone_status_not_allowed",
        evidence={
            "drone_id": drone.drone_id,
            "drone_status": drone.status,
            "allowed_statuses": list(policy.allowed_drone_statuses),
        },
    )


def _battery_check(
    assignment: Assignment,
    drone: DroneState | None,
    policy: SafetyPolicy,
) -> SafetyCheck:
    if drone is None:
        return SafetyCheck(
            category="battery",
            status="not_evaluated",
            reason="assigned_drone_missing_from_current_state",
            evidence={"drone_id": assignment.drone_id},
        )
    passed = drone.battery_percent >= policy.minimum_battery_percent
    return SafetyCheck(
        category="battery",
        status="passed" if passed else "failed",
        reason="battery_at_or_above_threshold" if passed else "battery_below_threshold",
        evidence={
            "drone_id": drone.drone_id,
            "battery_percent": drone.battery_percent,
            "minimum_battery_percent": policy.minimum_battery_percent,
        },
    )


def _altitude_check(
    altitude_m: float,
    policy: SafetyPolicy,
    command_altitude_ceiling_m: float | None,
) -> SafetyCheck:
    within_policy = 0.0 < altitude_m <= policy.maximum_altitude_m
    within_command = (
        command_altitude_ceiling_m is None or altitude_m < command_altitude_ceiling_m
    )
    passed = within_policy and within_command
    if passed:
        reason = "altitude_within_policy_and_command_constraint"
    elif not within_policy:
        reason = "altitude_outside_policy"
    else:
        reason = "altitude_violates_command_ceiling"
    return SafetyCheck(
        category="altitude",
        status="passed" if passed else "failed",
        reason=reason,
        evidence={
            "mission_altitude_m": altitude_m,
            "minimum_altitude_exclusive_m": 0.0,
            "maximum_altitude_m": policy.maximum_altitude_m,
            "command_altitude_ceiling_m": command_altitude_ceiling_m,
        },
    )


def _restricted_area_check(
    assignment: Assignment,
    location: MapLocation | None,
    policy: SafetyPolicy,
) -> SafetyCheck:
    if location is None:
        return SafetyCheck(
            category="restricted_area",
            status="not_evaluated",
            reason="assignment_target_missing_from_map",
            evidence={"target_location_id": assignment.target_location_id},
        )
    blocked = (
        not location.flyable
        or location.requires_clearance
        or location.map_role in policy.blocked_map_roles
    )
    return SafetyCheck(
        category="restricted_area",
        status="failed" if blocked else "passed",
        reason="target_is_restricted_or_requires_clearance" if blocked else "target_is_flyable",
        evidence={
            "target_location_id": location.id,
            "map_role": location.map_role,
            "flyable": location.flyable,
            "requires_clearance": location.requires_clearance,
            "blocked_map_roles": list(policy.blocked_map_roles),
        },
    )


def _nonempty_text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    result = tuple(str(item).strip() for item in value)
    if any(not item for item in result):
        raise ValueError(f"{field_name} entries must be non-empty")
    return result
