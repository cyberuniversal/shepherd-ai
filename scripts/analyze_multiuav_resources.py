"""Analyze the admitted MultiUAV resource campaign without scoring outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resource_analysis import (  # noqa: E402
    analyze_admitted_resource_campaign,
)


CAMPAIGN_DIR = (
    ROOT
    / "datasets"
    / "multiuav_plat"
    / "nautilus"
    / "resource_campaign_attempt3_complete"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--admission",
        type=Path,
        default=(
            ROOT
            / "datasets"
            / "multiuav_plat"
            / "resource_campaign_admission_v1.json"
        ),
    )
    parser.add_argument(
        "--analysis-freeze",
        type=Path,
        default=(
            ROOT
            / "datasets"
            / "multiuav_plat"
            / "resource_analysis_freeze_v1.json"
        ),
    )
    parser.add_argument(
        "--deviation",
        type=Path,
        default=(
            ROOT
            / "datasets"
            / "multiuav_plat"
            / "resource_analysis_protocol_deviation_v1.json"
        ),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=CAMPAIGN_DIR / "resource-v1-attempt3-complete.tar.gz",
    )
    parser.add_argument(
        "--resource-schedule",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "resource_schedule_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "outputs"
            / "evaluations"
            / "multiuav_resource_analysis_v1"
        ),
    )
    args = parser.parse_args()

    summary = analyze_admitted_resource_campaign(
        repository_root=ROOT,
        admission_path=args.admission,
        analysis_freeze_path=args.analysis_freeze,
        deviation_path=args.deviation,
        archive_path=args.archive,
        resource_schedule_path=args.resource_schedule,
        output_dir=args.output_dir,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_bytes(rendered.encode("utf-8"))
    print(rendered, end="")


if __name__ == "__main__":
    main()
