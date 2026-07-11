"""Status summary helpers for Week 3 grounding artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Week3GroundingStatus:
    """Aggregated Week 3 status from validation, evaluation, and review files."""

    map_validation: dict[str, Any]
    grounding_evaluations: list[dict[str, Any]] = field(default_factory=list)
    clarification_reports: list[dict[str, Any]] = field(default_factory=list)
    applied_resolutions: list[dict[str, Any]] = field(default_factory=list)
    readiness: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_validation": self.map_validation,
            "grounding_evaluations": self.grounding_evaluations,
            "clarification_reports": self.clarification_reports,
            "applied_resolutions": self.applied_resolutions,
            "readiness": self.readiness,
        }


def build_week3_grounding_status(
    *,
    map_validation: dict[str, Any],
    grounding_evaluations: list[dict[str, Any]],
    clarification_reports: list[dict[str, Any]],
    applied_resolutions: list[dict[str, Any]],
) -> Week3GroundingStatus:
    """Build a compact status summary from Week 3 artifacts."""

    validation_summary = _map_validation_summary(map_validation)
    evaluation_summaries = [_evaluation_summary(payload) for payload in grounding_evaluations]
    clarification_summaries = [
        _clarification_summary(payload) for payload in clarification_reports
    ]
    resolution_summaries = [_resolution_summary(payload) for payload in applied_resolutions]
    readiness = _readiness(validation_summary, evaluation_summaries, clarification_summaries, resolution_summaries)

    return Week3GroundingStatus(
        map_validation=validation_summary,
        grounding_evaluations=evaluation_summaries,
        clarification_reports=clarification_summaries,
        applied_resolutions=resolution_summaries,
        readiness=readiness,
    )


def render_week3_grounding_status_markdown(status: Week3GroundingStatus) -> str:
    """Render a Markdown report for the aggregated Week 3 grounding status."""

    payload = status.to_dict()
    lines = [
        "# Week 3 Grounding Status",
        "",
        "This report aggregates synthetic Week 3 grounding artifacts. It is not a real-world grounding benchmark, route-planning result, or safety certificate.",
        "",
        "## Readiness",
        "",
        f"- Week 3 synthetic development slice internally complete: `{str(payload['readiness']['development_handoff_ready']).lower()}`",
        f"- Reason: {payload['readiness']['reason']}",
        "- Advancement decision: use `docs/week3_completion_audit.md`; this status report alone is not permission to move weeks.",
        "",
        "## Map Validation",
        "",
        f"- Records: {payload['map_validation']['records']}",
        f"- Ambiguous terms: {payload['map_validation']['ambiguous_terms']}",
        f"- Restricted records: {payload['map_validation']['restricted_records']}",
        f"- Obstacle records: {payload['map_validation']['obstacle_records']}",
        f"- Warnings: {payload['map_validation']['warnings']}",
        "",
        "## Grounding Evaluations",
        "",
    ]
    for evaluation in payload["grounding_evaluations"]:
        lines.extend(
            [
                f"- `{evaluation['dataset']}`: {evaluation['exact_record_matches']} / {evaluation['records']} exact records, {evaluation['reference_matches']} / {evaluation['total_references']} reference matches, ready records {evaluation['ready_for_planning_records']} / {evaluation['records']}",
            ]
        )
    if not payload["grounding_evaluations"]:
        lines.append("- None")

    lines.extend(["", "## Clarification Reports", ""])
    for report in payload["clarification_reports"]:
        lines.append(
            f"- `{report['source']}`: requests {report['requests']}, blocks_planning `{str(report['blocks_planning']).lower()}`"
        )
    if not payload["clarification_reports"]:
        lines.append("- None")

    lines.extend(["", "## Applied Resolutions", ""])
    for resolution in payload["applied_resolutions"]:
        lines.append(
            f"- `{resolution['source']}`: choices {resolution['choices']}, remaining requests {resolution['remaining_requests']}, blocks_planning `{str(resolution['blocks_planning']).lower()}`"
        )
    if not payload["applied_resolutions"]:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- All current map records and grounding examples are synthetic development artifacts.",
            "- The exact-match results do not measure real-world grounding accuracy.",
            "- Operator-applied clarifications are explicit interventions, not automatic model success.",
            "- Safety metadata is surfaced but not enforced by a safety validator.",
        ]
    )
    return "\n".join(lines) + "\n"


def _map_validation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": int(payload.get("records", 0)),
        "ambiguous_terms": len(payload.get("ambiguous_terms", [])),
        "restricted_records": len(payload.get("restricted_records", [])),
        "obstacle_records": len(payload.get("obstacle_records", [])),
        "warnings": len(payload.get("warnings", [])),
        "warning_codes": list(payload.get("warnings", [])),
    }


def _evaluation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    records = payload.get("records", [])
    return {
        "dataset": payload.get("metadata", {}).get("dataset", "not stated"),
        "records": int(summary.get("records", 0)),
        "exact_record_matches": int(summary.get("exact_record_matches", 0)),
        "exact_record_accuracy": float(summary.get("exact_record_accuracy", 0.0)),
        "reference_matches": int(summary.get("reference_matches", 0)),
        "total_references": int(summary.get("total_references", 0)),
        "reference_accuracy": float(summary.get("reference_accuracy", 0.0)),
        "ready_for_planning_records": sum(1 for record in records if record.get("ready_for_planning")),
        "blocked_records": sum(1 for record in records if not record.get("ready_for_planning")),
    }


def _clarification_summary(payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("clarification_report", {})
    return {
        "source": payload.get("metadata", {}).get("source_grounded_json")
        or payload.get("metadata", {}).get("map", "not stated"),
        "requests": len(report.get("requests", [])),
        "blocks_planning": bool(report.get("blocks_planning", False)),
        "issues": list(report.get("issues", [])),
    }


def _resolution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("clarification_report", {})
    return {
        "source": payload.get("metadata", {}).get("source_grounded_json", "not stated"),
        "choices": len(payload.get("operator_choices", {})),
        "remaining_requests": len(report.get("requests", [])),
        "blocks_planning": bool(report.get("blocks_planning", False)),
        "ready_for_planning": bool(report.get("ready_for_planning", False)),
    }


def _readiness(
    validation: dict[str, Any],
    evaluations: list[dict[str, Any]],
    clarifications: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> dict[str, Any]:
    has_map = validation["records"] > 0
    evaluations_match = bool(evaluations) and all(
        evaluation["records"] > 0
        and evaluation["exact_record_matches"] == evaluation["records"]
        and evaluation["reference_matches"] == evaluation["total_references"]
        for evaluation in evaluations
    )
    has_blocking_clarification = any(report["blocks_planning"] for report in clarifications)
    has_successful_resolution = any(
        resolution["choices"] > 0
        and resolution["remaining_requests"] == 0
        and not resolution["blocks_planning"]
        for resolution in resolutions
    )
    ready = has_map and evaluations_match and has_blocking_clarification and has_successful_resolution
    reason = (
        "synthetic_grounding_slice_has_validation_evaluation_clarification_and_resolution_artifacts"
        if ready
        else "missing_required_week3_development_artifacts"
    )
    return {
        "development_handoff_ready": ready,
        "reason": reason,
        "not_real_world_benchmark": True,
    }
