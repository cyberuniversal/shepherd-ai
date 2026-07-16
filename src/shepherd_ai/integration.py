"""Bounded Week 7 integration of interpretation, grounding, planning, scheduling, and safety."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from shepherd_ai.constraint_normalization import normalize_constraints
from shepherd_ai.feedback import FeedbackLog, simulate_mission_status_updates
from shepherd_ai.grounding import MapLocation, ground_intent
from shepherd_ai.grounding_clarification import build_clarification_report
from shepherd_ai.intent import MissionIntent, parse_intent
from shepherd_ai.mission_planning import plan_grounded_mission, validate_mission_plan
from shepherd_ai.safety import SafetyPolicy, validate_schedule_safety
from shepherd_ai.scheduling import extract_tasks_from_plan_payloads, load_drones, schedule_tasks


WORKFLOW_NAME = "deterministic_week7_integrated_workflow_v1"


@dataclass(frozen=True)
class IntegratedWorkflowResult:
    """Serializable output from one non-executing Week 7 workflow run."""

    status: str
    workflow: str
    command: str
    intent: dict[str, Any]
    grounded_intent: dict[str, Any]
    clarification_report: dict[str, Any]
    mission_plan: dict[str, Any] | None
    mission_plan_validation: dict[str, Any] | None
    schedule: dict[str, Any] | None
    safety_report: dict[str, Any] | None
    simulated_status_updates: tuple[dict[str, Any], ...]
    feedback: dict[str, Any]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "workflow": self.workflow,
            "command": self.command,
            "intent": self.intent,
            "grounded_intent": self.grounded_intent,
            "clarification_report": self.clarification_report,
            "mission_plan": self.mission_plan,
            "mission_plan_validation": self.mission_plan_validation,
            "schedule": self.schedule,
            "safety_report": self.safety_report,
            "simulated_status_updates": list(self.simulated_status_updates),
            "feedback": self.feedback,
            "limitations": list(self.limitations),
        }


def run_integrated_workflow(
    command: str,
    *,
    locations: Iterable[MapLocation],
    fleet_payload: Mapping[str, Any],
    safety_policy: SafetyPolicy,
    strategy: str = "least_loaded",
    mission_altitude_m: float | None = None,
    current_fleet_payload: Mapping[str, Any] | None = None,
    intent_override: MissionIntent | None = None,
) -> IntegratedWorkflowResult:
    """Run prior bounded modules and stop before any simulated execution."""

    feedback = FeedbackLog()
    feedback.add("input", "command_received", "Mission command received.")
    location_list = tuple(locations)
    location_index = {location.id: location for location in location_list}
    intent = intent_override or parse_intent(command)
    feedback.add(
        "intent",
        "intent_extracted",
        "Structured mission intent produced.",
        details={"parser": intent.parser, "action": intent.action, "count": intent.count},
    )
    grounded = ground_intent(intent, location_list)
    clarification = build_clarification_report(grounded)
    if clarification.blocks_planning:
        feedback.add(
            "grounding",
            "clarification_required",
            "Grounding is ambiguous or unresolved; operator clarification is required.",
            blocks_progress=True,
            details={"requests": len(clarification.requests)},
        )
        return _result(
            "clarification_required",
            command,
            intent.to_dict(),
            grounded.to_dict(),
            clarification.to_dict(),
            feedback,
        )
    feedback.add("grounding", "grounding_ready", "Command references grounded to the map.")

    plan = plan_grounded_mission(grounded)
    validation = validate_mission_plan(plan)
    if plan.status != "planned" or not validation.valid:
        feedback.add(
            "planning",
            "planning_blocked",
            "Mission plan is not valid for scheduling.",
            blocks_progress=True,
            details={"plan_issues": list(plan.issues), "validation_issues": list(validation.issues)},
        )
        return _result(
            "planning_blocked",
            command,
            intent.to_dict(),
            grounded.to_dict(),
            clarification.to_dict(),
            feedback,
            mission_plan=plan.to_dict(),
            mission_plan_validation=validation.to_dict(),
        )
    feedback.add("planning", "plan_ready", "Validated mission plan produced.")

    planning_payload = {"mission_plan": plan.to_dict()}
    tasks = extract_tasks_from_plan_payloads([planning_payload])
    scheduling_drones = load_drones(fleet_payload, location_index)
    schedule = schedule_tasks(tasks, scheduling_drones, strategy=strategy)
    if schedule.unassigned_tasks or not schedule.assignments:
        feedback.add(
            "scheduling",
            "scheduling_incomplete",
            "One or more mission tasks could not be assigned.",
            blocks_progress=True,
            details={"unassigned_tasks": list(schedule.unassigned_tasks)},
        )
    else:
        feedback.add(
            "scheduling",
            "schedule_ready",
            "All schedulable mission tasks were assigned.",
            details={"assignments": len(schedule.assignments), "strategy": strategy},
        )

    current_drones = load_drones(current_fleet_payload or fleet_payload, location_index)
    command_altitude_ceiling_m = _command_altitude_ceiling(intent.constraints)
    safety = validate_schedule_safety(
        schedule,
        current_drones,
        location_index,
        safety_policy,
        mission_altitude_m=mission_altitude_m,
        command_altitude_ceiling_m=command_altitude_ceiling_m,
    )
    if safety.status == "approved":
        workflow_status = "ready_for_simulated_execution"
        simulated_updates = tuple(simulate_mission_status_updates(schedule))
        feedback.add(
            "safety",
            "safety_approved",
            "All configured pre-execution safety checks passed.",
            details=safety.summary,
        )
    elif safety.status == "rejected":
        workflow_status = "safety_rejected"
        simulated_updates = ()
        feedback.add(
            "safety",
            "safety_rejected",
            "At least one configured safety check failed; execution is blocked.",
            blocks_progress=True,
            details=safety.summary,
        )
    else:
        workflow_status = "safety_incomplete"
        simulated_updates = ()
        feedback.add(
            "safety",
            "safety_incomplete",
            "Safety evidence is incomplete; execution is blocked.",
            blocks_progress=True,
            details=safety.summary,
        )
    return _result(
        workflow_status,
        command,
        intent.to_dict(),
        grounded.to_dict(),
        clarification.to_dict(),
        feedback,
        mission_plan=plan.to_dict(),
        mission_plan_validation=validation.to_dict(),
        schedule=schedule.to_dict(),
        safety_report=safety.to_dict(),
        simulated_status_updates=simulated_updates,
    )


def _command_altitude_ceiling(constraints: list[str]) -> float | None:
    ceilings = [
        float(constraint.value)
        for constraint in normalize_constraints(constraints)
        if constraint.kind == "altitude_limit" and isinstance(constraint.value, (int, float))
    ]
    return min(ceilings) if ceilings else None


def _result(
    status: str,
    command: str,
    intent: dict[str, Any],
    grounded_intent: dict[str, Any],
    clarification_report: dict[str, Any],
    feedback: FeedbackLog,
    *,
    mission_plan: dict[str, Any] | None = None,
    mission_plan_validation: dict[str, Any] | None = None,
    schedule: dict[str, Any] | None = None,
    safety_report: dict[str, Any] | None = None,
    simulated_status_updates: tuple[dict[str, Any], ...] = (),
) -> IntegratedWorkflowResult:
    return IntegratedWorkflowResult(
        status=status,
        workflow=WORKFLOW_NAME,
        command=command,
        intent=intent,
        grounded_intent=grounded_intent,
        clarification_report=clarification_report,
        mission_plan=mission_plan,
        mission_plan_validation=mission_plan_validation,
        schedule=schedule,
        safety_report=safety_report,
        simulated_status_updates=simulated_status_updates,
        feedback=feedback.to_dict(),
        limitations=(
            "Week 7 pre-execution simulation workflow; it does not control physical drones.",
            "Mission-specific vision execution and full mission reporting remain Week 8 work.",
            "Safety approval applies only to the configured synthetic policy and available evidence.",
        ),
    )
