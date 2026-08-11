"""Score-blind admission for a preserved MultiUAV resource campaign."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import tarfile
from typing import Any
from zipfile import BadZipFile, ZipFile

from shepherd_ai.multiuav_checkpoints import (
    CHECKPOINT_SCHEMA_VERSION,
    RunConfig,
    expected_result_keys,
)
from shepherd_ai.multiuav_resource_controls import validate_resource_measurement
from shepherd_ai.multiuav_resource_execution import (
    load_bound_resource_config,
    validate_resource_bindings,
)
from shepherd_ai.multiuav_resource_protocol import (
    EXPECTED_CASES,
    EXPECTED_CONDITIONS,
    EXPECTED_ROWS,
    sha256_file,
)


ADMISSION_CONTRACT_VERSION = "multiuav_resource_admission_v1"
_CHECKPOINT_MEMBERS = frozenset(
    {"manifest.json", "results.jsonl", "run_config.json"}
)
_CAMPAIGN_STATUS = "complete_resource_campaign_raw_results_unscored"
_CONDITION_STATUS = "complete_valid_resource_condition"
_RUN_CONFIG_STATUS = "final_resource_configs_bound_no_measurement_started"
_SOURCE_STATUS = "complete_resource_campaign_raw_results_unscored"
_SHA256_LENGTH = 64
_ROW_FIELDS = frozenset(
    {
        "schema_version",
        "config_hash",
        "result_key",
        "case_id",
        "method_id",
        "model_id",
        "model_revision",
        "result",
    }
)


def admit_resource_campaign(
    *,
    archive_path: Path,
    source_manifest_path: Path,
    preservation_manifest_path: Path,
    run_configs_path: Path,
    resource_schedule_path: Path,
    hardware_protocol_path: Path,
    accuracy_manifest_path: Path,
    intervention_dataset_path: Path,
) -> dict[str, Any]:
    """Admit one complete campaign without accessing outputs or hidden labels."""

    paths = {
        "archive": archive_path.resolve(),
        "source_manifest": source_manifest_path.resolve(),
        "preservation_manifest": preservation_manifest_path.resolve(),
        "run_configs": run_configs_path.resolve(),
        "resource_schedule": resource_schedule_path.resolve(),
        "hardware_protocol": hardware_protocol_path.resolve(),
        "accuracy_manifest": accuracy_manifest_path.resolve(),
        "intervention_dataset": intervention_dataset_path.resolve(),
    }
    source_manifest = _read_object(paths["source_manifest"])
    preservation = _read_object(paths["preservation_manifest"])
    registry = _read_object(paths["run_configs"])
    schedule = _read_object(paths["resource_schedule"])
    protocol = _read_object(paths["hardware_protocol"])
    accuracy_manifest = _read_object(paths["accuracy_manifest"])

    archive_audit = audit_tar_source_inventory(paths["archive"], source_manifest)
    _validate_preservation_manifest(
        preservation,
        archive_path=paths["archive"],
        archive_sha256=archive_audit["archive_sha256"],
        source_manifest_path=paths["source_manifest"],
    )
    _validate_campaign_registry(registry, schedule)

    root = str(archive_audit["root"])
    reports: list[dict[str, Any]] = []
    hardware_lock: dict[str, Any]
    campaign_summary: dict[str, Any]
    with tarfile.open(paths["archive"], mode="r:gz") as archive:
        campaign_summary = _read_tar_object(
            archive, f"{root}/campaign_summary.json"
        )
        hardware_lock = _read_tar_object(archive, f"{root}/hardware_lock.json")
        _validate_hardware_lock(
            hardware_lock,
            protocol=protocol,
            protocol_sha256=sha256_file(paths["hardware_protocol"]),
        )
        for scheduled in _condition_schedule(schedule):
            repetition = int(scheduled["repetition"])
            condition_order = int(scheduled["condition_order"])
            config = load_bound_resource_config(
                registry,
                repetition=repetition,
                condition_order=condition_order,
            )
            validate_resource_bindings(
                config_artifact=registry,
                config=config,
                schedule=schedule,
                hardware_protocol=protocol,
                accuracy_manifest=accuracy_manifest,
                schedule_path=paths["resource_schedule"],
                hardware_protocol_path=paths["hardware_protocol"],
                accuracy_manifest_path=paths["accuracy_manifest"],
                intervention_dataset_path=paths["intervention_dataset"],
            )
            prefix = f"{root}/r{repetition}-o{condition_order}"
            checkpoint_bytes = _read_tar_bytes(archive, f"{prefix}/checkpoint.zip")
            archived_config, rows, checkpoint_audit = _load_checkpoint_bytes(
                checkpoint_bytes
            )
            if archived_config != config.to_dict():
                raise ValueError(
                    f"r{repetition}-o{condition_order}: checkpoint config differs"
                )
            sidecar = _read_tar_object(
                archive, f"{prefix}/results.jsonl.config.json"
            )
            if sidecar != config.to_dict():
                raise ValueError(
                    f"r{repetition}-o{condition_order}: sidecar config differs"
                )
            result_source = _source_record(
                source_manifest, f"r{repetition}-o{condition_order}/results.jsonl"
            )
            if result_source.get("sha256") != checkpoint_audit["results_sha256"]:
                raise ValueError(
                    f"r{repetition}-o{condition_order}: raw and checkpoint results differ"
                )
            start_controls = _read_condition_start_controls(
                archive,
                root=root,
                repetition=repetition,
                condition_order=condition_order,
                source_manifest=source_manifest,
            )
            case_ids = _case_ids_for_repetition(schedule, repetition=repetition)
            condition_audit = validate_resource_condition_rows(
                rows,
                config=config,
                expected_case_ids=case_ids,
                protocol=protocol,
                start_controls=start_controls,
                hardware_lock=hardware_lock,
            )
            run_summary = _read_tar_object(archive, f"{prefix}/run_summary.json")
            checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
            _validate_condition_summary(
                run_summary,
                config=config,
                condition_audit=condition_audit,
                results_sha256=str(checkpoint_audit["results_sha256"]),
                checkpoint_sha256=checkpoint_sha256,
                hardware_lock=hardware_lock,
                protocol=protocol,
            )
            reports.append(
                {
                    "valid": True,
                    "repetition": repetition,
                    "condition_order": condition_order,
                    "model_id": config.model_id,
                    "model_revision": config.model_revision,
                    "method_id": config.methods[0],
                    "config_hash": config.config_hash,
                    "rows": len(rows),
                    "segments": condition_audit["segments"],
                    "checkpoint_sha256": checkpoint_sha256,
                    "results_sha256": checkpoint_audit["results_sha256"],
                    "run_summary_sha256": hashlib.sha256(
                        _read_tar_bytes(archive, f"{prefix}/run_summary.json")
                    ).hexdigest(),
                    "raw_model_outputs_inspected": False,
                    "hidden_labels_accessed": False,
                    "resource_scores_computed": False,
                }
            )

    _validate_campaign_summary(campaign_summary, reports=reports)
    if len(reports) != EXPECTED_CONDITIONS:
        raise ValueError("admitted condition count differs from registration")
    rows_total = sum(int(report["rows"]) for report in reports)
    if rows_total != EXPECTED_ROWS:
        raise ValueError("admitted resource row total differs from registration")
    models = sorted({str(report["model_id"]) for report in reports})
    methods = sorted({str(report["method_id"]) for report in reports})
    return {
        "schema_version": 1,
        "admission_contract_version": ADMISSION_CONTRACT_VERSION,
        "status": "complete_resource_campaign_admitted_for_analysis",
        "valid": True,
        "claim_status": "resource_campaign_admitted_unscored",
        "artifact_bindings": {
            "archive_sha256": archive_audit["archive_sha256"],
            "source_manifest_sha256": sha256_file(paths["source_manifest"]),
            "preservation_manifest_sha256": sha256_file(
                paths["preservation_manifest"]
            ),
            "resource_run_configs_sha256": sha256_file(paths["run_configs"]),
            "resource_schedule_sha256": sha256_file(paths["resource_schedule"]),
            "hardware_protocol_sha256": sha256_file(paths["hardware_protocol"]),
            "accuracy_manifest_sha256": sha256_file(paths["accuracy_manifest"]),
            "intervention_dataset_sha256": sha256_file(
                paths["intervention_dataset"]
            ),
        },
        "conditions": len(reports),
        "rows_total": rows_total,
        "models": models,
        "methods": methods,
        "repetitions": sorted({int(report["repetition"]) for report in reports}),
        "hardware_lock": hardware_lock,
        "archive_integrity": archive_audit,
        "condition_admissions": reports,
        "raw_model_outputs_inspected": False,
        "hidden_labels_accessed": False,
        "resource_scores_computed": False,
        "scored_rows": 0,
        "next_gate": "registered_resource_analysis_authorized_not_started",
    }


def audit_tar_source_inventory(
    archive_path: Path, source_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify safe tar members and every preserved source hash and size."""

    files = source_manifest.get("files")
    if not isinstance(files, Mapping) or not files:
        raise ValueError("source manifest file inventory is absent")
    if source_manifest.get("file_count") != len(files):
        raise ValueError("source manifest file count differs")
    if (
        source_manifest.get("schema_version") != 1
        or source_manifest.get("artifact_status") != _SOURCE_STATUS
    ):
        raise ValueError("source manifest status differs")
    if source_manifest.get("raw_model_outputs_inspected") is not False:
        raise ValueError("source manifest reports raw-output inspection")
    if source_manifest.get("hidden_labels_inspected") is not False:
        raise ValueError("source manifest reports hidden-label inspection")

    archive_path = archive_path.resolve()
    archive_sha256 = sha256_file(archive_path)
    observed: dict[str, dict[str, Any]] = {}
    roots: set[str] = set()
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            names: set[str] = set()
            for member in archive.getmembers():
                if member.name in names:
                    raise ValueError("archive contains duplicate members")
                names.add(member.name)
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or any(not part for part in path.parts)
                ):
                    raise ValueError(f"archive contains unsafe member: {member.name}")
                roots.add(path.parts[0])
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(
                        f"archive contains unsafe non-file member: {member.name}"
                    )
                if len(path.parts) < 2:
                    raise ValueError("archive file is outside the campaign root")
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"archive member is unreadable: {member.name}")
                digest = hashlib.sha256()
                size = 0
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                    size += len(block)
                observed[relative] = {
                    "bytes": size,
                    "sha256": digest.hexdigest(),
                }
    except (OSError, tarfile.TarError) as error:
        raise ValueError(f"invalid resource campaign archive: {archive_path}") from error
    if len(roots) != 1:
        raise ValueError("archive must contain exactly one campaign root")
    if set(observed) != set(files):
        raise ValueError("archive members differ from the source manifest")
    for name, expected in files.items():
        if not isinstance(expected, Mapping) or observed[name] != dict(expected):
            raise ValueError(f"archive source hash or size differs: {name}")
    total_bytes = sum(int(record["bytes"]) for record in observed.values())
    if source_manifest.get("total_bytes") != total_bytes:
        raise ValueError("source manifest total bytes differ")
    return {
        "status": "complete_source_inventory_verified",
        "root": next(iter(roots)),
        "verified_files": len(observed),
        "verified_bytes": total_bytes,
        "archive_sha256": archive_sha256,
        "raw_model_outputs_inspected": False,
        "hidden_labels_accessed": False,
        "resource_scores_computed": False,
    }


