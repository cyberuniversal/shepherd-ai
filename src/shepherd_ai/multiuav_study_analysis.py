"""Registered source-cluster bootstrap analysis for MultiUAV scores."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from shepherd_ai.multiuav_statistics import paired_cluster_bootstrap


ANALYSIS_RUN_VERSION = "multiuav_accuracy_cluster_bootstrap_v1"
_SCORING_STATUS = "accuracy_scoring_complete_cluster_analysis_pending"
_SCORING_NEXT_GATE = "registered_source_cluster_bootstrap_analysis_not_started"
_EXPECTED_VARIANTS = frozenset(
    {
        "canonical_execute",
        "official_alias_execute",
        "missing_information_clarify",
        "restored_information_execute",
        "resource_conflict_block",
    }
)
_SCORED_ARCHIVE_MEMBERS = frozenset(
    {"manifest.json", "scored_rows.jsonl", "scoring_metadata.json"}
)


def analyze_scored_study(
    *,
    repository_root: Path,
    scoring_summary_path: Path,
    protocol_path: Path,
    intervention_dataset_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Run every registered model, contrast, and primary-outcome analysis."""

    repository_root = repository_root.resolve()
    scoring_summary_path = scoring_summary_path.resolve()
    protocol_path = protocol_path.resolve()
    intervention_dataset_path = intervention_dataset_path.resolve()
    output_dir = output_dir.resolve()
    scoring_summary = _read_object(scoring_summary_path)
    protocol = _read_object(protocol_path)
    _validate_scoring_boundary(scoring_summary, repository_root, protocol_path)
    analysis_spec = _analysis_spec(protocol)
    session_by_cluster = _load_session_bindings(intervention_dataset_path)

    model_reports: list[dict[str, Any]] = []
    cluster_evidence: list[dict[str, Any]] = []
    draw_evidence: list[dict[str, Any]] = []
    session_statistics: list[dict[str, Any]] = []
    failure_reports: list[dict[str, Any]] = []
    failure_cases: list[dict[str, Any]] = []
    matrices = scoring_summary.get("matrices")
    if not isinstance(matrices, list) or not matrices:
        raise ValueError("scoring summary matrix records are absent")
    for matrix in matrices:
        if not isinstance(matrix, Mapping):
            raise ValueError("scoring summary matrix record is malformed")
        archive_record = matrix.get("scored_rows_archive")
        if not isinstance(archive_record, Mapping):
            raise ValueError("scored-row archive binding is absent")
        archive_path = repository_root / str(archive_record.get("path", ""))
        rows = _load_scored_rows(archive_path, archive_record)
        model_id = str(matrix.get("model_id", ""))
        reports, clusters, draws = analyze_scored_rows(
            rows=rows,
            protocol=protocol,
            model_id=model_id,
        )
        model_reports.append(
            {
                "model_id": model_id,
                "model_revision": matrix.get("model_revision"),
                "scored_rows_archive_sha256": archive_record.get("sha256"),
                "analyses": reports,
            }
        )
        cluster_evidence.extend(clusters)
        draw_evidence.extend(draws)
        model_session_statistics = summarize_scored_rows_by_session(
            rows=rows,
            session_by_cluster=session_by_cluster,
            model_id=model_id,
        )
        session_statistics.extend(model_session_statistics)
        failure_report, model_failure_cases = summarize_scored_failures(
            rows=rows,
            session_by_cluster=session_by_cluster,
            model_id=model_id,
        )
        failure_reports.extend(failure_report)
        failure_cases.extend(model_failure_cases)

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "bootstrap_evidence.zip"
    evidence_record = write_bootstrap_evidence_archive(
        cluster_summaries=cluster_evidence,
        draw_records=draw_evidence,
        output_path=evidence_path,
        metadata={
            "schema_version": 1,
            "analysis_run_version": ANALYSIS_RUN_VERSION,
            "scoring_summary_sha256": _sha256_file(scoring_summary_path),
            "accuracy_protocol_sha256": _sha256_file(protocol_path),
            "intervention_dataset_sha256": _sha256_file(
                intervention_dataset_path
            ),
            **analysis_spec,
        },
    )
    try:
        evidence_record["path"] = evidence_path.relative_to(repository_root).as_posix()
    except ValueError:
        evidence_record["path"] = evidence_path.as_posix()

    return {
        "schema_version": 1,
        "analysis_run_version": ANALYSIS_RUN_VERSION,
        "status": "accuracy_cluster_bootstrap_complete_figures_pending",
        "claim_status": "registered_paired_intervals_computed_reporting_pending",
        "artifact_bindings": {
            "scoring_summary_sha256": _sha256_file(scoring_summary_path),
            "accuracy_protocol_sha256": _sha256_file(protocol_path),
            "intervention_dataset_sha256": _sha256_file(
                intervention_dataset_path
            ),
        },
        "source_code_sha256": _analysis_source_hashes(repository_root),
        "analysis_spec": analysis_spec,
        "models": len(model_reports),
        "registered_analyses": sum(
            len(model["analyses"]) for model in model_reports
        ),
        "model_results": model_reports,
        "descriptive_session_statistics": {
            "analysis_status": "post_hoc_descriptive_no_inference",
            "session_rows": session_statistics,
            "aggregate_rows": aggregate_session_statistics(session_statistics),
        },
        "descriptive_failure_analysis": {
            "analysis_status": "post_hoc_descriptive_no_inference",
            "method_rows": failure_reports,
            "failure_case_rows": failure_cases,
        },
        "bootstrap_evidence_archive": evidence_record,
        "null_hypothesis_tests_run": False,
        "resource_analysis_included": False,
        "next_gate": "accuracy_figures_and_resource_experiment_pending",
    }


