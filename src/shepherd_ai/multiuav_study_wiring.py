"""Truthful component wiring and readiness checks for the MultiUAV study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from shepherd_ai.multiuav_checkpoints import RunConfig


STUDY_ID = "multiuav_validation_placement_v1"
ACTIVE_BRANCH = "codex/multiuav-validation-study"
EXPECTED_SOURCE_COMMIT = "1794e45e421fb5de03094f0b63f9ca95f86ab42f"
EXPECTED_SOURCE_ARCHIVE_SHA256 = (
    "b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3"
)
EXPECTED_MODEL_REVISIONS = {
    "Qwen/Qwen2.5-3B-Instruct": (
        "aa8e72537993ba99e69dfaafa59ed015b17504d1"
    ),
    "Qwen/Qwen2.5-7B-Instruct": (
        "a09a35458c702b33eeacc393d103063234e8bc28"
    ),
}


def audit_primary_study_wiring(repository_root: Path) -> dict[str, Any]:
    """Validate completed data gates and report the actual active components."""

    metadata = repository_root / "datasets" / "multiuav_plat"
    source_path = metadata / "source_audit_v1.json"
    split_path = metadata / "session_split_v1.json"
    eligibility_path = metadata / "task_eligibility_v1.json"
    context_path = metadata / "agent_context_audit_v1.json"
    recoverability_path = metadata / "recoverability_audit_v1.json"
    pilot_dataset_path = metadata / "intervention_pilot_v2.json"
    pilot_summary_path = metadata / "intervention_pilot_summary_v2.json"
    pilot_validation_path = metadata / "intervention_pilot_validation_v2.json"
    intervention_negative_controls_path = (
        metadata / "intervention_validator_negative_controls_v1.json"
    )
    method_contract_path = metadata / "method_contract_audit_v1.json"
    grounding_contract_path = metadata / "grounding_contract_audit_v1.json"
    model_revision_path = metadata / "model_revision_audit_v1.json"
    runner_contract_path = metadata / "runner_contract_audit_v1.json"
    offline_runtime_path = (
        metadata / "offline_runtime_contract_audit_v1.json"
    )
    qwen_3b_cache_path = metadata / "qwen25_3b_cache_audit_v1.json"
    qwen_3b_smoke_path = metadata / "qwen25_3b_load_smoke_v1.json"
    qwen_3b_failed_smoke_path = (
        metadata / "qwen25_3b_load_smoke_attempt1_failed_v1.json"
    )
    qwen_3b_historical_smoke_path = (
        metadata / "qwen25_3b_load_smoke_pre_offload_option_v1.json"
    )
    qwen_7b_cache_path = metadata / "qwen25_7b_cache_audit_v1.json"
    qwen_7b_smoke_path = metadata / "qwen25_7b_load_smoke_v1.json"
    execution_scope_path = metadata / "execution_scope_audit_v1.json"
    hardware_measurement_path = (
        metadata / "hardware_measurement_contract_audit_v1.json"
    )
    resource_schedule_path = metadata / "resource_schedule_candidate_v1.json"
    resource_hardware_protocol_path = (
        metadata / "resource_hardware_protocol_v1.json"
    )
    resource_final_schedule_path = metadata / "resource_schedule_v1.json"
    resource_run_configs_path = metadata / "resource_run_configs_v1.json"
    pilot_review_path = (
        repository_root
        / "reports"
        / "multiuav_intervention_pilot_review_v2.csv"
    )
    completed_pilot_review_path = (
        repository_root
        / "reports"
        / "multiuav_intervention_pilot_review_completed_v2.csv"
    )
    completed_pilot_review_validation_path = (
        metadata / "intervention_pilot_review_validation_v2.json"
    )
    pilot_review_normalization_path = (
        metadata / "intervention_pilot_review_normalization_v2.json"
    )
    intervention_dataset_path = metadata / "intervention_dataset_v1.json"
    intervention_dataset_summary_path = (
        metadata / "intervention_dataset_summary_v1.json"
    )
    intervention_dataset_validation_path = (
        metadata / "intervention_dataset_validation_v1.json"
    )
    intervention_review_path = (
        repository_root / "reports" / "multiuav_intervention_review_v1.csv"
    )
    expert_qc_path = metadata / "expert_qc_audit_v1.json"
    accuracy_protocol_path = metadata / "accuracy_protocol_freeze_v1.json"
    accuracy_manifest_path = metadata / "accuracy_case_manifest_v1.json"
    scoring_contract_path = metadata / "scoring_contract_audit_v1.json"
    accuracy_run_configs_path = metadata / "accuracy_run_configs_v1.json"
    failed_attempts = metadata / "failed_attempts"
    excluded_local_attempt_summary_path = (
        failed_attempts / "qwen25_3b_local_accuracy_attempt1_summary.json"
    )
    excluded_local_attempt_results_path = (
        failed_attempts / "qwen25_3b_local_accuracy_attempt1_results.jsonl"
    )
    excluded_local_attempt_config_path = (
        failed_attempts / "qwen25_3b_local_accuracy_attempt1_run_config.json"
    )
    excluded_local_attempt_stderr_path = (
        failed_attempts / "qwen25_3b_local_accuracy_attempt1_stderr.log"
    )
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
    pilot_summary = _read_object(pilot_summary_path, errors)
    pilot_validation = _read_object(pilot_validation_path, errors)
    intervention_negative_controls = _read_object(
        intervention_negative_controls_path,
        errors,
    )
    method_contract = _read_object(method_contract_path, errors)
    grounding_contract = _read_object(grounding_contract_path, errors)
    model_revisions = _read_object(model_revision_path, errors)
    runner_contract = _read_object(runner_contract_path, errors)
    offline_runtime = _read_object(offline_runtime_path, errors)
    qwen_3b_cache = _read_object(qwen_3b_cache_path, errors)
    qwen_3b_smoke = _read_object(qwen_3b_smoke_path, errors)
    qwen_3b_failed_smoke = _read_object(qwen_3b_failed_smoke_path, errors)
    qwen_3b_historical_smoke = _read_object(
        qwen_3b_historical_smoke_path, errors
    )
    qwen_7b_cache = _read_object(qwen_7b_cache_path, errors)
    qwen_7b_smoke = _read_object(qwen_7b_smoke_path, errors)
    execution_scope = _read_object(execution_scope_path, errors)
    hardware_measurement = _read_object(hardware_measurement_path, errors)
    resource_schedule = _read_object(resource_schedule_path, errors)
    resource_hardware_protocol = _read_object(
        resource_hardware_protocol_path, errors
    )
    resource_final_schedule = _read_object(
        resource_final_schedule_path, errors
    )
    resource_run_configs = _read_optional_object(
        resource_run_configs_path, errors
    )
    completed_pilot_review_validation = _read_object(
        completed_pilot_review_validation_path,
        errors,
    )
    pilot_review_normalization = _read_object(
        pilot_review_normalization_path,
        errors,
    )
    intervention_dataset_summary = _read_object(
        intervention_dataset_summary_path,
        errors,
    )
    intervention_dataset_validation = _read_object(
        intervention_dataset_validation_path,
        errors,
    )
    expert_qc = _read_object(expert_qc_path, errors)
    accuracy_protocol = _read_object(accuracy_protocol_path, errors)
    accuracy_manifest = _read_object(accuracy_manifest_path, errors)
    scoring_contract = _read_object(scoring_contract_path, errors)
    accuracy_run_configs = _read_optional_object(accuracy_run_configs_path, errors)
    excluded_local_attempt = _read_optional_object(
        excluded_local_attempt_summary_path,
        errors,
    )
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
    if pilot_summary:
        if (
            pilot_summary.get("source_archive_sha256")
            != EXPECTED_SOURCE_ARCHIVE_SHA256
        ):
            errors.append("intervention pilot is not bound to the pinned source")
        if eligibility_path.is_file() and pilot_summary.get(
            "eligibility_sha256"
        ) != _sha256(eligibility_path):
            errors.append("intervention pilot is not bound to task eligibility")
        if pilot_dataset_path.is_file() and pilot_summary.get(
            "dataset_sha256"
        ) != _sha256(pilot_dataset_path):
            errors.append("intervention pilot dataset hash does not match")
        if pilot_review_path.is_file() and pilot_summary.get(
            "review_packet_sha256"
        ) != _sha256(pilot_review_path):
            errors.append("intervention pilot review-packet hash does not match")
        pilot_counts = pilot_summary.get("summary", {})
        if pilot_counts.get("clusters") != 30 or pilot_counts.get("cases") != 150:
            errors.append("intervention pilot does not contain 30 complete clusters")
        if pilot_counts.get("pending_human_review_clusters") != 30:
            errors.append("intervention pilot review status is unexpected")
        if pilot_counts.get("approved_clusters") != 0:
            errors.append("unreviewed intervention pilot reports approved clusters")
    if pilot_validation:
        if pilot_validation.get("valid") is not True:
            errors.append("intervention pilot validation did not pass")
        if pilot_dataset_path.is_file() and pilot_validation.get(
            "dataset_sha256"
        ) != _sha256(pilot_dataset_path):
            errors.append("pilot validation is not bound to the pilot dataset")
        if pilot_review_path.is_file() and pilot_validation.get(
            "review_packet_sha256"
        ) != _sha256(pilot_review_path):
            errors.append("pilot validation is not bound to the review packet")
        if pilot_summary_path.is_file() and pilot_validation.get(
            "generation_summary_sha256"
        ) != _sha256(pilot_summary_path):
            errors.append("pilot validation is not bound to the generation summary")
    if completed_pilot_review_validation:
        review_summary = completed_pilot_review_validation.get("summary", {})
        if completed_pilot_review_validation.get("valid") is not True:
            errors.append("completed pilot review validation did not pass")
        if pilot_dataset_path.is_file() and completed_pilot_review_validation.get(
            "dataset_sha256"
        ) != _sha256(pilot_dataset_path):
            errors.append("completed pilot review is not bound to the pilot dataset")
        if completed_pilot_review_path.is_file() and completed_pilot_review_validation.get(
            "review_packet_sha256"
        ) != _sha256(completed_pilot_review_path):
            errors.append("completed pilot review packet hash does not match")
        if review_summary.get("status_counts") != {"approved": 150}:
            errors.append("completed pilot review does not approve all 150 cases")
        if review_summary.get("cluster_status_counts") != {"approved": 30}:
            errors.append("completed pilot review does not approve all 30 clusters")
        if not review_summary.get("reviewer_ids"):
            errors.append("completed pilot review has no reviewer pseudonym")
    if pilot_review_normalization:
        if pilot_review_normalization.get("notes_preserved_exactly") is not True:
            errors.append("pilot review normalization did not preserve reviewer notes")
        normalization_output = pilot_review_normalization.get("output", {})
        if completed_pilot_review_path.is_file() and normalization_output.get(
            "sha256"
        ) != _sha256(completed_pilot_review_path):
            errors.append("pilot review normalization output hash does not match")
    if intervention_dataset_summary:
        full_counts = intervention_dataset_summary.get("summary", {})
        if intervention_dataset_path.is_file() and intervention_dataset_summary.get(
            "dataset_sha256"
        ) != _sha256(intervention_dataset_path):
            errors.append("full intervention dataset hash does not match")
        if intervention_review_path.is_file() and intervention_dataset_summary.get(
            "review_packet_sha256"
        ) != _sha256(intervention_review_path):
            errors.append("full intervention review-packet hash does not match")
        if full_counts.get("eligible_clusters") != 1_473:
            errors.append("full intervention dataset does not contain 1,473 clusters")
        if full_counts.get("generated_post_eligibility_cases") != 7_365:
            errors.append("full intervention dataset does not contain 7,365 cases")
        if full_counts.get("pending_human_review_clusters") != 1_473:
            errors.append("full intervention dataset review status is unexpected")
        if full_counts.get("approved_clusters") != 0:
            errors.append("unreviewed full intervention dataset reports approvals")
    if intervention_dataset_validation:
        if intervention_dataset_validation.get("valid") is not True:
            errors.append("full intervention dataset validation did not pass")
        if intervention_dataset_path.is_file() and intervention_dataset_validation.get(
            "dataset_sha256"
        ) != _sha256(intervention_dataset_path):
            errors.append("full dataset validation is not bound to the dataset")
        if intervention_review_path.is_file() and intervention_dataset_validation.get(
            "review_packet_sha256"
        ) != _sha256(intervention_review_path):
            errors.append("full dataset validation is not bound to the review packet")
        if (
            intervention_dataset_summary_path.is_file()
            and intervention_dataset_validation.get("generation_summary_sha256")
            != _sha256(intervention_dataset_summary_path)
        ):
            errors.append("full dataset validation is not bound to its summary")
    if expert_qc:
        if expert_qc.get("valid") is not True:
            errors.append("expert QC audit did not pass")
        if expert_qc.get("sample", {}).get("approved_cases") != 150:
            errors.append("expert QC audit does not contain 150 approved cases")
        if expert_qc.get("sample", {}).get("approved_clusters") != 30:
            errors.append("expert QC audit does not contain 30 approved clusters")
        if expert_qc.get("full_row_level_human_review_required") is not False:
            errors.append("expert QC audit incorrectly requires full row review")
        qc_bindings = expert_qc.get("artifact_bindings", {})
        if intervention_dataset_path.is_file() and qc_bindings.get(
            "full_dataset_sha256"
        ) != _sha256(intervention_dataset_path):
            errors.append("expert QC audit is not bound to the full dataset")
    if accuracy_protocol:
        if accuracy_protocol.get("study_scores_inspected") is not False:
            errors.append("accuracy protocol was not registered score-blind")
        if accuracy_protocol.get("expected_accuracy_rows") != 11_360:
            errors.append("accuracy protocol has the wrong expected row count")
        if accuracy_protocol.get("expected_model_calls") != 17_040:
            errors.append("accuracy protocol has the wrong expected call count")
        if accuracy_protocol.get("run_policy", {}).get(
            "hardware_warmup_required_for_accuracy"
        ) is not False:
            errors.append("accuracy protocol incorrectly requires GPU warm-up")
        protocol_bindings = accuracy_protocol.get("artifact_bindings", {})
        if expert_qc_path.is_file() and protocol_bindings.get(
            "expert_qc_sha256"
        ) != _sha256(expert_qc_path):
            errors.append("accuracy protocol is not bound to expert QC")
    if accuracy_manifest:
        if accuracy_manifest.get("data_status") != "approved_evaluation_data":
            errors.append("accuracy case manifest is not approved")
        if accuracy_manifest.get("source_clusters") != 284:
            errors.append("accuracy case manifest does not contain 284 clusters")
        if accuracy_manifest.get("case_count") != 1_420:
            errors.append("accuracy case manifest does not contain 1,420 cases")
        if accuracy_manifest.get("materialization_validation", {}).get(
            "gold_fields_in_model_context"
        ) != 0:
            errors.append("accuracy case manifest leaks gold fields")
        manifest_bindings = accuracy_manifest.get("artifact_bindings", {})
        if accuracy_protocol_path.is_file() and manifest_bindings.get(
            "protocol_freeze_sha256"
        ) != _sha256(accuracy_protocol_path):
            errors.append("accuracy case manifest is not bound to the protocol")
    if scoring_contract:
        if scoring_contract.get("valid") is not True:
            errors.append("accuracy scoring contract audit is not valid")
        contract = scoring_contract.get("scoring_contract", {})
        if contract.get("scoring_contract_version") != (
            "multiuav_accuracy_scoring_v1"
        ):
            errors.append("accuracy scoring contract version is unexpected")
        if contract.get("gold_access") != (
            "label_separated_after_complete_matrix_admission"
        ):
            errors.append("accuracy scoring does not enforce label separation")
        result_access = scoring_contract.get("study_results", {})
        if result_access.get("checkpoint_rows_read") != 0:
            errors.append("scoring audit read study checkpoint rows")
        if result_access.get("scores_inspected") is not False:
            errors.append("scoring audit inspected study scores")
        scoring_bindings = scoring_contract.get("artifact_bindings", {})
        if accuracy_protocol_path.is_file() and scoring_bindings.get(
            "accuracy_protocol_sha256"
        ) != _sha256(accuracy_protocol_path):
            errors.append("scoring contract is not bound to the accuracy protocol")
        if accuracy_manifest_path.is_file() and scoring_bindings.get(
            "accuracy_manifest_sha256"
        ) != _sha256(accuracy_manifest_path):
            errors.append("scoring contract is not bound to the accuracy manifest")
        _check_source_hashes(
            repository_root,
            scoring_contract.get("source_code_sha256", {}),
            {
                "multiuav_scoring.py": "src/shepherd_ai/multiuav_scoring.py",
                "audit_multiuav_scoring_contract.py": (
                    "scripts/audit_multiuav_scoring_contract.py"
                ),
            },
            errors,
            label="accuracy scoring contract audit",
        )
    accuracy_config_ready = _validate_accuracy_run_configs(
        accuracy_run_configs,
        accuracy_run_configs_path=accuracy_run_configs_path,
        accuracy_manifest_path=accuracy_manifest_path,
        accuracy_protocol_path=accuracy_protocol_path,
        errors=errors,
    )
    resource_config_ready = _validate_resource_run_configs(
        resource_run_configs,
        resource_run_configs_path=resource_run_configs_path,
        resource_schedule_path=resource_final_schedule_path,
        resource_hardware_protocol_path=resource_hardware_protocol_path,
        accuracy_manifest_path=accuracy_manifest_path,
        intervention_dataset_path=intervention_dataset_path,
        errors=errors,
    )
    excluded_local_attempt_registered = _validate_excluded_local_attempt(
        excluded_local_attempt,
        results_path=excluded_local_attempt_results_path,
        config_path=excluded_local_attempt_config_path,
        stderr_path=excluded_local_attempt_stderr_path,
        errors=errors,
    )
    if intervention_negative_controls:
        controls_summary = intervention_negative_controls.get("summary", {})
        if controls_summary.get("probe_count") != 2:
            errors.append("intervention validator must contain two negative controls")
        if controls_summary.get("observed_rejections") != 2:
            errors.append("intervention validator did not reject both negative controls")
        if pilot_dataset_path.is_file() and intervention_negative_controls.get(
            "pilot_dataset_sha256"
        ) != _sha256(pilot_dataset_path):
            errors.append("negative controls are not bound to the active pilot")
    if method_contract:
        if method_contract.get("valid") is not True:
            errors.append("method contract audit is not valid")
        call_counts = method_contract.get("method_validation", {}).get(
            "call_counts"
        )
        if call_counts != {
            "M1_monolithic": 1,
            "M2_post_plan_deterministic": 1,
            "M3_stage_wise": 2,
            "M4_post_plan_compute_matched": 2,
        }:
            errors.append("method call budgets do not match the frozen protocol")
        contract = method_contract.get("strict_output_contract", {})
        if contract.get("malformed_output_status") != "PARSE_ERROR":
            errors.append("method contract does not preserve PARSE_ERROR")
        if contract.get("execute_requires_nonempty_plan") is not True:
            errors.append("method contract permits empty executable plans")
        source_hashes = method_contract.get("source_code_sha256", {})
        methods_source = (
            repository_root / "src" / "shepherd_ai" / "multiuav_methods.py"
        )
        plan_contract_source = (
            repository_root
            / "src"
            / "shepherd_ai"
            / "multiuav_plan_contract.py"
        )
        if methods_source.is_file() and source_hashes.get(
            "multiuav_methods.py"
        ) != _sha256(methods_source):
            errors.append("method contract is not bound to method source code")
        if plan_contract_source.is_file() and source_hashes.get(
            "multiuav_plan_contract.py"
        ) != _sha256(plan_contract_source):
            errors.append("method contract is not bound to parser source code")
    if grounding_contract:
        if grounding_contract.get("valid") is not True:
            errors.append("grounding contract audit is not valid")
        if grounding_contract.get("endpoint_count") != 11:
            errors.append("grounding endpoint count does not match the frozen catalog")
        if grounding_contract.get("hidden_reference_inputs_used") is not False:
            errors.append("grounding contract permits hidden reference inputs")
        if grounding_contract.get("model_invoked") is not False:
            errors.append("grounding contract audit unexpectedly invoked a model")
        grounding = grounding_contract.get("grounding_contract", {})
        if grounding.get("recursive_waypoint_validation") is not True:
            errors.append("grounding contract does not recursively validate waypoints")
        if grounding.get("provenance_recorded_per_grounded_leaf") is not True:
            errors.append("grounding contract does not record leaf provenance")
        source_hashes = grounding_contract.get("source_code_sha256", {})
        grounding_source = (
            repository_root
            / "src"
            / "shepherd_ai"
            / "multiuav_grounding_validator.py"
        )
        if grounding_source.is_file() and source_hashes.get(
            "multiuav_grounding_validator.py"
        ) != _sha256(grounding_source):
            errors.append("grounding contract is not bound to validator source code")
    if model_revisions:
        if model_revisions.get("valid") is not True:
            errors.append("model revision audit is not valid")
        if model_revisions.get("remote_verification_performed") is not True:
            errors.append("model revisions were not verified remotely")
        if model_revisions.get("weights_downloaded") is not False:
            errors.append("model revision audit unexpectedly downloaded weights")
        if model_revisions.get("model_invoked") is not False:
            errors.append("model revision audit unexpectedly invoked a model")
        observed_revisions = {
            str(item.get("model_id")): item.get("revision")
            for item in model_revisions.get("models", [])
            if isinstance(item, dict)
        }
        if observed_revisions != EXPECTED_MODEL_REVISIONS:
            errors.append("model revisions do not match the frozen registry")
        if not all(
            item.get("remote_verified") is True
            for item in model_revisions.get("models", [])
            if isinstance(item, dict)
        ):
            errors.append("one or more model revisions lack remote verification")
        source_hashes = model_revisions.get("source_code_sha256", {})
        model_revision_source = (
            repository_root
            / "src"
            / "shepherd_ai"
            / "multiuav_model_revisions.py"
        )
        model_revision_script = (
            repository_root
            / "scripts"
            / "audit_multiuav_model_revisions.py"
        )
        if model_revision_source.is_file() and source_hashes.get(
            "multiuav_model_revisions.py"
        ) != _sha256(model_revision_source):
            errors.append("model revision audit is not bound to registry source")
        if model_revision_script.is_file() and source_hashes.get(
            "audit_multiuav_model_revisions.py"
        ) != _sha256(model_revision_script):
            errors.append("model revision audit is not bound to audit source")
    if runner_contract:
        if runner_contract.get("valid") is not True:
            errors.append("runner contract audit is not valid")
        prompt_contract = runner_contract.get("prompt_contract", {})
        if prompt_contract.get("prompt_contract_version") != (
            "multiuav_prompt_contract_v1"
        ):
            errors.append("runner prompt contract version is not frozen")
        runner = runner_contract.get("runner_contract", {})
        if runner.get("method_call_counts") != {
            "M1_monolithic": 1,
            "M2_post_plan_deterministic": 1,
            "M3_stage_wise": 2,
            "M4_post_plan_compute_matched": 2,
        }:
            errors.append("runner call counts differ from the frozen methods")
        if runner.get("m3_second_call_always_required") is not True:
            errors.append("runner permits M3 to skip its second call")
        if runner.get("pending_human_review_allowed") is not False:
            errors.append("runner permits unreviewed cases")
        if runner.get("qwen_backend_implemented") is not True:
            errors.append("runner audit does not register the local Qwen backend")
        if runner.get("qwen_local_files_only_required") is not True:
            errors.append("runner audit does not require local-only Qwen loading")
        if runner.get("qwen_weights_loaded_by_this_audit") is not False:
            errors.append("runner contract audit unexpectedly loaded Qwen weights")
        if runner.get("accuracy_execution_cli_implemented") is not True:
            errors.append("runner audit does not register the accuracy execution CLI")
        if runner.get(
            "accuracy_preflight_validates_commit_data_cache_and_counts"
        ) is not True:
            errors.append("accuracy execution preflight is not fully registered")
        if runner.get("durable_row_progress_reporting") is not True:
            errors.append("runner audit does not register durable row progress")
        if runner.get("qwen_3b_synthetic_load_smoke_registered") is not True:
            errors.append("runner audit does not register the Qwen 3B smoke")
        if runner.get("qwen_7b_synthetic_load_smoke_registered") is not True:
            errors.append("runner audit does not register the Qwen 7B smoke")
        if runner.get("resource_measurement_unit") != "complete_method_case":
            errors.append("runner audit has the wrong resource measurement unit")
        if runner.get("resource_monitor_required_for_resource_runs") is not True:
            errors.append("runner audit does not require resource monitoring")
        checkpoint = runner_contract.get("checkpoint_contract", {})
        if checkpoint.get("row_written_after_each_method_case") is not True:
            errors.append("runner does not checkpoint every method-case row")
        if checkpoint.get("incompatible_resume_rejected") is not True:
            errors.append("runner does not reject incompatible resume")
        if checkpoint.get("matrix_completeness_check") is not True:
            errors.append("runner does not enforce complete result matrices")
        if checkpoint.get("schema_version") != 3:
            errors.append("runner checkpoint schema is not version 3")
        if checkpoint.get("resource_repetition_bound_in_config_hash") is not True:
            errors.append("runner does not bind resource repetition")
        if checkpoint.get("hardware_protocol_hash_bound_in_config_hash") is not True:
            errors.append("runner does not bind the hardware protocol")
        if checkpoint.get("resource_condition_order_bound_in_config_hash") is not True:
            errors.append("runner does not bind resource condition order")
        if checkpoint.get("resource_schedule_hash_bound_in_config_hash") is not True:
            errors.append("runner does not bind the resource schedule")
        publication_gate = runner_contract.get("publication_accuracy_gate", {})
        if publication_gate.get("accuracy_run_only") is not True:
            errors.append("publication gate permits non-accuracy runs")
        if publication_gate.get("approved_evaluation_cases_only") is not True:
            errors.append("publication gate permits unapproved cases")
        if publication_gate.get("complete_matrix_required") is not True:
            errors.append("publication gate permits incomplete matrices")
        if publication_gate.get("synthetic_and_resource_rows_rejected") is not True:
            errors.append("publication gate permits synthetic or resource rows")
        if publication_gate.get("parse_errors_retained") is not True:
            errors.append("publication gate drops parse errors")
        if publication_gate.get("study_rows_scored_by_this_audit") is not False:
            errors.append("runner audit unexpectedly scored study rows")
        if runner_contract.get("model_invoked_by_this_audit") is not False:
            errors.append("runner contract audit unexpectedly invoked a model")
        if runner_contract.get("weights_loaded_by_this_audit") is not False:
            errors.append("runner contract audit unexpectedly loaded weights")
        leakage = runner_contract.get("pilot_prompt_leakage_audit", {})
        if leakage.get("method_first_prompts_audited") != 600:
            errors.append("runner prompt leakage audit does not cover 600 prompts")
        if leakage.get("privileged_or_label_leak_count") != 0:
            errors.append("runner prompt leakage audit found privileged data")
        source_hashes = runner_contract.get("source_code_sha256", {})
        for filename in (
            "multiuav_prompts.py",
            "multiuav_ledger_contract.py",
            "multiuav_runner.py",
            "multiuav_checkpoints.py",
            "multiuav_experiment.py",
            "multiuav_resources.py",
            "multiuav_resource_schedule.py",
            "multiuav_publication.py",
            "multiuav_offline_runtime.py",
            "multiuav_qwen_backend.py",
        ):
            runner_source_path = (
                repository_root / "src" / "shepherd_ai" / filename
            )
            if runner_source_path.is_file() and source_hashes.get(
                filename
            ) != _sha256(runner_source_path):
                errors.append(
                    f"runner contract is not bound to source code: {filename}"
                )
        runner_audit_script = (
            repository_root
            / "scripts"
            / "audit_multiuav_runner_contract.py"
        )
        if runner_audit_script.is_file() and source_hashes.get(
            "audit_multiuav_runner_contract.py"
        ) != _sha256(runner_audit_script):
            errors.append("runner contract is not bound to its audit script")
        accuracy_run_script = repository_root / "scripts" / "run_multiuav_accuracy.py"
        if accuracy_run_script.is_file() and source_hashes.get(
            "run_multiuav_accuracy.py"
        ) != _sha256(accuracy_run_script):
            errors.append("runner contract is not bound to the accuracy execution CLI")
    if offline_runtime:
        if offline_runtime.get("valid") is not True:
            errors.append("offline runtime contract audit is not valid")
        if offline_runtime.get("weights_cached") is not False:
            errors.append("offline runtime audit unexpectedly claims cached weights")
        if offline_runtime.get("weights_loaded") is not False:
            errors.append("offline runtime audit unexpectedly claims loaded weights")
        if offline_runtime.get("model_invoked") is not False:
            errors.append("offline runtime audit unexpectedly invoked a model")
        if offline_runtime.get("study_cases_evaluated") is not False:
            errors.append("offline runtime audit unexpectedly evaluated study cases")
        offline_contract = offline_runtime.get("offline_contract", {})
        if offline_contract.get("local_files_only_required") is not True:
            errors.append("offline runtime does not require local-only loading")
        if offline_contract.get("non_loopback_blocked") is not True:
            errors.append("offline runtime does not block non-loopback sockets")
        if offline_contract.get("isolation_scope") != "python_process":
            errors.append("offline runtime isolation scope is not registered")
        observed_revisions = {
            str(item.get("model_id")): item.get("revision")
            for item in offline_runtime.get("backend_contracts", [])
            if isinstance(item, dict)
        }
        if observed_revisions != EXPECTED_MODEL_REVISIONS:
            errors.append("offline runtime model revisions differ from the registry")
        source_hashes = offline_runtime.get("source_code_sha256", {})
        offline_sources = {
            "multiuav_offline_runtime.py": (
                repository_root
                / "src"
                / "shepherd_ai"
                / "multiuav_offline_runtime.py"
            ),
            "multiuav_qwen_backend.py": (
                repository_root
                / "src"
                / "shepherd_ai"
                / "multiuav_qwen_backend.py"
            ),
            "audit_multiuav_offline_runtime.py": (
                repository_root
                / "scripts"
                / "audit_multiuav_offline_runtime.py"
            ),
        }
        for filename, offline_source_path in offline_sources.items():
            if offline_source_path.is_file() and source_hashes.get(
                filename
            ) != _sha256(offline_source_path):
                errors.append(
                    "offline runtime contract is not bound to source code: "
                    f"{filename}"
                )
    if qwen_3b_cache:
        if qwen_3b_cache.get("model_id") != "Qwen/Qwen2.5-3B-Instruct":
            errors.append("Qwen 3B cache audit has the wrong model id")
        if qwen_3b_cache.get("revision") != EXPECTED_MODEL_REVISIONS[
            "Qwen/Qwen2.5-3B-Instruct"
        ]:
            errors.append("Qwen 3B cache audit has the wrong revision")
        if qwen_3b_cache.get("weights_cached") is not True:
            errors.append("Qwen 3B cache audit does not confirm cached weights")
        if qwen_3b_cache.get("all_weights_safetensors") is not True:
            errors.append("Qwen 3B cache audit contains non-safetensors weights")
        _check_source_hashes(
            repository_root,
            qwen_3b_cache.get("source_code_sha256", {}),
            {
                "multiuav_model_cache.py": "src/shepherd_ai/multiuav_model_cache.py",
                "cache_multiuav_qwen.py": "scripts/cache_multiuav_qwen.py",
            },
            errors,
            label="Qwen 3B cache audit",
        )
    if qwen_3b_smoke:
        if qwen_3b_smoke.get("cache_audit_sha256") != _sha256(qwen_3b_cache_path):
            errors.append("Qwen 3B smoke is not bound to the cache audit")
        if qwen_3b_smoke.get("smoke_status") != "passed":
            errors.append("Qwen 3B synthetic load smoke did not pass")
        if qwen_3b_smoke.get("weights_loaded") is not True:
            errors.append("Qwen 3B smoke did not load weights")
        if qwen_3b_smoke.get("model_invoked") is not True:
            errors.append("Qwen 3B smoke did not invoke the model")
        if qwen_3b_smoke.get("study_cases_evaluated") is not False:
            errors.append("Qwen 3B smoke unexpectedly evaluated study cases")
        if qwen_3b_smoke.get("network_block_probe", {}).get("observed") != "blocked":
            errors.append("Qwen 3B smoke did not prove socket blocking")
        _check_source_hashes(
            repository_root,
            qwen_3b_smoke.get("source_code_sha256", {}),
            {
                "multiuav_model_cache.py": "src/shepherd_ai/multiuav_model_cache.py",
                "multiuav_offline_runtime.py": "src/shepherd_ai/multiuav_offline_runtime.py",
                "multiuav_qwen_backend.py": "src/shepherd_ai/multiuav_qwen_backend.py",
                "smoke_multiuav_qwen.py": "scripts/smoke_multiuav_qwen.py",
            },
            errors,
            label="Qwen 3B smoke",
        )
    if qwen_3b_failed_smoke:
        if qwen_3b_failed_smoke.get("smoke_status") != "failed":
            errors.append("preserved Qwen 3B failed attempt is not marked failed")
        if qwen_3b_failed_smoke.get("model_invoked") is not False:
            errors.append("failed Qwen 3B attempt unexpectedly invoked the model")
    if qwen_3b_historical_smoke:
        if qwen_3b_historical_smoke.get("smoke_status") != "passed":
            errors.append("historical Qwen 3B smoke is not marked passed")
        if qwen_3b_historical_smoke.get("study_cases_evaluated") is not False:
            errors.append("historical Qwen 3B smoke evaluated study cases")
    if qwen_7b_cache:
        if qwen_7b_cache.get("model_id") != "Qwen/Qwen2.5-7B-Instruct":
            errors.append("Qwen 7B cache audit has the wrong model id")
        if qwen_7b_cache.get("revision") != EXPECTED_MODEL_REVISIONS[
            "Qwen/Qwen2.5-7B-Instruct"
        ]:
            errors.append("Qwen 7B cache audit has the wrong revision")
        if qwen_7b_cache.get("weights_cached") is not True:
            errors.append("Qwen 7B cache audit does not confirm cached weights")
        if qwen_7b_cache.get("all_weights_safetensors") is not True:
            errors.append("Qwen 7B cache audit contains non-safetensors weights")
        _check_source_hashes(
            repository_root,
            qwen_7b_cache.get("source_code_sha256", {}),
            {
                "multiuav_model_cache.py": "src/shepherd_ai/multiuav_model_cache.py",
                "cache_multiuav_qwen.py": "scripts/cache_multiuav_qwen.py",
            },
            errors,
            label="Qwen 7B cache audit",
        )
    if qwen_7b_smoke:
        if qwen_7b_smoke.get("cache_audit_sha256") != _sha256(qwen_7b_cache_path):
            errors.append("Qwen 7B smoke is not bound to the cache audit")
        if qwen_7b_smoke.get("smoke_status") != "passed":
            errors.append("Qwen 7B synthetic load smoke did not pass")
        if qwen_7b_smoke.get("weights_loaded") is not True:
            errors.append("Qwen 7B smoke did not load weights")
        if qwen_7b_smoke.get("model_invoked") is not True:
            errors.append("Qwen 7B smoke did not invoke the model")
        if qwen_7b_smoke.get("study_cases_evaluated") is not False:
            errors.append("Qwen 7B smoke unexpectedly evaluated study cases")
        if qwen_7b_smoke.get("network_block_probe", {}).get("observed") != "blocked":
            errors.append("Qwen 7B smoke did not prove socket blocking")
        if qwen_7b_smoke.get("backend_config", {}).get("offload_folder") is None:
            errors.append("Qwen 7B smoke does not record its offload folder")
        _check_source_hashes(
            repository_root,
            qwen_7b_smoke.get("source_code_sha256", {}),
            {
                "multiuav_model_cache.py": "src/shepherd_ai/multiuav_model_cache.py",
                "multiuav_offline_runtime.py": "src/shepherd_ai/multiuav_offline_runtime.py",
                "multiuav_qwen_backend.py": "src/shepherd_ai/multiuav_qwen_backend.py",
                "smoke_multiuav_qwen.py": "scripts/smoke_multiuav_qwen.py",
            },
            errors,
            label="Qwen 7B smoke",
        )
    if execution_scope:
        if execution_scope.get("valid") is not True:
            errors.append("execution scope audit is not valid")
        if execution_scope.get("primary_scope") != "static_plan_fidelity":
            errors.append("execution scope is not static plan fidelity")
        if execution_scope.get("official_server_submission_in_primary_scope") is not False:
            errors.append("execution scope unexpectedly includes server submission")
        if execution_scope.get("official_server_invoked_by_this_audit") is not False:
            errors.append("execution scope audit unexpectedly invoked the server")
        _check_source_hashes(
            repository_root,
            execution_scope.get("source_code_sha256", {}),
            {
                "multiuav_execution_scope.py": "src/shepherd_ai/multiuav_execution_scope.py",
                "audit_multiuav_execution_scope.py": "scripts/audit_multiuav_execution_scope.py",
            },
            errors,
            label="execution scope audit",
        )
    if hardware_measurement:
        if hardware_measurement.get("valid") is not True:
            errors.append("hardware measurement contract audit is not valid")
        if hardware_measurement.get("measurement_unit") != "complete_method_case":
            errors.append("hardware measurement unit is not method-case")
        if hardware_measurement.get("synthetic_probe", {}).get("sample_target_hz") != 20.0:
            errors.append("hardware measurement target is not 20 Hz")
        if hardware_measurement.get("model_invoked") is not False:
            errors.append("hardware contract audit unexpectedly invoked a model")
        if hardware_measurement.get("study_cases_evaluated") is not False:
            errors.append("hardware contract audit evaluated study cases")
        _check_source_hashes(
            repository_root,
            hardware_measurement.get("source_code_sha256", {}),
            {
                "multiuav_resources.py": "src/shepherd_ai/multiuav_resources.py",
                "multiuav_experiment.py": "src/shepherd_ai/multiuav_experiment.py",
                "multiuav_runner.py": "src/shepherd_ai/multiuav_runner.py",
                "multiuav_checkpoints.py": "src/shepherd_ai/multiuav_checkpoints.py",
                "audit_multiuav_hardware_protocol.py": "scripts/audit_multiuav_hardware_protocol.py",
            },
            errors,
            label="hardware measurement audit",
        )
    if resource_schedule:
        summary = resource_schedule.get("summary", {})
        selection = resource_schedule.get("selection", {})
        condition_schedule = resource_schedule.get("condition_schedule", {})
        selected_tasks = selection.get("source_tasks", [])
        condition_rows = condition_schedule.get("rows", [])
        if resource_schedule.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE_SHA256:
            errors.append("resource schedule source archive does not match")
        if eligibility_path.is_file() and resource_schedule.get(
            "eligibility_sha256"
        ) != _sha256(eligibility_path):
            errors.append("resource schedule is not bound to task eligibility")
        if resource_schedule.get("claim_status") != (
            "candidate_source_subset_and_condition_order_only"
        ):
            errors.append("resource schedule claim status is not provisional")
        if resource_schedule.get("model_invocation", {}).get("performed") is not False:
            errors.append("resource schedule unexpectedly invoked a model")
        if summary.get("source_tasks") != 30 or len(selected_tasks) != 30:
            errors.append("resource schedule does not contain 30 source tasks")
        if summary.get("strata") != 15:
            errors.append("resource schedule does not contain 15 strata")
        if summary.get("conditions") != 24 or len(condition_rows) != 24:
            errors.append("resource schedule does not contain 24 conditions")
        if summary.get("planned_method_case_rows") != 3_600:
            errors.append("resource schedule row count is not 3,600")
        if any(
            row.get("split") != "test" or row.get("eligible") is not True
            for row in selected_tasks
        ):
            errors.append("resource schedule contains a non-eligible test task")
        if len({row.get("task_id") for row in selected_tasks}) != 30:
            errors.append("resource schedule source tasks are not unique")
        if set(selection.get("stratum_counts", {}).values()) != {2}:
            errors.append("resource schedule is not two tasks per stratum")
        expected_conditions = {
            (model_id, method_id, repetition)
            for model_id in EXPECTED_MODEL_REVISIONS
            for method_id in (
                "M1_monolithic",
                "M2_post_plan_deterministic",
                "M3_stage_wise",
                "M4_post_plan_compute_matched",
            )
            for repetition in (1, 2, 3)
        }
        observed_conditions = {
            (row.get("model_id"), row.get("method_id"), row.get("repetition"))
            for row in condition_rows
        }
        if observed_conditions != expected_conditions:
            errors.append("resource condition matrix is incomplete")
        _check_source_hashes(
            repository_root,
            resource_schedule.get("source_code_sha256", {}),
            {
                "multiuav_resource_schedule.py": (
                    "src/shepherd_ai/multiuav_resource_schedule.py"
                ),
                "build_multiuav_resource_schedule.py": (
                    "scripts/build_multiuav_resource_schedule.py"
                ),
            },
            errors,
            label="resource schedule",
        )
    if resource_hardware_protocol:
        if resource_hardware_protocol.get("status") != (
            "final_resource_hardware_protocol_no_measurement_started"
        ):
            errors.append("resource hardware protocol is not final")
        hardware = resource_hardware_protocol.get("hardware", {})
        measurement = resource_hardware_protocol.get("measurement", {})
        start_control = resource_hardware_protocol.get("start_control", {})
        if hardware.get("required_runtime_gpu_name") != (
            "NVIDIA GeForce RTX 3090"
        ):
            errors.append("resource hardware protocol GPU is not RTX 3090")
        if hardware.get("required_gpu_compute_processes") != 1 or hardware.get(
            "maximum_gpu_compute_processes"
        ) != 1:
            errors.append("resource GPU process isolation is not frozen")
        if measurement.get("sample_target_hz") != 20.0:
            errors.append("resource measurement target is not 20 Hz")
        if start_control.get("baseline_samples") != 5 or start_control.get(
            "post_warmup_consecutive_idle_samples"
        ) != 15:
            errors.append("resource warm-up and thermal controls are incomplete")
    if resource_final_schedule:
        expected = resource_final_schedule.get("expected", {})
        bindings = resource_final_schedule.get("artifact_bindings", {})
        if resource_final_schedule.get("status") != (
            "final_resource_schedule_bound_no_measurement_started"
        ):
            errors.append("final resource schedule status is invalid")
        if expected.get("conditions") != 24 or expected.get(
            "total_method_case_rows"
        ) != 3_600:
            errors.append("final resource schedule dimensions are invalid")
        if resource_hardware_protocol_path.is_file() and bindings.get(
            "hardware_protocol_sha256"
        ) != _sha256(resource_hardware_protocol_path):
            errors.append("resource schedule hardware binding differs")
        if accuracy_manifest_path.is_file() and bindings.get(
            "accuracy_manifest_sha256"
        ) != _sha256(accuracy_manifest_path):
            errors.append("resource schedule manifest binding differs")
        if intervention_dataset_path.is_file() and bindings.get(
            "intervention_dataset_sha256"
        ) != _sha256(intervention_dataset_path):
            errors.append("resource schedule dataset binding differs")

    completed_gates = [
        "pinned_source_integrity",
        "session_split",
        "task_eligibility",
        "official_alias_selection",
        "agent_visible_context_projection",
        "recoverability_rule",
        "training_pilot_generation",
        "training_pilot_deterministic_validation",
        "training_pilot_structural_review_validation",
        "full_intervention_dataset_generation_and_deterministic_validation",
        "stratified_expert_construction_qc",
        "score_blind_accuracy_protocol_registration",
        "heldout_accuracy_case_manifest_approval",
        "deterministic_label_separated_scoring_contract",
        "method_call_budget",
        "strict_structural_output_contract",
        "deterministic_recursive_grounding_validator",
        "immutable_qwen_checkpoint_resolution",
        "method_runners_and_prompts",
        "commit_bound_accuracy_execution_cli",
        "row_checkpoint_resume_contract",
        "local_qwen_backend_and_process_socket_isolation_contract",
        "qwen_3b_cached_checksums_and_synthetic_load_smoke",
        "qwen_7b_cached_checksums_and_synthetic_load_smoke",
        "static_plan_fidelity_execution_scope",
        "method_case_hardware_measurement_instrumentation",
        "resource_candidate_subset_and_condition_order",
        "resource_run_config_builder_with_approval_gate",
        "resource_approved_subset_and_case_order",
        "resource_hardware_warmup_thermal_and_process_controls",
        "publication_accuracy_smoke_leak_gate",
    ]
    if excluded_local_attempt_registered:
        completed_gates.append("excluded_local_feasibility_attempt_preserved")
    if resource_config_ready:
        completed_gates.append("resource_commit_bound_run_configs")
    accuracy_blocking_gates = (
        [] if accuracy_config_ready else ["final_accuracy_run_config_commit_binding"]
    )
    resource_blocking_gates = [
        *([] if resource_config_ready else ["resource_run_configs_commit_binding"]),
        "resource_cluster_preflight",
    ]
    blocking_gates = [*accuracy_blocking_gates, *resource_blocking_gates]
    return {
        "study_id": STUDY_ID,
        "active_branch": ACTIVE_BRANCH,
        "valid": not errors,
        "errors": errors,
        "status": (
            "ready_for_accuracy_model_inference"
            if not errors and accuracy_config_ready
            else "accuracy_manifest_approved_final_commit_binding_pending"
            if not errors
            else "invalid_completed_gate_wiring"
        ),
        "completed_gates": completed_gates,
        "blocking_gates": blocking_gates,
        "primary_path": {
            "input_modality": "text",
            "source_adapter": "multiuav_plat_pinned_source_v1",
            "dataset": "approved_test_manifest_284_clusters_1420_cases",
            "model_family": "Qwen2.5-3B_and_7B_synthetic_smokes_passed",
            "model_revisions": EXPECTED_MODEL_REVISIONS,
            "methods": ["M1", "M2", "M3", "M4"],
            "api_plan_parser": "strict_multiuav_json_contract_v1",
            "deterministic_validator": (
                "recursive_visible_evidence_grounding_v1"
            ),
            "method_runner": "provider_independent_m1_m4_runner_v1",
            "model_backend": "local_qwen_3b_and_7b_synthetic_smokes_passed",
            "checkpoint_writer": "config_bound_jsonl_and_compact_zip_v1",
            "accuracy_scorer": "multiuav_accuracy_scoring_v1",
            "accuracy_execution_cli": "commit_bound_accuracy_matrix_runner_v1",
            "execution_backend": "static_plan_fidelity_only",
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
            "qwen_invoked": True,
            "qwen_invocation_scope": (
                "synthetic_fixture_and_excluded_local_feasibility_attempt"
                if excluded_local_attempt_registered
                else "synthetic_fixture_only"
            ),
            "qwen_study_cases_evaluated": excluded_local_attempt_registered,
            "qwen_study_rows_evaluated": (
                1 if excluded_local_attempt_registered else 0
            ),
        },
        "ready_for_intervention_generation": not errors,
        "ready_for_human_review": False,
        "expert_qc_complete": not errors,
        "ready_for_accuracy_run_config_binding": not errors,
        "ready_for_model_inference": not errors and accuracy_config_ready,
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
            "intervention_pilot": _artifact_record(
                pilot_dataset_path, repository_root
            ),
            "intervention_pilot_summary": _artifact_record(
                pilot_summary_path, repository_root
            ),
            "intervention_pilot_validation": _artifact_record(
                pilot_validation_path, repository_root
            ),
            "intervention_validator_negative_controls": _artifact_record(
                intervention_negative_controls_path, repository_root
            ),
            "intervention_pilot_review_packet": _artifact_record(
                pilot_review_path, repository_root
            ),
            "completed_intervention_pilot_review_packet": _artifact_record(
                completed_pilot_review_path, repository_root
            ),
            "completed_intervention_pilot_review_validation": _artifact_record(
                completed_pilot_review_validation_path, repository_root
            ),
            "intervention_pilot_review_normalization": _artifact_record(
                pilot_review_normalization_path, repository_root
            ),
            "intervention_dataset": _artifact_record(
                intervention_dataset_path, repository_root
            ),
            "intervention_dataset_summary": _artifact_record(
                intervention_dataset_summary_path, repository_root
            ),
            "intervention_dataset_validation": _artifact_record(
                intervention_dataset_validation_path, repository_root
            ),
            "intervention_review_packet": _artifact_record(
                intervention_review_path, repository_root
            ),
            "expert_qc_audit": _artifact_record(
                expert_qc_path, repository_root
            ),
            "accuracy_protocol_freeze": _artifact_record(
                accuracy_protocol_path, repository_root
            ),
            "accuracy_case_manifest": _artifact_record(
                accuracy_manifest_path, repository_root
            ),
            "scoring_contract_audit": _artifact_record(
                scoring_contract_path, repository_root
            ),
            "accuracy_run_configs": _artifact_record(
                accuracy_run_configs_path, repository_root
            ),
            "excluded_local_accuracy_attempt_summary": _artifact_record(
                excluded_local_attempt_summary_path, repository_root
            ),
            "excluded_local_accuracy_attempt_results": _artifact_record(
                excluded_local_attempt_results_path, repository_root
            ),
            "excluded_local_accuracy_attempt_config": _artifact_record(
                excluded_local_attempt_config_path, repository_root
            ),
            "excluded_local_accuracy_attempt_stderr": _artifact_record(
                excluded_local_attempt_stderr_path, repository_root
            ),
            "method_contract_audit": _artifact_record(
                method_contract_path, repository_root
            ),
            "grounding_contract_audit": _artifact_record(
                grounding_contract_path, repository_root
            ),
            "model_revision_audit": _artifact_record(
                model_revision_path, repository_root
            ),
            "runner_contract_audit": _artifact_record(
                runner_contract_path, repository_root
            ),
            "offline_runtime_contract_audit": _artifact_record(
                offline_runtime_path, repository_root
            ),
            "qwen_3b_cache_audit": _artifact_record(
                qwen_3b_cache_path, repository_root
            ),
            "qwen_3b_load_smoke": _artifact_record(
                qwen_3b_smoke_path, repository_root
            ),
            "qwen_3b_failed_load_smoke": _artifact_record(
                qwen_3b_failed_smoke_path, repository_root
            ),
            "qwen_3b_historical_load_smoke": _artifact_record(
                qwen_3b_historical_smoke_path, repository_root
            ),
            "qwen_7b_cache_audit": _artifact_record(
                qwen_7b_cache_path, repository_root
            ),
            "qwen_7b_load_smoke": _artifact_record(
                qwen_7b_smoke_path, repository_root
            ),
            "execution_scope_audit": _artifact_record(
                execution_scope_path, repository_root
            ),
            "hardware_measurement_contract_audit": _artifact_record(
                hardware_measurement_path, repository_root
            ),
            "resource_schedule_candidate": _artifact_record(
                resource_schedule_path, repository_root
            ),
            "resource_hardware_protocol": _artifact_record(
                resource_hardware_protocol_path, repository_root
            ),
            "resource_final_schedule": _artifact_record(
                resource_final_schedule_path, repository_root
            ),
            "resource_run_configs": _artifact_record(
                resource_run_configs_path, repository_root
            ),
            "historical_distilbert_wiring_smoke": _artifact_record(
                distilbert_smoke_path, repository_root
            ),
        },
        "claim_status": (
            "accuracy_execution_ready_after_excluded_local_feasibility_attempt"
            if not errors and accuracy_config_ready and excluded_local_attempt_registered
            else "accuracy_execution_ready_no_study_inference"
            if not errors and accuracy_config_ready
            else "expert_qc_protocol_manifest_and_scoring_contract_complete_"
            "final_commit_binding_pending"
        ),
        "accuracy_blocking_gates": accuracy_blocking_gates,
        "resource_blocking_gates": resource_blocking_gates,
    }


def _check_source_hashes(
    repository_root: Path,
    observed: dict[str, Any],
    expected_paths: dict[str, str],
    errors: list[str],
    *,
    label: str,
) -> None:
    for name, relative in expected_paths.items():
        path = repository_root / relative
        if path.is_file() and observed.get(name) != _sha256(path):
            errors.append(f"{label} is not bound to source code: {name}")


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


def _read_optional_object(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return _read_object(path, errors)


def _validate_accuracy_run_configs(
    artifact: dict[str, Any],
    *,
    accuracy_run_configs_path: Path,
    accuracy_manifest_path: Path,
    accuracy_protocol_path: Path,
    errors: list[str],
) -> bool:
    if not accuracy_run_configs_path.is_file():
        return False
    if not artifact:
        return False
    initial_error_count = len(errors)
    if artifact.get("status") != "final_accuracy_configs_bound_no_inference_started":
        errors.append("accuracy run configs are not in the final pre-inference state")
    if accuracy_manifest_path.is_file() and artifact.get(
        "accuracy_manifest_sha256"
    ) != _sha256(accuracy_manifest_path):
        errors.append("accuracy run configs are not bound to the accuracy manifest")
    if accuracy_protocol_path.is_file() and artifact.get(
        "protocol_freeze_sha256"
    ) != _sha256(accuracy_protocol_path):
        errors.append("accuracy run configs are not bound to the frozen protocol")
    if artifact.get("expected_rows_per_model") != 5_680:
        errors.append("accuracy run configs have the wrong per-model row count")
    if artifact.get("expected_rows_total") != 11_360:
        errors.append("accuracy run configs have the wrong total row count")
    code_commit = artifact.get("code_commit")
    records = artifact.get("configs")
    if not isinstance(records, list) or len(records) != 2:
        errors.append("accuracy run configs must contain exactly two model configs")
        return False
    observed_models: set[str] = set()
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict) or not isinstance(record.get("config"), dict):
                raise ValueError("config record must contain an object payload")
            payload = dict(record["config"])
            payload["methods"] = tuple(payload["methods"])
            config = RunConfig(**payload)
            if config.to_dict() != record:
                raise ValueError("stored config hash or payload is invalid")
            if config.code_commit != code_commit:
                raise ValueError("model config commit differs from artifact commit")
            if config.run_kind != "accuracy":
                raise ValueError("model config is not an accuracy run")
            if config.methods != (
                "M1_monolithic",
                "M2_post_plan_deterministic",
                "M3_stage_wise",
                "M4_post_plan_compute_matched",
            ):
                raise ValueError("model config method order differs from the protocol")
            observed_models.add(config.model_id)
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"invalid accuracy run config {index}: {error}")
    if observed_models != set(EXPECTED_MODEL_REVISIONS):
        errors.append("accuracy run configs do not cover both frozen Qwen models")
    return len(errors) == initial_error_count


def _validate_resource_run_configs(
    artifact: dict[str, Any],
    *,
    resource_run_configs_path: Path,
    resource_schedule_path: Path,
    resource_hardware_protocol_path: Path,
    accuracy_manifest_path: Path,
    intervention_dataset_path: Path,
    errors: list[str],
) -> bool:
    if not resource_run_configs_path.is_file() or not artifact:
        return False
    initial_error_count = len(errors)
    if artifact.get("status") != (
        "final_resource_configs_bound_no_measurement_started"
    ):
        errors.append("resource run configs are not in the final pre-measurement state")
    bindings = (
        ("resource_schedule_sha256", resource_schedule_path),
        ("hardware_protocol_sha256", resource_hardware_protocol_path),
        ("accuracy_manifest_sha256", accuracy_manifest_path),
        ("intervention_dataset_sha256", intervention_dataset_path),
    )
    for key, path in bindings:
        if path.is_file() and artifact.get(key) != _sha256(path):
            errors.append(f"resource run configs have a mismatched binding: {key}")
    if artifact.get("expected_conditions") != 24:
        errors.append("resource run configs do not contain 24 conditions")
    if artifact.get("expected_rows_total") != 3_600:
        errors.append("resource run configs do not bind 3,600 rows")
    code_commit = artifact.get("code_commit")
    records = artifact.get("configs")
    if not isinstance(records, list) or len(records) != 24:
        errors.append("resource run configs must contain exactly 24 configs")
        return False
    observed: set[tuple[str, str, int]] = set()
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict) or not isinstance(record.get("config"), dict):
                raise ValueError("config record must contain an object payload")
            payload = dict(record["config"])
            payload["methods"] = tuple(payload["methods"])
            config = RunConfig(**payload)
            if config.to_dict() != record:
                raise ValueError("stored config hash or payload is invalid")
            if config.code_commit != code_commit or config.run_kind != "resource":
                raise ValueError("resource config commit or run kind differs")
            observed.add(
                (config.model_id, config.methods[0], int(config.resource_repetition))
            )
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"invalid resource run config {index}: {error}")
    expected = {
        (model_id, method_id, repetition)
        for model_id in EXPECTED_MODEL_REVISIONS
        for method_id in (
            "M1_monolithic",
            "M2_post_plan_deterministic",
            "M3_stage_wise",
            "M4_post_plan_compute_matched",
        )
        for repetition in (1, 2, 3)
    }
    if observed != expected:
        errors.append("resource run configs do not cover the frozen condition matrix")
    return len(errors) == initial_error_count


def _validate_excluded_local_attempt(
    summary: dict[str, Any],
    *,
    results_path: Path,
    config_path: Path,
    stderr_path: Path,
    errors: list[str],
) -> bool:
    if not summary:
        return False
    initial_error_count = len(errors)
    if summary.get("status") != (
        "accuracy_run_aborted_feasibility_attempt_raw_results_unscored"
    ):
        errors.append("excluded local attempt has the wrong status")
    if summary.get("study_inference_started") is not True:
        errors.append("excluded local attempt does not record study inference")
    if summary.get("completed_rows") != 1:
        errors.append("excluded local attempt must contain exactly one durable row")
    if summary.get("scores_inspected") is not False:
        errors.append("excluded local attempt reports score inspection")
    if not summary.get("protocol_deviation"):
        errors.append("excluded local attempt omits the protocol deviation")
    for label, path, field in (
        ("results", results_path, "results_sha256"),
        ("run config", config_path, "run_config_sha256"),
        ("stderr", stderr_path, "stderr_sha256"),
    ):
        if not path.is_file():
            errors.append(f"excluded local attempt is missing {label}")
        elif summary.get(field) != _sha256(path):
            errors.append(f"excluded local attempt {label} hash differs")
    return len(errors) == initial_error_count


def _artifact_record(path: Path, repository_root: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(repository_root.resolve()).as_posix(),
        "sha256": _sha256(path) if path.is_file() else None,
        "exists": path.is_file(),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
