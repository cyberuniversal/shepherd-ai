"""Case-matrix orchestration over the config-bound checkpoint writer."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, TypeVar

from shepherd_ai.multiuav_checkpoints import (
    JsonlCheckpoint,
    RunConfig,
    create_compact_checkpoint_zip,
    expected_result_keys,
    result_key,
)
from shepherd_ai.multiuav_runner import ModelBackend, run_method_case


T = TypeVar("T")


class ResourceMonitor(Protocol):
    def measure(self, operation: Callable[[], T]) -> tuple[T, dict[str, Any]]:
        """Measure one complete method-case operation."""


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    case_status: str
    context: Mapping[str, Any]


def run_case_matrix(
    *,
    config: RunConfig,
    cases: tuple[EvaluationCase, ...],
    backend: ModelBackend,
    checkpoint: JsonlCheckpoint,
    compact_zip_path: Path | None = None,
    compact_every_rows: int = 250,
    resource_monitor_factory: Callable[[], ResourceMonitor] | None = None,
) -> dict[str, Any]:
    """Run missing case-method rows and durably checkpoint each result."""

    if checkpoint.config != config:
        raise ValueError("checkpoint and matrix configs differ")
    if not cases:
        raise ValueError("case matrix must be non-empty")
    if compact_every_rows < 1:
        raise ValueError("compact_every_rows must be positive")
    if config.run_kind == "resource" and resource_monitor_factory is None:
        raise ValueError("resource runs require a resource monitor factory")
    if config.run_kind != "resource" and resource_monitor_factory is not None:
        raise ValueError("resource monitor is only valid for resource runs")
    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("case ids must be unique")
    expected = expected_result_keys(case_ids, config.methods)
    checkpoint.initialize()
    completed = checkpoint.completed_keys()
    appended = 0
    skipped = 0
    for case in cases:
        for method_id in config.methods:
            key = result_key(case.case_id, method_id)
            if key in completed:
                skipped += 1
                continue
            def operation():
                return run_method_case(
                    case_id=case.case_id,
                    case_status=case.case_status,
                    method_id=method_id,
                    context=case.context,
                    backend=backend,
                )

            if resource_monitor_factory is not None:
                result, measurement = resource_monitor_factory().measure(operation)
                result = replace(result, resource_measurement=measurement)
            else:
                result = operation()
            checkpoint.append(result)
            completed.add(key)
            appended += 1
            if (
                compact_zip_path is not None
                and appended % compact_every_rows == 0
            ):
                create_compact_checkpoint_zip(checkpoint, compact_zip_path)
    checkpoint.assert_complete(expected)
    archive = (
        create_compact_checkpoint_zip(checkpoint, compact_zip_path)
        if compact_zip_path is not None
        else None
    )
    return {
        "config_hash": config.config_hash,
        "expected_rows": len(expected),
        "appended_rows": appended,
        "resumed_rows": skipped,
        "complete": True,
        "checkpoint_path": checkpoint.results_path.as_posix(),
        "compact_archive": archive,
        "model_inference_backend": type(backend).__name__,
        "resource_measurement_enabled": resource_monitor_factory is not None,
    }
