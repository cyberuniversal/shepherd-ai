"""Completion-gate audit for Week 7 safety, feedback, and integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompletionGate:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week7CompletionAudit:
    roadmap_gates: tuple[CompletionGate, ...]
    research_gates: tuple[CompletionGate, ...]
    advancement_allowed: bool
    decision: str
    blockers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "roadmap_gates": [gate.to_dict() for gate in self.roadmap_gates],
            "research_gates": [gate.to_dict() for gate in self.research_gates],
            "roadmap_gates_passed": all(gate.passed for gate in self.roadmap_gates),
            "research_gates_passed": all(gate.passed for gate in self.research_gates),
            "advancement_allowed": self.advancement_allowed,
            "decision": self.decision,
            "blockers": list(self.blockers),
        }


def build_week7_completion_audit(
    *,
    evaluation: dict[str, Any],
    supervision_evaluation: dict[str, Any],
    clarification_evaluation: dict[str, Any],
    route_evaluation: dict[str, Any],
    integration_evaluation: dict[str, Any],
    sensitivity_evaluation: dict[str, Any],
    policy: dict[str, Any],
    acceptance_criteria: dict[str, Any],
    research_deferrals: dict[str, Any],
    notebook_text: str,
) -> Week7CompletionAudit:
    """Audit stored Week 7 evidence without rerunning or inventing results."""

    cases = evaluation.get("cases", [])
    expected_count = int(acceptance_criteria.get("registered_development_case_count", 0))
    required_categories = set(acceptance_criteria.get("required_roadmap_checks", []))
    observed_categories = {
        str(check.get("category"))
        for case in cases if isinstance(case, dict)
        for assignment in (case.get("workflow_result", {}).get("safety_report") or {}).get("assignment_results", [])
        for check in assignment.get("checks", [])
    }
    failed_categories = {
        str(category)
        for case in cases if isinstance(case, dict)
        for category in case.get("actual_failed_categories", [])
    }
    statuses = {str(case.get("actual_workflow_status")) for case in cases if isinstance(case, dict)}
    supervision_cases = supervision_evaluation.get("cases", [])
    supervision_summary = supervision_evaluation.get("summary", {})
    expected_supervision_count = int(
        acceptance_criteria.get("registered_supervision_case_count", 0)
    )
    supervision_events = [
        event
        for case in supervision_cases if isinstance(case, dict)
        for event in case.get("supervision_result", {}).get("events", [])
    ]
    supervision_event_types = {
        str(event.get("event_type")) for event in supervision_events if isinstance(event, dict)
    }
    runtime_failed_categories = {
        str(category)
        for event in supervision_events if event.get("event_type") == "telemetry_safety_intervention"
        for category in event.get("failed_categories", [])
    }
    supervision_metadata = supervision_evaluation.get("metadata", {})
    clarification_summary = clarification_evaluation.get("summary", {})
    clarification_metadata = clarification_evaluation.get("metadata", {})
    clarification_cases = clarification_evaluation.get("cases", [])
    expected_clarification_count = int(
        acceptance_criteria.get("registered_clarification_case_count", 0)
    )
    integration_summary = integration_evaluation.get("summary", {})
    integration_metadata = integration_evaluation.get("metadata", {})
    integration_cases = integration_evaluation.get("cases", [])
    expected_integration_count = int(
        acceptance_criteria.get("registered_integration_case_count", 0)
    )
    sensitivity_summary = sensitivity_evaluation.get("summary", {})
    sensitivity_metadata = sensitivity_evaluation.get("metadata", {})
    expected_sensitivity_count = int(
        acceptance_criteria.get("registered_sensitivity_dimension_count", 0)
    )
    integrated_stages = set(integration_metadata.get("integrated_stages", []))
    route_summary = route_evaluation.get("summary", {})
    route_metadata = route_evaluation.get("metadata", {})
    route_cases = route_evaluation.get("cases", [])
    expected_route_count = int(
        acceptance_criteria.get("registered_route_safety_case_count", 0)
    )
    safety_capabilities = set(route_metadata.get("safety_capabilities", [])) | set(
        supervision_metadata.get("safety_capabilities", [])
    )
    intervention_preserves_work = any(
        case.get("actual_final_status") in {"intervention_required", "paused"}
        and any(
            task.get("status") in {"paused", "return_requested"}
            for task in case.get("supervision_result", {}).get("tasks", {}).values()
        )
        for case in supervision_cases
        if isinstance(case, dict)
    )
    roadmap_gates = (
        _gate("registered_case_count", len(cases) == expected_count and expected_count > 0, f"cases={len(cases)}, expected={expected_count}"),
        _gate(
            "all_expected_statuses_match",
            int(evaluation.get("summary", {}).get("expected_status_matches", -1)) == expected_count,
            f"matches={evaluation.get('summary', {}).get('expected_status_matches')}, expected={expected_count}",
        ),
        _gate(
            "all_expected_failed_categories_match",
            int(evaluation.get("summary", {}).get("expected_failed_category_matches", -1)) == expected_count,
            f"matches={evaluation.get('summary', {}).get('expected_failed_category_matches')}, expected={expected_count}",
        ),
        _gate("four_roadmap_checks_present", required_categories == observed_categories, f"observed={sorted(observed_categories)}"),
        _gate("four_failure_categories_exercised", required_categories == failed_categories, f"failed={sorted(failed_categories)}"),
        _gate(
            "clarification_and_safety_outcomes_present",
            {"clarification_required", "ready_for_simulated_execution", "safety_rejected", "safety_incomplete"} <= statuses,
            f"statuses={sorted(statuses)}",
        ),
        _gate(
            "stateful_clarification_dialogue_evaluated",
            clarification_metadata.get("clarification_dialogue_mode") == "stateful_multi_turn"
            and len(clarification_cases) == expected_clarification_count
            and expected_clarification_count > 0
            and clarification_summary.get("expected_status_matches") == expected_clarification_count
            and clarification_summary.get("expected_event_type_matches") == expected_clarification_count,
            f"cases={len(clarification_cases)}, expected={expected_clarification_count}",
        ),
        _gate(
            "event_driven_mission_status_evaluated",
            len(supervision_cases) == expected_supervision_count
            and expected_supervision_count > 0
            and supervision_summary.get("expected_final_status_matches") == expected_supervision_count
            and supervision_summary.get("expected_event_type_matches") == expected_supervision_count
            and all(event.get("mode") == "event_driven_simulation" for event in supervision_events),
            f"cases={len(supervision_cases)}, expected={expected_supervision_count}, events={len(supervision_events)}",
        ),
        _gate(
            "runtime_safety_rechecks_evaluated",
            {"battery", "availability"} <= runtime_failed_categories,
            f"runtime_failed_categories={sorted(runtime_failed_categories)}",
        ),
        _gate(
            "previous_modules_integrated",
            {
                "speech_or_text_input",
                "trained_intent_interface",
                "grounding",
                "planning",
                "scheduling",
                "vision_result_binding",
                "safety",
                "supervision",
            }
            <= integrated_stages
            and len(integration_cases) == expected_integration_count
            and expected_integration_count > 0
            and integration_summary.get("expected_status_matches") == expected_integration_count,
            f"cases={len(integration_cases)}, expected={expected_integration_count}, integrated_stages={sorted(integrated_stages)}",
        ),
        _gate(
            "notebook_runs_workflow_and_evaluation",
            all(
                token in notebook_text
                for token in [
                    "run_week7_workflow.py",
                    "evaluate_week7_safety.py",
                    "evaluate_week7_clarification.py",
                    "evaluate_week7_supervision.py",
                    "evaluate_week7_route_safety.py",
                    "evaluate_week7_integration.py",
                    "evaluate_week7_policy_sensitivity.py",
                    "audit_week7_completion.py",
                ]
            ),
            "Notebook7 must run preflight, supervision, and completion-audit scripts",
        ),
    )
    notes = " ".join(str(note) for note in policy.get("notes", [])).lower()
    deferrals = research_deferrals.get("deferrals", {}) if isinstance(research_deferrals, dict) else {}
    research_gates = (
        _gate(
            "synthetic_threshold_scope_declared",
            policy.get("data_type") == "synthetic_simulation_safety_policy" and "synthetic" in notes and "not legal" in notes,
            "policy thresholds must be labeled synthetic assumptions, not legal limits",
        ),
        _gate(
            "physical_safety_not_claimed",
            _deferral_recorded(deferrals, "physical_safety_not_claimed"),
            "physical safety limitation is recorded",
        ),
        _gate(
            "operator_lifecycle_controls_evaluated",
            {"operator_confirmed", "operator_paused", "operator_resumed", "operator_cancelled"}
            <= supervision_event_types,
            f"event_types={sorted(supervision_event_types)}",
        ),
        _gate(
            "unfinished_work_preserved_after_intervention",
            intervention_preserves_work,
            "failed or held work must remain inspectable for return or replanning",
        ),
        _gate(
            "route_aware_restricted_area_enforcement_evaluated",
            "route_restricted_area_intersection" in safety_capabilities
            and len(route_cases) == expected_route_count
            and expected_route_count > 0
            and route_summary.get("expected_decision_matches") == expected_route_count
            and route_summary.get("expected_intersection_matches") == expected_route_count,
            f"cases={len(route_cases)}, expected={expected_route_count}, safety_capabilities={sorted(safety_capabilities)}",
        ),
        _gate(
            "inter_drone_separation_or_collision_handling_evaluated",
            "inter_drone_separation" in safety_capabilities,
            f"safety_capabilities={sorted(safety_capabilities)}",
        ),
        _gate(
            "multi_snapshot_telemetry_sequence_evaluated",
            any(
                case.get("case_input", {}).get("notes")
                and "multi_snapshot_telemetry_sequence" in case.get("case_input", {}).get("notes", [])
                and "telemetry_accepted" in case.get("actual_event_types", [])
                and "telemetry_safety_intervention" in case.get("actual_event_types", [])
                for case in supervision_cases
                if isinstance(case, dict)
            ),
            "requires a registered safe-to-unsafe telemetry sequence",
        ),
        _gate(
            "synthetic_policy_threshold_sensitivity_evaluated",
            set(sensitivity_metadata.get("dimensions", []))
            == {
                "minimum_battery_percent",
                "maximum_altitude_m",
                "route_clearance_margin_m",
                "minimum_inter_drone_separation_m",
            }
            and sensitivity_summary.get("dimension_count") == expected_sensitivity_count
            and sensitivity_summary.get("expected_sequence_matches") == expected_sensitivity_count
            and sensitivity_summary.get("monotonicity_checks_passed") == expected_sensitivity_count,
            f"dimensions={sensitivity_metadata.get('dimensions', [])}, expected={expected_sensitivity_count}",
        ),
    )
    blockers = tuple(gate.name for gate in (*roadmap_gates, *research_gates) if not gate.passed)
    allowed = not blockers
    return Week7CompletionAudit(
        roadmap_gates=roadmap_gates,
        research_gates=research_gates,
        advancement_allowed=allowed,
        decision=(
            "week7_complete_for_advancement_to_week8_end_to_end_evaluation"
            if allowed
            else "remain_on_week7_until_safety_feedback_integration_blockers_are_resolved"
        ),
        blockers=blockers,
    )


def render_week7_completion_markdown(audit: Week7CompletionAudit) -> str:
    payload = audit.to_dict()
    lines = [
        "# Week 7 Completion Gate Audit",
        "",
        "This audit checks the complete Week 7 roadmap scope against literature-supported execution and safety boundaries. Synthetic branch coverage alone cannot complete the milestone.",
        "",
        "## Decision",
        "",
        f"- Advancement allowed: `{str(payload['advancement_allowed']).lower()}`",
        f"- Decision: `{payload['decision']}`",
        "",
        "## Roadmap Gates",
        "",
        *_format_gates(payload["roadmap_gates"]),
        "",
        "## Research Gates",
        "",
        *_format_gates(payload["research_gates"]),
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- `{blocker}`" for blocker in payload["blockers"])
    if not payload["blockers"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _gate(name: str, passed: bool, detail: str) -> CompletionGate:
    return CompletionGate(name=name, passed=bool(passed), detail=detail)


def _deferral_recorded(deferrals: Any, name: str) -> bool:
    item = deferrals.get(name) if isinstance(deferrals, dict) else None
    return isinstance(item, dict) and item.get("status") in {
        "deferred_to_later_planning_or_execution_work",
        "deferred_to_execution_simulation",
        "deferred_to_week8",
        "recorded_caveat",
    }


def _format_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in gates
    ]