def summarize_scored_rows_by_session(
    *,
    rows: Iterable[Mapping[str, Any]],
    session_by_cluster: Mapping[str, str],
    model_id: str,
) -> list[dict[str, Any]]:
    """Return transparent per-session descriptive rates for each frozen method."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for source in rows:
        row = dict(source)
        cluster_id = str(row.get("cluster_id", ""))
        try:
            session_id = session_by_cluster[cluster_id]
        except KeyError as error:
            raise ValueError(f"session binding is absent: {cluster_id}") from error
        method_id = str(row.get("method_id", ""))
        if not method_id:
            raise ValueError("scored row method id is absent")
        grouped.setdefault((session_id, method_id), []).append(row)

    summaries: list[dict[str, Any]] = []
    nonexecution_variants = {
        "missing_information_clarify",
        "resource_conflict_block",
    }
    for (session_id, method_id), group in sorted(grouped.items()):
        nonexecution = [
            row for row in group if row.get("variant") in nonexecution_variants
        ]
        executable = [
            row for row in group if row.get("variant") not in nonexecution_variants
        ]
        unsafe = sum(bool(row.get("unsafe_proceed")) for row in nonexecution)
        strict_success = sum(bool(row.get("end_to_end_success")) for row in group)
        static_fidelity = sum(
            bool(row.get("static_plan_fidelity")) for row in executable
        )
        summaries.append(
            {
                "model_id": model_id,
                "method_id": method_id,
                "method_label": _method_label(method_id),
                "session_id": session_id,
                "clusters": len({str(row["cluster_id"]) for row in group}),
                "cases": len(group),
                "nonexecution_cases": len(nonexecution),
                "unsafe_proceed_nonexecution": unsafe,
                "unsafe_proceed_rate_nonexecution": _rate(
                    unsafe, len(nonexecution)
                ),
                "all_nonexecution_contained": unsafe == 0,
                "executable_cases": len(executable),
                "static_plan_fidelity_execute": static_fidelity,
                "static_plan_fidelity_rate_execute": _rate(
                    static_fidelity, len(executable)
                ),
                "false_nonexecution_execute": sum(
                    bool(row.get("false_nonexecution")) for row in executable
                ),
                "parse_errors": sum(bool(row.get("parse_error")) for row in group),
                "strict_success_cases": strict_success,
                "strict_success_rate": _rate(strict_success, len(group)),
            }
        )
    return summaries


def aggregate_session_statistics(
    session_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate session rows without treating sessions as inferential replicates."""

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in session_rows:
        key = (str(row["model_id"]), str(row["method_id"]))
        grouped.setdefault(key, []).append(row)
    aggregates = []
    for (model_id, method_id), group in sorted(grouped.items()):
        aggregates.append(
            {
                "model_id": model_id,
                "method_id": method_id,
                "method_label": _method_label(method_id),
                "sessions": len(group),
                "clusters": sum(int(row["clusters"]) for row in group),
                "cases": sum(int(row["cases"]) for row in group),
                "mean_session_unsafe_proceed_rate_nonexecution": statistics.fmean(
                    float(row["unsafe_proceed_rate_nonexecution"]) for row in group
                ),
                "sessions_with_any_unsafe_proceed": sum(
                    int(row["unsafe_proceed_nonexecution"]) > 0 for row in group
                ),
                "sessions_with_all_nonexecution_contained": sum(
                    bool(row["all_nonexecution_contained"]) for row in group
                ),
                "mean_session_static_plan_fidelity_rate_execute": statistics.fmean(
                    float(row["static_plan_fidelity_rate_execute"]) for row in group
                ),
                "mean_session_strict_success_rate": statistics.fmean(
                    float(row["strict_success_rate"]) for row in group
                ),
                "sessions_with_any_strict_success": sum(
                    int(row["strict_success_cases"]) > 0 for row in group
                ),
            }
        )
    return aggregates


