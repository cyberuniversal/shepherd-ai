"""Runtime integrity controls for MultiUAV resource measurements."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any, Callable, Mapping, Protocol, TypeVar


T = TypeVar("T")


class ControlTelemetry(Protocol):
    def identity(self) -> dict[str, Any]: ...

    def sample(self) -> dict[str, Any]: ...

    def compute_process_ids(self) -> tuple[int, ...] | None: ...

    def close(self) -> None: ...


class MeasuredOperation(Protocol):
    def measure(self, operation: Callable[[], T]) -> tuple[T, dict[str, Any]]: ...


def probe_nvml_preflight(
    *,
    telemetry: ControlTelemetry,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify exact-GPU NVML capabilities without loading a model."""

    hardware = _mapping(protocol.get("hardware"), "hardware")
    try:
        identity = telemetry.identity()
        _validate_identity(identity, hardware)
        sample = telemetry.sample()
        process_ids = telemetry.compute_process_ids()
        energy_counter = getattr(telemetry, "total_energy_millijoules", None)
        total_energy = energy_counter() if callable(energy_counter) else None
    finally:
        telemetry.close()
    required_sample_fields = (
        "power_milliwatts",
        "board_memory_used_bytes",
        "gpu_utilization_percent",
        "temperature_celsius",
    )
    for field in required_sample_fields:
        if not isinstance(sample.get(field), int):
            raise ValueError(f"NVML preflight field is unavailable: {field}")
    if process_ids is None:
        raise ValueError("NVML compute-process enumeration is unsupported")
    if len(process_ids) > int(hardware["maximum_gpu_compute_processes"]):
        raise ValueError("foreign GPU compute process detected during preflight")
    return {
        "status": "nvml_resource_preflight_passed_no_model_loaded",
        "gpu": identity,
        "sample": {
            field: int(sample[field]) for field in required_sample_fields
        },
        "compute_process_count": len(process_ids),
        "total_energy_counter_supported": total_energy is not None,
        "power_integration_fallback_available": True,
        "model_loaded": False,
        "measurement_started": False,
    }


