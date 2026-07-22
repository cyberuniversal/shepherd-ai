"""Build traceable Week 9 paper tables, diagrams, and runtime figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week9_paper import (  # noqa: E402
    evaluation_workflow_mermaid,
    load_week9_paper_evidence,
    render_csv,
    render_traceability_markdown,
    system_architecture_mermaid,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = load_week9_paper_evidence(root)

    evaluation_dir = root / "outputs/evaluations"
    table_dir = root / "outputs/tables"
    figure_dir = root / "reports/figures"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    (evaluation_dir / "week9_paper_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (table_dir / "week9_end_to_end_metrics.csv").write_text(
        render_csv(
            evidence["metric_rows"],
            ("metric", "value", "denominator", "unit", "definition", "source_artifact"),
        ),
        encoding="utf-8",
    )
    (table_dir / "week9_runtime_stages.csv").write_text(
        render_csv(evidence["runtime_rows"], ("stage", "seconds")), encoding="utf-8"
    )
    (figure_dir / "week9_system_architecture.mmd").write_text(
        system_architecture_mermaid(), encoding="utf-8"
    )
    (figure_dir / "week9_evaluation_workflow.mmd").write_text(
        evaluation_workflow_mermaid(), encoding="utf-8"
    )
    (root / "reports/week9_evidence_traceability.md").write_text(
        render_traceability_markdown(evidence), encoding="utf-8"
    )
    _render_runtime_figure(evidence["runtime_rows"], figure_dir / "week9_stage_runtime.png")
    print(json.dumps({"status": "built", "metrics": len(evidence["metric_rows"])}, indent=2))


def _render_runtime_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt

    labels = [str(row["stage"]).replace("_seconds", "").replace("_", " ") for row in rows]
    values = [float(row["seconds"]) for row in rows]
    figure, axis = plt.subplots(figsize=(8, 4.5))
    bars = axis.barh(labels, values, color=["#3B6F8C", "#5C8D62", "#8D6E63", "#7A7A7A", "#B65C4A"])
    axis.set_xlabel("Warm-model wall-clock time (seconds)")
    axis.set_title("Week 8 measured runtime by pipeline stage")
    axis.grid(axis="x", alpha=0.25)
    axis.bar_label(bars, fmt="%.3f", padding=3)
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    main()
