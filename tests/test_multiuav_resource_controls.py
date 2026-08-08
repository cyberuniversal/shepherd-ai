from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_resource_controls import (
    acquire_hardware_lock,
    prepare_resource_condition,
    probe_nvml_preflight,
    validate_resource_measurement,
)
from shepherd_ai.multiuav_resource_protocol import build_resource_hardware_protocol


class _Telemetry:
    def __init__(self, *, processes=(101,), recovery_temperature=42) -> None:
        self.processes = processes
        self.recovery_temperature = recovery_temperature
        self.closed = False

    def identity(self):
        return {
            "name": "NVIDIA GeForce RTX 3090",
            "uuid": "GPU-fixed",
            "driver_version": "synthetic",
        }

    def sample(self):
        return {
            "power_milliwatts": 30_000,
            "board_memory_used_bytes": 15_000,
            "gpu_utilization_percent": 0,
            "temperature_celsius": self.recovery_temperature,
            "process_gpu_memory_bytes": 14_000,
        }

    def compute_process_ids(self):
        return tuple(self.processes)

    def total_energy_millijoules(self):
        return 1234

    def close(self):
        self.closed = True


class MultiUavResourceControlTests(unittest.TestCase):
    def test_nvml_preflight_validates_capabilities_without_model(self) -> None:
        report = probe_nvml_preflight(
            telemetry=_Telemetry(processes=()),
            protocol=build_resource_hardware_protocol(),
        )

        self.assertEqual(
            report["status"], "nvml_resource_preflight_passed_no_model_loaded"
        )
        self.assertEqual(report["compute_process_count"], 0)
        self.assertTrue(report["total_energy_counter_supported"])
        self.assertFalse(report["model_loaded"])

    def test_passes_warmup_idle_control_and_locks_hardware(self) -> None:
        protocol = build_resource_hardware_protocol()
        telemetry = _Telemetry()
        now = [0.0]

        def clock():
            now[0] += 1.0
            return now[0]

        with tempfile.TemporaryDirectory() as temporary:
            report = prepare_resource_condition(
                telemetry=telemetry,
                protocol=protocol,
                protocol_sha256="a" * 64,
                hardware_lock_path=Path(temporary) / "hardware.json",
                node_name="node-3090",
                warmup_operation=lambda: None,
                sleeper=lambda _: None,
                clock=clock,
            )

        self.assertEqual(report["status"], "resource_start_control_passed")
        self.assertEqual(len(report["baseline_samples"]), 5)
        self.assertEqual(len(report["post_warmup_samples"]), 15)
        self.assertFalse(report["measurement_started"])
        self.assertTrue(telemetry.closed)

    def test_rejects_background_gpu_process(self) -> None:
        protocol = build_resource_hardware_protocol()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "foreign GPU"):
                prepare_resource_condition(
                    telemetry=_Telemetry(processes=(101, 202)),
                    protocol=protocol,
                    protocol_sha256="a" * 64,
                    hardware_lock_path=Path(temporary) / "hardware.json",
                    node_name="node-3090",
                    warmup_operation=lambda: None,
                    sleeper=lambda _: None,
                )

    def test_hardware_lock_rejects_gpu_uuid_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "hardware.json"
            identity = {
                "name": "NVIDIA GeForce RTX 3090",
                "uuid": "GPU-first",
                "driver_version": "driver",
            }
            acquire_hardware_lock(
                path,
                identity=identity,
                node_name="node-3090",
                protocol_sha256="a" * 64,
            )
            identity["uuid"] = "GPU-second"

            with self.assertRaisesRegex(ValueError, "identity drifted"):
                acquire_hardware_lock(
                    path,
                    identity=identity,
                    node_name="node-3090",
                    protocol_sha256="a" * 64,
                )

    def test_marks_low_sample_rate_measurement_invalid(self) -> None:
        protocol = build_resource_hardware_protocol()
        report = {
            "valid": True,
            "sample_count": 2,
            "observed_sample_hz": 10.0,
            "gpu": {
                "name": "NVIDIA GeForce RTX 3090",
                "uuid": "GPU-fixed",
                "driver_version": "driver",
            },
            "energy": {"joules": 2.0},
            "samples": [{"compute_process_ids": [101]}] * 2,
            "errors": [],
        }

        result = validate_resource_measurement(
            report,
            protocol=protocol,
            expected_identity=report["gpu"],
        )

        self.assertFalse(result["valid"])
        self.assertIn("observed sample rate", result["errors"][0])

    def test_marks_foreign_compute_process_measurement_invalid(self) -> None:
        protocol = build_resource_hardware_protocol()
        report = {
            "valid": True,
            "sample_count": 2,
            "observed_sample_hz": 20.0,
            "gpu": {
                "name": "NVIDIA GeForce RTX 3090",
                "uuid": "GPU-fixed",
                "driver_version": "driver",
            },
            "energy": {"joules": 2.0},
            "samples": [{"compute_process_ids": [101, 202]}] * 2,
            "errors": [],
        }

        result = validate_resource_measurement(
            report,
            protocol=protocol,
            expected_identity=report["gpu"],
        )

        self.assertFalse(result["valid"])
        self.assertTrue(
            any(
                "compute-process count" in error
                for error in result["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
