"""Completion-gate audit for Week 2 speech and intent extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompletionGate:
    """One auditable Week 2 completion condition."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week2CompletionAudit:
    """Week 2 completion status split into roadmap and research gates."""

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


def build_week2_completion_audit(
    *,
    status_summary: dict[str, Any] | None,
    performance_risk_audit: dict[str, Any] | None,
    handoff: dict[str, Any] | None,
    fresh_manifest_audit: dict[str, Any] | None,
    fresh_intent_review_summary: dict[str, Any] | None,
    fresh_asr_evaluation: dict[str, Any] | None,
    fresh_intent_evaluation: dict[str, Any] | None,
    acceptance_criteria: dict[str, Any] | None = None,
) -> Week2CompletionAudit:
    """Build a Week 2 audit without fabricating missing benchmark evidence."""

    roadmap_gates = [
        _gate(
            "speech_to_text_pipeline_recorded",
            _has_asr_status(status_summary),
            _asr_status_detail(status_summary),
        ),
        _gate(
            "intent_json_fields_present",
            _handoff_schema_has_roadmap_fields(handoff),
            _handoff_schema_detail(handoff),
        ),
        _gate(
            "trained_language_component_recorded",
            _trained_component_recorded(status_summary),
            _trained_component_detail(status_summary),
        ),
        _gate(
            "example_command_and_audio_data_recorded",
            _example_data_recorded(status_summary, performance_risk_audit),
            _example_data_detail(status_summary, performance_risk_audit),
        ),
    ]

    research_gates = [
        _gate(
            "acceptance_thresholds_defined",
            _acceptance_criteria_defined(acceptance_criteria),
            _acceptance_threshold_detail(acceptance_criteria),
        ),
        _gate(
            "known_week2_risks_recorded",
            _risk_audit_recorded(performance_risk_audit),
            _risk_audit_detail(performance_risk_audit),
        ),
        _gate(
            "handoff_is_not_claimed_final",
            _handoff_caveat_recorded(handoff),
            _handoff_caveat_detail(handoff),
        ),
        _gate(
            "fresh_post_development_manifest_non_overlapping",
            _fresh_manifest_non_overlapping(fresh_manifest_audit, acceptance_criteria),
            _fresh_manifest_detail(fresh_manifest_audit),
        ),
        _gate(
            "fresh_audio_intent_labels_human_reviewed",
            _fresh_intent_review_ready(fresh_intent_review_summary, acceptance_criteria),
            _fresh_intent_review_detail(fresh_intent_review_summary),
        ),
        _gate(
            "fresh_asr_evaluation_recorded",
            _fresh_asr_evaluation_recorded(fresh_asr_evaluation, acceptance_criteria),
            _fresh_asr_detail(fresh_asr_evaluation),
        ),
        _gate(
            "fresh_intent_evaluation_recorded",
            _fresh_intent_evaluation_recorded(fresh_intent_evaluation, acceptance_criteria),
            _fresh_intent_eval_detail(fresh_intent_evaluation),
        ),
        _gate(
            "transformer_negative_result_preserved",
            _transformer_negative_result_preserved(handoff),
            "Week 2 handoff records that transformer span paths are not the current primary intent JSON path",
        ),
    ]

    blockers = [gate.name for gate in (*roadmap_gates, *research_gates) if not gate.passed]
    advancement_allowed = all(gate.passed for gate in roadmap_gates) and all(
        gate.passed for gate in research_gates
    )
    decision = (
        "week2_complete_for_clean_reconfirmation_of_weeks3_to5"
        if advancement_allowed
        else "remain_on_week2_until_clean_post_development_benchmark_exists"
    )
    return Week2CompletionAudit(
        roadmap_gates=roadmap_gates,
        research_gates=research_gates,
        advancement_allowed=advancement_allowed,
        decision=decision,
        blockers=blockers,
    )


