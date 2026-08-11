"""Admit the preserved MultiUAV resource campaign without scoring results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resource_admission import (  # noqa: E402
    admit_resource_campaign,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


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
        "--archive",
        type=Path,
        default=CAMPAIGN_DIR / "resource-v1-attempt3-complete.tar.gz",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=CAMPAIGN_DIR / "source_manifest.json",
    )
    parser.add_argument(
        "--preservation-manifest",
        type=Path,
        default=CAMPAIGN_DIR / "preservation_manifest.json",
    )
    parser.add_argument(
        "--run-configs",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "resource_run_configs_v1.json",
    )
    parser.add_argument(
        "--resource-schedule",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "resource_schedule_v1.json",
    )
    parser.add_argument(
        "--hardware-protocol",
        type=Path,
        default=(
            ROOT / "datasets" / "multiuav_plat" / "resource_hardware_protocol_v1.json"
        ),
    )
    parser.add_argument(
        "--accuracy-manifest",
        type=Path,
        default=(
            ROOT / "datasets" / "multiuav_plat" / "accuracy_case_manifest_v1.json"
        ),
    )
    parser.add_argument(
        "--intervention-dataset",
        type=Path,
        default=(
            ROOT / "datasets" / "multiuav_plat" / "intervention_dataset_v1.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT / "datasets" / "multiuav_plat" / "resource_campaign_admission_v1.json"
        ),
    )
    args = parser.parse_args()

    report = admit_resource_campaign(
        archive_path=args.archive,
        source_manifest_path=args.source_manifest,
        preservation_manifest_path=args.preservation_manifest,
        run_configs_path=args.run_configs,
        resource_schedule_path=args.resource_schedule,
        hardware_protocol_path=args.hardware_protocol,
        accuracy_manifest_path=args.accuracy_manifest,
        intervention_dataset_path=args.intervention_dataset,
    )
    report["source_code_sha256"] = {
        "multiuav_checkpoints.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_checkpoints.py"
        ),
        "multiuav_resource_admission.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_resource_admission.py"
        ),
        "multiuav_resource_controls.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_resource_controls.py"
        ),
        "multiuav_resource_execution.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_resource_execution.py"
        ),
        "multiuav_resource_protocol.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_resource_protocol.py"
        ),
        "multiuav_resources.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_resources.py"
        ),
        "admit_multiuav_resource_campaign.py": sha256_file(Path(__file__)),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
