"""Method-case resource measurement for the MultiUAV study."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from threading import Event, Thread
from time import monotonic
from typing import Any, Callable, Protocol, TypeVar


T = TypeVar("T")
RESOURCE_MEASUREMENT_SCHEMA_VERSION = 1
REGISTERED_SAMPLE_HZ = 20.0


class GpuTelemetry(Protocol):
    def identity(self) -> dict[str, Any]:
        """Return stable GPU and driver metadata."""

    def sample(self) -> dict[str, Any]:
        """Return one board telemetry sample."""

    def total_energy_millijoules(self) -> int | None:
        """Return the cumulative board counter or None when unsupported."""

    def compute_process_ids(self) -> tuple[int, ...] | None:
        """Return board compute PIDs, or None when unsupported."""

    def close(self) -> None:
        """Release the telemetry library."""


@dataclass(frozen=True)
class ResourceSample:
    monotonic_seconds: float
    power_milliwatts: int
    board_memory_used_bytes: int
    gpu_utilization_percent: int
    temperature_celsius: int
    process_gpu_memory_bytes: int | None
    compute_process_ids: tuple[int, ...] | None
    process_rss_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "monotonic_seconds": self.monotonic_seconds,
            "power_milliwatts": self.power_milliwatts,
            "board_memory_used_bytes": self.board_memory_used_bytes,
            "gpu_utilization_percent": self.gpu_utilization_percent,
            "temperature_celsius": self.temperature_celsius,
            "process_gpu_memory_bytes": self.process_gpu_memory_bytes,
            "compute_process_ids": (
                list(self.compute_process_ids)
                if self.compute_process_ids is not None
                else None
            ),
            "process_rss_bytes": self.process_rss_bytes,
        }


class NvmlDeviceTelemetry:
    """Read one NVIDIA board through the official NVML Python bindings."""

    def __init__(
        self,
        *,
        gpu_index: int = 0,
        process_id: int | None = None,
        pynvml_module: Any | None = None,
    ) -> None:
        if gpu_index < 0:
            raise ValueError("gpu_index must be non-negative")
        self._nvml = pynvml_module or importlib.import_module("pynvml")
        self._nvml.nvmlInit()
        self._closed = False
        self._handle = self._nvml.nvmlDeviceGetHandleByIndex(gpu_index)
        self._gpu_index = gpu_index
        self._process_id = process_id if process_id is not None else os.getpid()

    def identity(self) -> dict[str, Any]:
        return {
            "gpu_index": self._gpu_index,
            "name": _decode(self._nvml.nvmlDeviceGetName(self._handle)),
            "uuid": _decode(self._nvml.nvmlDeviceGetUUID(self._handle)),
            "driver_version": _decode(self._nvml.nvmlSystemGetDriverVersion()),
        }

    def sample(self) -> dict[str, Any]:
        memory = self._nvml.nvmlDeviceGetMemoryInfo(self._handle)
        utilization = self._nvml.nvmlDeviceGetUtilizationRates(self._handle)
        process_ids, process_gpu_memory = self._process_snapshot()
        return {
            "power_milliwatts": int(
                self._nvml.nvmlDeviceGetPowerUsage(self._handle)
            ),
            "board_memory_used_bytes": int(memory.used),
            "gpu_utilization_percent": int(utilization.gpu),
            "temperature_celsius": int(
                self._nvml.nvmlDeviceGetTemperature(
                    self._handle,
                    self._nvml.NVML_TEMPERATURE_GPU,
                )
            ),
            "process_gpu_memory_bytes": process_gpu_memory,
            "compute_process_ids": process_ids,
        }

    def total_energy_millijoules(self) -> int | None:
        try:
            return int(
                self._nvml.nvmlDeviceGetTotalEnergyConsumption(self._handle)
            )
        except self._nvml.NVMLError_NotSupported:
            return None

    def compute_process_ids(self) -> tuple[int, ...] | None:
        function = self._compute_process_function()
        if function is None:
            return None
        try:
            return tuple(sorted(int(process.pid) for process in function(self._handle)))
        except self._nvml.NVMLError_NotSupported:
            return None

    def close(self) -> None:
        if not self._closed:
            self._nvml.nvmlShutdown()
            self._closed = True

    def _process_snapshot(self) -> tuple[tuple[int, ...] | None, int | None]:
        function = self._compute_process_function()
        if function is None:
            return None, None
        try:
            processes = function(self._handle)
        except self._nvml.NVMLError_NotSupported:
            return None, None
        process_ids = tuple(sorted(int(process.pid) for process in processes))
        for process in processes:
            if int(process.pid) != self._process_id:
                continue
            used = getattr(process, "usedGpuMemory", None)
            memory = int(used) if isinstance(used, int) and used >= 0 else None
            return process_ids, memory
        return process_ids, 0

    def _compute_process_function(self) -> Any | None:
        for name in (
            "nvmlDeviceGetComputeRunningProcesses_v3",
            "nvmlDeviceGetComputeRunningProcesses_v2",
            "nvmlDeviceGetComputeRunningProcesses",
        ):
            function = getattr(self._nvml, name, None)
            if function is not None:
                return function
        return None


class NvmlResourceMonitor:
    """Measure one complete method-case with NVML samples and process RSS."""

    def __init__(
        self,
        *,
        sample_hz: float = REGISTERED_SAMPLE_HZ,
        telemetry: GpuTelemetry | None = None,
        process_rss_reader: Callable[[], int] | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if sample_hz <= 0:
            raise ValueError("sample_hz must be positive")
        self.sample_hz = float(sample_hz)
        self._telemetry = telemetry or NvmlDeviceTelemetry()
        if process_rss_reader is None:
            psutil = importlib.import_module("psutil")
            process = psutil.Process(os.getpid())
            process_rss_reader = lambda: int(process.memory_info().rss)
        self._process_rss_reader = process_rss_reader
        self._clock = clock

    def measure(self, operation: Callable[[], T]) -> tuple[T, dict[str, Any]]:
        """Run an operation and return its value plus a complete report."""

        if not callable(operation):
            raise TypeError("operation must be callable")
        samples: list[ResourceSample] = []
        errors: list[str] = []
        stop = Event()
        interval = 1.0 / self.sample_hz

        def capture() -> None:
            try:
                observed = self._telemetry.sample()
                samples.append(
                    ResourceSample(
                        monotonic_seconds=self._clock(),
                        process_rss_bytes=int(self._process_rss_reader()),
                        **observed,
                    )
                )
            except Exception as error:  # retained in the measurement report
                errors.append(f"{type(error).__name__}: {error}")

        energy_start = self._telemetry.total_energy_millijoules()
        started = self._clock()
        capture()

        def sample_loop() -> None:
            next_sample = started + interval
            while not stop.wait(max(0.0, next_sample - self._clock())):
                capture()
                if errors:
                    return
                next_sample += interval

        thread = Thread(target=sample_loop, name="multiuav-nvml-sampler")
        thread.start()
        try:
            value = operation()
        finally:
            stop.set()
            thread.join()
            capture()
            completed = self._clock()
            energy_end = self._telemetry.total_energy_millijoules()
            identity = self._telemetry.identity()
            self._telemetry.close()

        report = build_resource_report(
            identity=identity,
            samples=samples,
            sample_target_hz=self.sample_hz,
            started=started,
            completed=completed,
            total_energy_start_millijoules=energy_start,
            total_energy_end_millijoules=energy_end,
            errors=errors,
        )
        return value, report


def build_resource_report(
    *,
    identity: dict[str, Any],
    samples: list[ResourceSample],
    sample_target_hz: float,
    started: float,
    completed: float,
    total_energy_start_millijoules: int | None,
    total_energy_end_millijoules: int | None,
    errors: list[str],
) -> dict[str, Any]:
    """Summarize samples under the registered board-energy definition."""

    duration = completed - started
    if duration < 0:
        errors.append("measurement clock moved backwards")
    integrated_joules = integrate_power_samples(samples)
    energy_method = "nvml_total_energy_counter"
    energy_joules: float | None = None
    if (
        total_energy_start_millijoules is not None
        and total_energy_end_millijoules is not None
        and total_energy_end_millijoules >= total_energy_start_millijoules
    ):
        energy_joules = (
            total_energy_end_millijoules - total_energy_start_millijoules
        ) / 1000.0
    else:
        energy_method = "nvml_power_trapezoidal_integration"
        energy_joules = integrated_joules
        if energy_joules is None:
            errors.append("fewer than two valid power samples")

    observed_hz = None
    if len(samples) >= 2:
        span = samples[-1].monotonic_seconds - samples[0].monotonic_seconds
        if span > 0:
            observed_hz = (len(samples) - 1) / span
    process_gpu_values = [
        sample.process_gpu_memory_bytes
        for sample in samples
        if sample.process_gpu_memory_bytes is not None
    ]
    return {
        "schema_version": RESOURCE_MEASUREMENT_SCHEMA_VERSION,
        "valid": not errors and energy_joules is not None,
        "duration_seconds": duration,
        "sample_target_hz": sample_target_hz,
        "sample_count": len(samples),
        "observed_sample_hz": observed_hz,
        "gpu": identity,
        "energy": {
            "scope": "nvidia_gpu_board_only",
            "method": energy_method,
            "joules": energy_joules,
            "counter_start_millijoules": total_energy_start_millijoules,
            "counter_end_millijoules": total_energy_end_millijoules,
            "diagnostic_power_integral_joules": integrated_joules,
            "counter_vs_integral_relative_difference": (
                _relative_difference(energy_joules, integrated_joules)
                if energy_method == "nvml_total_energy_counter"
                and energy_joules is not None
                and integrated_joules is not None
                else None
            ),
        },
        "process_ram": _summary(
            [sample.process_rss_bytes for sample in samples]
        ),
        "board_vram": _summary(
            [sample.board_memory_used_bytes for sample in samples]
        ),
        "process_vram": (
            _summary(process_gpu_values) if process_gpu_values else None
        ),
        "power_milliwatts": _summary(
            [sample.power_milliwatts for sample in samples]
        ),
        "gpu_utilization_percent": _summary(
            [sample.gpu_utilization_percent for sample in samples]
        ),
        "temperature_celsius": _summary(
            [sample.temperature_celsius for sample in samples]
        ),
        "compute_process_ids_observed": sorted(
            {
                process_id
                for sample in samples
                if sample.compute_process_ids is not None
                for process_id in sample.compute_process_ids
            }
        ),
        "samples": [sample.to_dict() for sample in samples],
        "errors": list(errors),
        "claim_limit": "not_total_workstation_simulator_network_or_uav_energy",
    }


def integrate_power_samples(samples: list[ResourceSample]) -> float | None:
    """Integrate milliwatt samples over monotonic time using trapezoids."""

    if len(samples) < 2:
        return None
    joules = 0.0
    for left, right in zip(samples, samples[1:]):
        delta = right.monotonic_seconds - left.monotonic_seconds
        if delta < 0:
            raise ValueError("sample timestamps must be monotonic")
        average_watts = (
            left.power_milliwatts + right.power_milliwatts
        ) / 2000.0
        joules += average_watts * delta
    return joules


def _summary(values: list[int]) -> dict[str, int] | None:
    if not values:
        return None
    return {
        "start": values[0],
        "end": values[-1],
        "minimum": min(values),
        "maximum": max(values),
    }


def _relative_difference(primary: float, comparison: float) -> float | None:
    denominator = max(abs(primary), abs(comparison))
    return abs(primary - comparison) / denominator if denominator else None


def _decode(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)
