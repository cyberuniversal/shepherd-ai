"""Completion-gate audit for Week 5 multi-drone scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompletionGate:
    """One auditable Week 5 completion condition."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week5CompletionAudit:
    """Week 5 completion status split into roadmap and research gates."""

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


def build_week5_completion_audit(
    *,
    schedule_comparison: dict[str, Any],
    assignment_csv_text: str,
    allocation_visualization_html: str,
    scheduler_notebook_text: str,
    acceptance_criteria: dict[str, Any] | None = None,
    research_deferrals: dict[str, Any] | None = None,
) -> Week5CompletionAudit:
    """Build a completion audit from generated Week 5 scheduling artifacts."""

    roadmap_gates = [
        _gate(
            "three_simulated_drones_present",
            _three_simulated_drones_present(schedule_comparison),
            _drone_detail(schedule_comparison),
        ),
        _gate(
            "automatic_assignments_present",
            _automatic_assignments_present(schedule_comparison),
            _primary_assignment_detail(schedule_comparison),
        ),
        _gate(
            "all_tasks_assigned",
            _all_tasks_assigned(schedule_comparison),
            _primary_assignment_detail(schedule_comparison),
        ),
        _gate(
            "all_three_drones_used",
            _all_three_drones_used(schedule_comparison),
            _primary_assignment_detail(schedule_comparison),
        ),
        _gate(
            "multi_drone_request_replicated",
            _multi_drone_request_replicated(schedule_comparison),
            "multi-drone command creates at least two schedulable task replicas and assigns both",
        ),
        _gate(
            "assignment_table_artifact_present",
            _assignment_table_present(assignment_csv_text, schedule_comparison),
            _assignment_table_detail(assignment_csv_text),
        ),
        _gate(
            "allocation_visualization_artifact_present",
            _allocation_visualization_present(allocation_visualization_html),
            "HTML allocation artifact includes the Week 5 title, table, and timeline bars",
        ),
        _gate(
            "simple_scheduling_logic_metrics_present",
            _simple_scheduling_metrics_present(schedule_comparison),
            "primary assignments include start, end, duration, and travel-distance fields",
        ),
        _gate(
            "strategy_comparison_present",
            _strategy_comparison_present(schedule_comparison),
            _strategy_comparison_detail(schedule_comparison),
        ),
        _gate(
            "strategy_metrics_present",
            _strategy_metrics_present(schedule_comparison),
            "comparison rows include assigned, unassigned, drones used, makespan, travel, and workload range",
        ),
        _gate(
            "scheduler_notebook_workflow_present",
            _scheduler_notebook_workflow_present(scheduler_notebook_text),
            "Notebook5_Scheduler.ipynb runs the Week 5 scheduler and audit scripts",
        ),
    ]

    research_gates = [
        _gate(
            "acceptance_thresholds_defined",
            _acceptance_criteria_defined(acceptance_criteria),
            _acceptance_threshold_detail(acceptance_criteria),
        ),
        _gate(
            "classical_baselines_before_llm_assignment",
            _classical_baseline_scope_declared(schedule_comparison),
            "schedule comparison declares deterministic classical baselines and no LLM assignment",
        ),
        _gate(
            "synthetic_metric_scope_declared",
            _synthetic_metric_scope_declared(schedule_comparison),
            "metadata and notes distinguish scheduling proxies from physical flight, safety, execution, and route optimization",
        ),
        _gate(
            "task_allocation_caveat_preserved",
            _research_item_recorded(research_deferrals, "task_allocation_review_conflict_caveat"),
            _research_deferral_detail(
                research_deferrals,
                "task_allocation_review_conflict_caveat",
                fallback="not stated: preserve paper #12 narrative/table conflict before using it as design evidence",
            ),
        ),
        _gate(
            "route_optimization_deferred_for_week5",
            _research_item_recorded(research_deferrals, "route_optimization_deferred_for_week5"),
            _research_deferral_detail(
                research_deferrals,
                "route_optimization_deferred_for_week5",
                fallback="not stated: Week 5 must not claim route optimization",
            ),
        ),
        _gate(
            "safety_validation_deferred_for_week5",
            _research_item_recorded(research_deferrals, "safety_validation_deferred_for_week5"),
            _research_deferral_detail(
                research_deferrals,
                "safety_validation_deferred_for_week5",
                fallback="not stated: Week 5 must not claim safety validation",
            ),
        ),
        _gate(
            "execution_deferred_for_week5",
            _research_item_recorded(research_deferrals, "execution_deferred_for_week5"),
            _research_deferral_detail(
                research_deferrals,
                "execution_deferred_for_week5",
                fallback="not stated: Week 5 must not claim simulated or physical execution",
            ),
        ),
        _gate(
            "optimality_not_claimed",
            _research_item_recorded(research_deferrals, "optimality_not_claimed"),
            _research_deferral_detail(
                research_deferrals,
                "optimality_not_claimed",
                fallback="not stated: simple baselines do not prove optimal schedules",
            ),
        ),
    ]

    blockers = [gate.name for gate in (*roadmap_gates, *research_gates) if not gate.passed]
    advancement_allowed = all(gate.passed for gate in roadmap_gates) and all(
        gate.passed for gate in research_gates
    )
    decision = (
        "week5_complete_for_advancement_to_week6_vision"
        if advancement_allowed
        else "remain_on_week5_until_scheduling_blockers_are_resolved_or_explicitly_deferred"
    )
    return Week5CompletionAudit(
        roadmap_gates=roadmap_gates,
        research_gates=research_gates,
        advancement_allowed=advancement_allowed,
        decision=decision,
        blockers=blockers,
    )


