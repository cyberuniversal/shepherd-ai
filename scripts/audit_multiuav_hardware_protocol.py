"""Run a synthetic NVML probe and freeze the resource-measurement contract."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import sys
from time import sleep


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resources import (  # noqa: E402
    NvmlResourceMonitor,
    REGISTERED_SAMPLE_HZ,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu-index", type=int, default=0)
    args = parser.parse_args()

    monitor = NvmlResourceMonitor(
        sample_hz=REGISTERED_SAMPLE_HZ,
        telemetry=_telemetry(args.gpu_index),
    )
    _, probe = monitor.measure(lambda: sleep(0.35))
    result = {
        "schema_version": 1,
        "valid": (
            probe["valid"]
            and probe["sample_target_hz"] == REGISTERED_SAMPLE_HZ
            and probe["sample_count"] >= 2
        ),
        "measurement_unit": "complete_method_case",
        "accuracy_resource_separation": {
            "accuracy_runs_per_checkpoint": 1,
            "resource_source_clusters": 30,
            "variants_per_cluster": 5,
            "resource_repetitions": 3,
            "repetition_binding": "separate_run_config_hash_per_repetition",
            "condition_order_binding": "schedule_hash_and_order_in_run_config",
        },
        "required_metrics": [
            "wall_clock_latency",
            "input_tokens",
            "output_tokens",
            "model_call_count",
            "process_ram",
            "board_vram",
            "process_vram_when_available",
            "nvidia_gpu_board_energy",
        ],
        "energy_policy": {
            "preferred": "nvml_total_energy_counter_millijoules",
            "fallback": "20_hz_nvml_power_trapezoidal_integration",
            "scope": "nvidia_gpu_board_only",
            "excluded": [
                "workstation_energy",
                "simulator_energy",
                "network_energy",
                "uav_energy",
            ],
        },
        "synthetic_probe": probe,
        "model_invoked": False,
        "study_cases_evaluated": False,
        "python_version": platform.python_version(),
        "package_versions": {
            name: _package_version(name)
            for name in ("nvidia-ml-py", "psutil")
        },
        "source_code_sha256": {
            "multiuav_resources.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_resources.py"
            ),
            "multiuav_experiment.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_experiment.py"
            ),
            "multiuav_runner.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_runner.py"
            ),
            "multiuav_checkpoints.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_checkpoints.py"
            ),
            "audit_multiuav_hardware_protocol.py": sha256_file(
                ROOT / "scripts" / "audit_multiuav_hardware_protocol.py"
            ),
        },
        "claim_status": "hardware_measurement_contract_synthetic_probe_only",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["valid"]:
        raise SystemExit(1)


def _telemetry(gpu_index: int):
    from shepherd_ai.multiuav_resources import NvmlDeviceTelemetry

    return NvmlDeviceTelemetry(gpu_index=gpu_index)


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


if __name__ == "__main__":
    main()