def summarize_scored_failures(
    *,
    rows: Iterable[Mapping[str, Any]],
    session_by_cluster: Mapping[str, str],
    model_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Describe scored failure modes and return non-sensitive failure-case rows."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    nonexecution_variants = {
        "missing_information_clarify",
        "resource_conflict_block",
    }
    for source in rows:
        row = dict(source)
        cluster_id = str(row.get("cluster_id", ""))
        if cluster_id not in session_by_cluster:
            raise ValueError(f"session binding is absent: {cluster_id}")
        method_id = str(row.get("method_id", ""))
        grouped.setdefault(method_id, []).append(row)
        if not bool(row.get("end_to_end_success")) or bool(row.get("unsafe_proceed")):
            failures.append(
                {
                    "model_id": model_id,
                    "method_id": method_id,
                    "method_label": _method_label(method_id),
                    "session_id": session_by_cluster[cluster_id],
                    "cluster_id": cluster_id,
                    "source_task_id": str(row.get("source_task_id", "")),
                    "case_id": str(row.get("case_id", "")),
                    "variant": str(row.get("variant", "")),
                    "containment_stage": str(row.get("containment_stage", "")),
                    "parse_error": bool(row.get("parse_error")),
                    "backend_error": bool(row.get("backend_error")),
                    "false_nonexecution": bool(row.get("false_nonexecution")),
                    "unsafe_proceed": bool(row.get("unsafe_proceed")),
                    "endpoint_fidelity": bool(row.get("endpoint_fidelity")),
                    "parameter_grounding_fidelity": bool(
                        row.get("parameter_grounding_fidelity")
                    ),
                    "official_command_fidelity": bool(
                        row.get("official_command_fidelity")
                    ),
                    "static_plan_fidelity": bool(row.get("static_plan_fidelity")),
                    "end_to_end_success": bool(row.get("end_to_end_success")),
                }
            )

    reports = []
    for method_id, group in sorted(grouped.items()):
        executable = [
            row for row in group if row.get("variant") not in nonexecution_variants
        ]
        nonexecution = [
            row for row in group if row.get("variant") in nonexecution_variants
        ]
        stages: dict[str, int] = {}
        for row in group:
            stage = str(row.get("containment_stage", "not_stated"))
            stages[stage] = stages.get(stage, 0) + 1
        reports.append(
            {
                "model_id": model_id,
                "method_id": method_id,
                "method_label": _method_label(method_id),
                "cases": len(group),
                "executable_cases": len(executable),
                "nonexecution_cases": len(nonexecution),
                "strict_success_failures": sum(
                    not bool(row.get("end_to_end_success")) for row in group
                ),
                "parse_errors": sum(bool(row.get("parse_error")) for row in group),
                "backend_errors": sum(
                    bool(row.get("backend_error")) for row in group
                ),
                "false_nonexecution_execute": sum(
                    bool(row.get("false_nonexecution")) for row in executable
                ),
                "unsafe_proceed_nonexecution": sum(
                    bool(row.get("unsafe_proceed")) for row in nonexecution
                ),
                "endpoint_fidelity_failures_execute": sum(
                    not bool(row.get("endpoint_fidelity")) for row in executable
                ),
                "parameter_grounding_fidelity_failures_execute": sum(
                    not bool(row.get("parameter_grounding_fidelity"))
                    for row in executable
                ),
                "official_command_fidelity_failures_execute": sum(
                    not bool(row.get("official_command_fidelity"))
                    for row in executable
                ),
                "static_plan_fidelity_failures_execute": sum(
                    not bool(row.get("static_plan_fidelity")) for row in executable
                ),
                "containment_stage_counts": dict(sorted(stages.items())),
            }
        )
    return reports, sorted(
        failures,
        key=lambda row: (
            row["model_id"],
            row["method_id"],
            row["session_id"],
            row["case_id"],
        ),
    )


