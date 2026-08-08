"""Bind all 24 resource conditions to a clean committed execution state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resource_protocol import sha256_file  # noqa: E402
from shepherd_ai.multiuav_resource_schedule import (  # noqa: E402
    build_resource_run_configs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets/multiuav_plat"
    parser.add_argument(
        "--schedule", type=Path, default=metadata / "resource_schedule_v1.json"
    )
    parser.add_argument(
        "--hardware-protocol",
        type=Path,
        default=metadata / "resource_hardware_protocol_v1.json",
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
        "--accuracy-protocol",
        type=Path,
        default=metadata / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=metadata / "resource_run_configs_v1.json",
    )
    args = parser.parse_args()

    if _git("status", "--porcelain").strip():
        raise ValueError("final resource configs require a clean committed worktree")
    code_commit = _git("rev-parse", "HEAD").strip().lower()
    schedule = _read(args.schedule)
    hardware = _read(args.hardware_protocol)
    manifest = _read(args.accuracy_manifest)
    protocol = _read(args.accuracy_protocol)
    schedule_hash = sha256_file(args.schedule)
    hardware_hash = sha256_file(args.hardware_protocol)
    manifest_hash = sha256_file(args.accuracy_manifest)
    dataset_hash = sha256_file(args.intervention_dataset)
    bindings = schedule.get("artifact_bindings", {})
    if bindings.get("hardware_protocol_sha256") != hardware_hash:
        raise ValueError("resource schedule is not bound to the hardware protocol")
    if bindings.get("accuracy_manifest_sha256") != manifest_hash:
        raise ValueError("resource schedule is not bound to the accuracy manifest")
    if bindings.get("intervention_dataset_sha256") != dataset_hash:
        raise ValueError("resource schedule is not bound to the intervention dataset")
    if manifest.get("data_status") != "approved_evaluation_data":
        raise ValueError("resource configs require approved evaluation data")
    if hardware.get("status") != "final_resource_hardware_protocol_no_measurement_started":
        raise ValueError("resource hardware protocol is not final")
    configs = build_resource_run_configs(
        schedule["condition_schedule"]["rows"],
        study_id="multiuav_validation_placement_v1",
        dataset_status=manifest["data_status"],
        dataset_sha256=manifest_hash,
        code_commit=code_commit,
        hardware_protocol_sha256=hardware_hash,
        resource_schedule_sha256=schedule_hash,
        decoding=protocol["decoding"],
    )
    artifact = {
        "schema_version": 1,
        "status": "final_resource_configs_bound_no_measurement_started",
        "claim_status": "registered_execution_configs_not_resource_results",
        "measurement_started": False,
        "code_commit": code_commit,
        "resource_schedule_sha256": schedule_hash,
        "hardware_protocol_sha256": hardware_hash,
        "accuracy_manifest_sha256": manifest_hash,
        "intervention_dataset_sha256": dataset_hash,
        "accuracy_protocol_sha256": sha256_file(args.accuracy_protocol),
        "expected_conditions": 24,
        "expected_rows_per_condition": 150,
        "expected_rows_total": 3_600,
        "configs": [config.to_dict() for config in configs],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(artifact, indent=2, sort_keys=True))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


if __name__ == "__main__":
    main()
