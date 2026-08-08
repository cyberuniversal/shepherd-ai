"""Binding and completion checks for MultiUAV resource conditions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_experiment import EvaluationCase
from shepherd_ai.multiuav_resource_protocol import (
    EXPECTED_CASES,
    EXPECTED_CONDITIONS,
    EXPECTED_ROWS,
    RESOURCE_PROTOCOL_VERSION,
    RESOURCE_SCHEDULE_VERSION,
    sha256_file,
)


def load_bound_resource_config(
    artifact: Mapping[str, Any], *, repetition: int, condition_order: int
) -> RunConfig:
    """Select one config and revalidate its stored schema-v3 hash."""

    if artifact.get("status") != "final_resource_configs_bound_no_measurement_started":
        raise ValueError("resource run configs are not final and inference-safe")
    records = artifact.get("configs")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError("resource config artifact requires config records")
    matches = [
        record
        for record in records
        if isinstance(record, Mapping)
        and isinstance(record.get("config"), Mapping)
        and record["config"].get("resource_repetition") == repetition
        and record["config"].get("resource_condition_order") == condition_order
    ]
    if len(matches) != 1:
        raise ValueError("resource condition must appear exactly once")
    record = matches[0]
    payload = dict(record["config"])
    payload["methods"] = tuple(payload["methods"])
    config = RunConfig(**payload)
    if config.to_dict() != dict(record):
        raise ValueError("stored resource config hash or payload is invalid")
    if artifact.get("code_commit") != config.code_commit:
        raise ValueError("resource artifact and condition commits differ")
    return config


def validate_resource_bindings(
    *,
    config_artifact: Mapping[str, Any],
    config: RunConfig,
    schedule: Mapping[str, Any],
    hardware_protocol: Mapping[str, Any],
    accuracy_manifest: Mapping[str, Any],
    schedule_path: Path,
    hardware_protocol_path: Path,
    accuracy_manifest_path: Path,
    intervention_dataset_path: Path,
) -> None:
    """Reject schedule, protocol, dataset, or condition drift before loading."""

    schedule_hash = sha256_file(schedule_path)
    hardware_hash = sha256_file(hardware_protocol_path)
    manifest_hash = sha256_file(accuracy_manifest_path)
    dataset_hash = sha256_file(intervention_dataset_path)
    expected_bindings = {
        "resource_schedule_sha256": schedule_hash,
        "hardware_protocol_sha256": hardware_hash,
        "accuracy_manifest_sha256": manifest_hash,
        "intervention_dataset_sha256": dataset_hash,
    }
    for key, expected in expected_bindings.items():
        if config_artifact.get(key) != expected:
            raise ValueError(f"resource config artifact binding mismatch: {key}")
    if config.dataset_sha256 != manifest_hash:
        raise ValueError("resource config is not bound to the approved manifest")
    if config.hardware_protocol_sha256 != hardware_hash:
        raise ValueError("resource config is not bound to the hardware protocol")
    if config.resource_schedule_sha256 != schedule_hash:
        raise ValueError("resource config is not bound to the final schedule")
    if schedule.get("schedule_version") != RESOURCE_SCHEDULE_VERSION:
        raise ValueError("resource schedule version differs from the frozen version")
    if schedule.get("status") != "final_resource_schedule_bound_no_measurement_started":
        raise ValueError("resource schedule is not final")
    if hardware_protocol.get("protocol_version") != RESOURCE_PROTOCOL_VERSION:
        raise ValueError("resource hardware protocol version differs")
    if hardware_protocol.get("status") != (
        "final_resource_hardware_protocol_no_measurement_started"
    ):
        raise ValueError("resource hardware protocol is not final")
    if accuracy_manifest.get("data_status") != "approved_evaluation_data":
        raise ValueError("resource execution data is not approved")
    schedule_bindings = schedule.get("artifact_bindings", {})
    for key, expected in (
        ("accuracy_manifest_sha256", manifest_hash),
        ("intervention_dataset_sha256", dataset_hash),
        ("hardware_protocol_sha256", hardware_hash),
    ):
        if schedule_bindings.get(key) != expected:
            raise ValueError(f"resource schedule binding mismatch: {key}")
    conditions = schedule.get("condition_schedule", {}).get("rows", [])
    match = [
        row
        for row in conditions
        if row.get("repetition") == config.resource_repetition
        and row.get("condition_order") == config.resource_condition_order
    ]
    if len(match) != 1:
        raise ValueError("bound resource condition is absent from the schedule")
    row = match[0]
    if row.get("model_id") != config.model_id or row.get("method_id") not in (
        config.methods
    ):
        raise ValueError("resource condition model or method differs from schedule")
    expected = schedule.get("expected", {})
    if expected.get("conditions") != EXPECTED_CONDITIONS or expected.get(
        "total_method_case_rows"
    ) != EXPECTED_ROWS:
        raise ValueError("resource schedule dimensions differ from registration")


def ordered_resource_cases(
    cases: Iterable[EvaluationCase],
    *,
    schedule: Mapping[str, Any],
    repetition: int,
) -> tuple[EvaluationCase, ...]:
    """Return the 150 approved cases in the frozen repetition order."""

    by_id = {case.case_id: case for case in cases}
    rows = [
        row
        for row in schedule.get("case_schedule", {}).get("rows", [])
        if row.get("repetition") == repetition
    ]
    rows.sort(key=lambda row: int(row["case_order"]))
    if len(rows) != EXPECTED_CASES or [row["case_order"] for row in rows] != list(
        range(1, EXPECTED_CASES + 1)
    ):
        raise ValueError("resource case order is incomplete")
    case_ids = [str(row["case_id"]) for row in rows]
    if len(set(case_ids)) != EXPECTED_CASES or not set(case_ids) <= set(by_id):
        raise ValueError("resource case schedule is not covered by approved cases")
    return tuple(by_id[case_id] for case_id in case_ids)


def warmup_case_id(schedule: Mapping[str, Any], *, repetition: int) -> str:
    rows = [
        row
        for row in schedule.get("case_schedule", {}).get("warmup_cases", [])
        if row.get("repetition") == repetition
    ]
    if len(rows) != 1 or not str(rows[0].get("case_id", "")):
        raise ValueError("resource warm-up case is absent")
    if rows[0].get("warmup_output_retained") is not False:
        raise ValueError("resource warm-up output policy changed")
    return str(rows[0]["case_id"])


def summarize_resource_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: RunConfig,
    start_control_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate condition completeness without reading model outputs or labels."""

    invalid: list[str] = []
    segments: set[str] = set()
    start_control_hashes: dict[str, str] = {}
    if len(rows) != EXPECTED_CASES:
        invalid.append("condition row count is not 150")
    for row in rows:
        result = row.get("result")
        if not isinstance(result, Mapping):
            invalid.append(f"{row.get('result_key')}: result is absent")
            continue
        measurement = result.get("resource_measurement")
        if not isinstance(measurement, Mapping) or measurement.get("valid") is not True:
            invalid.append(f"{row.get('result_key')}: resource measurement is invalid")
            continue
        run_control = measurement.get("run_control")
        if not isinstance(run_control, Mapping):
            invalid.append(f"{row.get('result_key')}: run control is absent")
            continue
        if run_control.get("protocol_sha256") != config.hardware_protocol_sha256:
            invalid.append(f"{row.get('result_key')}: protocol hash differs")
        segment_id = str(run_control.get("segment_id", ""))
        if not segment_id:
            invalid.append(f"{row.get('result_key')}: segment id is absent")
        else:
            segments.add(segment_id)
            control_hash = str(run_control.get("start_control_sha256", ""))
            if len(control_hash) != 64:
                invalid.append(
                    f"{row.get('result_key')}: start-control hash is absent"
                )
            elif segment_id in start_control_hashes and (
                start_control_hashes[segment_id] != control_hash
            ):
                invalid.append(
                    f"{row.get('result_key')}: segment start-control hash differs"
                )
            else:
                start_control_hashes[segment_id] = control_hash
    if start_control_dir is not None:
        invalid.extend(
            _validate_start_control_reports(
                start_control_hashes,
                start_control_dir=start_control_dir,
                protocol_sha256=str(config.hardware_protocol_sha256),
            )
        )
    return {
        "schema_version": 1,
        "status": (
            "complete_valid_resource_condition"
            if not invalid
            else "complete_or_partial_invalid_resource_condition"
        ),
        "valid": not invalid,
        "expected_rows": EXPECTED_CASES,
        "observed_rows": len(rows),
        "invalid_rows_or_controls": len(invalid),
        "errors": invalid,
        "segments": sorted(segments),
        "segment_count": len(segments),
        "start_control_reports_validated": (
            len(start_control_hashes) if start_control_dir is not None else 0
        ),
        "raw_model_outputs_inspected": False,
        "hidden_labels_inspected": False,
    }


