"""Internal traceability audit for the active MultiUAV manuscript."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


AUDIT_VERSION = "multiuav_manuscript_traceability_v1"


def audit_multiuav_manuscript(
    repository_root: Path,
    *,
    manuscript_path: Path | None = None,
    resource_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Audit aggregate evidence and manuscript claims without raw-row access."""

    root = repository_root.resolve()
    manuscript_path = (
        manuscript_path
        or root / "reports" / "multiuav_validation_placement_manuscript_v1.md"
    ).resolve()
    resource_manifest_path = (
        resource_manifest_path
        or root
        / "outputs"
        / "evaluations"
        / "multiuav_resource_reporting_v1"
        / "manifest.json"
    ).resolve()
    paths = {
        "accuracy_admission": root
        / "datasets/multiuav_plat/accuracy_matrix_admission_v1.json",
        "accuracy_scoring_summary": root
        / "outputs/evaluations/multiuav_accuracy_scoring_v1/summary.json",
        "accuracy_bootstrap_summary": root
        / "outputs/evaluations/multiuav_accuracy_bootstrap_v1/summary.json",
        "accuracy_figure_manifest": root
        / "outputs/evaluations/multiuav_accuracy_figures_v1/manifest.json",
        "accuracy_rate_table": root
        / "outputs/tables/multiuav_accuracy_primary_rates_v1.csv",
        "accuracy_contrast_table": root
        / "outputs/tables/multiuav_accuracy_registered_contrasts_v1.csv",
        "resource_admission": root
        / "datasets/multiuav_plat/resource_campaign_admission_v1.json",
        "resource_analysis_freeze": root
        / "datasets/multiuav_plat/resource_analysis_freeze_v1.json",
        "resource_analysis_deviation": root
        / "datasets/multiuav_plat/resource_analysis_protocol_deviation_v1.json",
        "resource_analysis_summary": root
        / "outputs/evaluations/multiuav_resource_analysis_v1/summary.json",
        "resource_derived_rows": root
        / "outputs/evaluations/multiuav_resource_analysis_v1/derived_resource_rows.zip",
        "resource_bootstrap_evidence": root
        / "outputs/evaluations/multiuav_resource_analysis_v1/bootstrap_evidence.zip",
        "resource_reporting_manifest": resource_manifest_path,
        "resource_descriptive_table": root
        / "outputs/tables/multiuav_resource_descriptive_v1.csv",
        "resource_contrast_table": root
        / "outputs/tables/multiuav_resource_contrasts_v1.csv",
        "manuscript": manuscript_path,
        "bibliography": root / "reports/week9_bibliography.md",
    }
    checks: dict[str, bool] = {
        "all_required_artifacts_present": all(path.is_file() for path in paths.values())
    }
    bindings = {
        name: _file_record(root, path)
        for name, path in paths.items()
        if path.is_file()
    }
    if not checks["all_required_artifacts_present"]:
        return _result(checks=checks, bindings=bindings)

    accuracy_admission = _read_object(paths["accuracy_admission"])
    accuracy_scoring = _read_object(paths["accuracy_scoring_summary"])
    accuracy_bootstrap = _read_object(paths["accuracy_bootstrap_summary"])
    accuracy_figures = _read_object(paths["accuracy_figure_manifest"])
    resource_admission = _read_object(paths["resource_admission"])
    resource_summary = _read_object(paths["resource_analysis_summary"])
    resource_manifest = _read_object(paths["resource_reporting_manifest"])
    manuscript = paths["manuscript"].read_text(encoding="utf-8-sig")
    bibliography = paths["bibliography"].read_text(encoding="utf-8-sig")

    checks.update(
        {
            "accuracy_admission_valid": (
                accuracy_admission.get("valid") is True
                and accuracy_admission.get("rows_total") == 11_360
            ),
            "accuracy_scoring_valid": (
                accuracy_scoring.get("status")
                == "accuracy_scoring_complete_cluster_analysis_pending"
                and accuracy_scoring.get("rows_total") == 11_360
                and accuracy_scoring.get("models_invoked") is False
            ),
            "accuracy_bootstrap_valid": (
                accuracy_bootstrap.get("status")
                == "accuracy_cluster_bootstrap_complete_figures_pending"
                and accuracy_bootstrap.get("registered_analyses") == 8
                and accuracy_bootstrap.get("null_hypothesis_tests_run") is False
            ),
            "accuracy_figure_manifest_valid": _manifest_valid(
                accuracy_figures,
                root=root,
                status="accuracy_publication_figures_complete",
            ),
            "resource_admission_valid": (
                resource_admission.get("valid") is True
                and resource_admission.get("rows_total") == 3_600
                and resource_admission.get("resource_scores_computed") is False
            ),
            "resource_analysis_valid": (
                resource_summary.get("status")
                == "resource_analysis_complete_reporting_pending"
                and resource_summary.get("resource_metric_rows") == 3_600
                and resource_summary.get("paired_contrast_count") == 96
                and resource_summary.get("models_invoked") is False
                and resource_summary.get("hidden_labels_accessed") is False
            ),
            "resource_reporting_manifest_valid": _manifest_valid(
                resource_manifest,
                root=root,
                status="resource_tables_figures_and_report_complete",
            ),
            "accuracy_values_traced": all(
                value in manuscript
                for value in ("-0.7905", "-0.6831", "0.1606", "0.1521")
            ),
            "resource_values_traced": all(
                value in manuscript
                for value in ("3,600", "3,297.68", "3,155.56", "5,669-6,279")
            ),
            "controlled_derivative_limit_disclosed": "controlled derivatives" in manuscript,
            "within_qwen_limit_disclosed": (
                "two scales in one model family" in manuscript
            ),
            "static_fidelity_limit_disclosed": "Plan fidelity is static" in manuscript,
            "call_count_match_limit_disclosed": (
                "matched to M3 only by model-call count" in manuscript
            ),
            "resource_secondary_exploratory_disclosed": (
                "secondary exploratory" in manuscript
                and "carry no confirmatory claim" in manuscript
            ),
            "resource_repetitions_separate_disclosed": (
                "Repetitions are reported separately" in manuscript
            ),
            "gpu_board_energy_scope_disclosed": (
                "GPU-board energy is not workstation, simulator, network, or UAV energy."
                in manuscript
            ),
            "resource_deviation_disclosed": (
                "post-admission diagnostic printed one row's request and raw output"
                in manuscript
            ),
            "negative_result_disclosed": (
                "each achieved zero strict end-to-end success" in manuscript
            ),
            "required_literature_resolves": all(
                identifier in bibliography
                for identifier in (
                    "[L1]",
                    "[L2]",
                    "[L7]",
                    "[L8]",
                    "[E1]",
                    "[E2]",
                    "[E3]",
                )
            ),
        }
    )
    return _result(checks=checks, bindings=bindings)


