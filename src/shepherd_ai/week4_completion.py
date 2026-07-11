"""Completion-gate audit for Week 4 mission planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompletionGate:
    """One auditable Week 4 completion condition."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week4CompletionAudit:
    """Week 4 completion status split into roadmap and research gates."""

    roadmap_gates: list[CompletionGate]
    research_gates: list[CompletionGate]
    advancement_allowed: bool
    decision: str
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "roadmap_gates": [gate.to_dict() for gate in self.roadmap_gates],
            "research_gates": [gate.to_dict() for gate in self.research_gates],
            "roadmap_gates_passed": all(gate.passed for gate in self.roadmap_gates),
            "research_gates_passed": all(gate.passed for gate in self.research_gates),
            "advancement_allowed": self.advancement_allowed,
            "decision": self.decision,
            "blockers": self.blockers,
        }


def build_week4_completion_audit(
    *,
    human_benchmark_planning: dict[str, Any],
    focused_planning_cases: dict[str, Any],
    flow_diagram_markdown: str,
    acceptance_criteria: dict[str, Any] | None = None,
    research_deferrals: dict[str, Any] | None = None,
) -> Week4CompletionAudit:
    """Build a completion audit from generated Week 4 planning artifacts."""

    roadmap_gates = [
        _gate(
            "human_grounding_benchmark_planning_contract_passes",
            _planning_evaluation_meets_thresholds(human_benchmark_planning, acceptance_criteria),
            _planning_summary_detail(human_benchmark_planning),
        ),
        _gate(
            "focused_planning_cases_contract_passes",
            _planning_evaluation_meets_thresholds(focused_planning_cases, acceptance_criteria),
            _planning_summary_detail(focused_planning_cases),
        ),
        _gate(
            "planned_and_blocked_cases_present",
            _has_planned_and_blocked(focused_planning_cases),
            _planned_blocked_detail(focused_planning_cases),
        ),
        _gate(
            "roadmap_scan_sequence_present",
            _roadmap_scan_sequence_present(focused_planning_cases),
            "scan case includes takeoff, fly_to, capture_images, run_vision_model, save results, and return",
        ),
        _gate(
            "mission_flow_diagram_present",
            _mission_flow_diagram_present(flow_diagram_markdown),
            "Mermaid mission-flow diagram artifact exists for Week 4 inspection",
        ),
        _gate(
            "task_graph_contract_present",
            _task_graph_contract_valid(focused_planning_cases),
            "planned records have explicit nodes and dependency edges; blocked records have empty graphs",
        ),
        _gate(
            "constraint_review_case_present",
            _constraint_review_case_present(focused_planning_cases),
            "at least one constrained command requires and emits review_constraints",
        ),
        _gate(
            "restricted_or_clearance_issues_preserved",
            _restricted_or_clearance_issues_preserved(focused_planning_cases),
            "planner preserves not-flyable or clearance issues for later safety validation",
        ),
        _gate(
            "readiness_matches_plan_status",
            _readiness_matches_status(human_benchmark_planning) and _readiness_matches_status(focused_planning_cases),
            "planned records are ready for scheduling and blocked records are not",
        ),
    ]

    research_gates = [
        _gate(
            "acceptance_thresholds_defined",
            _acceptance_criteria_defined(acceptance_criteria),
            _acceptance_threshold_detail(acceptance_criteria),
        ),
        _gate(
            "human_written_command_planning_evaluation_exists",
            _human_written_command_planning_evaluation_exists(human_benchmark_planning),
            _human_written_detail(human_benchmark_planning),
        ),
        _gate(
            "scheduling_deferred_for_week4",
            _research_item_deferred(research_deferrals, "scheduling_deferred_for_week4"),
            _research_deferral_detail(
                research_deferrals,
                "scheduling_deferred_for_week4",
                fallback="not stated: Week 4 must not claim multi-drone scheduling",
            ),
        ),
        _gate(
            "route_optimization_deferred_for_week4",
            _research_item_deferred(research_deferrals, "route_optimization_deferred_for_week4"),
            _research_deferral_detail(
                research_deferrals,
                "route_optimization_deferred_for_week4",
                fallback="not stated: Week 4 must not claim route feasibility",
            ),
        ),
        _gate(
            "safety_validation_deferred_for_week4",
            _research_item_deferred(research_deferrals, "safety_validation_deferred_for_week4"),
            _research_deferral_detail(
                research_deferrals,
                "safety_validation_deferred_for_week4",
                fallback="not stated: Week 4 must not claim safety validation",
            ),
        ),
        _gate(
            "simulation_execution_deferred_for_week4",
            _research_item_deferred(research_deferrals, "simulation_execution_deferred_for_week4"),
            _research_deferral_detail(
                research_deferrals,
                "simulation_execution_deferred_for_week4",
                fallback="not stated: Week 4 must not claim simulated execution",
            ),
        ),
    ]

    blockers = [gate.name for gate in (*roadmap_gates, *research_gates) if not gate.passed]
    roadmap_passed = all(gate.passed for gate in roadmap_gates)
    research_passed = all(gate.passed for gate in research_gates)
    advancement_allowed = roadmap_passed and research_passed
    decision = (
        "week4_complete_for_advancement_to_week5_scheduling"
        if advancement_allowed
        else "remain_on_week4_until_planning_blockers_are_resolved_or_explicitly_deferred"
    )
    return Week4CompletionAudit(
        roadmap_gates=roadmap_gates,
        research_gates=research_gates,
        advancement_allowed=advancement_allowed,
        decision=decision,
        blockers=blockers,
    )