def render_week2_completion_markdown(audit: Week2CompletionAudit) -> str:
    """Render a Markdown completion audit."""

    payload = audit.to_dict()
    lines = [
        "# Week 2 Completion Gate Audit",
        "",
        "This audit checks speech-to-text and intent-extraction readiness. It blocks advancement when the only evidence is provisional, post-hoc, overlapping, or not human-reviewed.",
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


def _headline(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload.get("headline", {}) if isinstance(payload, dict) else {}


def _summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload.get("summary", {}) if isinstance(payload, dict) else {}


def _has_asr_status(status_summary: dict[str, Any] | None) -> bool:
    headline = _headline(status_summary)
    return (
        int(headline.get("audio_records", 0)) > 0
        and "asr_exact_match_accuracy" in headline
        and "asr_mean_word_error_rate" in headline
    )


def _asr_status_detail(status_summary: dict[str, Any] | None) -> str:
    headline = _headline(status_summary)
    return (
        f"audio_records={headline.get('audio_records', 0)}, "
        f"asr_exact={headline.get('asr_exact_match_accuracy', 'not stated')}, "
        f"wer={headline.get('asr_mean_word_error_rate', 'not stated')}"
    )


def _handoff_schema_has_roadmap_fields(handoff: dict[str, Any] | None) -> bool:
    schema = handoff.get("handoff_contract", {}).get("intent_schema", {}) if isinstance(handoff, dict) else {}
    return {"action", "count", "location", "target", "constraints"} <= set(schema)


def _handoff_schema_detail(handoff: dict[str, Any] | None) -> str:
    schema = handoff.get("handoff_contract", {}).get("intent_schema", {}) if isinstance(handoff, dict) else {}
    return f"intent_fields={sorted(schema)}"


def _trained_component_recorded(status_summary: dict[str, Any] | None) -> bool:
    headline = _headline(status_summary)
    return (
        "colab_t4_distilbert_test_entity_f1" in headline
        and "trained_human_intent_exact_accuracy" in headline
    )


def _trained_component_detail(status_summary: dict[str, Any] | None) -> str:
    headline = _headline(status_summary)
    return (
        f"distilbert_span_f1={headline.get('colab_t4_distilbert_test_entity_f1', 'not stated')}, "
        f"trained_human_intent_exact={headline.get('trained_human_intent_exact_accuracy', 'not stated')}"
    )


def _example_data_recorded(
    status_summary: dict[str, Any] | None,
    risk_audit: dict[str, Any] | None,
) -> bool:
    headline = _headline(status_summary)
    risk_summary = _summary(risk_audit)
    return (
        int(headline.get("audio_records", 0)) > 0
        and int(risk_summary.get("command_records", 0)) > 0
        and int(risk_summary.get("span_records", 0)) > 0
    )


def _example_data_detail(
    status_summary: dict[str, Any] | None,
    risk_audit: dict[str, Any] | None,
) -> str:
    headline = _headline(status_summary)
    risk_summary = _summary(risk_audit)
    return (
        f"audio={headline.get('audio_records', 0)}, "
        f"commands={risk_summary.get('command_records', 0)}, "
        f"spans={risk_summary.get('span_records', 0)}"
    )


def _acceptance_criteria_defined(criteria: dict[str, Any] | None) -> bool:
    if not isinstance(criteria, dict):
        return False
    thresholds = criteria.get("thresholds")
    required = {
        "fresh_audio_records_min",
        "fresh_manifest_overlap_records_max",
        "fresh_manifest_duplicate_transcripts_max",
        "fresh_intent_review_ready_required",
        "fresh_asr_records_min",
        "fresh_intent_eval_records_min",
        "fresh_intent_systems_min",
    }
    return (
        criteria.get("scope") == "week2_clean_post_development_completion_gate_v1"
        and criteria.get("not_final_end_to_end_benchmark") is True
        and isinstance(thresholds, dict)
        and required <= set(thresholds)
    )


def _threshold(criteria: dict[str, Any] | None, name: str, default: int | float | bool) -> Any:
    if not isinstance(criteria, dict):
        return default
    thresholds = criteria.get("thresholds", {})
    if not isinstance(thresholds, dict):
        return default
    return thresholds.get(name, default)


def _acceptance_threshold_detail(criteria: dict[str, Any] | None) -> str:
    if not _acceptance_criteria_defined(criteria):
        return "not defined: expected docs/week2_completion_criteria.json"
    return "defined for a clean post-development Week 2 benchmark; not an end-to-end benchmark"


def _risk_audit_recorded(risk_audit: dict[str, Any] | None) -> bool:
    return isinstance(risk_audit, dict) and int(_summary(risk_audit).get("risk_factor_count", 0)) > 0


def _risk_audit_detail(risk_audit: dict[str, Any] | None) -> str:
    summary = _summary(risk_audit)
    return f"risk_factors={summary.get('risk_factor_count', 'not stated')}"


def _handoff_caveat_recorded(handoff: dict[str, Any] | None) -> bool:
    if not isinstance(handoff, dict):
        return False
    note = str(handoff.get("metadata", {}).get("note", "")).lower()
    debts = " ".join(str(item).lower() for item in handoff.get("week2_carry_forward_debt", []))
    return "development handoff" in note and "fresh" in debts and "before treating it as generalized" in debts


def _handoff_caveat_detail(handoff: dict[str, Any] | None) -> str:
    if not isinstance(handoff, dict):
        return "missing handoff caveat"
    return str(handoff.get("metadata", {}).get("note", "not stated"))


def _fresh_manifest_non_overlapping(
    manifest_audit: dict[str, Any] | None,
    criteria: dict[str, Any] | None,
) -> bool:
    summary = _summary(manifest_audit)
    return (
        int(summary.get("records", 0)) >= int(_threshold(criteria, "fresh_audio_records_min", 30))
        and int(summary.get("overlap_records", 999_999))
        <= int(_threshold(criteria, "fresh_manifest_overlap_records_max", 0))
        and int(summary.get("duplicate_transcripts_within_candidate", 999_999))
        <= int(_threshold(criteria, "fresh_manifest_duplicate_transcripts_max", 0))
        and summary.get("passes_non_overlap_policy") is True
    )


def _fresh_manifest_detail(manifest_audit: dict[str, Any] | None) -> str:
    if not isinstance(manifest_audit, dict):
        return "missing fresh manifest non-overlap audit"
    summary = _summary(manifest_audit)
    return (
        f"records={summary.get('records', 0)}, overlap={summary.get('overlap_records', 'not stated')}, "
        f"duplicates={summary.get('duplicate_transcripts_within_candidate', 'not stated')}, "
        f"passes={summary.get('passes_non_overlap_policy', False)}"
    )


def _fresh_intent_review_ready(
    review_summary: dict[str, Any] | None,
    criteria: dict[str, Any] | None,
) -> bool:
    summary = _summary(review_summary)
    required = bool(_threshold(criteria, "fresh_intent_review_ready_required", True))
    return (not required) or summary.get("ready_for_gold_evaluation") is True


def _fresh_intent_review_detail(review_summary: dict[str, Any] | None) -> str:
    if not isinstance(review_summary, dict):
        return "missing fresh audio-intent review summary"
    summary = _summary(review_summary)
    return (
        f"records={summary.get('records', 0)}, ready={summary.get('ready_for_gold_evaluation', False)}, "
        f"draft={summary.get('draft_records', 'not stated')}, "
        f"not_reviewed={summary.get('not_reviewed_records', 'not stated')}"
    )


def _fresh_asr_evaluation_recorded(
    asr_evaluation: dict[str, Any] | None,
    criteria: dict[str, Any] | None,
) -> bool:
    summary = _summary(asr_evaluation)
    return int(summary.get("records", 0)) >= int(_threshold(criteria, "fresh_asr_records_min", 30))


def _fresh_asr_detail(asr_evaluation: dict[str, Any] | None) -> str:
    if not isinstance(asr_evaluation, dict):
        return "missing fresh ASR evaluation"
    summary = _summary(asr_evaluation)
    return (
        f"records={summary.get('records', 0)}, "
        f"exact={summary.get('exact_match_accuracy', 'not stated')}, "
        f"wer={summary.get('mean_word_error_rate', 'not stated')}"
    )


def _fresh_intent_evaluation_recorded(
    intent_evaluation: dict[str, Any] | None,
    criteria: dict[str, Any] | None,
) -> bool:
    summary = _summary(intent_evaluation)
    systems = _intent_system_count(intent_evaluation)
    return (
        int(summary.get("records", 0)) >= int(_threshold(criteria, "fresh_intent_eval_records_min", 30))
        and systems >= int(_threshold(criteria, "fresh_intent_systems_min", 3))
    )


def _fresh_intent_eval_detail(intent_evaluation: dict[str, Any] | None) -> str:
    if not isinstance(intent_evaluation, dict):
        return "missing fresh intent evaluation"
    summary = _summary(intent_evaluation)
    return f"records={summary.get('records', 0)}, systems={_intent_system_count(intent_evaluation)}"


def _intent_system_count(intent_evaluation: dict[str, Any] | None) -> int:
    if not isinstance(intent_evaluation, dict):
        return 0
    if isinstance(intent_evaluation.get("systems"), list):
        return len(intent_evaluation["systems"])
    if isinstance(intent_evaluation.get("results_by_system"), dict):
        return len(intent_evaluation["results_by_system"])
    if isinstance(intent_evaluation.get("system_results"), dict):
        return len(intent_evaluation["system_results"])
    return 0


def _transformer_negative_result_preserved(handoff: dict[str, Any] | None) -> bool:
    if not isinstance(handoff, dict):
        return False
    contract = handoff.get("handoff_contract", {})
    return contract.get("not_yet_handoff_primary", {}).get("transformer_span_paths") is not None


def _format_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in gates
    ]
