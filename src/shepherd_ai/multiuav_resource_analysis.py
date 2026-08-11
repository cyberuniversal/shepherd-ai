"""Registered secondary resource analysis for admitted MultiUAV measurements."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import tarfile
from typing import Any
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from shepherd_ai.multiuav_statistics import paired_cluster_bootstrap
from shepherd_ai.multiuav_study_analysis import write_bootstrap_evidence_archive


ANALYSIS_VERSION = "multiuav_resource_analysis_v1"
_ADMISSION_STATUS = "complete_resource_campaign_admitted_for_analysis"
_ADMISSION_GATE = "registered_resource_analysis_authorized_not_started"
_FREEZE_STATUS = (
    "post_execution_binding_of_registered_resource_policy_before_aggregate_inspection"
)
_CHECKPOINT_MEMBERS = frozenset(
    {"manifest.json", "results.jsonl", "run_config.json"}
)
_METHODS = frozenset(
    {
        "M1_monolithic",
        "M2_post_plan_deterministic",
        "M3_stage_wise",
        "M4_post_plan_compute_matched",
    }
)
_VARIANTS = frozenset(
    {
        "canonical_execute",
        "official_alias_execute",
        "missing_information_clarify",
        "restored_information_execute",
        "resource_conflict_block",
    }
)
_METRIC_FIELDS = (
    "method_case_duration_seconds",
    "input_tokens",
    "output_tokens",
    "model_call_count",
    "process_ram_peak_bytes",
    "board_vram_peak_bytes",
    "process_vram_peak_bytes",
    "gpu_board_energy_joules",
    "gpu_utilization_peak_percent",
    "temperature_peak_celsius",
)
_DERIVED_ID_FIELDS = (
    "schema_version",
    "repetition",
    "condition_order",
    "model_id",
    "model_revision",
    "method_id",
    "case_id",
    "cluster_id",
    "source_task_id",
    "case_variant",
    "config_hash",
    "result_key",
)
_DERIVED_FIELDS = frozenset((*_DERIVED_ID_FIELDS, *_METRIC_FIELDS))
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "raw_output",
        "request",
        "messages",
        "prompt",
        "response",
        "text",
        "instruction",
        "api_plan",
        "final_parse",
        "intermediate_ledger",
        "preplan_report",
        "deterministic_postplan_report",
    }
)


def analyze_admitted_resource_campaign(
    *,
    repository_root: Path,
    admission_path: Path,
    analysis_freeze_path: Path,
    deviation_path: Path,
    archive_path: Path,
    resource_schedule_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Derive and analyze resource metrics without accessing output fields."""

    repository_root = repository_root.resolve()
    admission_path = admission_path.resolve()
    analysis_freeze_path = analysis_freeze_path.resolve()
    deviation_path = deviation_path.resolve()
    archive_path = archive_path.resolve()
    resource_schedule_path = resource_schedule_path.resolve()
    output_dir = output_dir.resolve()
    admission = _read_object(admission_path)
    analysis_spec = _read_object(analysis_freeze_path)
    deviation = _read_object(deviation_path)
    schedule = _read_object(resource_schedule_path)
    validate_resource_analysis_boundary(admission)
    _validate_analysis_freeze(
        analysis_spec,
        repository_root=repository_root,
        admission_path=admission_path,
        schedule_path=resource_schedule_path,
        deviation_path=deviation_path,
    )
    _validate_deviation(deviation)
    archive_binding = admission.get("artifact_bindings")
    if not isinstance(archive_binding, Mapping) or archive_binding.get(
        "archive_sha256"
    ) != _sha256_file(archive_path):
        raise ValueError("resource archive differs from admission")
    schedule_binding = analysis_spec.get("artifact_bindings")
    if not isinstance(schedule_binding, Mapping) or schedule_binding.get(
        "resource_schedule_sha256"
    ) != _sha256_file(resource_schedule_path):
        raise ValueError("resource schedule differs from analysis freeze")

    schedule_cases = _schedule_cases(schedule)
    conditions = admission.get("condition_admissions")
    if not isinstance(conditions, list) or len(conditions) != 24:
        raise ValueError("resource condition admissions are incomplete")
    root = str(admission.get("archive_integrity", {}).get("root", ""))
    if not root:
        raise ValueError("resource campaign archive root is absent")
    derived_rows: list[dict[str, Any]] = []
    try:
        with tarfile.open(archive_path, mode="r:gz") as campaign:
            for condition in sorted(
                conditions,
                key=lambda row: (
                    int(row["repetition"]),
                    int(row["condition_order"]),
                ),
            ):
                repetition = int(condition["repetition"])
                condition_order = int(condition["condition_order"])
                checkpoint_name = (
                    f"{root}/r{repetition}-o{condition_order}/checkpoint.zip"
                )
                checkpoint = _read_tar_bytes(campaign, checkpoint_name)
                if hashlib.sha256(checkpoint).hexdigest() != condition.get(
                    "checkpoint_sha256"
                ):
                    raise ValueError("resource checkpoint differs from admission")
                rows, results_sha256 = _load_checkpoint_rows(checkpoint)
                if results_sha256 != condition.get("results_sha256"):
                    raise ValueError("resource result rows differ from admission")
                for row in rows:
                    case_id = str(row.get("case_id", ""))
                    case = schedule_cases.get((repetition, case_id))
                    if case is None:
                        raise ValueError("resource row is absent from frozen schedule")
                    projected = derive_resource_metric_row(
                        row,
                        repetition=repetition,
                        condition_order=condition_order,
                        schedule_case=case,
                    )
                    if (
                        projected["model_id"] != condition.get("model_id")
                        or projected["model_revision"]
                        != condition.get("model_revision")
                        or projected["method_id"] != condition.get("method_id")
                        or projected["config_hash"] != condition.get("config_hash")
                    ):
                        raise ValueError("resource row differs from admitted condition")
                    derived_rows.append(projected)
    except (OSError, tarfile.TarError) as error:
        raise ValueError("invalid admitted resource archive") from error

    analysis, cluster_evidence, draw_evidence = analyze_resource_metric_rows(
        rows=derived_rows,
        analysis_spec=analysis_spec,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1,
        "analysis_version": ANALYSIS_VERSION,
        "resource_admission_sha256": _sha256_file(admission_path),
        "resource_analysis_freeze_sha256": _sha256_file(analysis_freeze_path),
        "resource_schedule_sha256": _sha256_file(resource_schedule_path),
        "analysis_pipeline_raw_output_fields_accessed": False,
        "hidden_labels_accessed": False,
    }
    derived_path = output_dir / "derived_resource_rows.zip"
    derived_record = write_derived_resource_rows_archive(
        rows=derived_rows,
        output_path=derived_path,
        metadata=metadata,
    )
    bootstrap_path = output_dir / "bootstrap_evidence.zip"
    bootstrap_record = write_bootstrap_evidence_archive(
        cluster_summaries=cluster_evidence,
        draw_records=draw_evidence,
        output_path=bootstrap_path,
        metadata={
            **metadata,
            "bootstrap_draws": analysis_spec["paired_analysis"][
                "bootstrap_draws"
            ],
            "bootstrap_seed": analysis_spec["paired_analysis"][
                "bootstrap_seed"
            ],
            "inference_status": analysis_spec["paired_analysis"][
                "inference_status"
            ],
        },
    )
    derived_record["path"] = _relative_path(derived_path, repository_root)
    bootstrap_record["path"] = _relative_path(bootstrap_path, repository_root)
    return {
        "schema_version": 1,
        "analysis_version": ANALYSIS_VERSION,
        "status": "resource_analysis_complete_reporting_pending",
        "claim_status": "secondary_exploratory_resource_results",
        "artifact_bindings": {
            "resource_campaign_admission_sha256": _sha256_file(admission_path),
            "resource_analysis_freeze_sha256": _sha256_file(
                analysis_freeze_path
            ),
            "resource_analysis_deviation_sha256": _sha256_file(deviation_path),
            "resource_archive_sha256": _sha256_file(archive_path),
            "resource_schedule_sha256": _sha256_file(resource_schedule_path),
        },
        "source_code_sha256": _source_hashes(repository_root),
        "analysis_spec": {
            "repetitions_reported_separately": True,
            "source_task_clusters": analysis_spec["scope"][
                "source_task_clusters"
            ],
            "variants_per_cluster": analysis_spec["scope"][
                "variants_per_cluster"
            ],
            "bootstrap_draws": analysis_spec["paired_analysis"][
                "bootstrap_draws"
            ],
            "bootstrap_seed": analysis_spec["paired_analysis"][
                "bootstrap_seed"
            ],
            "confidence_interval": analysis_spec["paired_analysis"][
                "confidence_interval"
            ],
            "null_hypothesis_tests": False,
            "inference_status": analysis_spec["paired_analysis"][
                "inference_status"
            ],
        },
        **analysis,
        "derived_resource_rows_archive": derived_record,
        "bootstrap_evidence_archive": bootstrap_record,
        "models_invoked": False,
        "hidden_labels_accessed": False,
        "analysis_pipeline_raw_output_fields_accessed": False,
        "post_admission_human_raw_output_inspection_deviation": True,
        "deviation_id": deviation["deviation_id"],
        "null_hypothesis_tests_run": False,
        "next_gate": "resource_tables_figures_and_manuscript_integration_pending",
    }


