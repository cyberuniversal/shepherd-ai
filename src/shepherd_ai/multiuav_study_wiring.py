"""Truthful component wiring and readiness checks for the MultiUAV study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


STUDY_ID = "multiuav_validation_placement_v1"
ACTIVE_BRANCH = "codex/multiuav-validation-study"
EXPECTED_SOURCE_COMMIT = "1794e45e421fb5de03094f0b63f9ca95f86ab42f"
EXPECTED_SOURCE_ARCHIVE_SHA256 = (
    "b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3"
)


def audit_primary_study_wiring(repository_root: Path) -> dict[str, Any]:
    """Validate completed data gates and report the actual active components."""

    metadata = repository_root / "datasets" / "multiuav_plat"
    source_path = metadata / "source_audit_v1.json"
    split_path = metadata / "session_split_v1.json"
    eligibility_path = metadata / "task_eligibility_v1.json"
    context_path = metadata / "agent_context_audit_v1.json"
    recoverability_path = metadata / "recoverability_audit_v1.json"
    distilbert_smoke_path = (
        repository_root
        / "outputs"
        / "evaluations"
        / "week7_distilbert_wiring_smoke_v1.json"
    )
    errors: list[str] = []

    source = _read_object(source_path, errors)
    split = _read_object(split_path, errors)
    eligibility = _read_object(eligibility_path, errors)
    context = _read_object(context_path, errors)
    recoverability = _read_object(recoverability_path, errors)
    if source:
        if source.get("valid") is not True:
            errors.append("source audit is not valid")
        if source.get("source", {}).get("commit") != EXPECTED_SOURCE_COMMIT:
            errors.append("source audit commit does not match the pinned commit")
        if (
            source.get("benchmark", {}).get("archive", {}).get("sha256")
            != EXPECTED_SOURCE_ARCHIVE_SHA256
        ):
            errors.append("source audit archive hash does not match the pin")
    if split:
        if split.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE_SHA256:
            errors.append("session split is not bound to the pinned source")
        if split.get("session_counts") != {
            "calibration": 15,
            "test": 15,
            "train": 45,
        }:
            errors.append("session split counts do not match the frozen protocol")
    if eligibility:
        if eligibility.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE_SHA256:
            errors.append("task eligibility is not bound to the pinned source")
        if split_path.is_file() and eligibility.get("session_split_sha256") != _sha256(
            split_path
        ):
            errors.append("task eligibility is not bound to the committed split")
        summary = eligibility.get("summary", {})
        if summary.get("eligible_task_count") != 1_473:
            errors.append("eligible task count does not match the frozen protocol")
        if summary.get("normalized_cross_split_overlap_count") != 0:
            errors.append("eligible task text has cross-split overlap")
    if context:
        if context.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE_SHA256:
            errors.append("agent context audit is not bound to the pinned source")
        context_summary = context.get("summary", {})
        if context_summary.get("tasks_audited") != 1_500:
            errors.append("agent context audit does not cover all source tasks")
        if context_summary.get("privileged_field_leaks") != 0:
            errors.append("agent context audit reports privileged-field leakage")
        if context_summary.get("privileged_noninterference_passes") != 1_500:
            errors.append("agent context privileged noninterference is incomplete")
    if recoverability:
        if (
            recoverability.get("source_archive_sha256")
            != EXPECTED_SOURCE_ARCHIVE_SHA256
        ):
            errors.append("recoverability audit is not bound to the pinned source")
        if eligibility_path.is_file() and recoverability.get(
            "eligibility_sha256"
        ) != _sha256(eligibility_path):
            errors.append("recoverability audit is not bound to task eligibility")
        recoverability_summary = recoverability.get("summary", {})
        if recoverability_summary.get("eligible_tasks_audited") != 1_473:
            errors.append("recoverability audit does not cover eligible tasks")
        if (
            recoverability_summary.get("tasks_with_operator_fact_candidates")
            != 1_473
        ):
            errors.append("recoverability candidate coverage is incomplete")
        if (
            recoverability_summary.get(
                "resource_conflict_block_justifications"
            )
            != 1_473
        ):
            errors.append("resource-conflict justification coverage is incomplete")

    completed_gates = [
        "pinned_source_integrity",
        "session_split",
        "task_eligibility",
        "official_alias_selection",
        "agent_visible_context_projection",
        "recoverability_rule",
    ]
    blocking_gates = [
        "intervention_generation_and_review",
        "m1_to_m4_call_budget",
        "strict_api_plan_contract",
        "deterministic_recursive_validator",
        "immutable_qwen_checkpoint_resolution",
        "offline_inference_isolation",
        "execution_scope",
        "hardware_measurement_protocol",
    ]
    return {
        "study_id": STUDY_ID,
        "active_branch": ACTIVE_BRANCH,
        "valid": not errors,
        "errors": errors,
        "status": (
            "ready_for_intervention_generation"
            if not errors
            else "invalid_completed_gate_wiring"
        ),
        "completed_gates": completed_gates,
        "blocking_gates": blocking_gates,
        "primary_path": {
            "input_modality": "text",
            "source_adapter": "multiuav_plat_pinned_source_v1",
            "dataset": "five_variant_dataset_not_implemented",
            "model_family": "Qwen2.5-Instruct_planned_not_loaded",
            "methods": ["M1", "M2", "M3", "M4"],
            "api_plan_parser": "not_implemented",
            "deterministic_validator": "not_implemented",
            "execution_backend": "not_selected",
        },
        "legacy_component_roles": {
            "whisper": "excluded_from_primary_text_first_study",
            "distilbert_week2_span_tagger": (
                "wired and smoke-tested in the historical Shepherd end-to-end "
                "path; excluded from the primary study because it was trained "
                "for Shepherd intent spans, not MultiUAV API planning"
            ),
            "week8_deterministic_mission_pipeline": (
                "historical_roadmap_evidence_not_a_primary_comparison_method"
            ),
            "week9_monolithic_diagnostic": (
                "historical_development_diagnostic_not_revised_study_evidence"
            ),
        },
        "runtime_invocation": {
            "whisper_invoked": False,
            "distilbert_invoked": False,
            "legacy_week8_pipeline_invoked": False,
            "qwen_invoked": False,
        },
        "ready_for_intervention_generation": not errors,
        "ready_for_model_inference": False,
        "artifact_bindings": {
            "source_audit": _artifact_record(source_path, repository_root),
            "session_split": _artifact_record(split_path, repository_root),
            "task_eligibility": _artifact_record(
                eligibility_path, repository_root
            ),
            "agent_context_audit": _artifact_record(
                context_path, repository_root
            ),
            "recoverability_audit": _artifact_record(
                recoverability_path, repository_root
            ),
            "historical_distilbert_wiring_smoke": _artifact_record(
                distilbert_smoke_path, repository_root
            ),
        },
        "claim_status": "component_wiring_audited_no_revised_inference",
    }


def _read_object(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing wiring artifact: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"invalid JSON wiring artifact {path}: {error.msg}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"wiring artifact must contain an object: {path}")
        return {}
    return payload


def _artifact_record(path: Path, repository_root: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(repository_root.resolve()).as_posix(),
        "sha256": _sha256(path) if path.is_file() else None,
        "exists": path.is_file(),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
