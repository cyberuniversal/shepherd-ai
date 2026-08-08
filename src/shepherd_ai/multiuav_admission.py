"""Score-blind admission for sealed MultiUAV accuracy checkpoints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from zipfile import BadZipFile, ZipFile

from shepherd_ai.multiuav_checkpoints import (
    CHECKPOINT_SCHEMA_VERSION,
    RunConfig,
)
from shepherd_ai.multiuav_publication import validate_accuracy_publication_matrix


_ARCHIVE_MEMBERS = frozenset(
    {"manifest.json", "results.jsonl", "run_config.json"}
)
_COMPLETE_STATUS = "complete_accuracy_matrix_raw_results_unscored"
_FROZEN_CONFIG_STATUS = "final_accuracy_configs_bound_no_inference_started"
ADMISSION_CONTRACT_VERSION = "multiuav_accuracy_admission_v1"


def admit_accuracy_checkpoint(
    *,
    checkpoint_path: Path,
    run_summary_path: Path,
    expected_config: RunConfig,
    expected_case_ids: Iterable[str],
) -> dict[str, Any]:
    """Validate one complete checkpoint without scoring or loading hidden labels."""

    checkpoint_path = checkpoint_path.resolve()
    run_summary_path = run_summary_path.resolve()
    expected_config.validate()
    archive_config, rows, archive_audit = _load_checkpoint_archive(checkpoint_path)
    if archive_config != expected_config:
        raise ValueError("checkpoint run config differs from the frozen config")

    case_ids = tuple(expected_case_ids)
    admission = validate_accuracy_publication_matrix(
        config=expected_config,
        rows=rows,
        expected_case_ids=case_ids,
    )
    summary = _read_object(run_summary_path)
    checkpoint_sha256 = _sha256_file(checkpoint_path)
    _validate_run_summary(
        summary=summary,
        config=expected_config,
        expected_rows=len(rows),
        results_sha256=archive_audit["results_sha256"],
        checkpoint_sha256=checkpoint_sha256,
    )
    if archive_audit["row_count"] != len(case_ids) * len(expected_config.methods):
        raise ValueError("checkpoint row count differs from case-method matrix")

    return {
        "valid": bool(admission["valid"]),
        "claim_status": "accuracy_matrix_admitted_for_scoring_not_yet_scored",
        "model_id": expected_config.model_id,
        "model_revision": expected_config.model_revision,
        "config_hash": expected_config.config_hash,
        "checkpoint_sha256": checkpoint_sha256,
        "run_summary_sha256": _sha256_file(run_summary_path),
        "results_sha256": archive_audit["results_sha256"],
        "cases": len(case_ids),
        "methods": list(expected_config.methods),
        "rows": len(rows),
        "archive_integrity": "passed",
        "scores_inspected": False,
        "hidden_labels_accessed": False,
    }


def admit_accuracy_study(
    *,
    manifest_path: Path,
    run_configs_path: Path,
    checkpoint_paths: Iterable[Path],
) -> dict[str, Any]:
    """Admit every frozen model matrix as one score-blind study gate."""

    manifest_path = manifest_path.resolve()
    run_configs_path = run_configs_path.resolve()
    manifest = _read_object(manifest_path)
    registry = _read_object(run_configs_path)
    case_ids = _approved_case_ids(manifest)
    manifest_sha256 = _sha256_file(manifest_path)
    configs = _load_frozen_configs(registry, manifest_sha256=manifest_sha256)

    paths_by_model: dict[str, Path] = {}
    for checkpoint_path in checkpoint_paths:
        resolved = checkpoint_path.resolve()
        config = _read_archive_config(resolved)
        if config.model_id in paths_by_model:
            raise ValueError(f"duplicate checkpoint model: {config.model_id}")
        paths_by_model[config.model_id] = resolved
    if set(paths_by_model) != set(configs):
        raise ValueError(
            "checkpoint models differ from frozen configs; "
            f"expected={sorted(configs)}, observed={sorted(paths_by_model)}"
        )

    reports = []
    for model_id in sorted(configs):
        checkpoint_path = paths_by_model[model_id]
        reports.append(
            admit_accuracy_checkpoint(
                checkpoint_path=checkpoint_path,
                run_summary_path=checkpoint_path.with_name("run_summary.json"),
                expected_config=configs[model_id],
                expected_case_ids=case_ids,
            )
        )

    expected_rows_total = sum(report["rows"] for report in reports)
    if registry.get("expected_rows_total") != expected_rows_total:
        raise ValueError("admitted row total differs from frozen run registry")
    expected_per_model = registry.get("expected_rows_per_model")
    if any(report["rows"] != expected_per_model for report in reports):
        raise ValueError("admitted model rows differ from frozen run registry")

    return {
        "schema_version": 1,
        "admission_contract_version": ADMISSION_CONTRACT_VERSION,
        "status": "complete_accuracy_matrices_admitted_for_scoring",
        "valid": True,
        "artifact_bindings": {
            "accuracy_manifest_sha256": manifest_sha256,
            "accuracy_run_configs_sha256": _sha256_file(run_configs_path),
        },
        "cases_per_model": len(case_ids),
        "models": len(reports),
        "rows_total": expected_rows_total,
        "matrices": reports,
        "scores_inspected": False,
        "hidden_labels_accessed": False,
        "scored_rows": 0,
        "next_gate": "label_separated_deterministic_scoring_authorized_not_started",
    }


def _load_checkpoint_archive(
    checkpoint_path: Path,
) -> tuple[RunConfig, list[dict[str, Any]], dict[str, Any]]:
    try:
        archive = ZipFile(checkpoint_path)
    except (BadZipFile, OSError) as error:
        raise ValueError(f"invalid checkpoint archive: {checkpoint_path}") from error
    with archive:
        names = [info.filename for info in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != _ARCHIVE_MEMBERS:
            raise ValueError("checkpoint archive members differ from the frozen schema")
        manifest_bytes = archive.read("manifest.json")
        run_config_bytes = archive.read("run_config.json")
        manifest = _read_json_bytes(manifest_bytes, label="checkpoint manifest")
        config_record = _read_json_bytes(run_config_bytes, label="checkpoint config")
        config = _run_config_from_record(config_record)
        _validate_archive_file_record(
            manifest=manifest,
            name="run_config.json",
            size=len(run_config_bytes),
            sha256=hashlib.sha256(run_config_bytes).hexdigest(),
        )

        rows: list[dict[str, Any]] = []
        results_digest = hashlib.sha256()
        results_bytes = 0
        with archive.open("results.jsonl") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                results_digest.update(raw_line)
                results_bytes += len(raw_line)
                if not raw_line.strip():
                    raise ValueError(
                        f"blank checkpoint row at archived line {line_number}"
                    )
                row = _read_json_bytes(
                    raw_line,
                    label=f"checkpoint row {line_number}",
                )
                rows.append(row)
        results_sha256 = results_digest.hexdigest()
        _validate_archive_file_record(
            manifest=manifest,
            name="results.jsonl",
            size=results_bytes,
            sha256=results_sha256,
        )
        if manifest.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("checkpoint manifest schema mismatch")
        if manifest.get("config_hash") != config.config_hash:
            raise ValueError("checkpoint manifest config hash mismatch")
        if manifest.get("row_count") != len(rows):
            raise ValueError("checkpoint manifest row count mismatch")
        return config, rows, {
            "row_count": len(rows),
            "results_bytes": results_bytes,
            "results_sha256": results_sha256,
        }


def _read_archive_config(checkpoint_path: Path) -> RunConfig:
    try:
        with ZipFile(checkpoint_path) as archive:
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)) or set(names) != _ARCHIVE_MEMBERS:
                raise ValueError(
                    "checkpoint archive members differ from the frozen schema"
                )
            record = _read_json_bytes(
                archive.read("run_config.json"),
                label="checkpoint config",
            )
    except (BadZipFile, OSError) as error:
        raise ValueError(f"invalid checkpoint archive: {checkpoint_path}") from error
    return _run_config_from_record(record)


def _load_frozen_configs(
    registry: Mapping[str, Any],
    *,
    manifest_sha256: str,
) -> dict[str, RunConfig]:
    if registry.get("status") != _FROZEN_CONFIG_STATUS:
        raise ValueError("accuracy run configs are not frozen")
    if registry.get("accuracy_manifest_sha256") != manifest_sha256:
        raise ValueError("accuracy manifest hash differs from frozen run configs")
    records = registry.get("configs")
    if not isinstance(records, list) or not records:
        raise ValueError("frozen run config registry is empty")
    configs: dict[str, RunConfig] = {}
    for record in records:
        config = _run_config_from_record(record)
        if config.run_kind != "accuracy":
            raise ValueError("frozen config registry contains a non-accuracy run")
        if config.dataset_sha256 != manifest_sha256:
            raise ValueError("run config dataset hash differs from accuracy manifest")
        if config.model_id in configs:
            raise ValueError(f"duplicate frozen model config: {config.model_id}")
        configs[config.model_id] = config
    return configs


def _run_config_from_record(record: Mapping[str, Any]) -> RunConfig:
    if not isinstance(record, Mapping):
        raise ValueError("run config record must be an object")
    payload = record.get("config")
    if not isinstance(payload, Mapping):
        raise ValueError("run config payload is absent")
    values = dict(payload)
    methods = values.get("methods")
    if not isinstance(methods, list):
        raise ValueError("run config methods must be a list")
    values["methods"] = tuple(str(method) for method in methods)
    try:
        config = RunConfig(**values)
    except TypeError as error:
        raise ValueError("run config payload fields differ from the schema") from error
    config.validate()
    if dict(record) != config.to_dict():
        raise ValueError("run config hash or payload differs from the frozen schema")
    return config


def _approved_case_ids(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    rows = manifest.get("cases")
    if not isinstance(rows, list) or not rows:
        raise ValueError("accuracy manifest contains no cases")
    if manifest.get("case_count") != len(rows):
        raise ValueError("accuracy manifest case count mismatch")
    case_ids = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"accuracy manifest case {index} is not an object")
        if row.get("case_status") != "approved_evaluation_case":
            raise ValueError(f"accuracy manifest case {index} is not approved")
        case_id = str(row.get("case_id", ""))
        if not case_id:
            raise ValueError(f"accuracy manifest case {index} has no id")
        case_ids.append(case_id)
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("accuracy manifest case ids are not unique")
    return tuple(case_ids)


def _validate_run_summary(
    *,
    summary: Mapping[str, Any],
    config: RunConfig,
    expected_rows: int,
    results_sha256: str,
    checkpoint_sha256: str,
) -> None:
    checks = {
        "status": _COMPLETE_STATUS,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "config_hash": config.config_hash,
        "expected_rows": expected_rows,
        "results_sha256": results_sha256,
        "checkpoint_zip_sha256": checkpoint_sha256,
        "scores_inspected": False,
    }
    for field, expected in checks.items():
        if summary.get(field) != expected:
            label = "checkpoint hash" if field == "checkpoint_zip_sha256" else field
            raise ValueError(f"run summary {label} mismatch")
    matrix = summary.get("matrix")
    if not isinstance(matrix, Mapping) or matrix.get("complete") is not True:
        raise ValueError("run summary matrix is not complete")
    if matrix.get("expected_rows") != expected_rows:
        raise ValueError("run summary matrix row count mismatch")


def _validate_archive_file_record(
    *,
    manifest: Mapping[str, Any],
    name: str,
    size: int,
    sha256: str,
) -> None:
    files = manifest.get("files")
    if not isinstance(files, Mapping) or set(files) != {
        "results.jsonl",
        "run_config.json",
    }:
        raise ValueError("checkpoint manifest file inventory mismatch")
    record = files.get(name)
    if not isinstance(record, Mapping):
        raise ValueError(f"checkpoint manifest record is absent: {name}")
    if record.get("bytes") != size or record.get("sha256") != sha256:
        raise ValueError(f"checkpoint archived file hash or size mismatch: {name}")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON object: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _read_json_bytes(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON: {label}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {label}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