def render_week5_completion_markdown(audit: Week5CompletionAudit) -> str:
    """Render a Markdown completion audit."""

    payload = audit.to_dict()
    lines = [
        "# Week 5 Completion Gate Audit",
        "",
        "This audit checks simulated multi-drone scheduling only. It is not route optimization, safety validation, mission execution, or physical-drone control.",
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


def _three_simulated_drones_present(payload: dict[str, Any]) -> bool:
    drones = payload.get("drones", [])
    return isinstance(drones, list) and len(drones) == 3 and all(
        isinstance(drone, dict) and str(drone.get("status")) == "idle" for drone in drones
    )


def _drone_detail(payload: dict[str, Any]) -> str:
    drones = payload.get("drones", [])
    ids = [str(drone.get("drone_id", "missing")) for drone in drones if isinstance(drone, dict)]
    return f"drones={len(drones) if isinstance(drones, list) else 0}, ids={ids}"


def _primary_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    primary = payload.get("primary_assignment", {})
    return primary.get("metrics", {}) if isinstance(primary, dict) else {}


def _primary_assignments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    primary = payload.get("primary_assignment", {})
    assignments = primary.get("assignments", []) if isinstance(primary, dict) else []
    return assignments if isinstance(assignments, list) else []


def _automatic_assignments_present(payload: dict[str, Any]) -> bool:
    metrics = _primary_metrics(payload)
    return int(metrics.get("assigned_tasks", 0)) > 0 and len(_primary_assignments(payload)) > 0


def _all_tasks_assigned(payload: dict[str, Any]) -> bool:
    metrics = _primary_metrics(payload)
    return (
        int(metrics.get("total_tasks", 0)) > 0
        and int(metrics.get("assigned_tasks", 0)) == int(metrics.get("total_tasks", -1))
        and int(metrics.get("unassigned_tasks", -1)) == 0
    )


def _all_three_drones_used(payload: dict[str, Any]) -> bool:
    return int(_primary_metrics(payload).get("drones_used", 0)) == 3


def _primary_assignment_detail(payload: dict[str, Any]) -> str:
    metrics = _primary_metrics(payload)
    return (
        f"total={metrics.get('total_tasks', 0)}, assigned={metrics.get('assigned_tasks', 0)}, "
        f"unassigned={metrics.get('unassigned_tasks', 0)}, drones_used={metrics.get('drones_used', 0)}"
    )


def _multi_drone_request_replicated(payload: dict[str, Any]) -> bool:
    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        return False
    replicated = [
        task
        for task in tasks
        if isinstance(task, dict)
        and str(task.get("source_plan_id")) == "mission_001"
        and int(task.get("required_drone_index", 0)) in {1, 2}
    ]
    assigned_ids = {str(assignment.get("task_id")) for assignment in _primary_assignments(payload)}
    return len(replicated) >= 2 and all(str(task.get("task_id")) in assigned_ids for task in replicated)


def _assignment_table_present(csv_text: str, payload: dict[str, Any]) -> bool:
    lines = [line for line in csv_text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("task_id,drone_id,strategy"):
        return False
    return len(lines) - 1 == len(_primary_assignments(payload))


def _assignment_table_detail(csv_text: str) -> str:
    lines = [line for line in csv_text.splitlines() if line.strip()]
    return f"csv_rows={max(len(lines) - 1, 0)}, header={lines[0] if lines else 'missing'}"


def _allocation_visualization_present(html: str) -> bool:
    return (
        "Week 5 Drone Allocation" in html
        and "<table>" in html
        and "class='track'" in html
        and "class='bar'" in html
    )


def _simple_scheduling_metrics_present(payload: dict[str, Any]) -> bool:
    required = {"start_min", "end_min", "duration_min", "travel_distance_m"}
    assignments = _primary_assignments(payload)
    return bool(assignments) and all(required <= set(assignment) for assignment in assignments)


def _strategy_comparison_present(payload: dict[str, Any]) -> bool:
    comparison = payload.get("comparison", {})
    results = comparison.get("strategy_results", []) if isinstance(comparison, dict) else []
    strategies = {str(result.get("strategy")) for result in results if isinstance(result, dict)}
    return len(results) >= 3 and {"round_robin", "least_loaded", "nearest_available"} <= strategies


def _strategy_comparison_detail(payload: dict[str, Any]) -> str:
    comparison = payload.get("comparison", {})
    rows = comparison.get("comparison_table", []) if isinstance(comparison, dict) else []
    best = comparison.get("best_strategy_by_makespan") if isinstance(comparison, dict) else None
    strategies = [row.get("strategy") for row in rows if isinstance(row, dict)]
    return f"strategies={strategies}, best_by_makespan={best}"


def _strategy_metrics_present(payload: dict[str, Any]) -> bool:
    comparison = payload.get("comparison", {})
    rows = comparison.get("comparison_table", []) if isinstance(comparison, dict) else []
    required = {
        "strategy",
        "assigned_tasks",
        "unassigned_tasks",
        "drones_used",
        "makespan_min",
        "total_travel_distance_m",
        "workload_range_min",
    }
    return bool(rows) and all(isinstance(row, dict) and required <= set(row) for row in rows)


def _scheduler_notebook_workflow_present(notebook_text: str) -> bool:
    return (
        "schedule_missions.py" in notebook_text
        and "audit_week5_completion.py" in notebook_text
        and "week5_schedule_comparison_v1.json" in notebook_text
    )


def _acceptance_criteria_defined(criteria: dict[str, Any] | None) -> bool:
    if not isinstance(criteria, dict):
        return False
    thresholds = criteria.get("thresholds")
    required = {
        "simulated_drones_required",
        "strategies_min",
        "unassigned_tasks_max",
        "drones_used_min",
        "assignment_table_required",
        "allocation_visualization_required",
    }
    return (
        criteria.get("scope") == "synthetic_week5_scheduling_gate_v1"
        and criteria.get("not_execution_benchmark") is True
        and isinstance(thresholds, dict)
        and required <= set(thresholds)
    )


def _acceptance_threshold_detail(criteria: dict[str, Any] | None) -> str:
    if not _acceptance_criteria_defined(criteria):
        return "not defined: expected docs/week5_acceptance_criteria.json with synthetic_week5_scheduling_gate_v1 scope"
    return "defined in docs/week5_acceptance_criteria.json for the synthetic Week 5 scheduling gate; not an execution benchmark"


def _classical_baseline_scope_declared(payload: dict[str, Any]) -> bool:
    notes = " ".join(str(note) for note in payload.get("comparison", {}).get("notes", []))
    return "Classical deterministic baselines" in notes and "no LLM assignment" in notes


def _synthetic_metric_scope_declared(payload: dict[str, Any]) -> bool:
    metadata_note = str(payload.get("metadata", {}).get("note", ""))
    comparison_notes = " ".join(str(note) for note in payload.get("comparison", {}).get("notes", []))
    combined = f"{metadata_note} {comparison_notes}".lower()
    return all(
        phrase in combined
        for phrase in [
            "synthetic scheduling proxies",
            "not route optimization",
            "safety validation",
            "execution",
            "physical",
        ]
    )


def _research_item_recorded(deferrals: dict[str, Any] | None, name: str) -> bool:
    if not isinstance(deferrals, dict) or deferrals.get("scope") != "week5_research_deferrals_v1":
        return False
    item = deferrals.get("deferrals", {}).get(name)
    return isinstance(item, dict) and item.get("status") in {"deferred_for_week5", "recorded_caveat"}


def _research_deferral_detail(deferrals: dict[str, Any] | None, name: str, *, fallback: str) -> str:
    if not _research_item_recorded(deferrals, name):
        return fallback
    item = deferrals["deferrals"][name]
    return f"{item.get('status')}: {item.get('reason', 'not stated')}"


def _format_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in gates
    ]
