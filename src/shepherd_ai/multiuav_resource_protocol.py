"""Frozen subset and execution controls for the MultiUAV resource study."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from shepherd_ai.multiuav_evaluation_data import (
    APPROVED_CASE_STATUS,
    APPROVED_EVALUATION_DATA_STATUS,
)
from shepherd_ai.multiuav_interventions import VARIANTS
from shepherd_ai.multiuav_methods import METHOD_SPECS
from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS
from shepherd_ai.multiuav_resource_schedule import RESOURCE_REPETITIONS


RESOURCE_PROTOCOL_VERSION = "multiuav_resource_hardware_protocol_v1"
RESOURCE_SCHEDULE_VERSION = "multiuav_resource_schedule_v1"
RESOURCE_CASE_ORDER_SEED = "shepherd-multiuav-resource-case-order-v1"
EXPECTED_SOURCE_TASKS = 30
EXPECTED_CASES = 150
EXPECTED_CONDITIONS = 24
EXPECTED_ROWS = 3_600


def build_resource_hardware_protocol() -> dict[str, Any]:
    """Return the final resource controls without running a measurement."""

    return {
        "schema_version": 1,
        "protocol_version": RESOURCE_PROTOCOL_VERSION,
        "status": "final_resource_hardware_protocol_no_measurement_started",
        "claim_status": "registered_controls_only_not_resource_results",
        "measurement_started": False,
        "hardware": {
            "kubernetes_gpu_product": "NVIDIA-GeForce-RTX-3090",
            "required_runtime_gpu_name": "NVIDIA GeForce RTX 3090",
            "required_gpu_count": 1,
            "minimum_total_memory_bytes": 24_000_000_000,
            "same_node_and_gpu_uuid_for_all_conditions": True,
            "foreign_gpu_compute_processes_allowed": False,
            "required_gpu_compute_processes": 1,
            "maximum_gpu_compute_processes": 1,
            "container_image": "pytorch/pytorch:2.7.1-cuda11.8-cudnn9-runtime",
            "cuda_runtime": "11.8",
        },
        "backend": {
            "dtype": "float16",
            "device_map": "auto",
            "offload_folder": None,
            "local_files_only": True,
            "do_sample": False,
            "num_beams": 1,
            "max_new_tokens": 512,
            "models": [
                {"model_id": item.model_id, "revision": item.revision}
                for item in REGISTERED_MODEL_REVISIONS
            ],
        },
        "runtime_packages": {
            "python": "3.11",
            "torch": "2.7.1+cu118",
            "transformers": "4.57.6",
            "accelerate": "1.14.0",
            "huggingface-hub": "0.36.2",
            "safetensors": "0.8.0",
            "nvidia-ml-py": "13.610.43",
            "psutil": "7.2.0",
        },
        "measurement": {
            "unit": "complete_method_case",
            "sample_target_hz": 20.0,
            "minimum_observed_sample_hz": 15.0,
            "energy_primary": "nvml_total_energy_counter_millijoules",
            "energy_fallback": "nvml_power_trapezoidal_integration",
            "energy_scope": "nvidia_gpu_board_only",
            "model_load_included": False,
            "warmup_included": False,
            "idle_wait_included": False,
        },
        "start_control": {
            "baseline_samples": 5,
            "baseline_sample_interval_seconds": 1.0,
            "maximum_baseline_temperature_celsius": 60,
            "warmup_complete_method_cases_per_condition_segment": 1,
            "warmup_output_retained": False,
            "post_warmup_consecutive_idle_samples": 15,
            "idle_sample_interval_seconds": 1.0,
            "maximum_gpu_utilization_percent": 5,
            "maximum_temperature_above_baseline_celsius": 2,
            "maximum_post_warmup_temperature_celsius": 60,
            "idle_timeout_seconds": 600,
        },
        "execution": {
            "source_task_clusters": EXPECTED_SOURCE_TASKS,
            "variants_per_cluster": len(VARIANTS),
            "method_case_rows_per_condition": EXPECTED_CASES,
            "models": len(REGISTERED_MODEL_REVISIONS),
            "methods": len(METHOD_SPECS),
            "repetitions": len(RESOURCE_REPETITIONS),
            "conditions": EXPECTED_CONDITIONS,
            "expected_rows": EXPECTED_ROWS,
            "condition_process_isolation": "one_model_method_condition_per_process",
            "case_order": "fixed_per_repetition_shared_across_conditions",
            "between_case_cooldown": False,
        },
        "failure_policy": {
            "raw_partial_rows_preserved": True,
            "invalid_measurement_rows_preserved": True,
            "condition_valid_only_if_all_150_rows_valid": True,
            "hardware_identity_drift_invalidates_attempt": True,
            "resume_requires_same_node_and_gpu_uuid": True,
            "every_resumed_process_repeats_warmup_and_idle_control": True,
            "publication_summary_excludes_invalid_conditions": True,
            "invalid_condition_rerun_uses_new_attempt_directory": True,
        },
        "analysis_policy": {
            "case_metrics_aggregate_within_source_task_cluster": True,
            "five_variants_treated_as_dependent": True,
            "three_repetition_estimates_reported_separately": True,
            "accuracy_rows_mixed_with_resource_rows": False,
        },
        "limitations": [
            "GPU-board energy is not total workstation, network, simulator, or UAV energy.",
            "The RTX 3090 result is hardware-specific and does not establish general deployment cost.",
            "M4 is model-call-count matched, not guaranteed latency, memory, token, or energy matched.",
            "These controls do not make static plan fidelity equivalent to live mission success.",
        ],
    }


def finalize_resource_schedule(
    *,
    candidate: Mapping[str, Any],
    accuracy_manifest: Mapping[str, Any],
    candidate_sha256: str,
    accuracy_manifest_sha256: str,
    intervention_dataset_sha256: str,
    hardware_protocol_sha256: str,
) -> dict[str, Any]:
    """Bind the provisional selection to complete approved five-case clusters."""

    if candidate.get("claim_status") != "candidate_source_subset_and_condition_order_only":
        raise ValueError("resource candidate status is not provisional")
    if accuracy_manifest.get("data_status") != APPROVED_EVALUATION_DATA_STATUS:
        raise ValueError("resource schedule requires approved evaluation data")
    source_records = candidate.get("selection", {}).get("source_tasks")
    if not isinstance(source_records, Sequence) or isinstance(
        source_records, (str, bytes)
    ):
        raise ValueError("resource candidate source tasks are absent")
    if len(source_records) != EXPECTED_SOURCE_TASKS:
        raise ValueError("resource candidate must contain 30 source tasks")
    selected_ids = [str(row.get("task_id", "")) for row in source_records]
    if not all(selected_ids) or len(set(selected_ids)) != EXPECTED_SOURCE_TASKS:
        raise ValueError("resource candidate source task ids are invalid")

    manifest_rows = accuracy_manifest.get("cases")
    if not isinstance(manifest_rows, Sequence) or isinstance(
        manifest_rows, (str, bytes)
    ):
        raise ValueError("accuracy manifest case rows are absent")
    selected_cases = [
        dict(row)
        for row in manifest_rows
        if str(row.get("source_task_id", "")) in set(selected_ids)
    ]
    if len(selected_cases) != EXPECTED_CASES:
        raise ValueError("resource subset is not covered by 150 approved cases")
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in selected_cases:
        source_task_id = str(row.get("source_task_id", ""))
        by_source.setdefault(source_task_id, []).append(row)
        if row.get("case_status") != APPROVED_CASE_STATUS:
            raise ValueError(f"resource case is not approved: {row.get('case_id')}")
        if row.get("split") != "test":
            raise ValueError(f"resource case is not held out: {row.get('case_id')}")
    if set(by_source) != set(selected_ids):
        raise ValueError("resource candidate is not fully covered by the manifest")
    for source_task_id, rows in by_source.items():
        if len(rows) != len(VARIANTS) or {
            str(row.get("variant", "")) for row in rows
        } != set(VARIANTS):
            raise ValueError(f"resource source cluster is incomplete: {source_task_id}")

    condition_rows = candidate.get("condition_schedule", {}).get("rows")
    if not isinstance(condition_rows, Sequence) or isinstance(
        condition_rows, (str, bytes)
    ):
        raise ValueError("resource condition schedule is absent")
    _validate_conditions(condition_rows)

    case_orders: list[dict[str, Any]] = []
    warmup_cases: list[dict[str, Any]] = []
    for repetition in RESOURCE_REPETITIONS:
        ranked = sorted(
            selected_cases,
            key=lambda row: (
                _case_rank(repetition, str(row["case_id"])),
                str(row["case_id"]),
            ),
        )
        for order, row in enumerate(ranked, start=1):
            case_orders.append(
                {
                    "repetition": repetition,
                    "case_order": order,
                    "case_id": str(row["case_id"]),
                    "cluster_id": str(row["cluster_id"]),
                    "source_task_id": str(row["source_task_id"]),
                    "variant": str(row["variant"]),
                    "order_rank_sha256": _case_rank(
                        repetition, str(row["case_id"])
                    ),
                }
            )
        warmup_cases.append(
            {
                "repetition": repetition,
                "case_id": str(ranked[0]["case_id"]),
                "selection": "first_case_in_frozen_repetition_order",
                "measured_later_in_condition": True,
                "warmup_output_retained": False,
            }
        )

    return {
        "schema_version": 1,
        "schedule_version": RESOURCE_SCHEDULE_VERSION,
        "status": "final_resource_schedule_bound_no_measurement_started",
        "claim_status": "registered_resource_subset_and_order_not_results",
        "measurement_started": False,
        "artifact_bindings": {
            "candidate_sha256": candidate_sha256,
            "accuracy_manifest_sha256": accuracy_manifest_sha256,
            "intervention_dataset_sha256": intervention_dataset_sha256,
            "hardware_protocol_sha256": hardware_protocol_sha256,
        },
        "selection": {
            "source_tasks": [dict(row) for row in source_records],
            "source_task_count": EXPECTED_SOURCE_TASKS,
            "case_count": EXPECTED_CASES,
            "cases_per_cluster": len(VARIANTS),
            "strata": 15,
            "source_tasks_per_stratum": 2,
        },
        "condition_schedule": {
            "rows": [dict(row) for row in condition_rows],
            "conditions": EXPECTED_CONDITIONS,
        },
        "case_schedule": {
            "seed": RESOURCE_CASE_ORDER_SEED,
            "strategy": "sha256_rank_by_repetition_shared_across_conditions",
            "rows": case_orders,
            "warmup_cases": warmup_cases,
        },
        "expected": {
            "models": len(REGISTERED_MODEL_REVISIONS),
            "methods": len(METHOD_SPECS),
            "repetitions": len(RESOURCE_REPETITIONS),
            "conditions": EXPECTED_CONDITIONS,
            "method_case_rows_per_condition": EXPECTED_CASES,
            "total_method_case_rows": EXPECTED_ROWS,
        },
        "model_invocation": {"performed": False, "study_cases_used": False},
        "hidden_fields_in_schedule": False,
        "limitations": [
            "This artifact is a final execution schedule, not a resource result.",
            "Registered decisions and official reference plans are absent from the schedule.",
            "Every condition still requires a valid start-control report before measurement.",
        ],
    }


def _validate_conditions(rows: Sequence[Any]) -> None:
    if len(rows) != EXPECTED_CONDITIONS:
        raise ValueError("resource schedule must contain 24 conditions")
    expected_models = {item.model_id for item in REGISTERED_MODEL_REVISIONS}
    expected_methods = {item.method_id for item in METHOD_SPECS}
    observed: set[tuple[str, str, int]] = set()
    orders: dict[int, set[int]] = {}
    for value in rows:
        if not isinstance(value, Mapping):
            raise ValueError("resource condition row is malformed")
        model_id = str(value.get("model_id", ""))
        method_id = str(value.get("method_id", ""))
        repetition = int(value.get("repetition", 0))
        condition_order = int(value.get("condition_order", 0))
        if model_id not in expected_models or method_id not in expected_methods:
            raise ValueError("resource condition uses an unregistered model or method")
        if repetition not in RESOURCE_REPETITIONS:
            raise ValueError("resource condition repetition is invalid")
        key = (model_id, method_id, repetition)
        if key in observed:
            raise ValueError("resource condition is duplicated")
        observed.add(key)
        orders.setdefault(repetition, set()).add(condition_order)
    if any(value != set(range(1, 9)) for value in orders.values()):
        raise ValueError("resource condition order is incomplete")


def _case_rank(repetition: int, case_id: str) -> str:
    value = f"{RESOURCE_CASE_ORDER_SEED}\0{repetition}\0{case_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
