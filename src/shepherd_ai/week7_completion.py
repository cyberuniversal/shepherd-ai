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
    simulated_updates = [
        update
        for case in cases if isinstance(case, dict)
        for update in case.get("workflow_result", {}).get("simulated_status_updates", [])
    ]
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
            "simulated_status_updates_present",
            bool(simulated_updates) and all(update.get("mode") == "schedule_based_simulation" for update in simulated_updates),
            f"updates={len(simulated_updates)}",
        ),
        _gate(
            "notebook_runs_workflow_and_evaluation",
            all(token in notebook_text for token in ["run_week7_workflow.py", "evaluate_week7_safety.py", "audit_week7_completion.py"]),
            "Notebook7 must run the workflow, evaluation, and completion audit scripts",
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
            "route_geometry_limit_recorded",
            _deferral_recorded(deferrals, "route_geometry_not_evaluated"),
            "route-geometry limitation is recorded",
        ),
        _gate(
            "collision_avoidance_limit_recorded",
            _deferral_recorded(deferrals, "collision_avoidance_not_evaluated"),
            "collision-avoidance limitation is recorded",
        ),
        _gate(
            "mission_specific_vision_deferred_to_week8",
            _deferral_recorded(deferrals, "mission_specific_vision_execution"),
            "mission-specific imagery is deferred rather than fabricated",
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
        "This audit covers the synthetic pre-execution safety, feedback, and integration milestone. It is not physical-flight safety evidence or Week 8 mission success.",
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