def render_manuscript_audit(audit: Mapping[str, Any]) -> str:
    """Render a concise human-readable audit report."""

    lines = [
        "# MultiUAV Manuscript Traceability Audit",
        "",
        f"- Status: `{audit['status']}`",
        f"- Valid: `{str(audit['valid']).lower()}`",
        f"- Final submission ready: `{str(audit['final_submission_ready']).lower()}`",
        f"- Raw model outputs accessed: `{str(audit['raw_model_outputs_accessed']).lower()}`",
        f"- Hidden labels accessed: `{str(audit['hidden_labels_accessed']).lower()}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in audit["checks"].items():
        lines.append(f"- `{name}`: `{'pass' if passed else 'fail'}`")
    lines.extend(["", "## Remaining Gates", ""])
    lines.extend(f"- {item}" for item in audit["remaining_gates"])
    lines.extend(
        [
            "",
            "This is an internal evidence and claim-boundary audit. It is not peer review, venue acceptance, or independent replication.",
            "",
        ]
    )
    return "\n".join(lines)


def _result(
    *, checks: Mapping[str, bool], bindings: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    failed = sorted(name for name, passed in checks.items() if not passed)
    valid = not failed
    return {
        "schema_version": 1,
        "audit_version": AUDIT_VERSION,
        "status": (
            "manuscript_internal_traceability_passed_external_review_pending"
            if valid
            else "manuscript_internal_traceability_failed"
        ),
        "valid": valid,
        "checks": dict(sorted(checks.items())),
        "failed_checks": failed,
        "artifact_bindings": dict(sorted(bindings.items())),
        "source_code_sha256": {
            "multiuav_manuscript_audit.py": _sha256_file(Path(__file__)),
        },
        "raw_model_outputs_accessed": False,
        "hidden_labels_accessed": False,
        "final_submission_ready": False,
        "remaining_gates": [
            "external scientific and manuscript review",
            "venue selection and venue-specific formatting",
            "final reference-format and citation audit",
        ],
        "next_gate": "external_review_and_venue_formatting_pending",
    }


def _manifest_valid(
    manifest: Mapping[str, Any], *, root: Path, status: str
) -> bool:
    if manifest.get("status") != status:
        return False
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return False
    for record in outputs:
        if not isinstance(record, Mapping):
            return False
        path = root / str(record.get("path", ""))
        if not path.is_file() or _sha256_file(path) != record.get("sha256"):
            return False
    return True


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid audit input: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"audit input is not an object: {path}")
    return value


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    try:
        rendered = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {
        "path": rendered,
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
