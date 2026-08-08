"""Freeze final MultiUAV resource controls and the approved 30-cluster schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resource_protocol import (  # noqa: E402
    build_resource_hardware_protocol,
    finalize_resource_schedule,
    sha256_file,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets/multiuav_plat"
    parser.add_argument(
        "--candidate",
        type=Path,
        default=metadata / "resource_schedule_candidate_v1.json",
    )
    parser.add_argument(
        "--accuracy-manifest",
        type=Path,
        default=metadata / "accuracy_case_manifest_v1.json",
    )
    parser.add_argument(
        "--intervention-dataset",
        type=Path,
        default=metadata / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--hardware-output",
        type=Path,
        default=metadata / "resource_hardware_protocol_v1.json",
    )
    parser.add_argument(
        "--schedule-output",
        type=Path,
        default=metadata / "resource_schedule_v1.json",
    )
    args = parser.parse_args()

    hardware = build_resource_hardware_protocol()
    _write(args.hardware_output, hardware)
    schedule = finalize_resource_schedule(
        candidate=_read(args.candidate),
        accuracy_manifest=_read(args.accuracy_manifest),
        candidate_sha256=sha256_file(args.candidate),
        accuracy_manifest_sha256=sha256_file(args.accuracy_manifest),
        intervention_dataset_sha256=sha256_file(args.intervention_dataset),
        hardware_protocol_sha256=sha256_file(args.hardware_output),
    )
    _write(args.schedule_output, schedule)
    print(
        json.dumps(
            {
                "status": "resource_protocol_and_schedule_frozen",
                "hardware_protocol_sha256": sha256_file(args.hardware_output),
                "resource_schedule_sha256": sha256_file(args.schedule_output),
                "source_tasks": schedule["selection"]["source_task_count"],
                "cases": schedule["selection"]["case_count"],
                "conditions": schedule["condition_schedule"]["conditions"],
                "expected_rows": schedule["expected"]["total_method_case_rows"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
