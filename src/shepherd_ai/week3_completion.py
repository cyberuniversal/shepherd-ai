"""Completion-gate audit for Week 3 grounding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompletionGate:
    """One auditable Week 3 completion condition."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week3CompletionAudit:
    """Week 3 completion status split into roadmap and research gates."""

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


def build_week3_completion_audit(
    *,
    map_validation: dict[str, Any],
    region_map_validation: dict[str, Any],
    grounding_evaluations: list[dict[str, Any]],
    grounding_dataset_validations: list[dict[str, Any]],
    coverage_report: dict[str, Any],
    week3_status: dict[str, Any],
    acceptance_criteria: dict[str, Any] | None = None,
    research_deferrals: dict[str, Any] | None = None,
    human_grounding_dataset_validation: dict[str, Any] | None = None,
    human_grounding_evaluation: dict[str, Any] | None = None,
) -> Week3CompletionAudit:
    """Build a completion audit from generated Week 3 artifacts."""

    roadmap_gates = [
        _gate(
            "explicit_main_map_exists",
            int(map_validation.get("records", 0)) > 0,
            f"{map_validation.get('records', 0)} main map records",
        ),
        _gate(
            "map_roles_include_restricted_and_obstacle_records",
            len(map_validation.get("restricted_records", [])) > 0 and len(map_validation.get("obstacle_records", [])) > 0,
            (
                f"restricted={len(map_validation.get('restricted_records', []))}, "
                f"obstacle={len(map_validation.get('obstacle_records', []))}"
            ),
        ),
        _gate(
            "geojson_polygon_fixture_validated",
            int(region_map_validation.get("geometry_counts", {}).get("polygon", 0)) > 0,
            f"polygon_records={region_map_validation.get('geometry_counts', {}).get('polygon', 0)}",
        ),
        _gate(
            "grounding_evaluations_match_expected_labels",
            bool(grounding_evaluations) and all(_evaluation_matches_expected(payload) for payload in grounding_evaluations),
            f"evaluations={len(grounding_evaluations)}",
        ),
        _gate(
            "grounding_dataset_labels_validated",
            bool(grounding_dataset_validations)
            and all(int(payload.get("records", 0)) > 0 for payload in grounding_dataset_validations),
            f"validated_datasets={len(grounding_dataset_validations)}",
        ),
        _gate(
            "ambiguity_and_unresolved_cases_present",
            _total_count(grounding_dataset_validations, "ambiguous_reference_count") > 0
            and _total_count(grounding_dataset_validations, "unresolved_reference_count") > 0,
            (
                f"ambiguous={_total_count(grounding_dataset_validations, 'ambiguous_reference_count')}, "
                f"unresolved={_total_count(grounding_dataset_validations, 'unresolved_reference_count')}"
            ),
        ),
        _gate(
            "main_synthetic_map_coverage_complete",
            int(coverage_report.get("map_records", 0)) > 0
            and len(coverage_report.get("covered_location_ids", [])) == int(coverage_report.get("map_records", 0))
            and not coverage_report.get("warnings", []),
            (
                f"covered={len(coverage_report.get('covered_location_ids', []))}/"
                f"{coverage_report.get('map_records', 0)}, warnings={len(coverage_report.get('warnings', []))}"
            ),
        ),
        _gate(
            "clarification_and_resolution_artifacts_exist",
            bool(week3_status.get("readiness", {}).get("development_handoff_ready", False)),
            week3_status.get("readiness", {}).get("reason", "not stated"),
        ),
        _gate(
            "synthetic_acceptance_thresholds_met",
            _acceptance_thresholds_met(
                acceptance_criteria=acceptance_criteria,
                map_validation=map_validation,
                region_map_validation=region_map_validation,
                grounding_evaluations=grounding_evaluations,
                grounding_dataset_validations=grounding_dataset_validations,
                coverage_report=coverage_report,
            ),
            _acceptance_threshold_detail(acceptance_criteria),
        ),
    ]

    research_gates = [
        _gate(
            "synthetic_data_labeled_as_synthetic",
            _all_data_types_are_synthetic(grounding_dataset_validations),
            "all current validation summaries use synthetic data_type labels",
        ),
        _gate(
            "human_collected_grounding_benchmark_exists",
            _human_grounding_benchmark_exists(
                validation=human_grounding_dataset_validation,
                evaluation=human_grounding_evaluation,
            ),
            _human_grounding_benchmark_detail(
                validation=human_grounding_dataset_validation,
                evaluation=human_grounding_evaluation,
            ),
        ),
        _gate(
            "real_map_or_public_benchmark_provenance_exists",
            _research_item_deferred(research_deferrals, "real_map_or_public_benchmark_provenance_exists"),
            _research_deferral_detail(
                research_deferrals,
                "real_map_or_public_benchmark_provenance_exists",
                fallback="not implemented: current maps are custom synthetic development maps",
            ),
        ),
        _gate(
            "formal_acceptance_threshold_defined",
            _acceptance_criteria_defined(acceptance_criteria),
            _acceptance_threshold_detail(acceptance_criteria),
        ),
    ]

    blockers = [gate.name for gate in research_gates if not gate.passed]
    roadmap_passed = all(gate.passed for gate in roadmap_gates)
    research_passed = all(gate.passed for gate in research_gates)
    advancement_allowed = roadmap_passed and research_passed
    decision = (
        "week3_complete_for_advancement"
        if advancement_allowed
        else "remain_on_week3_until_research_blockers_are_resolved_or_explicitly_deferred"
    )
    return Week3CompletionAudit(
        roadmap_gates=roadmap_gates,
        research_gates=research_gates,
        advancement_allowed=advancement_allowed,
        decision=decision,
        blockers=blockers,
    )