def _validate_start_control_reports(
    expected: Mapping[str, str],
    *,
    start_control_dir: Path,
    protocol_sha256: str,
) -> list[str]:
    errors: list[str] = []
    hardware_lock: Mapping[str, Any] | None = None
    for segment_id, expected_hash in sorted(expected.items()):
        if Path(segment_id).name != segment_id:
            errors.append(f"{segment_id}: unsafe start-control segment id")
            continue
        path = start_control_dir / f"{segment_id}.json"
        if not path.is_file():
            errors.append(f"{segment_id}: start-control report is absent")
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{segment_id}: invalid start-control report: {error}")
            continue
        if not isinstance(report, Mapping):
            errors.append(f"{segment_id}: start-control report is not an object")
            continue
        stored_hash = report.get("sha256")
        payload = dict(report)
        payload.pop("sha256", None)
        observed_hash = _sha256_json(payload)
        if stored_hash != expected_hash or observed_hash != expected_hash:
            errors.append(f"{segment_id}: start-control report hash differs")
        if report.get("status") != "resource_start_control_passed":
            errors.append(f"{segment_id}: start-control status is not passed")
        if report.get("protocol_sha256") != protocol_sha256:
            errors.append(f"{segment_id}: start-control protocol differs")
        if report.get("measurement_started") is not False:
            errors.append(f"{segment_id}: start-control measurement flag differs")
        warmup = report.get("warmup")
        if not isinstance(warmup, Mapping) or warmup.get(
            "complete_method_cases"
        ) != 1 or warmup.get("output_retained") is not False:
            errors.append(f"{segment_id}: warm-up evidence is invalid")
        current_lock = report.get("hardware_lock")
        if not isinstance(current_lock, Mapping):
            errors.append(f"{segment_id}: hardware lock is absent")
        elif hardware_lock is None:
            hardware_lock = current_lock
        elif current_lock != hardware_lock:
            errors.append(f"{segment_id}: hardware lock differs across segments")
    return errors


def _sha256_json(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
