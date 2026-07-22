"""Completion audit for the Week 8 end-to-end roadmap scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


ROADMAP_COMMAND = (
    "Send two drones north to inspect crops and one drone east to inspect irrigation."
)
REQUIRED_METRICS = (
    "intent_extraction_accuracy",
    "grounding_accuracy",
    "scheduling_quality",
    "detection_performance",
    "overall_execution_time",
)


@dataclass(frozen=True)
class CompletionGate:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week8CompletionAudit:
    gates: tuple[CompletionGate, ...]
    completion_allowed: bool
    decision: str
    blockers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gates": [gate.to_dict() for gate in self.gates],
            "gates_passed": all(gate.passed for gate in self.gates),
            "completion_allowed": self.completion_allowed,
            "decision": self.decision,
            "blockers": list(self.blockers),
        }


def build_week8_completion_audit(
    *,
    simulation: Mapping[str, Any] | None,
    asr_evidence: Mapping[str, Any] | None,
    intent_evaluation: Mapping[str, Any] | None,
    vision_evaluation: Mapping[str, Any] | None,
    evaluation_summary: Mapping[str, Any] | None,
    artifact_status: Mapping[str, bool],
) -> Week8CompletionAudit:
    """Check stored evidence without running models or filling missing values."""

    simulation = simulation or {}
    asr_evidence = asr_evidence or {}
    intent_evaluation = intent_evaluation or {}
    vision_evaluation = vision_evaluation or {}
    evaluation_summary = evaluation_summary or {}
    preparation = simulation.get("preparation", {})
    simulation_result = simulation.get("simulation", {})
    decomposition = preparation.get("decomposition", {})
    schedule = preparation.get("schedule") or {}
    safety = preparation.get("safety_report") or {}
    asr_audio = asr_evidence.get("audio", {})
    asr_model = asr_evidence.get("model", {})
    intent_records = intent_evaluation.get("records", [])
    vision_manifest = vision_evaluation.get("manifest", {})
    vision_metrics = vision_evaluation.get("metrics", {})
    metrics = evaluation_summary.get("metrics", {})

    gates = (
        _gate(
            "fixed_scenario_preserved",
            decomposition.get("source_text") == ROADMAP_COMMAND,
            f"source_text={decomposition.get('source_text')!r}",
        ),
        _gate(
            "two_clauses_and_three_drones",
            len(decomposition.get("clauses", [])) == 2
            and decomposition.get("total_requested_drones") == 3,
            (
                f"clauses={len(decomposition.get('clauses', []))}, "
                f"requested_drones={decomposition.get('total_requested_drones')}"
            ),
        ),
        _gate(
            "three_drone_schedule_and_safety",
            len(schedule.get("assignments", [])) == 3
            and safety.get("status") == "approved"
            and safety.get("safe_to_execute") is True,
            (
                f"assignments={len(schedule.get('assignments', []))}, "
                f"safety_status={safety.get('status')!r}"
            ),
        ),
        _gate(
            "software_simulation_completed",
            simulation_result.get("simulator") == "deterministic_2d_mission_simulator_v1"
            and simulation_result.get("status") == "completed"
            and simulation_result.get("assignment_count") == 3
            and int(simulation_result.get("telemetry_records", 0)) > 0,
            (
                f"simulator={simulation_result.get('simulator')!r}, "
                f"status={simulation_result.get('status')!r}, "
                f"telemetry_records={simulation_result.get('telemetry_records')}"
            ),
        ),
        _gate(
            "exact_scenario_asr_evidence",
            asr_evidence.get("scenario_source") == "roadmap_week8_fixed_scenario"
            and asr_evidence.get("reference_transcript") == ROADMAP_COMMAND
            and bool(asr_evidence.get("predicted_transcript"))
            and bool(asr_audio.get("path"))
            and bool(asr_audio.get("sha256"))
            and asr_audio.get("data_type") == "human_recorded_audio"
            and bool(asr_model.get("name"))
            and bool(asr_model.get("version")),
            (
                f"audio_type={asr_audio.get('data_type')!r}, "
                f"audio_hash_present={bool(asr_audio.get('sha256'))}, "
                f"prediction_present={bool(asr_evidence.get('predicted_transcript'))}"
            ),
        ),
        _gate(
            "trained_two_clause_intent_evaluation",
            intent_evaluation.get("scenario_source") == "roadmap_week8_fixed_scenario"
            and intent_evaluation.get("model_role") == "frozen_trained_checkpoint"
            and len(intent_records) == 2
            and all(
                record.get("gold_source") in {"human_verified", "roadmap_specification"}
                for record in intent_records
            )
            and _numeric(intent_evaluation.get("exact_match_accuracy")),
            (
                f"model_role={intent_evaluation.get('model_role')!r}, "
                f"records={len(intent_records)}, "
                f"accuracy={intent_evaluation.get('exact_match_accuracy')!r}"
            ),
        ),
        _gate(
            "mission_assigned_vision_evaluation",
            vision_evaluation.get("scenario_source") == "roadmap_week8_fixed_scenario"
            and int(vision_manifest.get("records", 0)) > 0
            and set(vision_manifest.get("clause_ids", [])) == {"clause_001", "clause_002"}
            and int(vision_manifest.get("records_with_sha256", 0))
            == int(vision_manifest.get("records", -1))
            and int(vision_manifest.get("records_with_labels", 0)) > 0
            and bool(vision_evaluation.get("model", {}).get("sha256"))
            and _numeric(vision_metrics.get("primary_value"))
            and int(vision_metrics.get("denominator", 0)) > 0,
            (
                f"records={vision_manifest.get('records')}, "
                f"clauses={vision_manifest.get('clause_ids')}, "
                f"labeled={vision_manifest.get('records_with_labels')}, "
                f"metric={vision_metrics.get('primary_value')!r}"
            ),
        ),
        _gate(
            "all_roadmap_metrics_reported",
            all(
                name in metrics
                and _numeric(metrics[name].get("value"))
                and int(metrics[name].get("denominator", 0)) > 0
                for name in REQUIRED_METRICS
            ),
            f"reported={sorted(metrics)}, required={list(REQUIRED_METRICS)}",
        ),
        _gate(
            "raw_and_derived_artifacts_present",
            all(
                artifact_status.get(name, False)
                for name in (
                    "raw_run",
                    "telemetry",
                    "animated_map",
                    "evaluation_summary",
                    "mission_report",
                    "demonstration_log",
                    "demonstration_screenshot",
                )
            ),
            f"artifacts={dict(sorted(artifact_status.items()))}",
        ),
        _gate(
            "claim_limits_preserved",
            evaluation_summary.get("physical_flight_claimed") is False
            and evaluation_summary.get("safety_guarantee_claimed") is False
            and evaluation_summary.get("novelty_claimed") is False,
            (
                f"physical={evaluation_summary.get('physical_flight_claimed')!r}, "
                f"guarantee={evaluation_summary.get('safety_guarantee_claimed')!r}, "
                f"novelty={evaluation_summary.get('novelty_claimed')!r}"
            ),
        ),
    )
    blockers = tuple(gate.name for gate in gates if not gate.passed)
    allowed = not blockers
    return Week8CompletionAudit(
        gates=gates,
        completion_allowed=allowed,
        decision=(
            "week8_complete_for_advancement_to_week9_paper_draft"
            if allowed
            else "remain_on_week8_until_end_to_end_evidence_is_complete"
        ),
        blockers=blockers,
    )


def render_week8_completion_markdown(audit: Week8CompletionAudit) -> str:
    payload = audit.to_dict()
    lines = [
        "# Week 8 Completion Gate Audit",
        "",
        "This audit checks the fixed roadmap scenario. A completed movement simulation alone is insufficient.",
        "",
        "## Decision",
        "",
        f"- Completion allowed: `{str(payload['completion_allowed']).lower()}`",
        f"- Decision: `{payload['decision']}`",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in payload["gates"]
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{blocker}`" for blocker in payload["blockers"])
    if not payload["blockers"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _gate(name: str, passed: bool, detail: str) -> CompletionGate:
    return CompletionGate(name=name, passed=bool(passed), detail=detail)


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