def render_week3_completion_markdown(audit: Week3CompletionAudit) -> str:
    """Render a Markdown completion audit."""

    payload = audit.to_dict()
    lines = [
        "# Week 3 Completion Gate Audit",
        "",
        "This audit separates synthetic roadmap-slice readiness from research-grade completion. It is not a real-world grounding benchmark.",
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


def _evaluation_matches_expected(payload: dict[str, Any]) -> bool:
    summary = payload.get("summary", {})
    return (
        int(summary.get("records", 0)) > 0
        and int(summary.get("exact_record_matches", 0)) == int(summary.get("records", 0))
        and int(summary.get("reference_matches", 0)) == int(summary.get("total_references", 0))
    )


def _total_count(payloads: list[dict[str, Any]], key: str) -> int:
    return sum(int(payload.get(key, 0)) for payload in payloads)


def _all_data_types_are_synthetic(payloads: list[dict[str, Any]]) -> bool:
    data_types = [
        data_type
        for payload in payloads
        for data_type in payload.get("data_type_counts", {})
    ]
    return bool(data_types) and all("synthetic" in data_type for data_type in data_types)


def _human_grounding_benchmark_exists(
    *,
    validation: dict[str, Any] | None,
    evaluation: dict[str, Any] | None,
) -> bool:
    if not isinstance(validation, dict) or not isinstance(evaluation, dict):
        return False
    data_types = list(validation.get("data_type_counts", {}))
    return (
        int(validation.get("records", 0)) > 0
        and bool(data_types)
        and all("human" in data_type and "benchmark" in data_type for data_type in data_types)
        and all("synthetic" not in data_type for data_type in data_types)
        and _evaluation_matches_expected(evaluation)
    )


def _human_grounding_benchmark_detail(
    *,
    validation: dict[str, Any] | None,
    evaluation: dict[str, Any] | None,
) -> str:
    if not isinstance(validation, dict) or not isinstance(evaluation, dict):
        return "not implemented: no filled, validated, and evaluated human-collected Week 3 grounding benchmark is present"
    records = int(validation.get("records", 0))
    data_types = ", ".join(sorted(validation.get("data_type_counts", {}))) or "not stated"
    summary = evaluation.get("summary", {})
    exact = summary.get("exact_record_matches", 0)
    total = summary.get("records", 0)
    return f"records={records}, data_types={data_types}, exact_record_matches={exact}/{total}"


def _format_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in gates
    ]


