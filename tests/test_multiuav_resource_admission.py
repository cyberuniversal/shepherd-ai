from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from shepherd_ai.multiuav_checkpoints import RunConfig, result_key
from shepherd_ai.multiuav_resource_admission import (
    audit_tar_source_inventory,
    validate_resource_condition_rows,
    validate_resource_measurement_evidence,
    validate_resource_start_control,
)


GPU = {
    "gpu_index": 0,
    "name": "NVIDIA GeForce RTX 3090",
    "uuid": "GPU-test",
    "driver_version": "595.71.05",
}
HARDWARE_LOCK = {
    "schema_version": 1,
    "protocol_sha256": "b" * 64,
    "node_name": "test-node",
    "gpu_name": GPU["name"],
    "gpu_uuid": GPU["uuid"],
    "driver_version": GPU["driver_version"],
}
PROTOCOL = {
    "status": "final_resource_hardware_protocol_no_measurement_started",
    "protocol_version": "multiuav_resource_hardware_v1",
    "hardware": {
        "required_runtime_gpu_name": GPU["name"],
        "required_gpu_compute_processes": 1,
        "maximum_gpu_compute_processes": 1,
    },
    "measurement": {
        "sample_target_hz": 20.0,
        "minimum_observed_sample_hz": 15.0,
        "energy_primary": "nvml_total_energy_counter_millijoules",
        "energy_fallback": "nvml_power_trapezoidal_integration",
        "energy_scope": "nvidia_gpu_board_only",
    },
    "start_control": {
        "baseline_samples": 5,
        "maximum_gpu_utilization_percent": 5,
        "maximum_baseline_temperature_celsius": 60,
        "maximum_temperature_above_baseline_celsius": 2,
        "maximum_post_warmup_temperature_celsius": 60,
        "post_warmup_consecutive_idle_samples": 15,
        "warmup_complete_method_cases_per_condition_segment": 1,
        "warmup_output_retained": False,
    },
}


def _config() -> RunConfig:
    return RunConfig(
        run_id="resource-test",
        study_id="multiuav_validation_placement_v1",
        run_kind="resource",
        model_id="Qwen/Qwen2.5-3B-Instruct",
        model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        methods=("M1_monolithic",),
        dataset_sha256="a" * 64,
        prompt_contract_version="multiuav_prompt_contract_v1",
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="c" * 40,
        resource_repetition=1,
        hardware_protocol_sha256="b" * 64,
        resource_condition_order=1,
        resource_schedule_sha256="d" * 64,
    )


def _sample(timestamp: float) -> dict[str, object]:
    return {
        "monotonic_seconds": timestamp,
        "power_milliwatts": 100_000,
        "board_memory_used_bytes": 8_000_000_000,
        "gpu_utilization_percent": 1,
        "temperature_celsius": 40,
        "process_gpu_memory_bytes": 7_000_000_000,
        "compute_process_ids": [123],
        "process_rss_bytes": 2_000_000_000,
    }


def _summary(value: int) -> dict[str, int]:
    return {"start": value, "end": value, "minimum": value, "maximum": value}


def _measurement(segment_id: str, control_sha256: str) -> dict[str, object]:
    samples = [_sample(0.0), _sample(0.05), _sample(0.10)]
    return {
        "schema_version": 1,
        "valid": True,
        "duration_seconds": 0.10,
        "sample_target_hz": 20.0,
        "sample_count": 3,
        "observed_sample_hz": 20.0,
        "gpu": copy.deepcopy(GPU),
        "energy": {
            "scope": "nvidia_gpu_board_only",
            "method": "nvml_total_energy_counter",
            "joules": 10.0,
            "counter_start_millijoules": 1_000,
            "counter_end_millijoules": 11_000,
            "diagnostic_power_integral_joules": 10.0,
            "counter_vs_integral_relative_difference": 0.0,
        },
        "process_ram": _summary(2_000_000_000),
        "board_vram": _summary(8_000_000_000),
        "process_vram": _summary(7_000_000_000),
        "power_milliwatts": _summary(100_000),
        "gpu_utilization_percent": _summary(1),
        "temperature_celsius": _summary(40),
        "compute_process_ids_observed": [123],
        "samples": samples,
        "errors": [],
        "claim_limit": "not_total_workstation_simulator_network_or_uav_energy",
        "protocol_validation": {
            "valid": True,
            "minimum_observed_sample_hz": 15.0,
            "same_gpu_identity": True,
        },
        "run_control": {
            "protocol_sha256": "b" * 64,
            "start_control_sha256": control_sha256,
            "segment_id": segment_id,
        },
    }


