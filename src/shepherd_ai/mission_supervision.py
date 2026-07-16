"""Event-driven mission supervision for the Week 7 software simulation.

The supervisor models lifecycle and intervention decisions over explicit
simulated events. It does not model vehicle dynamics or control drones.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import MapLocation
from shepherd_ai.safety import (
    SafetyCheck,
    SafetyPolicy,
    SafetyReport,
    validate_inter_drone_separation,
    validate_schedule_safety,
)
from shepherd_ai.scheduling import DroneState, ScheduleResult


TERMINAL_MISSION_STATES = {"blocked", "cancelled", "completed"}


@dataclass(frozen=True)
class SupervisionEvent:
    """One observed or operator-triggered state transition."""

    sequence: int
    event_type: str
    mission_status: str
    message: str
    mode: str = "event_driven_simulation"
    safety_status: str | None = None
    intervention: str | None = None
    failed_categories: tuple[str, ...] = ()
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failed_categories"] = list(self.failed_categories)
        payload["details"] = dict(self.details or {})
        return payload


class MissionSupervisor:
    """Deterministic state machine around a scheduled simulated mission."""

    def __init__(
        self,
        schedule: ScheduleResult,
        initial_drones: Iterable[DroneState],
        map_locations: Mapping[str, MapLocation],
        safety_policy: SafetyPolicy,
        *,
        mission_altitude_m: float,
        command_altitude_ceiling_m: float | None = None,
    ) -> None:
        if not schedule.assignments:
            raise ValueError("mission supervision requires at least one scheduled assignment")
        self._schedule = schedule
        self._map_locations = dict(map_locations)
        self._safety_policy = safety_policy
        self._mission_altitude_m = float(mission_altitude_m)
        self._command_altitude_ceiling_m = command_altitude_ceiling_m
        self._current_drones = tuple(initial_drones)
        self._mission_status = "awaiting_confirmation"
        self._tasks: dict[str, dict[str, Any]] = {
            assignment.task_id: {
                "task_id": assignment.task_id,
                "drone_id": assignment.drone_id,
                "target_location_id": assignment.target_location_id,
                "status": "awaiting_confirmation",
            }
            for assignment in schedule.assignments
        }
        self._events: list[SupervisionEvent] = []
        self._last_safety_report: SafetyReport | None = None
        self._last_separation_check: SafetyCheck | None = None
        self._record(
            "mission_created",
            "Mission schedule is awaiting explicit operator confirmation.",
        )

    def confirm_and_start(self, current_drones: Iterable[DroneState]) -> None:
        """Confirm the mission and enter active state only after preflight passes."""

        self._require_status("awaiting_confirmation")
        report = self._recheck_safety(current_drones)
        separation = self._last_separation_check
        if not report.safe_to_execute or separation is None or separation.status != "passed":
            self._mission_status = "blocked"
            self._set_nonterminal_tasks("blocked")
            self._record(
                "preflight_blocked",
                "Operator confirmed the mission, but preflight safety blocked execution.",
                safety_report=report,
                additional_failed_categories=_failed_check_category(separation),
            )
            return
        self._mission_status = "active"
        self._set_nonterminal_tasks("running")
        self._record(
            "operator_confirmed",
            "Operator confirmed the mission and preflight safety passed.",
            safety_report=report,
        )

    def apply_telemetry(self, current_drones: Iterable[DroneState]) -> None:
        """Recheck safety against a new simulated drone-state snapshot."""

        if self._mission_status not in {"active", "paused"}:
            raise ValueError(f"telemetry cannot update mission in state: {self._mission_status}")
        report = self._recheck_safety(current_drones)
        separation = self._last_separation_check
        if report.safe_to_execute and separation is not None and separation.status == "passed":
            self._record(
                "telemetry_accepted",
                "Updated simulated drone state passed the configured safety checks.",
                safety_report=report,
            )
            return

        failed_by_task = _failed_categories_by_task(report)
        all_failed = sorted({category for values in failed_by_task.values() for category in values})
        if separation is not None and separation.status != "passed":
            all_failed.append(separation.category)
        if "battery" in all_failed:
            for task_id, task in self._tasks.items():
                if "battery" in failed_by_task.get(task_id, ()):
                    task["status"] = "return_requested"
                elif task["status"] == "running":
                    task["status"] = "paused"
            self._mission_status = "intervention_required"
            intervention = "return_to_launch_requested"
            message = "A battery check failed; affected drones must return and unfinished work remains pending."
        else:
            self._set_running_tasks("paused")
            self._mission_status = "paused"
            intervention = "hold_and_replan_requested"
            message = "Updated state failed or lacked safety evidence; the mission is held for replanning."
        self._record(
            "telemetry_safety_intervention",
            message,
            safety_report=report,
            intervention=intervention,
            additional_failed_categories=_failed_check_category(separation),
        )

    def pause(self, reason: str) -> None:
        """Pause active work in response to an explicit operator command."""

        self._require_status("active")
        self._set_running_tasks("paused")
        self._mission_status = "paused"
        self._record("operator_paused", "Operator paused the mission.", details={"reason": reason})

    def resume(self, current_drones: Iterable[DroneState]) -> None:
        """Resume paused work only after a fresh safety check."""

        self._require_status("paused")
        report = self._recheck_safety(current_drones)
        separation = self._last_separation_check
        if not report.safe_to_execute or separation is None or separation.status != "passed":
            self._record(
                "resume_blocked",
                "The mission remains paused because the fresh safety check did not pass.",
                safety_report=report,
                intervention="hold_and_replan_requested",
                additional_failed_categories=_failed_check_category(separation),
            )
            return
        for task in self._tasks.values():
            if task["status"] == "paused":
                task["status"] = "running"
        self._mission_status = "active"
        self._record(
            "operator_resumed",
            "Operator resumed the mission after a fresh safety check.",
            safety_report=report,
        )

    def cancel(self, reason: str) -> None:
        """Cancel every unfinished task and preserve the cancellation reason."""

        if self._mission_status in TERMINAL_MISSION_STATES:
            raise ValueError(f"mission is already terminal: {self._mission_status}")
        self._set_nonterminal_tasks("cancelled")
        self._mission_status = "cancelled"
        self._record("operator_cancelled", "Operator cancelled the mission.", details={"reason": reason})

    def complete_task(self, task_id: str) -> None:
        """Record explicit simulated task completion and update mission state."""

        if task_id not in self._tasks:
            raise ValueError(f"unknown supervised task: {task_id}")
        task = self._tasks[task_id]
        if task["status"] != "running":
            raise ValueError(f"task cannot complete from state: {task['status']}")
        task["status"] = "completed"
        if all(item["status"] == "completed" for item in self._tasks.values()):
            self._mission_status = "completed"
        self._record(
            "task_completed",
            "A task completion event was received from the simulation.",
            details={"task_id": task_id, "drone_id": task["drone_id"]},
        )

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable state and complete transition history."""

        return {
            "mode": "event_driven_simulation",
            "mission_status": self._mission_status,
            "tasks": {task_id: dict(task) for task_id, task in self._tasks.items()},
            "events": [event.to_dict() for event in self._events],
            "last_safety_report": (
                self._last_safety_report.to_dict() if self._last_safety_report is not None else None
            ),
            "last_separation_check": (
                self._last_separation_check.to_dict()
                if self._last_separation_check is not None
                else None
            ),
            "limitations": [
                "State transitions consume explicit simulated events; no vehicle dynamics are modeled.",
                "Return, hold, and replanning interventions are requests, not executed trajectories.",
                "Collision avoidance and route-geometry validation are not implemented.",
            ],
        }

    def _recheck_safety(self, current_drones: Iterable[DroneState]) -> SafetyReport:
        self._current_drones = tuple(current_drones)
        report = validate_schedule_safety(
            self._schedule,
            self._current_drones,
            self._map_locations,
            self._safety_policy,
            mission_altitude_m=self._mission_altitude_m,
            command_altitude_ceiling_m=self._command_altitude_ceiling_m,
        )
        self._last_safety_report = report
        assigned_ids = {assignment.drone_id for assignment in self._schedule.assignments}
        self._last_separation_check = validate_inter_drone_separation(
            (drone for drone in self._current_drones if drone.drone_id in assigned_ids),
            self._safety_policy,
        )
        return report

    def _record(
        self,
        event_type: str,
        message: str,
        *,
        safety_report: SafetyReport | None = None,
        intervention: str | None = None,
        details: dict[str, Any] | None = None,
        additional_failed_categories: tuple[str, ...] = (),
    ) -> None:
        failed = tuple(
            sorted(
                set(_all_failed_categories(safety_report) if safety_report is not None else ())
                | set(additional_failed_categories)
            )
        )
        self._events.append(
            SupervisionEvent(
                sequence=len(self._events) + 1,
                event_type=event_type,
                mission_status=self._mission_status,
                message=message,
                safety_status=(
                    "rejected"
                    if additional_failed_categories
                    else safety_report.status if safety_report is not None else None
                ),
                intervention=intervention,
                failed_categories=failed,
                details=details,
            )
        )

    def _set_nonterminal_tasks(self, status: str) -> None:
        for task in self._tasks.values():
            if task["status"] not in {"cancelled", "completed"}:
                task["status"] = status

    def _set_running_tasks(self, status: str) -> None:
        for task in self._tasks.values():
            if task["status"] == "running":
                task["status"] = status

    def _require_status(self, expected: str) -> None:
        if self._mission_status != expected:
            raise ValueError(
                f"mission state must be {expected}, found {self._mission_status}"
            )


def _failed_categories_by_task(report: SafetyReport) -> dict[str, tuple[str, ...]]:
    return {
        assignment.task_id: tuple(
            sorted(check.category for check in assignment.checks if check.status != "passed")
        )
        for assignment in report.assignment_results
    }


def _all_failed_categories(report: SafetyReport) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                check.category
                for assignment in report.assignment_results
                for check in assignment.checks
                if check.status != "passed"
            }
        )
    )


def _failed_check_category(check: SafetyCheck | None) -> tuple[str, ...]:
    if check is None or check.status == "passed":
        return ()
    return (check.category,)