def _acceptance_criteria_defined(criteria: dict[str, Any] | None) -> bool:
    if not isinstance(criteria, dict):
        return False
    thresholds = criteria.get("thresholds")
    return (
        criteria.get("scope") == "synthetic_week3_completion_gate_v1"
        and criteria.get("not_real_world_benchmark") is True
        and isinstance(thresholds, dict)
    )


def _acceptance_thresholds_met(
    *,
    acceptance_criteria: dict[str, Any] | None,
    map_validation: dict[str, Any],
    region_map_validation: dict[str, Any],
    grounding_evaluations: list[dict[str, Any]],
    grounding_dataset_validations: list[dict[str, Any]],
    coverage_report: dict[str, Any],
) -> bool:
    if not _acceptance_criteria_defined(acceptance_criteria):
        return False
    thresholds = acceptance_criteria["thresholds"]
    exact_min = float(thresholds.get("synthetic_exact_record_accuracy_min", 1.0))
    reference_min = float(thresholds.get("synthetic_reference_accuracy_min", 1.0))
    dataset_records_min = int(thresholds.get("dataset_validation_records_min", 1))
    coverage_fraction_min = float(thresholds.get("main_map_coverage_fraction_min", 1.0))
    coverage_warnings_max = int(thresholds.get("coverage_warnings_max", 0))
    ambiguous_min = int(thresholds.get("ambiguous_reference_count_min", 1))
    unresolved_min = int(thresholds.get("unresolved_reference_count_min", 1))
    restricted_min = int(thresholds.get("restricted_records_min", 1))
    obstacle_min = int(thresholds.get("obstacle_records_min", 1))
    polygon_min = int(thresholds.get("polygon_records_min", 1))

    evaluations_pass = bool(grounding_evaluations) and all(
        float(payload.get("summary", {}).get("exact_record_accuracy", 0.0)) >= exact_min
        and float(payload.get("summary", {}).get("reference_accuracy", 0.0)) >= reference_min
        for payload in grounding_evaluations
    )
    validations_pass = bool(grounding_dataset_validations) and all(
        int(payload.get("records", 0)) >= dataset_records_min
        for payload in grounding_dataset_validations
    )
    map_records = int(coverage_report.get("map_records", 0))
    covered_records = len(coverage_report.get("covered_location_ids", []))
    coverage_fraction = covered_records / map_records if map_records else 0.0

    return (
        evaluations_pass
        and validations_pass
        and coverage_fraction >= coverage_fraction_min
        and len(coverage_report.get("warnings", [])) <= coverage_warnings_max
        and _total_count(grounding_dataset_validations, "ambiguous_reference_count") >= ambiguous_min
        and _total_count(grounding_dataset_validations, "unresolved_reference_count") >= unresolved_min
        and len(map_validation.get("restricted_records", [])) >= restricted_min
        and len(map_validation.get("obstacle_records", [])) >= obstacle_min
        and int(region_map_validation.get("geometry_counts", {}).get("polygon", 0)) >= polygon_min
    )


def _acceptance_threshold_detail(criteria: dict[str, Any] | None) -> str:
    if not _acceptance_criteria_defined(criteria):
        return "not defined: expected docs/week3_acceptance_criteria.json with synthetic_week3_completion_gate_v1 scope"
    return "defined in docs/week3_acceptance_criteria.json for the synthetic Week 3 gate; not a real-world benchmark"


def _research_item_deferred(deferrals: dict[str, Any] | None, name: str) -> bool:
    if not isinstance(deferrals, dict) or deferrals.get("scope") != "week3_research_deferrals_v1":
        return False
    item = deferrals.get("deferrals", {}).get(name)
    return isinstance(item, dict) and item.get("status") == "deferred_for_week3"


def _research_deferral_detail(deferrals: dict[str, Any] | None, name: str, *, fallback: str) -> str:
    if not _research_item_deferred(deferrals, name):
        return fallback
    reason = str(deferrals["deferrals"][name].get("reason", "deferred for Week 3"))
    return f"deferred for Week 3: {reason}"
