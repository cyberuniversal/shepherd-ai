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
    def __init__(
        self,
        *,
        processes=(101,),
        recovery_temperature=42,
        temperature_sequence=(),
        utilization_sequence=(),
    ) -> None:
        self.processes = processes
        self.recovery_temperature = recovery_temperature
        self.temperature_sequence = list(temperature_sequence)
        self.utilization_sequence = list(utilization_sequence)
        self.closed = False

    def identity(self):
        return {
            "name": "NVIDIA GeForce RTX 3090",
            "uuid": "GPU-fixed",
            "driver_version": "synthetic",
        }

    def sample(self):
        utilization = (
            self.utilization_sequence.pop(0)
            if self.utilization_sequence
            else 0
        )
        temperature = (
            self.temperature_sequence.pop(0)
            if self.temperature_sequence
            else self.recovery_temperature
        )
        return {
            "power_milliwatts": 30_000,
            "board_memory_used_bytes": 15_000,
            "gpu_utilization_percent": utilization,
            "temperature_celsius": temperature,
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

    def test_waits_for_consecutive_idle_baseline_samples(self) -> None:
        protocol = build_resource_hardware_protocol()
        telemetry = _Telemetry(utilization_sequence=(30, 20, 0, 0, 0, 0, 0))
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

        self.assertEqual(len(report["baseline_wait_samples"]), 7)
        self.assertEqual(len(report["baseline_samples"]), 5)
        self.assertTrue(
            all(
                sample["gpu_utilization_percent"] == 0
                for sample in report["baseline_samples"]
            )
        )

    def test_waits_for_consecutive_thermally_eligible_baseline_samples(self) -> None:
        protocol = build_resource_hardware_protocol()
        telemetry = _Telemetry(
            temperature_sequence=(68, 65, 60, 59, 58, 57, 56)
        )
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

        self.assertEqual(len(report["baseline_wait_samples"]), 7)
        self.assertEqual(len(report["baseline_samples"]), 5)
        self.assertEqual(
            [sample["temperature_celsius"] for sample in report["baseline_samples"]],
            [60, 59, 58, 57, 56],
        )

    def test_hot_idle_baseline_fails_closed_at_registered_timeout(self) -> None:
        protocol = build_resource_hardware_protocol()
        telemetry = _Telemetry(recovery_temperature=68)
        now = [0.0]

        def clock():
            now[0] += 200.0
            return now[0]

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                TimeoutError, "baseline idle and thermal sampling"
            ):
                prepare_resource_condition(
                    telemetry=telemetry,
                    protocol=protocol,
                    protocol_sha256="a" * 64,
                    hardware_lock_path=Path(temporary) / "hardware.json",
                    node_name="node-3090",
                    warmup_operation=lambda: None,
                    sleeper=lambda _: None,
                    clock=clock,
                )

        self.assertTrue(telemetry.closed)

    def test_baseline_wait_fails_closed_at_registered_timeout(self) -> None:
        protocol = build_resource_hardware_protocol()
        telemetry = _Telemetry(utilization_sequence=(30,) * 10)
        now = [0.0]

        def clock():
            now[0] += 200.0
            return now[0]

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                TimeoutError, "baseline idle and thermal sampling"
            ):
                prepare_resource_condition(
                    telemetry=telemetry,
                    protocol=protocol,
                    protocol_sha256="a" * 64,
                    hardware_lock_path=Path(temporary) / "hardware.json",
                    node_name="node-3090",
                    warmup_operation=lambda: None,
                    sleeper=lambda _: None,
                    clock=clock,
                )

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
