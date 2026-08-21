"""Build the compact IEEE resource-contrast figure from frozen study tables."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "multiuav_resource_contrasts_v1.csv"
OUTPUT = ROOT / "figures" / "resource_contrasts_compact"

CONTRASTS = ("M3 minus M1", "M3 minus M4")
METRICS = (
    ("method_case_duration_seconds", "Duration", "s", 1.0),
    ("output_tokens", "Output tokens", "tokens", 1.0),
    ("process_ram_peak_bytes", "Process RAM peak", "MiB", 1024.0**2),
    ("gpu_board_energy_joules", "GPU-board energy", "J", 1.0),
)
MODELS = ("Qwen2.5-3B", "Qwen2.5-7B")
COLORS = {"Qwen2.5-3B": "#B44C43", "Qwen2.5-7B": "#27778A"}
MARKERS = {1: "o", 2: "s", 3: "^"}


def load_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    wanted = {metric_id for metric_id, _, _, _ in METRICS}
    return [
        row
        for row in rows
        if row["contrast_label"] in CONTRASTS and row["metric_id"] in wanted
    ]


def main() -> None:
    rows = load_rows()
    expected = len(CONTRASTS) * len(METRICS) * len(MODELS) * 3
    if len(rows) != expected:
        raise ValueError(f"expected {expected} frozen contrast rows, found {len(rows)}")

    style = {
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.titlesize": 8.5,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
    with plt.rc_context(style):
        figure, axes = plt.subplots(2, 4, figsize=(7.16, 3.75), sharey=True)
        y_labels = [f"{model.split('-')[-1]} R{rep}" for model in MODELS for rep in (1, 2, 3)]
        y_positions = list(range(len(y_labels)))

        for row_index, contrast in enumerate(CONTRASTS):
            for column_index, (metric_id, title, unit, scale) in enumerate(METRICS):
                axis = axes[row_index, column_index]
                selected = sorted(
                    (
                        row
                        for row in rows
                        if row["contrast_label"] == contrast
                        and row["metric_id"] == metric_id
                    ),
                    key=lambda row: (
                        MODELS.index(row["model_label"]),
                        int(row["repetition"]),
                    ),
                )
                for y, row in enumerate(selected):
                    point = float(row["point_estimate"]) / scale
                    lower = float(row["ci_lower"]) / scale
                    upper = float(row["ci_upper"]) / scale
                    repetition = int(row["repetition"])
                    axis.errorbar(
                        point,
                        y,
                        xerr=[[point - lower], [upper - point]],
                        fmt=MARKERS[repetition],
                        color=COLORS[row["model_label"]],
                        markersize=3.8,
                        capsize=2.0,
                        elinewidth=1.0,
                        markeredgewidth=0.6,
                    )

                axis.axvline(0, color="#555555", linewidth=0.75, linestyle="--")
                axis.grid(axis="x", color="#D9D9D9", linewidth=0.55)
                axis.set_ylim(len(y_labels) - 0.35, -0.65)
                axis.set_yticks(y_positions, y_labels)
                axis.set_xlabel(unit, labelpad=1.5)
                axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
                if row_index == 0:
                    axis.set_title(title, pad=3)
                if column_index == 0:
                    axis.set_ylabel(contrast, fontweight="bold", labelpad=3)
                axis.margins(x=0.12)

        figure.text(
            0.5,
            0.012,
            "Point estimates and 95% source-task-cluster bootstrap intervals; repetitions are not pooled.",
            ha="center",
            fontsize=6.8,
        )
        figure.tight_layout(rect=(0, 0.045, 1, 1), h_pad=1.15, w_pad=0.85)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            OUTPUT.with_suffix(".png"),
            dpi=600,
            bbox_inches="tight",
            metadata={"Software": "Shepherd-AI frozen resource reporting"},
        )
        figure.savefig(
            OUTPUT.with_suffix(".pdf"),
            bbox_inches="tight",
            metadata={
                "Title": "Compact exploratory resource contrasts",
                "Creator": "Shepherd-AI frozen resource reporting",
                "CreationDate": None,
                "ModDate": None,
            },
        )
        plt.close(figure)


if __name__ == "__main__":
    main()