def _start_control(segment_id: str = "segment-1") -> dict[str, object]:
    del segment_id
    idle_sample = {
        "monotonic_seconds": 1.0,
        "gpu_utilization_percent": 0,
        "temperature_celsius": 40,
        "power_milliwatts": 25_000,
        "board_memory_used_bytes": 8_000_000_000,
        "compute_process_ids": [123],
    }
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "resource_start_control_passed",
        "protocol_sha256": "b" * 64,
        "hardware_lock": copy.deepcopy(HARDWARE_LOCK),
        "gpu": copy.deepcopy(GPU),
        "baseline_temperature_celsius": 40.0,
        "temperature_limit_celsius": 42.0,
        "warmup": {
            "complete_method_cases": 1,
            "output_retained": False,
            "duration_seconds": 1.0,
        },
        "baseline_wait_samples": [copy.deepcopy(idle_sample) for _ in range(5)],
        "baseline_samples": [copy.deepcopy(idle_sample) for _ in range(5)],
        "post_warmup_samples": [copy.deepcopy(idle_sample) for _ in range(15)],
        "measurement_started": False,
    }
    rendered = json.dumps(
        report, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    report["sha256"] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return report


class ResourceMeasurementAdmissionTests(unittest.TestCase):
    def test_revalidates_measurement_from_retained_samples(self) -> None:
        report = _measurement("segment-1", "e" * 64)

        audit = validate_resource_measurement_evidence(
            report,
            protocol=PROTOCOL,
            hardware_lock=HARDWARE_LOCK,
        )

        self.assertTrue(audit["valid"])
        self.assertEqual(audit["sample_count"], 3)
        report["observed_sample_hz"] = 1000.0
        with self.assertRaisesRegex(ValueError, "observed sample rate"):
            validate_resource_measurement_evidence(
                report,
                protocol=PROTOCOL,
                hardware_lock=HARDWARE_LOCK,
            )

    def test_rejects_energy_and_process_tampering(self) -> None:
        report = _measurement("segment-1", "e" * 64)
        report["energy"]["joules"] = 99.0
        with self.assertRaisesRegex(ValueError, "energy"):
            validate_resource_measurement_evidence(
                report,
                protocol=PROTOCOL,
                hardware_lock=HARDWARE_LOCK,
            )
        report = _measurement("segment-1", "e" * 64)
        report["samples"][0]["compute_process_ids"] = [123, 456]
        with self.assertRaisesRegex(ValueError, "process"):
            validate_resource_measurement_evidence(
                report,
                protocol=PROTOCOL,
                hardware_lock=HARDWARE_LOCK,
            )


class ResourceStartControlAdmissionTests(unittest.TestCase):
    def test_validates_control_hash_thermal_recovery_and_lock(self) -> None:
        report = _start_control()

        audit = validate_resource_start_control(
            report,
            protocol=PROTOCOL,
            hardware_lock=HARDWARE_LOCK,
        )

        self.assertTrue(audit["valid"])
        self.assertEqual(audit["post_warmup_consecutive_samples"], 15)

    def test_rejects_control_hash_and_hardware_drift(self) -> None:
        report = _start_control()
        report["gpu"]["uuid"] = "GPU-other"
        with self.assertRaisesRegex(ValueError, "hash"):
            validate_resource_start_control(
                report,
                protocol=PROTOCOL,
                hardware_lock=HARDWARE_LOCK,
            )
        report = _start_control()
        report["hardware_lock"]["node_name"] = "other-node"
        payload = dict(report)
        payload.pop("sha256")
        report["sha256"] = hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "hardware lock"):
            validate_resource_start_control(
                report,
                protocol=PROTOCOL,
                hardware_lock=HARDWARE_LOCK,
            )


class ResourceConditionAdmissionTests(unittest.TestCase):
    def test_rejects_duplicate_or_missing_matrix_rows(self) -> None:
        config = _config()
        control = _start_control()
        case_ids = tuple(f"case-{index:03}" for index in range(150))
        rows = []
        for case_id in case_ids:
            row_key = result_key(case_id, config.methods[0])
            rows.append(
                {
                    "schema_version": 3,
                    "config_hash": config.config_hash,
                    "result_key": row_key,
                    "case_id": case_id,
                    "method_id": config.methods[0],
                    "model_id": config.model_id,
                    "model_revision": config.model_revision,
                    "result": {
                        "case_id": case_id,
                        "method_id": config.methods[0],
                        "resource_measurement": _measurement(
                            "segment-1", str(control["sha256"])
                        ),
                    },
                }
            )

        audit = validate_resource_condition_rows(
            rows,
            config=config,
            expected_case_ids=case_ids,
            protocol=PROTOCOL,
            start_controls={"segment-1": control},
            hardware_lock=HARDWARE_LOCK,
        )

        self.assertTrue(audit["valid"])
        self.assertEqual(audit["rows"], 150)
        rows[-1] = copy.deepcopy(rows[0])
        with self.assertRaisesRegex(ValueError, "matrix"):
            validate_resource_condition_rows(
                rows,
                config=config,
                expected_case_ids=case_ids,
                protocol=PROTOCOL,
                start_controls={"segment-1": control},
                hardware_lock=HARDWARE_LOCK,
            )


class ResourceArchiveAdmissionTests(unittest.TestCase):
    def test_verifies_exact_source_inventory_and_rejects_unsafe_members(self) -> None:
        content = b"campaign\n"
        source_manifest = {
            "schema_version": 1,
            "artifact_status": "complete_resource_campaign_raw_results_unscored",
            "file_count": 1,
            "total_bytes": len(content),
            "raw_model_outputs_inspected": False,
            "hidden_labels_inspected": False,
            "files": {
                "campaign_summary.json": {
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "campaign.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                root = tarfile.TarInfo("resource-v1-attempt3/")
                root.type = tarfile.DIRTYPE
                archive.addfile(root)
                member = tarfile.TarInfo(
                    "resource-v1-attempt3/campaign_summary.json"
                )
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

            audit = audit_tar_source_inventory(archive_path, source_manifest)
            self.assertEqual(audit["verified_files"], 1)

            with tarfile.open(archive_path, "w:gz") as archive:
                member = tarfile.TarInfo("../escape")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with self.assertRaisesRegex(ValueError, "unsafe"):
                audit_tar_source_inventory(archive_path, source_manifest)


if __name__ == "__main__":
    unittest.main()
