"""Week 8 preparation pipeline for compound simulated missions."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import GroundedIntent, MapLocation, ground_intent
from shepherd_ai.mission_decomposition import decompose_mission_command
from shepherd_ai.mission_planning import plan_grounded_mission, validate_mission_plan
from shepherd_ai.safety import SafetyPolicy, validate_schedule_safety
from shepherd_ai.scheduling import extract_tasks_from_plan_payloads, load_drones, schedule_tasks


PIPELINE_NAME = "week8_compound_mission_preparation_v1"


def prepare_week8_mission(
    command: str,
    *,
    locations: Iterable[MapLocation],
    fleet_payload: Mapping[str, Any],
    safety_policy: SafetyPolicy,
    strategy: str = "least_loaded",
) -> dict[str, Any]:
    """Prepare all command clauses through shared scheduling and safety.

    This function intentionally stops before simulated mission execution and
    vision. It exposes missing Week 8 evidence instead of binding unrelated
    development artifacts.
    """

    started = perf_counter()
    location_list = tuple(locations)
    location_index = {location.id: location for location in location_list}
    decomposition = decompose_mission_command(command)
    if decomposition.status == "clarification_required" or decomposition.issues:
        return _result(
            "clarification_required",
            decomposition.to_dict(),
            issues=list(decomposition.issues),
            started=started,
        )

    clause_results: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    issues: list[str] = []
    blocking_clauses: list[str] = []
    for clause in decomposition.clauses:
        grounded = ground_intent(clause.intent, location_list)
        reference_ids = {
            reference.location.id
            for reference in grounded.references
            if reference.status == "grounded" and reference.location is not None
        }
        clause_issues: list[str] = list(grounded.issues)
        if len(reference_ids) > 1:
            clause_issues.append(f"{clause.clause_id}_distinct_location_and_target")
        clause_result: dict[str, Any] = {
            "clause_id": clause.clause_id,
            "text": clause.text,
            "intent": clause.intent.to_dict(),
            "grounded_intent": grounded.to_dict(),
            "issues": clause_issues,
        }
        if clause_issues or not grounded.ready_for_planning:
            blocking_clauses.append(clause.clause_id)
            issues.extend(clause_issues or [f"{clause.clause_id}_grounding_not_ready"])
            clause_results.append(clause_result)
            continue

        plan = plan_grounded_mission(grounded)
        validation = validate_mission_plan(plan)
        clause_result["mission_plan"] = plan.to_dict()
        clause_result["mission_plan_validation"] = validation.to_dict()
        if plan.status != "planned" or not validation.valid:
            blocking_clauses.append(clause.clause_id)
            plan_issue = f"{clause.clause_id}_planning_not_ready"
            clause_result["issues"].append(plan_issue)
            issues.append(plan_issue)
        else:
            plans.append({"mission_plan": plan.to_dict()})
        clause_results.append(clause_result)

    if blocking_clauses:
        return _result(
            "clarification_required",
            decomposition.to_dict(),
            clause_results=clause_results,
            plans=plans,
            issues=issues,
            blocking_clauses=blocking_clauses,
            started=started,
        )

    drones = load_drones(fleet_payload, location_index)
    tasks = extract_tasks_from_plan_payloads(plans)
    schedule = schedule_tasks(tasks, drones, strategy=strategy)
    safety = validate_schedule_safety(
        schedule,
        drones,
        location_index,
        safety_policy,
        mission_altitude_m=safety_policy.default_mission_altitude_m,
    )
    if schedule.unassigned_tasks:
        status = "scheduling_incomplete"
        issues.append("schedule_contains_unassigned_tasks")
    elif not safety.safe_to_execute:
        status = "safety_blocked"
        issues.extend(safety.issues or ("safety_not_approved",))
    else:
        status = "awaiting_required_week8_evidence"

    return _result(
        status,
        decomposition.to_dict(),
        clause_results=clause_results,
        plans=plans,
        schedule=schedule.to_dict(),
        safety_report=safety.to_dict(),
        issues=issues,
        missing_evidence=[
            "exact_scenario_asr_prediction",
            "mission_image_manifest",
            "mission_vision_results",
        ],
        started=started,
    )


def _result(
    status: str,
    decomposition: dict[str, Any],
    *,
    clause_results: list[dict[str, Any]] | None = None,
    plans: list[dict[str, Any]] | None = None,
    schedule: dict[str, Any] | None = None,
    safety_report: dict[str, Any] | None = None,
    issues: list[str] | None = None,
    blocking_clauses: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    started: float,
) -> dict[str, Any]:
    return {
        "status": status,
        "pipeline": PIPELINE_NAME,
        "decomposition": decomposition,
        "clause_results": clause_results or [],
        "plans": plans or [],
        "schedule": schedule,
        "safety_report": safety_report,
        "blocking_clauses": blocking_clauses or [],
        "issues": issues or [],
        "missing_evidence": missing_evidence or [],
        "preparation_elapsed_seconds": perf_counter() - started,
        "limitations": [
            "Software-simulation preparation only; no physical drones are controlled.",
            "No mission is successful until ASR, mission imagery, vision, supervision, and reporting evidence are stored.",
            "Distinct grounded references are blocked because the custom map has no relation model that can reconcile them.",
        ],
    }
