"""Gate-bound execution of the frozen MultiUAV accuracy scorer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_scoring import (
    SCORING_CONTRACT_VERSION,
    load_official_command_labels,
    score_accuracy_matrix,
    scoring_contract,
)


SCORING_RUN_VERSION = "multiuav_accuracy_scoring_run_v1"
_ADMISSION_STATUS = "complete_accuracy_matrices_admitted_for_scoring"
_ADMISSION_NEXT_GATE = "label_separated_deterministic_scoring_authorized_not_started"
_CONFIG_STATUS = "final_accuracy_configs_bound_no_inference_started"
_CHECKPOINT_MEMBERS = frozenset(
    {"manifest.json", "results.jsonl", "run_config.json"}
)


def score_admitted_study(
    *,
    repository_root: Path,
    admission_path: Path,
    manifest_path: Path,
    dataset_path: Path,
    protocol_path: Path,
    run_configs_path: Path,
    source_archive_path: Path,
    checkpoint_paths: Iterable[Path],
    output_dir: Path,
) -> dict[str, Any]:
    """Score both admitted matrices and keep derived rows separate from summaries."""

    repository_root = repository_root.resolve()
    admission_path = admission_path.resolve()
    manifest_path = manifest_path.resolve()
    dataset_path = dataset_path.resolve()
    protocol_path = protocol_path.resolve()
    run_configs_path = run_configs_path.resolve()
    source_archive_path = source_archive_path.resolve()
    output_dir = output_dir.resolve()

    gate = validate_admission_for_scoring(
        repository_root=repository_root,
        admission_path=admission_path,
        manifest_path=manifest_path,
        run_configs_path=run_configs_path,
        checkpoint_paths=checkpoint_paths,
    )
    manifest = _read_object(manifest_path)
    dataset = _read_object(dataset_path)
    protocol = _read_object(protocol_path)
    _validate_scoring_protocol(protocol)
    if protocol.get("dataset", {}).get("dataset_sha256") != _sha256_file(
        dataset_path
    ):
        raise ValueError("study dataset hash differs from the frozen protocol")

    # Hidden official command labels are intentionally loaded only after the
    # complete two-model admission gate above succeeds.
    official_commands = load_official_command_labels(source_archive_path, manifest)

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_reports: list[dict[str, Any]] = []
    for model_id in sorted(gate["configs"]):
        config = gate["configs"][model_id]
        binding = gate["matrices"][model_id]
        checkpoint_path = gate["checkpoints"][model_id]
        checkpoint_rows = _load_checkpoint_rows(
            checkpoint_path,
            expected_rows=int(binding["rows"]),
            expected_results_sha256=str(binding["results_sha256"]),
        )
        scored = score_accuracy_matrix(
            config=config,
            checkpoint_rows=checkpoint_rows,
            dataset=dataset,
            manifest=manifest,
            official_commands_by_source=official_commands,
        )
        slug = "qwen25_3b" if "3B" in model_id else "qwen25_7b"
        scored_archive = output_dir / f"{slug}_scored_rows.zip"
        archive_record = write_scored_rows_archive(
            rows=scored["scored_rows"],
            output_path=scored_archive,
            metadata={
                "schema_version": 1,
                "scoring_run_version": SCORING_RUN_VERSION,
                "scoring_contract_version": SCORING_CONTRACT_VERSION,
                "model_id": config.model_id,
                "model_revision": config.model_revision,
                "config_hash": config.config_hash,
                "checkpoint_sha256": binding["checkpoint_sha256"],
                "checkpoint_results_sha256": binding["results_sha256"],
                "admission_sha256": _sha256_file(admission_path),
                "rows": len(scored["scored_rows"]),
            },
        )
        try:
            archive_record["path"] = scored_archive.relative_to(
                repository_root
            ).as_posix()
        except ValueError:
            archive_record["path"] = scored_archive.as_posix()
        matrix_reports.append(
            {
                "model_id": config.model_id,
                "model_revision": config.model_revision,
                "config_hash": config.config_hash,
                "checkpoint_sha256": binding["checkpoint_sha256"],
                "checkpoint_results_sha256": binding["results_sha256"],
                "rows": len(scored["scored_rows"]),
                "scored_rows_archive": archive_record,
                "admission": scored["admission"],
                "summary": scored["summary"],
            }
        )

    return {
        "schema_version": 1,
        "scoring_run_version": SCORING_RUN_VERSION,
        "scoring_contract_version": SCORING_CONTRACT_VERSION,
        "status": "accuracy_scoring_complete_cluster_analysis_pending",
        "claim_status": "descriptive_scores_computed_not_yet_cluster_analyzed",
        "artifact_bindings": {
            "admission_sha256": _sha256_file(admission_path),
            "accuracy_manifest_sha256": _sha256_file(manifest_path),
            "intervention_dataset_sha256": _sha256_file(dataset_path),
            "accuracy_protocol_sha256": _sha256_file(protocol_path),
            "accuracy_run_configs_sha256": _sha256_file(run_configs_path),
            "source_archive_sha256": _sha256_file(source_archive_path),
        },
        "source_code_sha256": _scoring_source_hashes(repository_root),
        "models": len(matrix_reports),
        "rows_total": sum(int(report["rows"]) for report in matrix_reports),
        "matrices": matrix_reports,
        "hidden_labels_accessed_after_admission": True,
        "scores_computed": True,
        "scores_inspected": True,
        "models_invoked": False,
        "next_gate": "registered_source_cluster_bootstrap_analysis_not_started",
    }


def validate_admission_for_scoring(
    *,
    repository_root: Path,
    admission_path: Path,
    manifest_path: Path,
    run_configs_path: Path,
    checkpoint_paths: Iterable[Path],
) -> dict[str, Any]:
    """Validate the committed score-blind boundary before label access."""

    repository_root = repository_root.resolve()
    admission_path = admission_path.resolve()
    manifest_path = manifest_path.resolve()
    run_configs_path = run_configs_path.resolve()
    admission = _read_object(admission_path)
    if admission.get("status") != _ADMISSION_STATUS or admission.get("valid") is not True:
        raise ValueError("complete score-blind admission is absent")
    if admission.get("next_gate") != _ADMISSION_NEXT_GATE:
        raise ValueError("admission does not authorize deterministic scoring")
    if admission.get("scores_inspected") is not False:
        raise ValueError("admission is not score-blind")
    if admission.get("hidden_labels_accessed") is not False:
        raise ValueError("hidden labels were accessed before admission")
    if admission.get("scored_rows") != 0:
        raise ValueError("admission artifact already reports scored rows")
    bindings = admission.get("artifact_bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("admission artifact bindings are absent")
    if bindings.get("accuracy_manifest_sha256") != _sha256_file(manifest_path):
        raise ValueError("admission manifest binding mismatch")
    if bindings.get("accuracy_run_configs_sha256") != _sha256_file(run_configs_path):
        raise ValueError("admission run-config binding mismatch")
    _validate_admission_source_hashes(admission, repository_root)

    registry = _read_object(run_configs_path)
    configs = _load_configs(registry)
    matrix_rows = admission.get("matrices")
    if not isinstance(matrix_rows, list) or not matrix_rows:
        raise ValueError("admission matrix records are absent")
    matrices: dict[str, dict[str, Any]] = {}
    for row in matrix_rows:
        if not isinstance(row, Mapping) or row.get("valid") is not True:
            raise ValueError("admission contains an invalid matrix")
        if row.get("scores_inspected") is not False:
            raise ValueError("matrix admission is not score-blind")
        if row.get("hidden_labels_accessed") is not False:
            raise ValueError("matrix labels were accessed before scoring")
        model_id = str(row.get("model_id", ""))
        if not model_id or model_id in matrices:
            raise ValueError("admission model ids are empty or duplicated")
        matrices[model_id] = dict(row)
    if set(matrices) != set(configs):
        raise ValueError("admission models differ from frozen run configs")

    checkpoints: dict[str, Path] = {}
    for path in checkpoint_paths:
        resolved = path.resolve()
        digest = _sha256_file(resolved)
        matches = [
            model_id
            for model_id, row in matrices.items()
            if row.get("checkpoint_sha256") == digest
        ]
        if len(matches) != 1:
            raise ValueError("checkpoint hash is absent or duplicated in admission")
        model_id = matches[0]
        if model_id in checkpoints:
            raise ValueError(f"duplicate checkpoint supplied for {model_id}")
        checkpoints[model_id] = resolved
    if set(checkpoints) != set(configs):
        raise ValueError("checkpoint set differs from admitted models")

    for model_id, config in configs.items():
        row = matrices[model_id]
        if row.get("model_revision") != config.model_revision:
            raise ValueError("admission model revision differs from frozen config")
        if row.get("config_hash") != config.config_hash:
            raise ValueError("admission config hash differs from frozen config")
        if row.get("rows") != registry.get("expected_rows_per_model"):
            raise ValueError("admission row count differs from frozen config")
    if sum(int(row["rows"]) for row in matrices.values()) != registry.get(
        "expected_rows_total"
    ):
        raise ValueError("admission total differs from frozen run configs")
    return {
        "admission": admission,
        "configs": configs,
        "matrices": matrices,
        "checkpoints": checkpoints,
    }


def write_scored_rows_archive(
    *,
    rows: Iterable[Mapping[str, Any]],
    output_path: Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Write deterministic derived-row evidence separately from its summary."""

    materialized = [dict(row) for row in rows]
    encoded_rows = b"".join(
        (_canonical_json(row) + "\n").encode("utf-8") for row in materialized
    )
    encoded_metadata = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    manifest = {
        "schema_version": 1,
        "row_count": len(materialized),
        "files": {
            "scored_rows.jsonl": _content_record(encoded_rows),
            "scoring_metadata.json": _content_record(encoded_metadata),
        },
    }
    encoded_manifest = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(
            {
                "manifest.json": encoded_manifest,
                "scored_rows.jsonl": encoded_rows,
                "scoring_metadata.json": encoded_metadata,
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
        "scored_rows_sha256": hashlib.sha256(encoded_rows).hexdigest(),
    }


def _load_checkpoint_rows(
    checkpoint_path: Path,
    *,
    expected_rows: int,
    expected_results_sha256: str,
) -> list[dict[str, Any]]:
    try:
        archive = ZipFile(checkpoint_path)
    except (BadZipFile, OSError) as error:
        raise ValueError(f"invalid checkpoint archive: {checkpoint_path}") from error
    with archive:
        names = [info.filename for info in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != _CHECKPOINT_MEMBERS:
            raise ValueError("checkpoint members differ from admitted schema")
        rows: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        with archive.open("results.jsonl") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                digest.update(raw_line)
                if not raw_line.strip():
                    raise ValueError(f"blank scored input row at line {line_number}")
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"invalid scored input JSON at line {line_number}"
                    ) from error
                if not isinstance(row, dict):
                    raise ValueError(f"scored input row {line_number} is not an object")
                rows.append(row)
    if len(rows) != expected_rows:
        raise ValueError("checkpoint row count differs from admission")
    if digest.hexdigest() != expected_results_sha256:
        raise ValueError("checkpoint result hash differs from admission")
    return rows


def _validate_scoring_protocol(protocol: Mapping[str, Any]) -> None:
    if protocol.get("study_scores_inspected") is not False:
        raise ValueError("accuracy protocol was not frozen score-blind")
    if protocol.get("scoring_contract_version") != SCORING_CONTRACT_VERSION:
        raise ValueError("scoring contract version differs from frozen protocol")
    if protocol.get("scoring_contract") != scoring_contract():
        raise ValueError("scoring contract differs from frozen protocol")


def _load_configs(registry: Mapping[str, Any]) -> dict[str, RunConfig]:
    if registry.get("status") != _CONFIG_STATUS:
        raise ValueError("accuracy run configs are not frozen")
    records = registry.get("configs")
    if not isinstance(records, list) or not records:
        raise ValueError("accuracy run config registry is empty")
    configs: dict[str, RunConfig] = {}
    for record in records:
        if not isinstance(record, Mapping) or not isinstance(
            record.get("config"), Mapping
        ):
            raise ValueError("run config record is malformed")
        payload = dict(record["config"])
        methods = payload.get("methods")
        if not isinstance(methods, list):
            raise ValueError("run config methods are malformed")
        payload["methods"] = tuple(str(method) for method in methods)
        try:
            config = RunConfig(**payload)
        except TypeError as error:
            raise ValueError("run config fields differ from schema") from error
        config.validate()
        if dict(record) != config.to_dict():
            raise ValueError("run config payload or hash mismatch")
        if config.model_id in configs:
            raise ValueError(f"duplicate model config: {config.model_id}")
        configs[config.model_id] = config
    return configs


def _validate_admission_source_hashes(
    admission: Mapping[str, Any], repository_root: Path
) -> None:
    expected = admission.get("source_code_sha256")
    if not isinstance(expected, Mapping):
        raise ValueError("admission source hashes are absent")
    paths = {
        "multiuav_admission.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_admission.py",
        "multiuav_publication.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_publication.py",
        "admit_multiuav_accuracy_matrices.py": repository_root
        / "scripts"
        / "admit_multiuav_accuracy_matrices.py",
    }
    if set(expected) != set(paths):
        raise ValueError("admission source inventory mismatch")
    for name, path in paths.items():
        if expected.get(name) != _sha256_file(path):
            raise ValueError(f"admission source hash mismatch: {name}")


def _scoring_source_hashes(repository_root: Path) -> dict[str, str]:
    paths = {
        "multiuav_study_scoring.py": Path(__file__).resolve(),
        "multiuav_scoring.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_scoring.py",
        "multiuav_publication.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_publication.py",
        "multiuav_grounding_validator.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_grounding_validator.py",
        "multiuav_plan_contract.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_plan_contract.py",
        "score_multiuav_accuracy_matrices.py": repository_root
        / "scripts"
        / "score_multiuav_accuracy_matrices.py",
    }
    return {name: _sha256_file(path) for name, path in sorted(paths.items())}


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