def analyze_scored_rows(
    *,
    rows: Iterable[Mapping[str, Any]],
    protocol: Mapping[str, Any],
    model_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Analyze one model's scored rows under the frozen contrasts and outcomes."""

    materialized = [dict(row) for row in rows]
    if not model_id or not materialized:
        raise ValueError("model id and scored rows are required")
    if {str(row.get("variant", "")) for row in materialized} != _EXPECTED_VARIANTS:
        raise ValueError("scored rows differ from the frozen five variants")
    methods = {str(row.get("method_id", "")) for row in materialized}
    if methods != set(protocol.get("methods", [])):
        raise ValueError("scored methods differ from the frozen protocol")

    statistics = protocol.get("statistics")
    if not isinstance(statistics, Mapping):
        raise ValueError("frozen statistics configuration is absent")
    draws = int(statistics.get("bootstrap_draws", 0))
    seed = str(statistics.get("bootstrap_seed", ""))
    if draws != 10_000 or not seed:
        raise ValueError("bootstrap draws or seed differ from the frozen protocol")

    reports: list[dict[str, Any]] = []
    cluster_evidence: list[dict[str, Any]] = []
    draw_evidence: list[dict[str, Any]] = []
    for contrast_name in ("primary_contrast", "confirmatory_contrast"):
        contrast = protocol.get(contrast_name)
        if not isinstance(contrast, Mapping):
            raise ValueError(f"frozen contrast is absent: {contrast_name}")
        method_a = str(contrast.get("method_a", ""))
        method_b = str(contrast.get("method_b", ""))
        for outcome in protocol.get("primary_outcomes", []):
            if not isinstance(outcome, Mapping):
                raise ValueError("frozen primary outcome is malformed")
            metric_id = str(outcome.get("metric_id", ""))
            metric_field, eligible_variants = _outcome_fields(outcome)
            analysis_id = f"{model_id}:{contrast_name}:{metric_id}"
            prepared = [
                {
                    "cluster_id": row["cluster_id"],
                    "case_variant": row["variant"],
                    "method_id": row["method_id"],
                    "metric_value": float(bool(row[metric_field])),
                }
                for row in materialized
                if row["method_id"] in {method_a, method_b}
                and row["variant"] in eligible_variants
            ]
            result = paired_cluster_bootstrap(
                prepared,
                method_a=method_a,
                method_b=method_b,
                expected_variants=len(eligible_variants),
                draws=draws,
                confidence_level=0.95,
                seed=seed,
            )
            analysis = dict(result["analysis"])
            reports.append(
                {
                    "analysis_id": analysis_id,
                    "contrast_role": contrast_name,
                    "outcome": metric_id,
                    "direction": outcome.get("direction"),
                    "eligible_variants": sorted(eligible_variants),
                    "analysis": analysis,
                }
            )
            cluster_evidence.extend(
                {
                    "analysis_id": analysis_id,
                    "model_id": model_id,
                    **dict(cluster),
                }
                for cluster in result["cluster_summaries"]
            )
            draw_evidence.append(
                {
                    "analysis_id": analysis_id,
                    "model_id": model_id,
                    "draws": result["raw_bootstrap_draws"],
                }
            )
    return reports, cluster_evidence, draw_evidence


def write_bootstrap_evidence_archive(
    *,
    cluster_summaries: Sequence[Mapping[str, Any]],
    draw_records: Sequence[Mapping[str, Any]],
    output_path: Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Store raw draws and cluster summaries apart from report-ready results."""

    cluster_bytes = b"".join(
        (_canonical_json(dict(row)) + "\n").encode("utf-8")
        for row in cluster_summaries
    )
    draw_bytes = b"".join(
        (_canonical_json(dict(row)) + "\n").encode("utf-8") for row in draw_records
    )
    metadata_bytes = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    manifest = {
        "schema_version": 1,
        "analysis_count": len(draw_records),
        "cluster_summary_rows": len(cluster_summaries),
        "files": {
            "bootstrap_draws.jsonl": _content_record(draw_bytes),
            "cluster_summaries.jsonl": _content_record(cluster_bytes),
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
                "bootstrap_draws.jsonl": draw_bytes,
                "cluster_summaries.jsonl": cluster_bytes,
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
        "analysis_count": len(draw_records),
        "cluster_summary_rows": len(cluster_summaries),
        "bootstrap_draws_sha256": hashlib.sha256(draw_bytes).hexdigest(),
        "cluster_summaries_sha256": hashlib.sha256(cluster_bytes).hexdigest(),
    }


def _validate_scoring_boundary(
    summary: Mapping[str, Any], repository_root: Path, protocol_path: Path
) -> None:
    if summary.get("status") != _SCORING_STATUS:
        raise ValueError("complete deterministic scoring boundary is absent")
    if summary.get("next_gate") != _SCORING_NEXT_GATE:
        raise ValueError("scoring boundary does not authorize bootstrap analysis")
    if summary.get("scores_computed") is not True:
        raise ValueError("scoring boundary contains no computed scores")
    if summary.get("models_invoked") is not False:
        raise ValueError("analysis must not invoke models")
    bindings = summary.get("artifact_bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("scoring artifact bindings are absent")
    if bindings.get("accuracy_protocol_sha256") != _sha256_file(protocol_path):
        raise ValueError("scoring boundary protocol hash mismatch")
    expected = summary.get("source_code_sha256")
    if not isinstance(expected, Mapping):
        raise ValueError("scoring source hashes are absent")
    for name, digest in expected.items():
        matches = list(repository_root.rglob(str(name)))
        if len(matches) != 1 or _sha256_file(matches[0]) != digest:
            raise ValueError(f"scoring source hash mismatch: {name}")


def _analysis_spec(protocol: Mapping[str, Any]) -> dict[str, Any]:
    statistics = protocol.get("statistics")
    if not isinstance(statistics, Mapping):
        raise ValueError("frozen statistics configuration is absent")
    expected = {
        "bootstrap_draws": 10_000,
        "bootstrap_seed": "shepherd-multiuav-primary-bootstrap-v1",
        "interval": "percentile_95_percent",
        "null_hypothesis_tests": False,
        "resampling_unit": "source_task_cluster",
    }
    for key, value in expected.items():
        if statistics.get(key) != value:
            raise ValueError(f"frozen statistics mismatch: {key}")
    return {
        **expected,
        "primary_contrast": dict(protocol["primary_contrast"]),
        "confirmatory_contrast": dict(protocol["confirmatory_contrast"]),
        "primary_outcomes": [dict(item) for item in protocol["primary_outcomes"]],
    }


def _outcome_fields(outcome: Mapping[str, Any]) -> tuple[str, frozenset[str]]:
    metric_id = outcome.get("metric_id")
    eligible = outcome.get("eligible_variants")
    if metric_id == "unsafe_proceed_rate_nonexecute":
        if not isinstance(eligible, list):
            raise ValueError("unsafe-proceed variants are not frozen as a list")
        variants = frozenset(str(item) for item in eligible)
        if variants != {
            "missing_information_clarify",
            "resource_conflict_block",
        }:
            raise ValueError("unsafe-proceed variants differ from the protocol")
        return "unsafe_proceed", variants
    if metric_id == "end_to_end_case_success_rate":
        if eligible != "all_five":
            raise ValueError("end-to-end success must include all five variants")
        return "end_to_end_success", _EXPECTED_VARIANTS
    raise ValueError(f"unsupported registered primary outcome: {metric_id}")


def _load_scored_rows(
    archive_path: Path, archive_record: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if _sha256_file(archive_path) != archive_record.get("sha256"):
        raise ValueError("scored-row archive hash mismatch")
    try:
        archive = ZipFile(archive_path)
    except (BadZipFile, OSError) as error:
        raise ValueError(f"invalid scored-row archive: {archive_path}") from error
    with archive:
        names = [info.filename for info in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != _SCORED_ARCHIVE_MEMBERS:
            raise ValueError("scored-row archive members differ from schema")
        content = archive.read("scored_rows.jsonl")
        if hashlib.sha256(content).hexdigest() != archive_record.get(
            "scored_rows_sha256"
        ):
            raise ValueError("scored-row content hash mismatch")
        rows = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid scored row at line {line_number}") from error
            if not isinstance(row, dict):
                raise ValueError(f"scored row {line_number} is not an object")
            rows.append(row)
    if len(rows) != archive_record.get("row_count"):
        raise ValueError("scored-row archive count mismatch")
    return rows


def _load_session_bindings(path: Path) -> dict[str, str]:
    payload = _read_object(path)
    clusters = payload.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        raise ValueError("intervention dataset clusters are absent")
    bindings: dict[str, str] = {}
    for index, cluster in enumerate(clusters):
        if not isinstance(cluster, Mapping):
            raise ValueError(f"intervention cluster {index} is malformed")
        cluster_id = str(cluster.get("cluster_id", ""))
        session_id = str(cluster.get("session_id", ""))
        if not cluster_id or not session_id:
            raise ValueError(f"intervention cluster {index} has no session binding")
        if cluster_id in bindings and bindings[cluster_id] != session_id:
            raise ValueError(f"conflicting session binding: {cluster_id}")
        bindings[cluster_id] = session_id
    return bindings


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise ValueError("descriptive rate denominator must be positive")
    return numerator / denominator


def _method_label(method_id: str) -> str:
    if method_id == "M4_post_plan_compute_matched":
        return "M4 model-call-count-matched post-plan"
    return method_id


def _analysis_source_hashes(repository_root: Path) -> dict[str, str]:
    paths = {
        "multiuav_study_analysis.py": Path(__file__).resolve(),
        "multiuav_statistics.py": repository_root
        / "src"
        / "shepherd_ai"
        / "multiuav_statistics.py",
        "analyze_multiuav_accuracy.py": repository_root
        / "scripts"
        / "analyze_multiuav_accuracy.py",
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