def prepare_resource_condition(
    *,
    telemetry: ControlTelemetry,
    protocol: Mapping[str, Any],
    protocol_sha256: str,
    hardware_lock_path: Path,
    node_name: str,
    warmup_operation: Callable[[], Any],
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Lock hardware, run one warm-up, and wait for the frozen start state."""

    identity = telemetry.identity()
    hardware = _mapping(protocol.get("hardware"), "hardware")
    start = _mapping(protocol.get("start_control"), "start_control")
    _validate_identity(identity, hardware)
    lock = acquire_hardware_lock(
        hardware_lock_path,
        identity=identity,
        node_name=node_name,
        protocol_sha256=protocol_sha256,
    )
    baseline_samples: list[dict[str, Any]] = []
    baseline_wait_samples: list[dict[str, Any]] = []
    recovery_samples: list[dict[str, Any]] = []
    try:
        required_baseline = int(start["baseline_samples"])
        baseline_deadline = clock() + float(start["idle_timeout_seconds"])
        while len(baseline_samples) < required_baseline:
            observed_at = clock()
            if observed_at > baseline_deadline:
                raise TimeoutError("baseline idle and thermal sampling timed out")
            observed = _control_sample(telemetry, observed_at)
            baseline_wait_samples.append(observed)
            _validate_process_count(observed, hardware)
            idle = observed["gpu_utilization_percent"] <= int(
                start["maximum_gpu_utilization_percent"]
            )
            thermal = observed["temperature_celsius"] <= float(
                start["maximum_baseline_temperature_celsius"]
            )
            if idle and thermal:
                baseline_samples.append(observed)
            else:
                baseline_samples.clear()
            if len(baseline_samples) < required_baseline:
                sleeper(float(start["baseline_sample_interval_seconds"]))
        baseline_temperature = float(
            statistics.median(
                sample["temperature_celsius"] for sample in baseline_samples
            )
        )
        if baseline_temperature > float(
            start["maximum_baseline_temperature_celsius"]
        ):
            raise ValueError("GPU baseline temperature exceeds the frozen maximum")

        warmup_started = clock()
        warmup_operation()
        warmup_completed = clock()
        temperature_limit = min(
            baseline_temperature
            + float(start["maximum_temperature_above_baseline_celsius"]),
            float(start["maximum_post_warmup_temperature_celsius"]),
        )
        required = int(start["post_warmup_consecutive_idle_samples"])
        deadline = clock() + float(start["idle_timeout_seconds"])
        consecutive = 0
        while consecutive < required:
            if clock() > deadline:
                raise TimeoutError("post-warmup idle and thermal recovery timed out")
            observed = _control_sample(telemetry, clock())
            recovery_samples.append(observed)
            _validate_process_count(observed, hardware)
            idle = observed["gpu_utilization_percent"] <= int(
                start["maximum_gpu_utilization_percent"]
            )
            thermal = observed["temperature_celsius"] <= temperature_limit
            consecutive = consecutive + 1 if idle and thermal else 0
            if consecutive < required:
                sleeper(float(start["idle_sample_interval_seconds"]))
    finally:
        telemetry.close()

    report = {
        "schema_version": 1,
        "status": "resource_start_control_passed",
        "protocol_sha256": protocol_sha256,
        "hardware_lock": lock,
        "gpu": identity,
        "baseline_temperature_celsius": baseline_temperature,
        "temperature_limit_celsius": temperature_limit,
        "warmup": {
            "complete_method_cases": 1,
            "output_retained": False,
            "duration_seconds": warmup_completed - warmup_started,
        },
        "baseline_wait_samples": baseline_wait_samples,
        "baseline_samples": baseline_samples,
        "post_warmup_samples": recovery_samples,
        "measurement_started": False,
    }
    report["sha256"] = _sha256_json(report)
    return report


def acquire_hardware_lock(
    path: Path,
    *,
    identity: Mapping[str, Any],
    node_name: str,
    protocol_sha256: str,
) -> dict[str, Any]:
    """Create or verify the attempt-wide node and GPU UUID lock."""

    if not node_name.strip():
        raise ValueError("resource attempt requires a Kubernetes node name")
    lock = {
        "schema_version": 1,
        "protocol_sha256": protocol_sha256,
        "node_name": node_name,
        "gpu_name": str(identity.get("name", "")),
        "gpu_uuid": str(identity.get("uuid", "")),
        "driver_version": str(identity.get("driver_version", "")),
    }
    if not lock["gpu_name"] or not lock["gpu_uuid"]:
        raise ValueError("GPU identity is incomplete")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        if stored != lock:
            raise ValueError("resource attempt hardware identity drifted")
        return lock
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return lock


class ProtocolBoundResourceMonitor:
    """Attach protocol bindings and fail-closed checks to one measurement."""

    def __init__(
        self,
        *,
        monitor: MeasuredOperation,
        protocol: Mapping[str, Any],
        protocol_sha256: str,
        expected_identity: Mapping[str, Any],
        start_control_sha256: str,
        segment_id: str,
    ) -> None:
        self._monitor = monitor
        self._protocol = protocol
        self._protocol_sha256 = protocol_sha256
        self._expected_identity = dict(expected_identity)
        self._start_control_sha256 = start_control_sha256
        self._segment_id = segment_id

    def measure(self, operation: Callable[[], T]) -> tuple[T, dict[str, Any]]:
        value, report = self._monitor.measure(operation)
        validated = validate_resource_measurement(
            report,
            protocol=self._protocol,
            expected_identity=self._expected_identity,
        )
        validated["run_control"] = {
            "protocol_sha256": self._protocol_sha256,
            "start_control_sha256": self._start_control_sha256,
            "segment_id": self._segment_id,
        }
        return value, validated


def validate_resource_measurement(
    report: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    expected_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Mark a method-case measurement invalid when a frozen control fails."""

    result = dict(report)
    errors = list(result.get("errors", []))
    measurement = _mapping(protocol.get("measurement"), "measurement")
    identity = _mapping(result.get("gpu"), "measurement.gpu")
    for key in ("name", "uuid", "driver_version"):
        if identity.get(key) != expected_identity.get(key):
            errors.append(f"GPU identity mismatch: {key}")
    if result.get("sample_count", 0) < 2:
        errors.append("measurement retained fewer than two samples")
    observed_hz = result.get("observed_sample_hz")
    if not isinstance(observed_hz, (int, float)) or observed_hz < float(
        measurement["minimum_observed_sample_hz"]
    ):
        errors.append("observed sample rate is below the frozen minimum")
    energy = result.get("energy")
    if not isinstance(energy, Mapping) or not isinstance(
        energy.get("joules"), (int, float)
    ):
        errors.append("GPU-board energy is unavailable")
    required_processes = int(protocol["hardware"]["required_gpu_compute_processes"])
    maximum_processes = int(protocol["hardware"]["maximum_gpu_compute_processes"])
    samples = result.get("samples")
    if not isinstance(samples, list) or not samples:
        errors.append("compute-process telemetry samples are unavailable")
    else:
        for sample in samples:
            process_ids = sample.get("compute_process_ids") if isinstance(sample, Mapping) else None
            if not isinstance(process_ids, list):
                errors.append("compute-process enumeration is unavailable")
                break
            if not required_processes <= len(process_ids) <= maximum_processes:
                errors.append("unexpected GPU compute-process count during measurement")
                break
    result["errors"] = errors
    result["valid"] = bool(result.get("valid")) and not errors
    result["protocol_validation"] = {
        "valid": not errors,
        "minimum_observed_sample_hz": measurement[
            "minimum_observed_sample_hz"
        ],
        "same_gpu_identity": not any(
            error.startswith("GPU identity mismatch") for error in errors
        ),
    }
    return result


def _validate_identity(
    identity: Mapping[str, Any], hardware: Mapping[str, Any]
) -> None:
    if identity.get("name") != hardware.get("required_runtime_gpu_name"):
        raise ValueError("resource run is not on the frozen GPU product")
    if not str(identity.get("uuid", "")):
        raise ValueError("resource GPU UUID is absent")


def _control_sample(telemetry: ControlTelemetry, timestamp: float) -> dict[str, Any]:
    observed = dict(telemetry.sample())
    processes = telemetry.compute_process_ids()
    if processes is None:
        raise ValueError("GPU compute-process enumeration is unsupported")
    return {
        "monotonic_seconds": timestamp,
        "gpu_utilization_percent": int(observed["gpu_utilization_percent"]),
        "temperature_celsius": int(observed["temperature_celsius"]),
        "power_milliwatts": int(observed["power_milliwatts"]),
        "board_memory_used_bytes": int(observed["board_memory_used_bytes"]),
        "compute_process_ids": list(processes),
    }


def _validate_process_count(
    sample: Mapping[str, Any], hardware: Mapping[str, Any]
) -> None:
    processes = sample["compute_process_ids"]
    if not int(hardware["required_gpu_compute_processes"]) <= len(processes) <= int(
        hardware["maximum_gpu_compute_processes"]
    ):
        raise ValueError("foreign GPU compute process detected")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"resource protocol section is absent: {label}")
    return value


def _sha256_json(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