def derive_resource_metric_row(
    row: Mapping[str, Any],
    *,
    repetition: int,
    condition_order: int,
    schedule_case: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one result to an output-free numeric resource record."""

    case_id = str(row.get("case_id", ""))
    method_id = str(row.get("method_id", ""))
    result = _mapping(row.get("result"), "resource result")
    if (
        not case_id
        or case_id != schedule_case.get("case_id")
        or result.get("case_id") != case_id
        or method_id not in _METHODS
        or result.get("method_id") != method_id
    ):
        raise ValueError("resource row identity differs from schedule")
    calls = result.get("calls")
    actual_calls = result.get("actual_model_call_count")
    if (
        not isinstance(calls, list)
        or not isinstance(actual_calls, int)
        or isinstance(actual_calls, bool)
        or actual_calls != len(calls)
    ):
        raise ValueError("resource model call count differs from retained calls")
    input_tokens = 0
    output_tokens = 0
    for call_index, call in enumerate(calls, start=1):
        generation = _mapping(
            _mapping(call, f"call {call_index}").get("generation"),
            f"call {call_index} generation",
        )
        input_tokens += _nonnegative_integer(
            generation.get("input_tokens"), f"call {call_index} input tokens"
        )
        output_tokens += _nonnegative_integer(
            generation.get("output_tokens"), f"call {call_index} output tokens"
        )
    measurement = _mapping(result.get("resource_measurement"), "measurement")
    if measurement.get("valid") is not True:
        raise ValueError("resource metric row contains an invalid measurement")
    energy = _mapping(measurement.get("energy"), "energy")
    if energy.get("scope") != "nvidia_gpu_board_only":
        raise ValueError("resource energy scope differs")
    projected = {
        "schema_version": 1,
        "repetition": repetition,
        "condition_order": condition_order,
        "model_id": str(row.get("model_id", "")),
        "model_revision": str(row.get("model_revision", "")),
        "method_id": method_id,
        "case_id": case_id,
        "cluster_id": str(schedule_case.get("cluster_id", "")),
        "source_task_id": str(schedule_case.get("source_task_id", "")),
        "case_variant": str(schedule_case.get("variant", "")),
        "config_hash": str(row.get("config_hash", "")),
        "result_key": str(row.get("result_key", "")),
        "method_case_duration_seconds": _finite_number(
            measurement.get("duration_seconds"), "method-case duration"
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_call_count": actual_calls,
        "process_ram_peak_bytes": _summary_maximum(measurement, "process_ram"),
        "board_vram_peak_bytes": _summary_maximum(measurement, "board_vram"),
        "process_vram_peak_bytes": _summary_maximum(
            measurement, "process_vram"
        ),
        "gpu_board_energy_joules": _finite_number(
            energy.get("joules"), "GPU-board energy"
        ),
        "gpu_utilization_peak_percent": _summary_maximum(
            measurement, "gpu_utilization_percent"
        ),
        "temperature_peak_celsius": _summary_maximum(
            measurement, "temperature_celsius"
        ),
    }
    if any(not str(projected[field]) for field in _DERIVED_ID_FIELDS[1:]):
        raise ValueError("resource derived-row identifier is absent")
    _validate_derived_row(projected)
    return projected


def analyze_resource_metric_rows(
    *,
    rows: Iterable[Mapping[str, Any]],
    analysis_spec: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute separate repetition summaries and exploratory paired intervals."""

    materialized = [dict(row) for row in rows]
    for row in materialized:
        _validate_derived_row(row)
    scope = _mapping(analysis_spec.get("scope"), "resource analysis scope")
    metrics = _metric_registry(analysis_spec)
    expected_rows = int(scope.get("method_case_rows", 0))
    if len(materialized) != expected_rows:
        raise ValueError("resource metric matrix row count differs")
    expected_clusters = int(scope.get("source_task_clusters", 0))
    expected_variants = int(scope.get("variants_per_cluster", 0))
    expected_models = int(scope.get("models", 0))
    expected_methods = int(scope.get("methods", 0))
    expected_repetitions = int(scope.get("repetitions", 0))
    if (
        expected_variants != 5
        or expected_methods != 4
        or scope.get("repetitions_reported_separately") is not True
        or scope.get("pooled_repetition_estimate") is not False
    ):
        raise ValueError("resource analysis scope differs")
    repetitions = sorted({int(row["repetition"]) for row in materialized})
    models = sorted({str(row["model_id"]) for row in materialized})
    methods = {str(row["method_id"]) for row in materialized}
    if (
        repetitions != list(range(1, expected_repetitions + 1))
        or len(models) != expected_models
        or len(methods) != expected_methods
        or methods != _METHODS
    ):
        raise ValueError("resource metric matrix dimensions differ")
    unique_keys = {
        (
            row["repetition"],
            row["model_id"],
            row["method_id"],
            row["case_id"],
        )
        for row in materialized
    }
    if len(unique_keys) != len(materialized):
        raise ValueError("resource metric matrix contains duplicate rows")
    _validate_cluster_matrix(
        materialized,
        expected_clusters=expected_clusters,
        expected_variants=expected_variants,
    )

    descriptive: list[dict[str, Any]] = []
    for repetition in repetitions:
        for model_id in models:
            for method_id in sorted(methods):
                selected = [
                    row
                    for row in materialized
                    if row["repetition"] == repetition
                    and row["model_id"] == model_id
                    and row["method_id"] == method_id
                ]
                for metric_id, metric in metrics.items():
                    by_cluster: dict[str, list[float]] = defaultdict(list)
                    for row in selected:
                        by_cluster[str(row["cluster_id"])].append(
                            float(row[metric_id])
                        )
                    cluster_means = [
                        statistics.fmean(by_cluster[cluster_id])
                        for cluster_id in sorted(by_cluster)
                    ]
                    if (
                        len(cluster_means) != expected_clusters
                        or any(
                            len(values) != expected_variants
                            for values in by_cluster.values()
                        )
                    ):
                        raise ValueError("resource descriptive cluster matrix differs")
                    descriptive.append(
                        {
                            "repetition": repetition,
                            "model_id": model_id,
                            "method_id": method_id,
                            "metric_id": metric_id,
                            "unit": metric["unit"],
                            "direction": metric["direction"],
                            "role": metric["role"],
                            "cluster_count": expected_clusters,
                            "cases_per_cluster": expected_variants,
                            "cluster_mean_statistics": _numeric_summary(
                                cluster_means
                            ),
                        }
                    )

    paired_spec = _mapping(
        analysis_spec.get("paired_analysis"), "paired resource analysis"
    )
    draws_count = int(paired_spec.get("bootstrap_draws", 0))
    seed = str(paired_spec.get("bootstrap_seed", ""))
    contrasts = paired_spec.get("contrasts")
    if not isinstance(contrasts, list) or len(contrasts) != 2:
        raise ValueError("resource paired contrasts differ")
    inferential_metrics = {
        metric_id: metric
        for metric_id, metric in metrics.items()
        if metric["role"] == paired_spec.get("eligible_metric_role")
    }
    paired: list[dict[str, Any]] = []
    cluster_evidence: list[dict[str, Any]] = []
    draw_evidence: list[dict[str, Any]] = []
    for repetition in repetitions:
        for model_id in models:
            subset = [
                row
                for row in materialized
                if row["repetition"] == repetition and row["model_id"] == model_id
            ]
            for contrast in contrasts:
                contrast = _mapping(contrast, "resource contrast")
                method_a = str(contrast.get("method_a", ""))
                method_b = str(contrast.get("method_b", ""))
                for metric_id, metric in inferential_metrics.items():
                    analysis_id = (
                        f"r{repetition}:{model_id}:{method_a}_minus_{method_b}:"
                        f"{metric_id}"
                    )
                    prepared = [
                        {
                            "cluster_id": row["cluster_id"],
                            "case_variant": row["case_variant"],
                            "method_id": row["method_id"],
                            "metric_value": row[metric_id],
                        }
                        for row in subset
                        if row["method_id"] in {method_a, method_b}
                    ]
                    result = paired_cluster_bootstrap(
                        prepared,
                        method_a=method_a,
                        method_b=method_b,
                        expected_variants=expected_variants,
                        draws=draws_count,
                        confidence_level=0.95,
                        seed=seed,
                    )
                    paired.append(
                        {
                            "analysis_id": analysis_id,
                            "repetition": repetition,
                            "model_id": model_id,
                            "contrast_role": contrast.get("contrast_role"),
                            "method_a": method_a,
                            "method_b": method_b,
                            "metric_id": metric_id,
                            "unit": metric["unit"],
                            "direction": metric["direction"],
                            "inference_status": paired_spec.get(
                                "inference_status"
                            ),
                            "analysis": result["analysis"],
                        }
                    )
                    cluster_evidence.extend(
                        {
                            "analysis_id": analysis_id,
                            "repetition": repetition,
                            "model_id": model_id,
                            "metric_id": metric_id,
                            **dict(cluster),
                        }
                        for cluster in result["cluster_summaries"]
                    )
                    draw_evidence.append(
                        {
                            "analysis_id": analysis_id,
                            "repetition": repetition,
                            "model_id": model_id,
                            "metric_id": metric_id,
                            "draws": result["raw_bootstrap_draws"],
                        }
                    )
    return (
        {
            "resource_metric_rows": len(materialized),
            "models": len(models),
            "methods": len(methods),
            "repetitions": repetitions,
            "source_task_clusters_per_condition": expected_clusters,
            "variants_per_cluster": expected_variants,
            "descriptive_summary_count": len(descriptive),
            "paired_contrast_count": len(paired),
            "descriptive_summaries": descriptive,
            "paired_contrasts": paired,
        },
        cluster_evidence,
        draw_evidence,
    )


def validate_resource_analysis_boundary(admission: Mapping[str, Any]) -> None:
    """Require the complete admitted, still-unscored resource boundary."""

    if (
        admission.get("status") != _ADMISSION_STATUS
        or admission.get("valid") is not True
        or admission.get("conditions") != 24
        or admission.get("rows_total") != 3600
        or admission.get("next_gate") != _ADMISSION_GATE
    ):
        raise ValueError("complete resource admission boundary is absent")
    if (
        admission.get("resource_scores_computed") is not False
        or admission.get("scored_rows") != 0
    ):
        raise ValueError("resource analysis requires an admitted unscored campaign")


def write_derived_resource_rows_archive(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_path: Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Store deterministic output-free metric rows separately from aggregates."""

    materialized = [dict(row) for row in rows]
    for row in materialized:
        _validate_derived_row(row)
    materialized.sort(
        key=lambda row: (
            int(row["repetition"]),
            str(row["model_id"]),
            str(row["method_id"]),
            str(row["case_id"]),
        )
    )
    rows_bytes = b"".join(
        (_canonical_json(row) + "\n").encode("utf-8") for row in materialized
    )
    metadata_bytes = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    manifest = {
        "schema_version": 1,
        "row_count": len(materialized),
        "raw_model_output_fields_present": False,
        "hidden_labels_present": False,
        "files": {
            "derived_resource_rows.jsonl": _content_record(rows_bytes),
            "metadata.json": _content_record(metadata_bytes),
        },
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(
            {
                "derived_resource_rows.jsonl": rows_bytes,
                "manifest.json": manifest_bytes,
                "metadata.json": metadata_bytes,
            }.items()
        ):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    temporary.replace(output_path)
    return {
        "path": output_path.as_posix(),
        "bytes": output_path.stat().st_size,
        "sha256": _sha256_file(output_path),
        "row_count": len(materialized),
        "derived_rows_sha256": hashlib.sha256(rows_bytes).hexdigest(),
        "raw_model_output_fields_present": False,
        "hidden_labels_present": False,
    }


def _validate_analysis_freeze(
    spec: Mapping[str, Any],
    *,
    repository_root: Path,
    admission_path: Path,
    schedule_path: Path,
    deviation_path: Path,
) -> None:
    if spec.get("analysis_version") != ANALYSIS_VERSION or spec.get(
        "status"
    ) != _FREEZE_STATUS:
        raise ValueError("resource analysis freeze is absent")
    inspection = _mapping(spec.get("inspection_state"), "inspection state")
    if (
        inspection.get("resource_aggregates_inspected") is not False
        or inspection.get("paired_resource_differences_inspected") is not False
        or inspection.get("hidden_labels_accessed") is not False
        or inspection.get("post_admission_raw_output_inspection_deviation_recorded")
        is not True
        or inspection.get("deviation_artifact")
        != _relative_path(deviation_path, repository_root)
    ):
        raise ValueError("resource analysis inspection state differs")
    bindings = _mapping(spec.get("artifact_bindings"), "analysis bindings")
    expected = {
        "accuracy_protocol_sha256": _sha256_file(
            repository_root
            / "datasets"
            / "multiuav_plat"
            / "accuracy_protocol_freeze_v1.json"
        ),
        "code_plan_sha256": _sha256_file(
            repository_root
            / "docs"
            / "source_material"
            / "code_plan_2026-07-25.docx"
        ),
        "hardware_measurement_protocol_doc_sha256": _sha256_file(
            repository_root
            / "docs"
            / "multiuav_hardware_measurement_protocol.md"
        ),
        "resource_campaign_admission_sha256": _sha256_file(admission_path),
        "resource_hardware_protocol_sha256": _sha256_file(
            repository_root
            / "datasets"
            / "multiuav_plat"
            / "resource_hardware_protocol_v1.json"
        ),
        "resource_schedule_sha256": _sha256_file(schedule_path),
        "validation_study_protocol_sha256": _sha256_file(
            repository_root / "docs" / "multiuav_validation_study_protocol.md"
        ),
    }
    for field, digest in expected.items():
        if bindings.get(field) != digest:
            raise ValueError(f"resource analysis binding differs: {field}")
    paired = _mapping(spec.get("paired_analysis"), "paired analysis")
    if (
        paired.get("bootstrap_draws") != 10_000
        or paired.get("bootstrap_seed")
        != "shepherd-multiuav-primary-bootstrap-v1"
        or paired.get("confidence_interval") != "percentile_95_percent"
        or paired.get("resampling_unit") != "source_task_cluster"
        or paired.get("null_hypothesis_tests") is not False
        or paired.get("inference_status")
        != "exploratory_secondary_no_confirmatory_claims"
    ):
        raise ValueError("resource paired analysis freeze differs")


def _validate_deviation(deviation: Mapping[str, Any]) -> None:
    if (
        deviation.get("deviation_id")
        != "resource_analysis_post_admission_schema_inspection_v1"
        or deviation.get("stage")
        != "post_campaign_completion_and_admission_before_resource_aggregate_analysis"
    ):
        raise ValueError("resource analysis deviation record differs")
    scope = _mapping(deviation.get("scope"), "deviation scope")
    timing = _mapping(deviation.get("timing"), "deviation timing")
    impact = _mapping(deviation.get("impact"), "deviation impact")
    if (
        scope.get("rows_printed") != 1
        or scope.get("hidden_labels_printed") is not False
        or scope.get("resource_aggregates_printed") is not False
        or timing.get("score_blind_resource_admission_complete") is not True
        or timing.get("resource_aggregate_analysis_started") is not False
        or impact.get("requires_disclosure") is not True
        or impact.get("invalidates_resource_campaign") is not False
    ):
        raise ValueError("resource analysis deviation scope differs")


def _schedule_cases(
    schedule: Mapping[str, Any],
) -> dict[tuple[int, str], Mapping[str, Any]]:
    rows = schedule.get("case_schedule", {}).get("rows", [])
    if not isinstance(rows, list) or len(rows) != 450:
        raise ValueError("resource case schedule is incomplete")
    result: dict[tuple[int, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("resource case schedule row is malformed")
        key = (int(row.get("repetition", 0)), str(row.get("case_id", "")))
        if key in result:
            raise ValueError("resource case schedule contains duplicates")
        result[key] = row
    return result


def _load_checkpoint_rows(content: bytes) -> tuple[list[dict[str, Any]], str]:
    try:
        archive = ZipFile(io.BytesIO(content))
    except BadZipFile as error:
        raise ValueError("invalid admitted resource checkpoint") from error
    with archive:
        names = [item.filename for item in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != _CHECKPOINT_MEMBERS:
            raise ValueError("resource checkpoint members differ")
        rows: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        with archive.open("results.jsonl") as handle:
            for line_number, line in enumerate(handle, start=1):
                digest.update(line)
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"invalid resource row at line {line_number}"
                    ) from error
                if not isinstance(row, dict):
                    raise ValueError(f"resource row {line_number} is not an object")
                rows.append(row)
    if len(rows) != 150:
        raise ValueError("resource checkpoint row count differs")
    return rows, digest.hexdigest()


def _validate_cluster_matrix(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_clusters: int,
    expected_variants: int,
) -> None:
    groups: dict[tuple[int, str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        key = (
            int(row["repetition"]),
            str(row["model_id"]),
            str(row["method_id"]),
            str(row["cluster_id"]),
        )
        variant = str(row["case_variant"])
        if variant in groups[key]:
            raise ValueError("resource cluster matrix contains duplicate variants")
        groups[key].add(variant)
    condition_keys = {
        (int(row["repetition"]), str(row["model_id"]), str(row["method_id"]))
        for row in rows
    }
    for condition in condition_keys:
        selected = [variants for key, variants in groups.items() if key[:3] == condition]
        if (
            len(selected) != expected_clusters
            or any(
                len(variants) != expected_variants or variants != _VARIANTS
                for variants in selected
            )
        ):
            raise ValueError("resource cluster matrix is incomplete")


def _metric_registry(spec: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records = spec.get("metrics")
    if not isinstance(records, list):
        raise ValueError("resource metric registry is absent")
    metrics: dict[str, Mapping[str, Any]] = {}
    for record in records:
        record = _mapping(record, "resource metric")
        metric_id = str(record.get("metric_id", ""))
        if metric_id in metrics:
            raise ValueError("resource metric registry contains duplicates")
        metrics[metric_id] = record
    if tuple(metrics) != _METRIC_FIELDS:
        raise ValueError("resource metric registry differs")
    return metrics


def _validate_derived_row(row: Mapping[str, Any]) -> None:
    if set(row) != _DERIVED_FIELDS:
        unexpected = sorted(set(row) - _DERIVED_FIELDS)
        label = "forbidden" if set(row) & _FORBIDDEN_OUTPUT_KEYS else "schema"
        raise ValueError(f"resource derived-row {label} differs: {unexpected}")
    _reject_forbidden_keys(row)
    for field in _METRIC_FIELDS:
        _finite_number(row.get(field), field)


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = set(value) & _FORBIDDEN_OUTPUT_KEYS
        if forbidden:
            raise ValueError(f"resource derived row contains forbidden fields: {sorted(forbidden)}")
        for nested in value.values():
            _reject_forbidden_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_keys(nested)


def _numeric_summary(values: Sequence[float]) -> dict[str, float]:
    if len(values) < 2:
        raise ValueError("resource summary requires at least two clusters")
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "sample_standard_deviation": statistics.stdev(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _summary_maximum(measurement: Mapping[str, Any], field: str) -> float:
    summary = _mapping(measurement.get(field), field)
    return _finite_number(summary.get("maximum"), f"{field} maximum")


def _finite_number(value: Any, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"resource {label} must be finite non-negative numeric")
    return float(value)


def _nonnegative_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"resource {label} must be a non-negative integer")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"resource mapping is absent: {label}")
    return value


def _read_tar_bytes(archive: tarfile.TarFile, name: str) -> bytes:
    try:
        member = archive.getmember(name)
    except KeyError as error:
        raise ValueError(f"resource archive member is absent: {name}") from error
    handle = archive.extractfile(member)
    if handle is None:
        raise ValueError(f"resource archive member is unreadable: {name}")
    return handle.read()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON object: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _content_record(content: bytes) -> dict[str, Any]:
    return {
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _source_hashes(repository_root: Path) -> dict[str, str]:
    paths = {
        "multiuav_resource_analysis.py": Path(__file__).resolve(),
        "multiuav_statistics.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_statistics.py",
        "multiuav_study_analysis.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_study_analysis.py",
        "analyze_multiuav_resources.py": repository_root
        / "scripts"
        / "analyze_multiuav_resources.py",
    }
    return {name: _sha256_file(path) for name, path in sorted(paths.items())}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
