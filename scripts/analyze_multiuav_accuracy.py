"""Run the registered MultiUAV source-cluster bootstrap analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_study_analysis import analyze_scored_study  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scoring-summary",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_scoring_v1"
        / "summary.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_bootstrap_v1",
    )
    args = parser.parse_args()

    report = analyze_scored_study(
        repository_root=ROOT,
        scoring_summary_path=args.scoring_summary,
        protocol_path=args.protocol,
        output_dir=args.output_dir,
    )
    output = args.output_dir / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
