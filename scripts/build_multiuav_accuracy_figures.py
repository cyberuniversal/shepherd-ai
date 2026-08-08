"""Build provenance-bound publication figures for MultiUAV accuracy results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_study_figures import (  # noqa: E402
    build_accuracy_figure_artifacts,
    load_accuracy_figure_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--scoring-summary",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--bootstrap-summary",
        type=Path,
        default=None,
    )
    parser.add_argument("--figure-dir", type=Path, default=None)
    parser.add_argument("--table-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    figure_dir = args.figure_dir or root / "reports/figures"
    table_dir = args.table_dir or root / "outputs/tables"
    manifest_path = (
        args.manifest
        or root
        / "outputs/evaluations/multiuav_accuracy_figures_v1/manifest.json"
    )
    figure_data = load_accuracy_figure_data(
        root,
        scoring_summary_path=args.scoring_summary,
        bootstrap_summary_path=args.bootstrap_summary,
    )
    manifest = build_accuracy_figure_artifacts(
        repository_root=root,
        figure_data=figure_data,
        figure_dir=figure_dir,
        table_dir=table_dir,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