def validate_resource_condition_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: RunConfig,
    expected_case_ids: Iterable[str],
    protocol: Mapping[str, Any],
    start_controls: Mapping[str, Mapping[str, Any]],
    hardware_lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Revalidate one complete condition without reading output fields."""

    config.validate()
    case_ids = tuple(expected_case_ids)
    if len(config.methods) != 1:
        raise ValueError("resource condition must contain exactly one method")
    method_id = config.methods[0]
    expected_keys = expected_result_keys(case_ids, (method_id,))
    observed_keys: list[str] = []
    observed_cases: list[str] = []
    segment_hashes: dict[str, str] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping) or set(row) != _ROW_FIELDS:
            raise ValueError(f"resource row schema differs at row {index}")
        checks = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "config_hash": config.config_hash,
            "method_id": method_id,
            "model_id": config.model_id,
            "model_revision": config.model_revision,
        }
        for field, expected in checks.items():
            if row.get(field) != expected:
                raise ValueError(f"resource row {field} differs at row {index}")
        case_id = str(row.get("case_id", ""))
        observed_cases.append(case_id)
        observed_keys.append(str(row.get("result_key", "")))
        result = row.get("result")
        if not isinstance(result, Mapping):
            raise ValueError(f"resource result is absent at row {index}")
        if result.get("case_id") != case_id or result.get("method_id") != method_id:
            raise ValueError(f"resource nested identity differs at row {index}")
        measurement = result.get("resource_measurement")
        if not isinstance(measurement, Mapping):
            raise ValueError(f"resource measurement is absent at row {index}")
        validate_resource_measurement_evidence(
            measurement,
            protocol=protocol,
            hardware_lock=hardware_lock,
        )
        run_control = _mapping(measurement.get("run_control"), "run control")
        if run_control.get("protocol_sha256") != config.hardware_protocol_sha256:
            raise ValueError(f"resource protocol hash differs at row {index}")
        segment_id = str(run_control.get("segment_id", ""))
        if PurePosixPath(segment_id).name != segment_id or not segment_id:
            raise ValueError(f"resource segment id is unsafe at row {index}")
        control_hash = str(run_control.get("start_control_sha256", ""))
        if len(control_hash) != _SHA256_LENGTH:
            raise ValueError(f"resource start-control hash is absent at row {index}")
        previous = segment_hashes.setdefault(segment_id, control_hash)
        if previous != control_hash:
            raise ValueError("resource segment start-control hash differs")
    if (
        len(rows) != EXPECTED_CASES
        or tuple(observed_cases) != case_ids
        or tuple(observed_keys) != expected_keys
        or len(set(observed_keys)) != len(observed_keys)
    ):
        raise ValueError("resource condition matrix differs from the frozen schedule")
    if set(segment_hashes) != set(start_controls):
        raise ValueError("resource start controls differ from referenced segments")
    for segment_id, expected_hash in sorted(segment_hashes.items()):
        control = start_controls[segment_id]
        if control.get("sha256") != expected_hash:
            raise ValueError(f"{segment_id}: referenced start-control hash differs")
        validate_resource_start_control(
            control,
            protocol=protocol,
            hardware_lock=hardware_lock,
        )
    return {
        "valid": True,
        "status": _CONDITION_STATUS,
        "rows": len(rows),
        "segments": sorted(segment_hashes),
        "start_control_hashes": sorted(segment_hashes.values()),
        "start_controls": len(start_controls),
        "measurements_revalidated": len(rows),
        "raw_model_outputs_inspected": False,
        "hidden_labels_accessed": False,
        "resource_scores_computed": False,
    }


def validate_resource_measurement_evidence(
    report: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    hardware_lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute telemetry consistency without interpreting model behavior."""

    identity = {
        "gpu_index": 0,
        "name": hardware_lock.get("gpu_name"),
        "uuid": hardware_lock.get("gpu_uuid"),
        "driver_version": hardware_lock.get("driver_version"),
    }
    revalidated = validate_resource_measurement(
        report,
        protocol=protocol,
        expected_identity=identity,
    )
    if revalidated.get("valid") is not True:
        reasons = "; ".join(str(error) for error in revalidated.get("errors", []))
        raise ValueError(
            "resource measurement fails frozen protocol revalidation"
            + (f": {reasons}" if reasons else "")
        )
    if report.get("protocol_validation") != revalidated.get("protocol_validation"):
        raise ValueError("resource protocol validation record differs")
    if report.get("errors") != []:
        raise ValueError("resource measurement contains retained errors")
    measurement = _mapping(protocol.get("measurement"), "measurement protocol")
    if not _numbers_close(
        report.get("sample_target_hz"), measurement.get("sample_target_hz")
    ):
        raise ValueError("resource sample target differs")
    samples = report.get("samples")
    if not isinstance(samples, list) or len(samples) < 2:
        raise ValueError("resource samples are absent")
    if report.get("sample_count") != len(samples):
        raise ValueError("resource sample count differs")
    timestamps = [_number(sample, "monotonic_seconds") for sample in samples]
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("resource sample timestamps are not increasing")
    span = timestamps[-1] - timestamps[0]
    observed_hz = (len(samples) - 1) / span
    if not _numbers_close(report.get("observed_sample_hz"), observed_hz):
        raise ValueError("resource observed sample rate differs from retained samples")
    duration = report.get("duration_seconds")
    if not isinstance(duration, (int, float)) or duration < span:
        raise ValueError("resource measurement duration differs from samples")
    _validate_sample_summaries(report, samples)
    process_ids = sorted(
        {
            int(process_id)
            for sample in samples
            for process_id in _process_ids(sample)
        }
    )
    if report.get("compute_process_ids_observed") != process_ids:
        raise ValueError("resource observed process inventory differs")
    _validate_energy(report, samples)
    if report.get("claim_limit") != (
        "not_total_workstation_simulator_network_or_uav_energy"
    ):
        raise ValueError("resource energy claim limit differs")
    return {
        "valid": True,
        "sample_count": len(samples),
        "observed_sample_hz": observed_hz,
        "energy_method": report["energy"]["method"],
        "raw_model_outputs_inspected": False,
        "hidden_labels_accessed": False,
        "resource_scores_computed": False,
    }


