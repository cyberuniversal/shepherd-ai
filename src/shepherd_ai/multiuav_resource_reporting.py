"""Publication artifacts for registered MultiUAV resource results."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
from typing import Any, Mapping, Sequence


REPORT_VERSION = "multiuav_resource_reporting_v1"
MODEL_ORDER = (
    "Qwen/Qwen2.5-3B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
)
METHOD_ORDER = (
    "M1_monolithic",
    "M2_post_plan_deterministic",
    "M3_stage_wise",
    "M4_post_plan_compute_matched",
)
METRIC_ORDER = (
    "method_case_duration_seconds",
    "input_tokens",
    "output_tokens",
    "model_call_count",
    "process_ram_peak_bytes",
    "board_vram_peak_bytes",
    "process_vram_peak_bytes",
    "gpu_board_energy_joules",
)
CONTRAST_ORDER = (
    "registered_primary_method_contrast_secondary_resource_outcome",
    "registered_confirmatory_method_contrast_secondary_resource_outcome",
)

_MODEL_LABELS = {
    "Qwen/Qwen2.5-3B-Instruct": "Qwen2.5-3B",
    "Qwen/Qwen2.5-7B-Instruct": "Qwen2.5-7B",
}
_METHOD_LABELS = {
    "M1_monolithic": "M1 monolithic",
    "M2_post_plan_deterministic": "M2 post-plan gate",
    "M3_stage_wise": "M3 stage-wise",
    "M4_post_plan_compute_matched": "M4 compute-matched",
}
_CONTRAST_LABELS = {
    CONTRAST_ORDER[0]: "M3 minus M1",
    CONTRAST_ORDER[1]: "M3 minus M4",
}
_METRIC_LABELS = {
    "method_case_duration_seconds": "Duration (s)",
    "input_tokens": "Input tokens",
    "output_tokens": "Output tokens",
    "model_call_count": "Model calls",
    "process_ram_peak_bytes": "Process RAM peak (bytes)",
    "board_vram_peak_bytes": "Board VRAM peak (bytes)",
    "process_vram_peak_bytes": "Process VRAM peak (bytes)",
    "gpu_board_energy_joules": "GPU-board energy (J)",
    "gpu_utilization_peak_percent": "GPU utilization peak (%)",
    "temperature_peak_celsius": "Temperature peak (C)",
}


def load_resource_report_data(
    repository_root: Path,
    *,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Load the complete registered resource summary for reporting."""

    repository_root = repository_root.resolve()
    summary_path = (
        summary_path
        or repository_root
        / "outputs"
        / "evaluations"
        / "multiuav_resource_analysis_v1"
        / "summary.json"
    ).resolve()
    summary = _read_object(summary_path)
    _validate_summary(summary, repository_root=repository_root)

    descriptive_rows: list[dict[str, Any]] = []
    for item in summary["descriptive_summaries"]:
        stats = _mapping(item.get("cluster_mean_statistics"), "descriptive statistics")
        descriptive_rows.append(
            {
                "repetition": int(item["repetition"]),
                "model_id": str(item["model_id"]),
                "model_label": _MODEL_LABELS[str(item["model_id"])],
                "method_id": str(item["method_id"]),
                "method_label": _METHOD_LABELS[str(item["method_id"])],
                "metric_id": str(item["metric_id"]),
                "metric_label": _METRIC_LABELS[str(item["metric_id"])],
                "unit": str(item["unit"]),
                "role": str(item["role"]),
                "cluster_count": int(item["cluster_count"]),
                "cases_per_cluster": int(item["cases_per_cluster"]),
                "mean": _finite(stats.get("mean"), "descriptive mean"),
                "median": _finite(stats.get("median"), "descriptive median"),
                "sample_standard_deviation": _finite(
                    stats.get("sample_standard_deviation"), "descriptive SD"
                ),
                "minimum": _finite(stats.get("minimum"), "descriptive minimum"),
                "maximum": _finite(stats.get("maximum"), "descriptive maximum"),
            }
        )

    contrast_rows: list[dict[str, Any]] = []
    for item in summary["paired_contrasts"]:
        analysis = _mapping(item.get("analysis"), "paired analysis")
        interval = _mapping(analysis.get("confidence_interval"), "confidence interval")
        role = str(item["contrast_role"])
        metric_id = str(item["metric_id"])
        point = _finite(analysis.get("point_estimate"), "point estimate")
        lower = _finite(interval.get("lower"), "interval lower")
        upper = _finite(interval.get("upper"), "interval upper")
        if not lower <= point <= upper:
            raise ValueError("resource interval does not contain its point estimate")
        contrast_rows.append(
            {
                "analysis_id": str(item["analysis_id"]),
                "repetition": int(item["repetition"]),
                "model_id": str(item["model_id"]),
                "model_label": _MODEL_LABELS[str(item["model_id"])],
                "contrast_role": role,
                "contrast_label": _CONTRAST_LABELS[role],
                "method_a": str(item["method_a"]),
                "method_b": str(item["method_b"]),
                "metric_id": metric_id,
                "metric_label": _METRIC_LABELS[metric_id],
                "unit": str(item["unit"]),
                "direction": str(item["direction"]),
                "inference_status": str(item["inference_status"]),
                "point_estimate": point,
                "ci_lower": lower,
                "ci_upper": upper,
                "confidence_level": float(interval["confidence_level"]),
                "cluster_count": int(analysis["cluster_count"]),
                "bootstrap_draws": int(analysis["draws"]),
            }
        )

    return {
        "schema_version": 1,
        "report_version": REPORT_VERSION,
        "status": "resource_report_data_validated",
        "source_files": [_file_record(repository_root, summary_path)],
        "source_scope": {
            "secondary_exploratory_results_only": True,
            "repetitions_reported_separately": True,
            "repetitions_pooled": False,
            "raw_model_outputs_accessed": False,
            "hidden_labels_accessed": False,
            "null_hypothesis_tests_run": False,
            "post_admission_human_raw_output_inspection_deviation_disclosed": True,
        },
        "descriptive_rows": sorted(
            descriptive_rows,
            key=lambda row: (
                row["repetition"],
                MODEL_ORDER.index(row["model_id"]),
                METHOD_ORDER.index(row["method_id"]),
                row["metric_id"],
            ),
        ),
        "contrast_rows": sorted(
            contrast_rows,
            key=lambda row: (
                CONTRAST_ORDER.index(row["contrast_role"]),
                row["repetition"],
                MODEL_ORDER.index(row["model_id"]),
                METRIC_ORDER.index(row["metric_id"]),
            ),
        ),
    }


