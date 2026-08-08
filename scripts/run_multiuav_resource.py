"""Run one frozen MultiUAV resource condition with hardware controls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_multiuav_accuracy import (  # noqa: E402
    _ARTIFACTS,
    _backend_config,
    _read_object,
    _runtime_metadata,
    _validate_checkout,
    _validate_runtime_audits,
    _write_json,
)
from shepherd_ai.multiuav_checkpoints import (  # noqa: E402
    JsonlCheckpoint,
    create_compact_checkpoint_zip,
)
from shepherd_ai.multiuav_evaluation_data import (  # noqa: E402
    load_accuracy_evaluation_cases,
)
from shepherd_ai.multiuav_experiment import run_case_matrix  # noqa: E402
from shepherd_ai.multiuav_model_cache import verify_cached_snapshot  # noqa: E402
from shepherd_ai.multiuav_resource_controls import (  # noqa: E402
    ProtocolBoundResourceMonitor,
    prepare_resource_condition,
)
from shepherd_ai.multiuav_resource_execution import (  # noqa: E402
    load_bound_resource_config,
    ordered_resource_cases,
    summarize_resource_rows,
    validate_resource_bindings,
    warmup_case_id,
)
from shepherd_ai.multiuav_resource_protocol import sha256_file  # noqa: E402
from shepherd_ai.multiuav_resources import (  # noqa: E402
    NvmlDeviceTelemetry,
    NvmlResourceMonitor,
)
from shepherd_ai.multiuav_runner import run_method_case  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets/multiuav_plat"
    parser.add_argument(
        "--run-configs", type=Path, default=metadata / "resource_run_configs_v1.json"
    )
    parser.add_argument(
        "--schedule", type=Path, default=metadata / "resource_schedule_v1.json"
    )
    parser.add_argument(
        "--hardware-protocol",
        type=Path,
        default=metadata / "resource_hardware_protocol_v1.json",
    )
    parser.add_argument(
        "--dataset", type=Path, default=metadata / "intervention_dataset_v1.json"
    )
    parser.add_argument(
        "--manifest", type=Path, default=metadata / "accuracy_case_manifest_v1.json"
    )
    parser.add_argument("--repetition", type=int, required=True)
    parser.add_argument("--condition-order", type=int, required=True)
    parser.add_argument("--cache-audit", type=Path)
    parser.add_argument("--smoke-audit", type=Path)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--checkpoint-zip", type=Path, required=True)
    parser.add_argument("--run-summary", type=Path, required=True)
    parser.add_argument("--start-control-dir", type=Path, required=True)
    parser.add_argument("--hardware-lock", type=Path, required=True)
    parser.add_argument("--node-name", default=os.environ.get("SHEPHERD_NODE_NAME", ""))
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--progress-every-rows", type=int, default=5)
    parser.add_argument("--compact-every-rows", type=int, default=25)
    args = parser.parse_args()

    configs = _read_object(args.run_configs)
    schedule = _read_object(args.schedule)
    hardware = _read_object(args.hardware_protocol)
    dataset = _read_object(args.dataset)
    manifest = _read_object(args.manifest)
    config = load_bound_resource_config(
        configs,
        repetition=args.repetition,
        condition_order=args.condition_order,
    )
    validate_resource_bindings(
        config_artifact=configs,
        config=config,
        schedule=schedule,
        hardware_protocol=hardware,
        accuracy_manifest=manifest,
        schedule_path=args.schedule,
        hardware_protocol_path=args.hardware_protocol,
        accuracy_manifest_path=args.manifest,
        intervention_dataset_path=args.dataset,
    )
    _validate_checkout(config.code_commit)
    _validate_packages(hardware)
    runtime = _runtime_metadata()
    _validate_runtime_gpu(runtime, hardware)
    all_cases = load_accuracy_evaluation_cases(dataset, manifest)
    cases = ordered_resource_cases(
        all_cases, schedule=schedule, repetition=args.repetition
    )
    warmup_id = warmup_case_id(schedule, repetition=args.repetition)
    warmup_case = next(case for case in cases if case.case_id == warmup_id)

    registered = _ARTIFACTS[config.model_id]
    cache_path = args.cache_audit or metadata / registered["cache"]
    smoke_path = args.smoke_audit or metadata / registered["smoke"]
    cache_audit = _read_object(cache_path)
    smoke_audit = _read_object(smoke_path)
    _validate_runtime_audits(config, cache_audit, smoke_audit)
    cache_verification = verify_cached_snapshot(cache_audit)
    backend_config = _backend_config(config, smoke_audit)
    _validate_backend(backend_config.to_dict(), hardware)
    protocol_hash = sha256_file(args.hardware_protocol)
    schedule_hash = sha256_file(args.schedule)
    segment_id = (
        f"{os.environ.get('SHEPHERD_POD_UID', 'local')}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    preflight = {
        "schema_version": 1,
        "status": (
            "resource_preflight_passed_no_model_loaded"
            if args.preflight_only
            else "resource_preflight_passed_model_run_pending"
        ),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "method_id": config.methods[0],
        "repetition": config.resource_repetition,
        "condition_order": config.resource_condition_order,
        "config_hash": config.config_hash,
        "code_commit": config.code_commit,
        "approved_cases": len(cases),
        "expected_rows": len(cases),
        "hardware_protocol_sha256": protocol_hash,
        "resource_schedule_sha256": schedule_hash,
        "cache_audit_sha256": sha256_file(cache_path),
        "smoke_audit_sha256": sha256_file(smoke_path),
        "cache_verification": cache_verification,
        "backend_config": backend_config.to_dict(),
        "runtime": runtime,
        "node_name": args.node_name,
        "segment_id": segment_id,
        "model_loaded": False,
        "measurement_started": False,
        "raw_model_outputs_inspected": False,
        "hidden_labels_inspected": False,
    }
    _write_json(args.run_summary, preflight)
    if args.preflight_only:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    try:
        from shepherd_ai.multiuav_qwen_backend import LocalQwenBackend

        backend = LocalQwenBackend.from_cached(backend_config)
        loaded = {
            **preflight,
            "status": "resource_model_loaded_start_control_pending",
            "model_loaded": True,
        }
        _write_json(args.run_summary, loaded)
        start_control = prepare_resource_condition(
            telemetry=NvmlDeviceTelemetry(),
            protocol=hardware,
            protocol_sha256=protocol_hash,
            hardware_lock_path=args.hardware_lock,
            node_name=args.node_name,
            warmup_operation=lambda: run_method_case(
                case_id=warmup_case.case_id,
                case_status=warmup_case.case_status,
                method_id=config.methods[0],
                context=warmup_case.context,
                backend=backend,
            ),
        )
        args.start_control_dir.mkdir(parents=True, exist_ok=True)
        start_path = args.start_control_dir / f"{segment_id}.json"
        _write_json(start_path, start_control)
        checkpoint = JsonlCheckpoint(args.results, config)

        def monitor_factory():
            return ProtocolBoundResourceMonitor(
                monitor=NvmlResourceMonitor(
                    sample_hz=float(hardware["measurement"]["sample_target_hz"])
                ),
                protocol=hardware,
                protocol_sha256=protocol_hash,
                expected_identity=start_control["gpu"],
                start_control_sha256=start_control["sha256"],
                segment_id=segment_id,
            )

        def progress(value: Mapping[str, Any]) -> None:
            if int(value["completed_rows"]) % args.progress_every_rows == 0:
                print(
                    json.dumps(
                        {"status": "resource_condition_progress", **dict(value)},
                        sort_keys=True,
                    ),
                    flush=True,
                )

        matrix = run_case_matrix(
            config=config,
            cases=cases,
            backend=backend,
            checkpoint=checkpoint,
            compact_zip_path=args.checkpoint_zip,
            compact_every_rows=args.compact_every_rows,
            resource_monitor_factory=monitor_factory,
            progress_callback=progress,
        )
        row_summary = summarize_resource_rows(
            checkpoint.load_rows(),
            config=config,
            start_control_dir=args.start_control_dir,
        )
        summary = {
            **preflight,
            "status": (
                "complete_valid_resource_condition"
                if row_summary["valid"]
                else "complete_invalid_resource_condition_preserved"
            ),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_loaded": True,
            "measurement_started": True,
            "start_control_path": start_path.as_posix(),
            "start_control_sha256": start_control["sha256"],
            "matrix": matrix,
            "condition_validation": row_summary,
            "results_sha256": sha256_file(args.results),
            "checkpoint_zip_sha256": sha256_file(args.checkpoint_zip),
        }
        _write_json(args.run_summary, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        if not row_summary["valid"]:
            raise RuntimeError("resource condition contains invalid measurements")
    except BaseException as error:
        if args.results.exists():
            try:
                create_compact_checkpoint_zip(
                    JsonlCheckpoint(args.results, config), args.checkpoint_zip
                )
            except Exception:
                pass
        existing = _read_object(args.run_summary)
        if existing.get("status") != "complete_invalid_resource_condition_preserved":
            results = _artifact_metadata(args.results, include_line_count=True)
            checkpoint_zip = _artifact_metadata(args.checkpoint_zip)
            failure = {
                **preflight,
                "status": "resource_condition_failed_raw_rows_preserved",
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "model_loaded": existing.get("model_loaded", False),
                "measurement_started": args.results.exists(),
                "results": results,
                "checkpoint_zip": checkpoint_zip,
            }
            _write_json(args.run_summary, failure)
        raise


def _validate_packages(protocol: Mapping[str, Any]) -> None:
    expected = protocol["runtime_packages"]
    if not platform.python_version().startswith(str(expected["python"]) + "."):
        raise ValueError("Python version differs from the resource protocol")
    package_names = {
        "torch": "torch",
        "transformers": "transformers",
        "accelerate": "accelerate",
        "huggingface-hub": "huggingface-hub",
        "safetensors": "safetensors",
        "nvidia-ml-py": "nvidia-ml-py",
        "psutil": "psutil",
    }
    for key, package in package_names.items():
        try:
            observed = version(package)
        except PackageNotFoundError as error:
            raise ValueError(f"resource package is not installed: {package}") from error
        if observed != expected[key]:
            raise ValueError(f"resource package version differs: {package}")


def _validate_runtime_gpu(runtime: Mapping[str, Any], protocol: Mapping[str, Any]) -> None:
    gpus = runtime.get("gpus")
    hardware = protocol["hardware"]
    if not runtime.get("cuda_available") or not isinstance(gpus, list) or len(gpus) != 1:
        raise ValueError("resource execution requires exactly one CUDA GPU")
    if gpus[0].get("name") != hardware["required_runtime_gpu_name"]:
        raise ValueError("resource execution is not on the frozen GPU product")
    if int(gpus[0].get("total_memory_bytes", 0)) < int(
        hardware["minimum_total_memory_bytes"]
    ):
        raise ValueError("resource GPU memory is below the frozen minimum")
    if runtime.get("cuda_runtime") != hardware["cuda_runtime"]:
        raise ValueError("CUDA runtime differs from the resource protocol")


def _validate_backend(backend: Mapping[str, Any], protocol: Mapping[str, Any]) -> None:
    frozen = protocol["backend"]
    for key in (
        "dtype",
        "device_map",
        "offload_folder",
        "local_files_only",
        "do_sample",
        "num_beams",
        "max_new_tokens",
    ):
        if backend.get(key) != frozen.get(key):
            raise ValueError(f"resource backend differs from protocol: {key}")


def _artifact_metadata(path: Path, *, include_line_count: bool = False) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "path": path.as_posix()}
    metadata: dict[str, Any] = {
        "present": True,
        "path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if include_line_count:
        metadata["durable_line_count"] = sum(
            1 for line in path.read_text(encoding="utf-8").splitlines() if line
        )
    return metadata


if __name__ == "__main__":
    main()