def validate_resource_start_control(
    report: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    hardware_lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute one warm-up, idle, thermal, and hardware-lock control."""

    stored_hash = report.get("sha256")
    payload = dict(report)
    payload.pop("sha256", None)
    if stored_hash != _sha256_json(payload):
        raise ValueError("resource start-control hash differs")
    protocol_sha256 = hardware_lock.get("protocol_sha256")
    checks = {
        "status": "resource_start_control_passed",
        "protocol_sha256": protocol_sha256,
        "measurement_started": False,
    }
    for field, expected in checks.items():
        if report.get(field) != expected:
            raise ValueError(f"resource start-control {field} differs")
    if report.get("hardware_lock") != hardware_lock:
        raise ValueError("resource start-control hardware lock differs")
    gpu = _mapping(report.get("gpu"), "start-control GPU")
    gpu_checks = {
        "name": hardware_lock.get("gpu_name"),
        "uuid": hardware_lock.get("gpu_uuid"),
        "driver_version": hardware_lock.get("driver_version"),
    }
    if any(gpu.get(key) != value for key, value in gpu_checks.items()):
        raise ValueError("resource start-control GPU differs from hardware lock")
    start = _mapping(protocol.get("start_control"), "start-control protocol")
    hardware = _mapping(protocol.get("hardware"), "hardware protocol")
    warmup = _mapping(report.get("warmup"), "warm-up report")
    if (
        warmup.get("complete_method_cases")
        != start.get("warmup_complete_method_cases_per_condition_segment")
        or warmup.get("output_retained") is not start.get("warmup_output_retained")
        or not isinstance(warmup.get("duration_seconds"), (int, float))
        or warmup["duration_seconds"] <= 0
    ):
        raise ValueError("resource warm-up evidence differs")
    baseline = _sample_list(report, "baseline_samples")
    baseline_wait = _sample_list(report, "baseline_wait_samples")
    required_baseline = int(start["baseline_samples"])
    if len(baseline) != required_baseline or baseline_wait[-required_baseline:] != baseline:
        raise ValueError("resource baseline sample sequence differs")
    for sample in baseline:
        _validate_control_processes(sample, hardware)
        if sample["gpu_utilization_percent"] > start["maximum_gpu_utilization_percent"]:
            raise ValueError("resource baseline utilization exceeds protocol")
        if sample["temperature_celsius"] > start[
            "maximum_baseline_temperature_celsius"
        ]:
            raise ValueError("resource baseline temperature exceeds protocol")
    baseline_temperature = float(
        statistics.median(sample["temperature_celsius"] for sample in baseline)
    )
    if not _numbers_close(
        report.get("baseline_temperature_celsius"), baseline_temperature
    ):
        raise ValueError("resource baseline temperature summary differs")
    temperature_limit = min(
        baseline_temperature + float(start["maximum_temperature_above_baseline_celsius"]),
        float(start["maximum_post_warmup_temperature_celsius"]),
    )
    if not _numbers_close(report.get("temperature_limit_celsius"), temperature_limit):
        raise ValueError("resource recovery temperature limit differs")
    recovery = _sample_list(report, "post_warmup_samples")
    required_recovery = int(start["post_warmup_consecutive_idle_samples"])
    if len(recovery) < required_recovery:
        raise ValueError("resource recovery sample sequence is incomplete")
    for sample in recovery:
        _validate_control_processes(sample, hardware)
    for sample in recovery[-required_recovery:]:
        if (
            sample["gpu_utilization_percent"]
            > start["maximum_gpu_utilization_percent"]
            or sample["temperature_celsius"] > temperature_limit
        ):
            raise ValueError("resource final recovery samples differ from protocol")
    return {
        "valid": True,
        "sha256": stored_hash,
        "baseline_samples": len(baseline),
        "post_warmup_consecutive_samples": required_recovery,
        "raw_model_outputs_inspected": False,
        "hidden_labels_accessed": False,
        "resource_scores_computed": False,
    }


def _load_checkpoint_bytes(
    content: bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    try:
        archive = ZipFile(io.BytesIO(content))
    except BadZipFile as error:
        raise ValueError("invalid resource checkpoint archive") from error
    with archive:
        names = [info.filename for info in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != _CHECKPOINT_MEMBERS:
            raise ValueError("resource checkpoint members differ")
        manifest_bytes = archive.read("manifest.json")
        config_bytes = archive.read("run_config.json")
        manifest = _read_json_bytes(manifest_bytes, label="checkpoint manifest")
        config = _read_json_bytes(config_bytes, label="checkpoint config")
        files = manifest.get("files")
        if not isinstance(files, Mapping) or set(files) != {
            "results.jsonl",
            "run_config.json",
        }:
            raise ValueError("resource checkpoint file inventory differs")
        _validate_file_record(files, "run_config.json", config_bytes)
        rows: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        results_bytes = 0
        with archive.open("results.jsonl") as handle:
            for line_number, line in enumerate(handle, start=1):
                digest.update(line)
                results_bytes += len(line)
                if not line.strip():
                    raise ValueError(
                        f"blank resource checkpoint row at line {line_number}"
                    )
                rows.append(
                    _read_json_bytes(line, label=f"resource row {line_number}")
                )
        results_sha256 = digest.hexdigest()
        record = files["results.jsonl"]
        if (
            not isinstance(record, Mapping)
            or record.get("bytes") != results_bytes
            or record.get("sha256") != results_sha256
        ):
            raise ValueError("resource checkpoint results hash or size differs")
        if (
            manifest.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
            or config.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
            or manifest.get("config_hash") != config.get("config_hash")
            or manifest.get("row_count") != len(rows)
        ):
            raise ValueError("resource checkpoint manifest differs")
        return config, rows, {
            "row_count": len(rows),
            "results_bytes": results_bytes,
            "results_sha256": results_sha256,
        }


def _validate_condition_summary(
    summary: Mapping[str, Any],
    *,
    config: RunConfig,
    condition_audit: Mapping[str, Any],
    results_sha256: str,
    checkpoint_sha256: str,
    hardware_lock: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> None:
    checks = {
        "status": _CONDITION_STATUS,
        "code_commit": config.code_commit,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "method_id": config.methods[0],
        "repetition": config.resource_repetition,
        "condition_order": config.resource_condition_order,
        "config_hash": config.config_hash,
        "expected_rows": EXPECTED_CASES,
        "approved_cases": EXPECTED_CASES,
        "hardware_protocol_sha256": config.hardware_protocol_sha256,
        "resource_schedule_sha256": config.resource_schedule_sha256,
        "measurement_started": True,
        "model_loaded": True,
        "raw_model_outputs_inspected": False,
        "hidden_labels_inspected": False,
        "results_sha256": results_sha256,
        "checkpoint_zip_sha256": checkpoint_sha256,
        "node_name": hardware_lock.get("node_name"),
    }
    for field, expected in checks.items():
        if summary.get(field) != expected:
            raise ValueError(f"resource run summary {field} differs")
    if summary.get("start_control_sha256") not in {
        str(value) for value in condition_audit.get("start_control_hashes", [])
    }:
        raise ValueError("resource run summary start-control hash differs")
    matrix = _mapping(summary.get("matrix"), "resource matrix summary")
    if (
        matrix.get("complete") is not True
        or matrix.get("expected_rows") != EXPECTED_CASES
        or matrix.get("config_hash") != config.config_hash
        or matrix.get("resource_measurement_enabled") is not True
    ):
        raise ValueError("resource run summary matrix differs")
    validation = _mapping(
        summary.get("condition_validation"), "condition validation summary"
    )
    if (
        validation.get("status") != _CONDITION_STATUS
        or validation.get("valid") is not True
        or validation.get("observed_rows") != EXPECTED_CASES
        or validation.get("invalid_rows_or_controls") != 0
        or validation.get("errors") != []
        or validation.get("raw_model_outputs_inspected") is not False
        or validation.get("hidden_labels_inspected") is not False
        or sorted(validation.get("segments", [])) != condition_audit.get("segments")
        or validation.get("segment_count") != len(condition_audit.get("segments", []))
        or validation.get("start_control_reports_validated")
        != condition_audit.get("start_controls")
    ):
        raise ValueError("resource condition validation summary differs")
    backend = _mapping(summary.get("backend_config"), "resource backend config")
    if (
        backend.get("model_id") != config.model_id
        or backend.get("revision") != config.model_revision
        or backend.get("do_sample") is not False
        or backend.get("num_beams") != 1
        or backend.get("max_new_tokens") != config.decoding.get("max_new_tokens")
        or backend.get("local_files_only") is not True
        or backend.get("trust_remote_code") is not False
        or backend.get("use_safetensors") is not True
    ):
        raise ValueError("resource backend configuration differs")
    for field in ("cache_audit_sha256", "smoke_audit_sha256"):
        if not _is_sha256(summary.get(field)):
            raise ValueError(f"resource run summary {field} differs")
    runtime = _mapping(summary.get("runtime"), "resource runtime")
    runtime_gpus = runtime.get("gpus")
    hardware_protocol = _mapping(protocol.get("hardware"), "hardware protocol")
    if (
        runtime.get("cuda_available") is not True
        or not isinstance(runtime_gpus, list)
        or len(runtime_gpus) != 1
        or not isinstance(runtime_gpus[0], Mapping)
        or runtime_gpus[0].get("name") != hardware_lock.get("gpu_name")
        or not isinstance(runtime_gpus[0].get("total_memory_bytes"), int)
        or runtime_gpus[0]["total_memory_bytes"]
        < int(hardware_protocol["minimum_total_memory_bytes"])
    ):
        raise ValueError("resource runtime GPU differs")
    nvml = _mapping(summary.get("nvml_preflight"), "NVML preflight")
    if (
        nvml.get("status") != "nvml_resource_preflight_passed_no_model_loaded"
        or nvml.get("model_loaded") is not False
        or nvml.get("measurement_started") is not False
        or nvml.get("power_integration_fallback_available") is not True
        or not isinstance(nvml.get("compute_process_count"), int)
        or nvml["compute_process_count"] < 0
        or nvml["compute_process_count"]
        > int(hardware_protocol["maximum_gpu_compute_processes"])
    ):
        raise ValueError("resource NVML preflight differs")
    gpu = _mapping(nvml.get("gpu"), "NVML preflight GPU")
    if (
        gpu.get("name") != hardware_lock.get("gpu_name")
        or gpu.get("uuid") != hardware_lock.get("gpu_uuid")
        or gpu.get("driver_version") != hardware_lock.get("driver_version")
    ):
        raise ValueError("resource NVML preflight GPU differs")


def _validate_campaign_registry(
    registry: Mapping[str, Any], schedule: Mapping[str, Any]
) -> None:
    if registry.get("status") != _RUN_CONFIG_STATUS:
        raise ValueError("resource run configs are not frozen")
    records = registry.get("configs")
    if not isinstance(records, list) or len(records) != EXPECTED_CONDITIONS:
        raise ValueError("resource run config count differs")
    expected = schedule.get("expected")
    if not isinstance(expected, Mapping) or (
        expected.get("conditions") != EXPECTED_CONDITIONS
        or expected.get("method_case_rows_per_condition") != EXPECTED_CASES
        or expected.get("total_method_case_rows") != EXPECTED_ROWS
        or expected.get("models") != 2
        or expected.get("methods") != 4
        or expected.get("repetitions") != 3
    ):
        raise ValueError("resource schedule dimensions differ")
    if (
        registry.get("expected_conditions") != EXPECTED_CONDITIONS
        or registry.get("expected_rows_per_condition") != EXPECTED_CASES
        or registry.get("expected_rows_total") != EXPECTED_ROWS
    ):
        raise ValueError("resource run config dimensions differ")


def _condition_schedule(schedule: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    section = schedule.get("condition_schedule")
    rows = section.get("rows") if isinstance(section, Mapping) else None
    if not isinstance(rows, list) or len(rows) != EXPECTED_CONDITIONS:
        raise ValueError("resource condition schedule differs")
    keys = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("resource condition schedule row is invalid")
        keys.append((row.get("repetition"), row.get("condition_order")))
    if len(set(keys)) != EXPECTED_CONDITIONS:
        raise ValueError("resource condition schedule contains duplicates")
    return rows


def _case_ids_for_repetition(
    schedule: Mapping[str, Any], *, repetition: int
) -> tuple[str, ...]:
    section = schedule.get("case_schedule")
    rows = section.get("rows") if isinstance(section, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("resource case schedule is absent")
    selected = [row for row in rows if row.get("repetition") == repetition]
    selected.sort(key=lambda row: int(row.get("case_order", 0)))
    if (
        len(selected) != EXPECTED_CASES
        or [row.get("case_order") for row in selected]
        != list(range(1, EXPECTED_CASES + 1))
    ):
        raise ValueError("resource case schedule is incomplete")
    case_ids = tuple(str(row.get("case_id", "")) for row in selected)
    if any(not case_id for case_id in case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError("resource case schedule ids differ")
    return case_ids


def _read_condition_start_controls(
    archive: tarfile.TarFile,
    *,
    root: str,
    repetition: int,
    condition_order: int,
    source_manifest: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    prefix = f"r{repetition}-o{condition_order}/start_controls/"
    files = source_manifest.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("source manifest file inventory is absent")
    names = sorted(
        str(name)
        for name in files
        if str(name).startswith(prefix) and str(name).endswith(".json")
    )
    if not names:
        raise ValueError(f"r{repetition}-o{condition_order}: start control is absent")
    controls: dict[str, dict[str, Any]] = {}
    for name in names:
        segment_id = PurePosixPath(name).stem
        if PurePosixPath(segment_id).name != segment_id or segment_id in controls:
            raise ValueError("resource start-control segment id is invalid")
        controls[segment_id] = _read_tar_object(archive, f"{root}/{name}")
    return controls


def _validate_hardware_lock(
    lock: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    protocol_sha256: str,
) -> None:
    hardware = _mapping(protocol.get("hardware"), "hardware protocol")
    if (
        lock.get("schema_version") != 1
        or lock.get("protocol_sha256") != protocol_sha256
        or lock.get("gpu_name") != hardware.get("required_runtime_gpu_name")
        or not str(lock.get("gpu_uuid", ""))
        or not str(lock.get("driver_version", ""))
        or not str(lock.get("node_name", ""))
    ):
        raise ValueError("resource campaign hardware lock differs")


def _validate_campaign_summary(
    summary: Mapping[str, Any], *, reports: Sequence[Mapping[str, Any]]
) -> None:
    observed = {
        (int(report["repetition"]), int(report["condition_order"]))
        for report in reports
    }
    completed = summary.get("completed_conditions")
    if not isinstance(completed, list):
        raise ValueError("resource campaign completed-condition list is absent")
    recorded = {
        (int(row["repetition"]), int(row["condition_order"]))
        for row in completed
        if isinstance(row, Mapping)
    }
    if (
        summary.get("status") != _CAMPAIGN_STATUS
        or summary.get("expected_conditions") != EXPECTED_CONDITIONS
        or summary.get("completed_condition_count") != EXPECTED_CONDITIONS
        or recorded != observed
        or summary.get("raw_model_outputs_inspected") is not False
        or summary.get("resource_scores_computed") is not False
    ):
        raise ValueError("resource campaign summary differs")


def _validate_preservation_manifest(
    manifest: Mapping[str, Any],
    *,
    archive_path: Path,
    archive_sha256: str,
    source_manifest_path: Path,
) -> None:
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("resource preservation file inventory is absent")
    archive_record = files.get(archive_path.name)
    source_record = files.get(source_manifest_path.name)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("artifact_status")
        != "resource_campaign_attempt3_complete_preserved_raw_unscored"
        or manifest.get("complete_conditions") != EXPECTED_CONDITIONS
        or manifest.get("durable_rows") != EXPECTED_ROWS
        or manifest.get("raw_model_outputs_inspected") is not False
        or manifest.get("hidden_labels_inspected") is not False
        or manifest.get("resource_scores_computed") is not False
        or not isinstance(archive_record, Mapping)
        or archive_record.get("sha256") != archive_sha256
        or archive_record.get("bytes") != archive_path.stat().st_size
        or not isinstance(source_record, Mapping)
        or source_record.get("sha256") != sha256_file(source_manifest_path)
        or source_record.get("bytes") != source_manifest_path.stat().st_size
    ):
        raise ValueError("resource preservation manifest differs")


def _validate_sample_summaries(
    report: Mapping[str, Any], samples: Sequence[Mapping[str, Any]]
) -> None:
    fields = {
        "process_ram": "process_rss_bytes",
        "board_vram": "board_memory_used_bytes",
        "process_vram": "process_gpu_memory_bytes",
        "power_milliwatts": "power_milliwatts",
        "gpu_utilization_percent": "gpu_utilization_percent",
        "temperature_celsius": "temperature_celsius",
    }
    for summary_name, sample_name in fields.items():
        values = [sample.get(sample_name) for sample in samples]
        numeric = [value for value in values if isinstance(value, int)]
        expected = (
            {
                "start": numeric[0],
                "end": numeric[-1],
                "minimum": min(numeric),
                "maximum": max(numeric),
            }
            if numeric
            else None
        )
        if report.get(summary_name) != expected:
            raise ValueError(f"resource telemetry summary differs: {summary_name}")


def _validate_energy(
    report: Mapping[str, Any], samples: Sequence[Mapping[str, Any]]
) -> None:
    energy = _mapping(report.get("energy"), "resource energy")
    integrated = 0.0
    for left, right in zip(samples, samples[1:]):
        delta = _number(right, "monotonic_seconds") - _number(
            left, "monotonic_seconds"
        )
        integrated += (
            _number(left, "power_milliwatts")
            + _number(right, "power_milliwatts")
        ) / 2000.0 * delta
    if not _numbers_close(energy.get("diagnostic_power_integral_joules"), integrated):
        raise ValueError("resource diagnostic energy differs from samples")
    method = energy.get("method")
    if method == "nvml_total_energy_counter":
        start = energy.get("counter_start_millijoules")
        end = energy.get("counter_end_millijoules")
        if not isinstance(start, int) or not isinstance(end, int) or end < start:
            raise ValueError("resource energy counter differs")
        expected = (end - start) / 1000.0
    elif method == "nvml_power_trapezoidal_integration":
        expected = integrated
    else:
        raise ValueError("resource energy method differs")
    if not _numbers_close(energy.get("joules"), expected):
        raise ValueError("resource energy differs from retained evidence")


def _validate_control_processes(
    sample: Mapping[str, Any], hardware: Mapping[str, Any]
) -> None:
    ids = _process_ids(sample)
    minimum = int(hardware["required_gpu_compute_processes"])
    maximum = int(hardware["maximum_gpu_compute_processes"])
    if not minimum <= len(ids) <= maximum:
        raise ValueError("resource control process inventory differs")


def _process_ids(sample: Mapping[str, Any]) -> list[int]:
    ids = sample.get("compute_process_ids")
    if not isinstance(ids, list) or any(
        not isinstance(process_id, int) or isinstance(process_id, bool)
        for process_id in ids
    ):
        raise ValueError("resource process telemetry differs")
    return ids


def _sample_list(report: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    samples = report.get(field)
    if not isinstance(samples, list) or not samples or not all(
        isinstance(sample, Mapping) for sample in samples
    ):
        raise ValueError(f"resource {field} is absent")
    return samples


def _number(value: Mapping[str, Any], field: str) -> float:
    number = value.get(field)
    if not isinstance(number, (int, float)) or isinstance(number, bool):
        raise ValueError(f"resource numeric telemetry differs: {field}")
    return float(number)


def _numbers_close(left: Any, right: Any) -> bool:
    return (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
        and math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    )


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _source_record(
    source_manifest: Mapping[str, Any], name: str
) -> Mapping[str, Any]:
    files = source_manifest.get("files")
    record = files.get(name) if isinstance(files, Mapping) else None
    if not isinstance(record, Mapping):
        raise ValueError(f"source manifest record is absent: {name}")
    return record


def _validate_file_record(
    files: Mapping[str, Any], name: str, content: bytes
) -> None:
    record = files.get(name)
    if (
        not isinstance(record, Mapping)
        or record.get("bytes") != len(content)
        or record.get("sha256") != hashlib.sha256(content).hexdigest()
    ):
        raise ValueError(f"resource checkpoint file hash or size differs: {name}")


def _read_tar_object(archive: tarfile.TarFile, name: str) -> dict[str, Any]:
    return _read_json_bytes(_read_tar_bytes(archive, name), label=name)


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
        return _read_json_bytes(path.read_bytes(), label=str(path))
    except OSError as error:
        raise ValueError(f"invalid JSON object: {path}") from error


def _read_json_bytes(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON object: {label}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {label}")
    return payload


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"resource mapping is absent: {label}")
    return value


def _sha256_json(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