def render_week4_completion_markdown(audit: Week4CompletionAudit) -> str:
    """Render a Markdown completion audit."""

    payload = audit.to_dict()
    lines = [
        "# Week 4 Completion Gate Audit",
        "",
        "This audit checks high-level mission-planning readiness only. It is not a scheduling, safety, route-feasibility, or execution result.",
        "",
        "## Decision",
        "",
        f"- Advancement allowed: `{str(payload['advancement_allowed']).lower()}`",
        f"- Decision: `{payload['decision']}`",
        "",
        "## Roadmap Gates",
        "",
    ]
    lines.extend(_format_gates(payload["roadmap_gates"]))
    lines.extend(["", "## Research Gates", ""])
    lines.extend(_format_gates(payload["research_gates"]))
    lines.extend(["", "## Blockers", ""])
    if payload["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in payload["blockers"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _gate(name: str, passed: bool, detail: str) -> CompletionGate:
    return CompletionGate(name=name, passed=bool(passed), detail=detail)


def _planning_evaluation_meets_thresholds(
    payload: dict[str, Any],
    acceptance_criteria: dict[str, Any] | None,
) -> bool:
    if not _acceptance_criteria_defined(acceptance_criteria):
        return False
    summary = payload.get("summary", {})
    thresholds = acceptance_criteria["thresholds"]
    records_min = int(thresholds.get("records_min", 1))
    status_min = float(thresholds.get("expected_status_accuracy_min", 1.0))
    action_min = float(thresholds.get("required_action_accuracy_min", 1.0))
    issue_min = float(thresholds.get("required_issue_accuracy_min", 1.0))
    contract_min = float(thresholds.get("valid_plan_contract_fraction_min", 1.0))
    records = int(summary.get("records", 0))
    valid_contracts = int(summary.get("valid_plan_contract_records", 0))
    contract_fraction = valid_contracts / records if records else 0.0
    return (
        records >= records_min
        and float(summary.get("expected_status_accuracy", 0.0)) >= status_min
        and float(summary.get("required_action_accuracy", 0.0)) >= action_min
        and float(summary.get("required_issue_accuracy", 0.0)) >= issue_min
        and contract_fraction >= contract_min
    )


def _planning_summary_detail(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    records = int(summary.get("records", 0))
    valid_contracts = int(summary.get("valid_plan_contract_records", 0))
    return (
        f"records={records}, planned={summary.get('planned_records', 0)}, "
        f"blocked={summary.get('blocked_records', 0)}, "
        f"status_accuracy={summary.get('expected_status_accuracy', 0.0)}, "
        f"required_action_accuracy={summary.get('required_action_accuracy', 0.0)}, "
        f"required_issue_accuracy={summary.get('required_issue_accuracy', 0.0)}, "
        f"valid_plan_contracts={valid_contracts}/{records}"
    )


def _has_planned_and_blocked(payload: dict[str, Any]) -> bool:
    summary = payload.get("summary", {})
    return int(summary.get("planned_records", 0)) > 0 and int(summary.get("blocked_records", 0)) > 0


def _planned_blocked_detail(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    return f"planned={summary.get('planned_records', 0)}, blocked={summary.get('blocked_records', 0)}"


def _task_graph_contract_valid(payload: dict[str, Any]) -> bool:
    records = payload.get("records", [])
    if not isinstance(records, list) or not records:
        return False
    for record in records:
        if not isinstance(record, dict):
            return False
        graph = record.get("task_graph", {})
        nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        edges = graph.get("edges", []) if isinstance(graph, dict) else []
        step_count = int(record.get("step_count", 0))
        if record.get("actual_plan_status") == "blocked":
            if step_count != 0 or nodes or edges:
                return False
            continue
        if record.get("actual_plan_status") != "planned":
            return False
        if len(nodes) != step_count:
            return False
        if step_count > 0 and len(edges) != step_count - 1:
            return False
        node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
        for edge in edges:
            if not isinstance(edge, dict):
                return False
            if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
                return False
    return True


def _roadmap_scan_sequence_present(payload: dict[str, Any]) -> bool:
    required = [
        "takeoff",
        "fly_to",
        "capture_images",
        "run_vision_model",
        "save_observation_results",
        "return_to_launch_area",
    ]
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        actions = record.get("step_actions", [])
        if "scan_area" not in actions:
            continue
        positions = [actions.index(action) for action in required if action in actions]
        if len(positions) == len(required) and positions == sorted(positions):
            return True
    return False


def _mission_flow_diagram_present(markdown: str) -> bool:
    return (
        "```mermaid" in markdown
        and "flowchart TD" in markdown
        and "capture_images" in markdown
        and "run_vision_model" in markdown
    )


def _constraint_review_case_present(payload: dict[str, Any]) -> bool:
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        if (
            "review_constraints" in record.get("required_actions", [])
            and "review_constraints" in record.get("step_actions", [])
            and record.get("required_actions_present") is True
        ):
            return True
    return False


def _restricted_or_clearance_issues_preserved(payload: dict[str, Any]) -> bool:
    issue_tokens = ("not_flyable", "requires_clearance")
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        issues = [str(issue) for issue in record.get("issues", [])]
        if any(any(token in issue for token in issue_tokens) for issue in issues):
            return True
    return False


def _readiness_matches_status(payload: dict[str, Any]) -> bool:
    records = payload.get("records", [])
    if not isinstance(records, list) or not records:
        return False
    for record in records:
        if not isinstance(record, dict):
            return False
        status = record.get("actual_plan_status")
        ready = record.get("ready_for_scheduling")
        if status == "planned" and ready is not True:
            return False
        if status == "blocked" and ready is not False:
            return False
    return True


def _acceptance_criteria_defined(criteria: dict[str, Any] | None) -> bool:
    if not isinstance(criteria, dict):
        return False
    thresholds = criteria.get("thresholds")
    return (
        criteria.get("scope") == "synthetic_week4_completion_gate_v1"
        and criteria.get("not_execution_benchmark") is True
        and isinstance(thresholds, dict)
    )


def _acceptance_threshold_detail(criteria: dict[str, Any] | None) -> str:
    if not _acceptance_criteria_defined(criteria):
        return "not defined: expected docs/week4_acceptance_criteria.json with synthetic_week4_completion_gate_v1 scope"
    return "defined in docs/week4_acceptance_criteria.json for the synthetic Week 4 planning gate; not an execution benchmark"


def _human_written_command_planning_evaluation_exists(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata", {})
    summary = payload.get("summary", {})
    dataset = str(metadata.get("dataset", ""))
    return "human_grounding_benchmark" in dataset and int(summary.get("records", 0)) > 0


def _human_written_detail(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata", {})
    summary = payload.get("summary", {})
    return f"dataset={metadata.get('dataset', 'not stated')}, records={summary.get('records', 0)}"


def _research_item_deferred(deferrals: dict[str, Any] | None, name: str) -> bool:
    if not isinstance(deferrals, dict) or deferrals.get("scope") != "week4_research_deferrals_v1":
        return False
    item = deferrals.get("deferrals", {}).get(name)
    return isinstance(item, dict) and item.get("status") == "deferred_for_week4"


def _research_deferral_detail(deferrals: dict[str, Any] | None, name: str, *, fallback: str) -> str:
    if not _research_item_deferred(deferrals, name):
        return fallback
    reason = str(deferrals["deferrals"][name].get("reason", "deferred for Week 4"))
    return f"deferred for Week 4: {reason}"


def _format_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in gates
    ]