def build_resource_report_artifacts(
    *,
    repository_root: Path,
    report_data: Mapping[str, Any],
    figure_dir: Path,
    table_dir: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Write source tables, registered contrast figures, and a report."""

    repository_root = repository_root.resolve()
    figure_dir = figure_dir.resolve()
    table_dir = table_dir.resolve()
    report_path = report_path.resolve()
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    descriptive_path = table_dir / "multiuav_resource_descriptive_v1.csv"
    contrast_path = table_dir / "multiuav_resource_contrasts_v1.csv"
    descriptive_path.write_bytes(
        _render_csv(
            report_data["descriptive_rows"],
            (
                "repetition",
                "model_id",
                "model_label",
                "method_id",
                "method_label",
                "metric_id",
                "metric_label",
                "unit",
                "role",
                "cluster_count",
                "cases_per_cluster",
                "mean",
                "median",
                "sample_standard_deviation",
                "minimum",
                "maximum",
            ),
        ).encode("utf-8")
    )
    contrast_path.write_bytes(
        _render_csv(
            report_data["contrast_rows"],
            (
                "analysis_id",
                "repetition",
                "model_id",
                "model_label",
                "contrast_role",
                "contrast_label",
                "method_a",
                "method_b",
                "metric_id",
                "metric_label",
                "unit",
                "direction",
                "inference_status",
                "point_estimate",
                "ci_lower",
                "ci_upper",
                "confidence_level",
                "cluster_count",
                "bootstrap_draws",
            ),
        ).encode("utf-8")
    )
    figures = _render_contrast_figures(
        rows=report_data["contrast_rows"], figure_dir=figure_dir
    )
    report_path.write_bytes(_render_report(report_data).encode("utf-8"))
    outputs = [descriptive_path, contrast_path, *figures, report_path]
    return {
        "schema_version": 1,
        "report_version": REPORT_VERSION,
        "status": "resource_tables_figures_and_report_complete",
        "source_files": list(report_data["source_files"]),
        "source_scope": dict(report_data["source_scope"]),
        "report_data_sha256": hashlib.sha256(
            _canonical_json(
                {
                    "descriptive_rows": report_data["descriptive_rows"],
                    "contrast_rows": report_data["contrast_rows"],
                }
            ).encode("utf-8")
        ).hexdigest(),
        "source_code_sha256": {
            "multiuav_resource_reporting.py": _sha256_file(Path(__file__)),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "outputs": [_file_record(repository_root, path) for path in outputs],
        "figures": 2,
        "figure_formats": ["pdf", "png"],
        "tables": 2,
        "reports": 1,
        "next_gate": "manuscript_integration_pending",
    }


def _validate_summary(summary: Mapping[str, Any], *, repository_root: Path) -> None:
    if (
        summary.get("status") != "resource_analysis_complete_reporting_pending"
        or summary.get("claim_status") != "secondary_exploratory_resource_results"
        or summary.get("resource_metric_rows") != 3600
        or summary.get("descriptive_summary_count") != 240
        or summary.get("paired_contrast_count") != 96
        or summary.get("repetitions") != [1, 2, 3]
    ):
        raise ValueError("complete registered resource analysis is absent")
    if summary.get("models_invoked") is not False:
        raise ValueError("resource reporting must not invoke models")
    if (
        summary.get("hidden_labels_accessed") is not False
        or summary.get("analysis_pipeline_raw_output_fields_accessed") is not False
        or summary.get("null_hypothesis_tests_run") is not False
    ):
        raise ValueError("resource reporting boundary contains prohibited analysis")
    if summary.get("post_admission_human_raw_output_inspection_deviation") is not True:
        raise ValueError("resource inspection deviation is not disclosed")
    spec = _mapping(summary.get("analysis_spec"), "analysis specification")
    if (
        spec.get("repetitions_reported_separately") is not True
        or spec.get("bootstrap_draws") != 10_000
        or spec.get("null_hypothesis_tests") is not False
        or spec.get("inference_status")
        != "exploratory_secondary_no_confirmatory_claims"
    ):
        raise ValueError("resource reporting specification differs")
    for key in ("derived_resource_rows_archive", "bootstrap_evidence_archive"):
        artifact = _mapping(summary.get(key), key)
        path = repository_root / str(artifact.get("path", ""))
        if _sha256_file(path) != artifact.get("sha256"):
            raise ValueError(f"resource reporting artifact hash mismatch: {key}")
    if not isinstance(summary.get("descriptive_summaries"), list) or not isinstance(
        summary.get("paired_contrasts"), list
    ):
        raise ValueError("resource reporting summaries are absent")
    models = {str(item.get("model_id", "")) for item in summary["descriptive_summaries"]}
    methods = {str(item.get("method_id", "")) for item in summary["descriptive_summaries"]}
    contrasts = {str(item.get("contrast_role", "")) for item in summary["paired_contrasts"]}
    paired_metrics = {str(item.get("metric_id", "")) for item in summary["paired_contrasts"]}
    if (
        models != set(MODEL_ORDER)
        or methods != set(METHOD_ORDER)
        or contrasts != set(CONTRAST_ORDER)
        or paired_metrics != set(METRIC_ORDER)
    ):
        raise ValueError("resource reporting matrix differs")


def _render_contrast_figures(
    *, rows: Sequence[Mapping[str, Any]], figure_dir: Path
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    colors = {
        "Qwen/Qwen2.5-3B-Instruct": "#B44C43",
        "Qwen/Qwen2.5-7B-Instruct": "#2A7485",
    }
    markers = {1: "o", 2: "s", 3: "^"}
    output: list[Path] = []
    style = {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
    with plt.rc_context(style):
        for contrast_role in CONTRAST_ORDER:
            figure, axes = plt.subplots(4, 2, figsize=(12, 14))
            for axis, metric_id in zip(axes.flat, METRIC_ORDER):
                metric_rows = [
                    row
                    for row in rows
                    if row["contrast_role"] == contrast_role
                    and row["metric_id"] == metric_id
                ]
                for index, row in enumerate(metric_rows):
                    point = float(row["point_estimate"])
                    lower = float(row["ci_lower"])
                    upper = float(row["ci_upper"])
                    axis.errorbar(
                        point,
                        index,
                        xerr=[[point - lower], [upper - point]],
                        fmt=markers[int(row["repetition"])],
                        color=colors[str(row["model_id"])],
                        markersize=5,
                        capsize=3,
                        linewidth=1.4,
                    )
                labels = [
                    f"{row['model_label']} R{row['repetition']}" for row in metric_rows
                ]
                axis.set_yticks(range(len(metric_rows)), labels)
                axis.invert_yaxis()
                axis.axvline(0, color="#555555", linewidth=0.9, linestyle="--")
                axis.grid(axis="x", alpha=0.25, linewidth=0.7)
                axis.set_title(_METRIC_LABELS[metric_id])
                axis.set_xlabel("Paired cluster-mean difference")
            figure.suptitle(
                f"{_CONTRAST_LABELS[contrast_role]}: exploratory resource contrasts",
                y=0.995,
            )
            figure.text(
                0.5,
                0.005,
                "Each repetition is separate; 30 source-task clusters; 10,000 fixed-seed bootstrap draws; no null-hypothesis tests.",
                ha="center",
                fontsize=8,
            )
            figure.tight_layout(rect=(0, 0.02, 1, 0.98), h_pad=2.0, w_pad=2.0)
            suffix = "m3_minus_m1" if contrast_role == CONTRAST_ORDER[0] else "m3_minus_m4"
            output.extend(
                _save_figure(
                    figure,
                    figure_dir / f"multiuav_resource_{suffix}_v1",
                )
            )
            plt.close(figure)
    return output


def _render_report(report_data: Mapping[str, Any]) -> str:
    lines = [
        "# MultiUAV Resource Results",
        "",
        "## Scope",
        "",
        "These resource outcomes are secondary and exploratory. They do not support confirmatory claims, and no null-hypothesis tests were run. The three hardware repetitions are reported separately and are not pooled.",
        "",
        "The analysis covers two immutable Qwen2.5 checkpoints, four methods, 30 source-task clusters, five dependent variants per cluster, and three repetitions. Within each repetition, model, and method, the first aggregate is the arithmetic mean across the five variants in a source-task cluster. Descriptive statistics summarize the resulting 30 cluster means.",
        "",
        "Registered paired differences are M3 minus M1 and M3 minus M4. Each interval is a 95% percentile source-cluster bootstrap interval from 10,000 fixed-seed draws. A positive resource difference means M3 used more of the named resource; a negative difference means M3 used less.",
        "",
        "## Boundaries",
        "",
        "GPU-board energy is not workstation, simulator, network, or UAV energy. Peak memory is an observed process or board maximum, not a baseline-subtracted allocation. Results are specific to the admitted RTX 3090 runs. M4 is matched to M3 only by model-call count, not by tokens, latency, memory, or energy.",
        "",
        "A post-admission diagnostic command exposed one row's nested request and raw model output before aggregate analysis. The campaign and score-blind admission were already immutable; no aggregate, paired comparison, or hidden label was exposed. The deviation is preserved in `datasets/multiuav_plat/resource_analysis_protocol_deviation_v1.json` and must be disclosed.",
        "",
        "## Registered Contrasts",
        "",
        "Exact descriptive results are in `outputs/tables/multiuav_resource_descriptive_v1.csv`; exact paired estimates and intervals are in `outputs/tables/multiuav_resource_contrasts_v1.csv`.",
        "",
        "| Contrast | Repetition | Model | Metric | Difference | 95% interval |",
        "|---|---:|---|---|---:|---:|",
    ]
    for row in report_data["contrast_rows"]:
        lines.append(
            "| {contrast} | {repetition} | {model} | {metric} | {point} | [{lower}, {upper}] |".format(
                contrast=row["contrast_label"],
                repetition=row["repetition"],
                model=row["model_label"],
                metric=row["metric_label"],
                point=_format_number(float(row["point_estimate"])),
                lower=_format_number(float(row["ci_lower"])),
                upper=_format_number(float(row["ci_upper"])),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Status",
            "",
            "The tables and figures are analysis outputs, not a causal or hardware-general performance claim. Cross-repetition consistency and practical magnitude should be discussed metric by metric in the manuscript without converting interval inclusion or exclusion of zero into an unregistered significance test.",
            "",
        ]
    )
    return "\n".join(lines)


def _save_figure(figure: Any, stem: Path) -> list[Path]:
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    figure.savefig(
        png,
        dpi=220,
        bbox_inches="tight",
        metadata={"Software": "Shepherd-AI registered resource reporting"},
    )
    figure.savefig(
        pdf,
        bbox_inches="tight",
        metadata={
            "Title": stem.name,
            "Creator": "Shepherd-AI registered resource reporting",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    return [png, pdf]


def _render_csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _format_number(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value:.4e}"
    return f"{value:.4f}"


def _finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"resource {label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"resource {label} must be finite")
    return result


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"resource mapping is absent: {label}")
    return value


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid resource summary: {path}") from error
    if not isinstance(value, dict):
        raise ValueError("resource summary root must be an object")
    return value


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    try:
        rendered = path.resolve().relative_to(root.resolve()).as_posix()
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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
