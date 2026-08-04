import time
import unittest

from shepherd_ai.multiuav_resources import (
    NvmlResourceMonitor,
    ResourceSample,
    integrate_power_samples,
)


class _FakeTelemetry:
    def __init__(self, counters=None) -> None:
        self.counters = list(counters or [None, None])
        self.sample_calls = 0
        self.closed = False

    def identity(self):
        return {
            "gpu_index": 0,
            "name": "synthetic-gpu",
            "uuid": "GPU-synthetic",
            "driver_version": "synthetic-driver",
        }

    def sample(self):
        self.sample_calls += 1
        return {
            "power_milliwatts": 10_000,
            "board_memory_used_bytes": 2_000,
            "gpu_utilization_percent": 25,
            "temperature_celsius": 40,
            "process_gpu_memory_bytes": 1_000,
        }

    def total_energy_millijoules(self):
        return self.counters.pop(0)

    def close(self):
        self.closed = True


def _sample(timestamp: float, power_mw: int) -> ResourceSample:
    return ResourceSample(
        monotonic_seconds=timestamp,
        power_milliwatts=power_mw,
        board_memory_used_bytes=2_000,
        gpu_utilization_percent=25,
        temperature_celsius=40,
        process_gpu_memory_bytes=1_000,
        process_rss_bytes=3_000,
    )


class MultiUavResourceTests(unittest.TestCase):
    def test_power_integration_uses_trapezoids_and_monotonic_seconds(self) -> None:
        energy = integrate_power_samples(
            [_sample(1.0, 10_000), _sample(1.5, 20_000)]
        )

        self.assertEqual(energy, 7.5)

    def test_monitor_falls_back_to_power_integration(self) -> None:
        telemetry = _FakeTelemetry()
        monitor = NvmlResourceMonitor(
            sample_hz=100,
            telemetry=telemetry,
            process_rss_reader=lambda: 3_000,
        )

        value, report = monitor.measure(lambda: (time.sleep(0.04), "done")[1])

        self.assertEqual(value, "done")
        self.assertTrue(report["valid"])
        self.assertGreaterEqual(report["sample_count"], 3)
        self.assertEqual(
            report["energy"]["method"],
            "nvml_power_trapezoidal_integration",
        )
        self.assertGreater(report["energy"]["joules"], 0)
        self.assertEqual(report["process_ram"]["maximum"], 3_000)
        self.assertTrue(telemetry.closed)

    def test_total_energy_counter_is_preferred_when_supported(self) -> None:
        telemetry = _FakeTelemetry(counters=[1_000, 1_600])
        monitor = NvmlResourceMonitor(
            sample_hz=100,
            telemetry=telemetry,
            process_rss_reader=lambda: 3_000,
        )

        _, report = monitor.measure(lambda: time.sleep(0.02))

        self.assertEqual(report["energy"]["method"], "nvml_total_energy_counter")
        self.assertEqual(report["energy"]["joules"], 0.6)
        self.assertIsNotNone(
            report["energy"]["diagnostic_power_integral_joules"]
        )
        self.assertIsNotNone(
            report["energy"]["counter_vs_integral_relative_difference"]
        )


if __name__ == "__main__":
    unittest.main()
