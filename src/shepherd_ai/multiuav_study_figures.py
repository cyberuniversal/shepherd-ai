"""Publication figures derived from frozen MultiUAV accuracy summaries."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
from typing import Any, Mapping, Sequence


FIGURE_RUN_VERSION = "multiuav_accuracy_figures_v1"
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
OUTCOME_ORDER = (
    "unsafe_proceed_rate_nonexecute",
    "end_to_end_case_success_rate",
)
CONTRAST_ORDER = ("primary_contrast", "confirmatory_contrast")

_MODEL_LABELS = {
    "Qwen/Qwen2.5-3B-Instruct": "Qwen2.5-3B",
    "Qwen/Qwen2.5-7B-Instruct": "Qwen2.5-7B",
}
_METHOD_LABELS = {
    "M1_monolithic": "M1\nMonolithic",
    "M2_post_plan_deterministic": "M2\nPost-plan gate",
    "M3_stage_wise": "M3\nStage-wise",
    "M4_post_plan_compute_matched": "M4\nCompute-matched",
}
_OUTCOME_LABELS = {
    "unsafe_proceed_rate_nonexecute": "Unsafe proceed",
    "end_to_end_case_success_rate": "End-to-end success",
}
_CONTRAST_LABELS = {
    "primary_contrast": "M3 - M1",
    "confirmatory_contrast": "M3 - M4",
}


def load_accuracy_figure_data(
    repository_root: Path,
    *,
    scoring_summary_path: Path | None = None,
    bootstrap_summary_path: Path | None = None,
) -> dict[str, Any]:
    """Load and validate the only summaries admitted to accuracy figures."""

    repository_root = repository_root.resolve()
    scoring_summary_path = (
        scoring_summary_path
        or repository_root
        / "outputs/evaluations/multiuav_accuracy_scoring_v1/summary.json"
    ).resolve()
    bootstrap_summary_path = (
        bootstrap_summary_path
        or repository_root
        / "outputs/evaluations/multiuav_accuracy_bootstrap_v1/summary.json"
    ).resolve()
    scoring = _read_object(scoring_summary_path)
    bootstrap = _read_object(bootstrap_summary_path)
    scoring_sha256 = _sha256_file(scoring_summary_path)
    _validate_scoring_summary(scoring)
    _validate_bootstrap_summary(
        bootstrap,
        repository_root=repository_root,
        scoring_summary_sha256=scoring_sha256,
    )

    matrices = {
        str(matrix.get("model_id", "")): matrix for matrix in scoring["matrices"]
    }
    if set(matrices) != set(MODEL_ORDER):
        raise ValueError("scoring summary models differ from the frozen figure contract")
    bootstrap_models = {
        str(model.get("model_id", "")): model for model in bootstrap["model_results"]
    }
    if set(bootstrap_models) != set(MODEL_ORDER):
        raise ValueError("bootstrap models differ from the frozen figure contract")

    rate_rows: list[dict[str, Any]] = []
    contrast_rows: list[dict[str, Any]] = []
    for model_id in MODEL_ORDER:
        matrix = matrices[model_id]
        model_result = bootstrap_models[model_id]
        archive = matrix.get("scored_rows_archive")
        if not isinstance(archive, Mapping):
            raise ValueError(f"scored-row archive binding is absent: {model_id}")
        if model_result.get("scored_rows_archive_sha256") != archive.get("sha256"):
            raise ValueError(f"bootstrap-to-scoring archive hash mismatch: {model_id}")
        matrix_summary = matrix.get("summary")
        if not isinstance(matrix_summary, Mapping):
            raise ValueError(f"matrix summary is absent: {model_id}")
        methods = matrix_summary.get("methods")
        if not isinstance(methods, Mapping) or set(methods) != set(METHOD_ORDER):
            raise ValueError(f"scored methods differ from the frozen figure contract: {model_id}")
        for method_id in METHOD_ORDER:
            primary = methods[method_id].get("primary")
            if not isinstance(primary, Mapping) or set(primary) != set(OUTCOME_ORDER):
                raise ValueError(f"primary outcomes are incomplete: {model_id}/{method_id}")
            for outcome in OUTCOME_ORDER:
                metric = _validated_rate(primary[outcome], f"{model_id}/{method_id}/{outcome}")
                rate_rows.append(
                    {
                        "model_id": model_id,
                        "model_label": _MODEL_LABELS[model_id],
                        "method_id": method_id,
                        "method_label": _METHOD_LABELS[method_id].replace("\n", " "),
                        "outcome": outcome,
                        "outcome_label": _OUTCOME_LABELS[outcome],
                        **metric,
                    }
                )

        analyses = model_result.get("analyses")
        if not isinstance(analyses, list):
            raise ValueError(f"registered analyses are absent: {model_id}")
        indexed = {
            (str(item.get("contrast_role", "")), str(item.get("outcome", ""))): item
            for item in analyses
            if isinstance(item, Mapping)
        }
        expected = {
            (contrast, outcome)
            for contrast in CONTRAST_ORDER
            for outcome in OUTCOME_ORDER
        }
        if set(indexed) != expected or len(analyses) != len(expected):
            raise ValueError(f"registered analyses are incomplete or duplicated: {model_id}")
        for contrast_role in CONTRAST_ORDER:
            for outcome in OUTCOME_ORDER:
                contrast_rows.append(
                    _validated_contrast(
                        indexed[(contrast_role, outcome)],
                        model_id=model_id,
                        contrast_role=contrast_role,
                        outcome=outcome,
                    )
                )

    return {
        "schema_version": 1,
        "figure_run_version": FIGURE_RUN_VERSION,
        "status": "accuracy_figure_data_validated",
        "source_files": [
            _file_record(repository_root, scoring_summary_path),
            _file_record(repository_root, bootstrap_summary_path),
        ],
        "source_scope": {
            "admitted_accuracy_summaries_only": True,
            "raw_model_outputs_accessed": False,
            "smoke_rows_included": False,
            "resource_rows_included": False,
            "new_metrics_computed": False,
            "null_hypothesis_tests_run": False,
        },
        "primary_rate_rows": rate_rows,
        "registered_contrast_rows": contrast_rows,
    }


def build_accuracy_figure_artifacts(
    *,
    repository_root: Path,
    figure_data: Mapping[str, Any],
    figure_dir: Path,
    table_dir: Path,
) -> dict[str, Any]:
    """Render figures and source tables, returning a provenance manifest."""

    repository_root = repository_root.resolve()
    figure_dir = figure_dir.resolve()
    table_dir = table_dir.resolve()
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    rate_table = table_dir / "multiuav_accuracy_primary_rates_v1.csv"
    contrast_table = table_dir / "multiuav_accuracy_registered_contrasts_v1.csv"
    rate_table.write_text(
        _render_csv(
            figure_data["primary_rate_rows"],
            (
                "model_id",
                "model_label",
                "method_id",
                "method_label",
                "outcome",
                "outcome_label",
                "numerator",
                "denominator",
                "rate",
            ),
        ),
        encoding="utf-8",
    )
    contrast_table.write_text(
        _render_csv(
            figure_data["registered_contrast_rows"],
            (
                "model_id",
                "model_label",
                "contrast_role",
                "contrast_label",
                "outcome",
                "outcome_label",
                "direction",
                "point_estimate",
                "ci_lower",
                "ci_upper",
                "confidence_level",
                "cluster_count",
                "bootstrap_draws",
            ),
        ),
        encoding="utf-8",
    )

    rendered = _render_figures(
        rate_rows=figure_data["primary_rate_rows"],
        contrast_rows=figure_data["registered_contrast_rows"],
        figure_dir=figure_dir,
    )
    outputs = [rate_table, contrast_table, *rendered]
    return {
        "schema_version": 1,
        "figure_run_version": FIGURE_RUN_VERSION,
        "status": "accuracy_publication_figures_complete",
        "source_files": list(figure_data["source_files"]),
        "source_scope": dict(figure_data["source_scope"]),
        "figure_data_sha256": hashlib.sha256(
            _canonical_json(
                {
                    "primary_rate_rows": figure_data["primary_rate_rows"],
                    "registered_contrast_rows": figure_data[
                        "registered_contrast_rows"
                    ],
                }
            ).encode("utf-8")
        ).hexdigest(),
        "source_code_sha256": _source_hashes(repository_root),
        "environment": _environment_record(),
        "outputs": [_file_record(repository_root, path) for path in outputs],
        "figures": 2,
        "figure_formats": ["pdf", "png"],
        "tables": 2,
        "next_gate": "resource_experiment_controls_and_execution_pending",
    }


def _render_figures(
    *,
    rate_rows: Sequence[Mapping[str, Any]],
    contrast_rows: Sequence[Mapping[str, Any]],
    figure_dir: Path,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import numpy as np

    style = {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
    output_paths: list[Path] = []
    with plt.rc_context(style):
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8), sharey=True)
        colors = ("#B44C43", "#2A7485")
        width = 0.34
        x = np.arange(len(METHOD_ORDER), dtype=float)
        for axis, model_id in zip(axes, MODEL_ORDER):
            model_rows = [row for row in rate_rows if row["model_id"] == model_id]
            for offset, outcome in zip((-width / 2, width / 2), OUTCOME_ORDER):
                values = [
                    next(
                        float(row["rate"])
                        for row in model_rows
                        if row["method_id"] == method and row["outcome"] == outcome
                    )
                    for method in METHOD_ORDER
                ]
                bars = axis.bar(
                    x + offset,
                    values,
                    width,
                    color=colors[OUTCOME_ORDER.index(outcome)],
                    label=_OUTCOME_LABELS[outcome],
                )
                axis.bar_label(
                    bars,
                    labels=[f"{value:.1%}" for value in values],
                    padding=2,
                    fontsize=8,
                    rotation=90,
                )
            axis.set_title(_MODEL_LABELS[model_id])
            axis.set_xticks(x, [_METHOD_LABELS[item] for item in METHOD_ORDER])
            axis.set_ylim(0, 1.08)
            axis.grid(axis="y", alpha=0.25, linewidth=0.7)
            axis.set_axisbelow(True)
        axes[0].set_ylabel("Rate")
        axes[1].legend(frameon=False, loc="upper right")
        figure.suptitle("Registered primary outcomes by model and method", y=0.99)
        figure.text(
            0.5,
            0.01,
            "Unsafe proceed: 568 non-execute cases per method; end-to-end success: 1,420 cases per method.",
            ha="center",
            fontsize=8.5,
            color="#444444",
        )
        figure.tight_layout(rect=(0, 0.055, 1, 0.95))
        output_paths.extend(
            _save_figure(
                figure,
                figure_dir / "multiuav_accuracy_primary_outcomes_v1",
            )
        )
        plt.close(figure)

        figure, axes = plt.subplots(1, 2, figsize=(11.0, 5.2))
        model_colors = {
            "Qwen/Qwen2.5-3B-Instruct": "#B44C43",
            "Qwen/Qwen2.5-7B-Instruct": "#2A7485",
        }
        row_order = [
            (model_id, contrast_role)
            for model_id in MODEL_ORDER
            for contrast_role in CONTRAST_ORDER
        ]
        y = np.arange(len(row_order), dtype=float)
        labels = [
            f"{_MODEL_LABELS[model]}  {_CONTRAST_LABELS[contrast]}"
            for model, contrast in row_order
        ]
        for axis, outcome in zip(axes, OUTCOME_ORDER):
            for position, (model_id, contrast_role) in zip(y, row_order):
                row = next(
                    item
                    for item in contrast_rows
                    if item["model_id"] == model_id
                    and item["contrast_role"] == contrast_role
                    and item["outcome"] == outcome
                )
                point = float(row["point_estimate"])
                lower = float(row["ci_lower"])
                upper = float(row["ci_upper"])
                axis.errorbar(
                    point,
                    position,
                    xerr=[[point - lower], [upper - point]],
                    fmt="o",
                    markersize=6,
                    capsize=4,
                    linewidth=1.8,
                    color=model_colors[model_id],
                )
            axis.axvline(0, color="#555555", linewidth=1, linestyle="--")
            axis.set_yticks(y, labels)
            axis.invert_yaxis()
            axis.set_title(_OUTCOME_LABELS[outcome])
            axis.grid(axis="x", alpha=0.25, linewidth=0.7)
            axis.set_axisbelow(True)
            axis.set_xlabel("Paired difference (M3 minus baseline)")
            values = [
                float(item[key])
                for item in contrast_rows
                if item["outcome"] == outcome
                for key in ("ci_lower", "ci_upper")
            ]
            padding = max(0.025, (max(values) - min(values)) * 0.08)
            axis.set_xlim(min(min(values) - padding, -padding), max(max(values) + padding, padding))
        axes[0].text(
            0.02,
            -0.19,
            "Lower is better",
            transform=axes[0].transAxes,
            fontsize=8.5,
            color="#444444",
        )
        axes[1].text(
            0.98,
            -0.19,
            "Higher is better",
            transform=axes[1].transAxes,
            fontsize=8.5,
            color="#444444",
            ha="right",
        )
        figure.suptitle("Registered M3 paired contrasts with 95% cluster-bootstrap intervals", y=0.99)
        figure.text(
            0.5,
            0.01,
            "284 source-task clusters; 10,000 fixed-seed bootstrap draws; no null-hypothesis tests.",
            ha="center",
            fontsize=8.5,
            color="#444444",
        )
        figure.tight_layout(rect=(0, 0.075, 1, 0.94), w_pad=2.8)
        output_paths.extend(
            _save_figure(
                figure,
                figure_dir / "multiuav_accuracy_registered_contrasts_v1",
            )
        )
        plt.close(figure)
    return output_paths


def _save_figure(figure: Any, stem: Path) -> list[Path]:
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    figure.savefig(
        png,
        dpi=240,
        bbox_inches="tight",
        metadata={"Software": "Shepherd-AI registered figure pipeline"},
    )
    figure.savefig(
        pdf,
        bbox_inches="tight",
        metadata={
            "Title": stem.name,
            "Author": "Shepherd-AI",
            "Creator": "Shepherd-AI registered figure pipeline",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    return [png, pdf]


def _validate_scoring_summary(summary: Mapping[str, Any]) -> None:
    if summary.get("status") != "accuracy_scoring_complete_cluster_analysis_pending":
        raise ValueError("complete deterministic scoring boundary is absent")
    if summary.get("scores_computed") is not True:
        raise ValueError("scoring summary contains no computed scores")
    if summary.get("models_invoked") is not False:
        raise ValueError("figure generation must not invoke models")
    if summary.get("rows_total") != 11_360:
        raise ValueError("scoring summary row count differs from the admitted matrices")
    if not isinstance(summary.get("matrices"), list) or len(summary["matrices"]) != 2:
        raise ValueError("scoring summary must contain two complete matrices")


def _validate_bootstrap_summary(
    summary: Mapping[str, Any],
    *,
    repository_root: Path,
    scoring_summary_sha256: str,
) -> None:
    if summary.get("status") != "accuracy_cluster_bootstrap_complete_figures_pending":
        raise ValueError("complete registered bootstrap boundary is absent")
    if summary.get("registered_analyses") != 8 or summary.get("models") != 2:
        raise ValueError("bootstrap summary does not contain all registered analyses")
    if summary.get("null_hypothesis_tests_run") is not False:
        raise ValueError("unregistered null-hypothesis tests cannot enter figures")
    if summary.get("resource_analysis_included") is not False:
        raise ValueError("resource results cannot enter accuracy figures")
    bindings = summary.get("artifact_bindings")
    if not isinstance(bindings, Mapping) or bindings.get(
        "scoring_summary_sha256"
    ) != scoring_summary_sha256:
        raise ValueError("bootstrap-to-scoring summary hash mismatch")
    evidence = summary.get("bootstrap_evidence_archive")
    if not isinstance(evidence, Mapping):
        raise ValueError("bootstrap evidence binding is absent")
    evidence_path = repository_root / str(evidence.get("path", ""))
    if _sha256_file(evidence_path) != evidence.get("sha256"):
        raise ValueError("bootstrap evidence archive hash mismatch")
    if evidence.get("analysis_count") != 8 or evidence.get("cluster_summary_rows") != 2_272:
        raise ValueError("bootstrap evidence dimensions differ from the registered analysis")
    if not isinstance(summary.get("model_results"), list):
        raise ValueError("bootstrap model results are absent")


def _validated_rate(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"rate record is malformed: {label}")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    rate = value.get("rate")
    if (
        isinstance(numerator, bool)
        or not isinstance(numerator, int)
        or isinstance(denominator, bool)
        or not isinstance(denominator, int)
        or denominator <= 0
        or numerator < 0
        or numerator > denominator
    ):
        raise ValueError(f"rate counts are invalid: {label}")
    rate = _finite_number(rate, f"{label}.rate")
    if not math.isclose(rate, numerator / denominator, rel_tol=0, abs_tol=1e-12):
        raise ValueError(f"rate does not match numerator and denominator: {label}")
    return {"numerator": numerator, "denominator": denominator, "rate": rate}


def _validated_contrast(
    item: Mapping[str, Any],
    *,
    model_id: str,
    contrast_role: str,
    outcome: str,
) -> dict[str, Any]:
    analysis = item.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("registered contrast analysis is malformed")
    interval = analysis.get("confidence_interval")
    if not isinstance(interval, Mapping):
        raise ValueError("registered confidence interval is absent")
    point = _finite_number(analysis.get("point_estimate"), "point_estimate")
    lower = _finite_number(interval.get("lower"), "confidence_interval.lower")
    upper = _finite_number(interval.get("upper"), "confidence_interval.upper")
    if lower > point or point > upper:
        raise ValueError("registered confidence interval does not contain its point estimate")
    if analysis.get("cluster_count") != 284 or analysis.get("draws") != 10_000:
        raise ValueError("registered cluster or bootstrap dimensions changed")
    if analysis.get("resampling_unit") != "source_task_cluster":
        raise ValueError("registered resampling unit changed")
    if interval.get("confidence_level") != 0.95 or interval.get("method") != "percentile_cluster_bootstrap":
        raise ValueError("registered interval contract changed")
    expected_methods = {
        "primary_contrast": ("M3_stage_wise", "M1_monolithic"),
        "confirmatory_contrast": (
            "M3_stage_wise",
            "M4_post_plan_compute_matched",
        ),
    }
    method_a, method_b = expected_methods[contrast_role]
    if analysis.get("method_a") != method_a or analysis.get("method_b") != method_b:
        raise ValueError("registered contrast methods changed")
    direction = item.get("direction")
    expected_direction = {
        "unsafe_proceed_rate_nonexecute": "lower_is_better",
        "end_to_end_case_success_rate": "higher_is_better",
    }[outcome]
    if direction != expected_direction:
        raise ValueError("registered outcome direction changed")
    return {
        "model_id": model_id,
        "model_label": _MODEL_LABELS[model_id],
        "contrast_role": contrast_role,
        "contrast_label": _CONTRAST_LABELS[contrast_role],
        "outcome": outcome,
        "outcome_label": _OUTCOME_LABELS[outcome],
        "direction": direction,
        "point_estimate": point,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence_level": 0.95,
        "cluster_count": 284,
        "bootstrap_draws": 10_000,
    }


def _render_csv(rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _source_hashes(repository_root: Path) -> dict[str, str]:
    paths = {
        "build_multiuav_accuracy_figures.py": repository_root
        / "scripts/build_multiuav_accuracy_figures.py",
        "multiuav_study_figures.py": Path(__file__).resolve(),
    }
    return {name: _sha256_file(path) for name, path in sorted(paths.items())}


def _environment_record() -> dict[str, str]:
    import matplotlib
    import numpy

    return {
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "numpy": numpy.__version__,
    }


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


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON object: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected finite number: {label}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"expected finite number: {label}")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise ValueError(f"required figure source is unavailable: {path}") from error
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
