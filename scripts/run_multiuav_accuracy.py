"""Run one commit-bound MultiUAV accuracy matrix with durable checkpoints."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_checkpoints import (  # noqa: E402
    JsonlCheckpoint,
    RunConfig,
)
from shepherd_ai.multiuav_evaluation_data import (  # noqa: E402
    load_accuracy_evaluation_cases,
)
from shepherd_ai.multiuav_experiment import run_case_matrix  # noqa: E402
from shepherd_ai.multiuav_model_cache import (  # noqa: E402
    verify_cached_snapshot,
)
from shepherd_ai.multiuav_qwen_backend import (  # noqa: E402
    LocalQwenBackend,
    QwenBackendConfig,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


_ARTIFACTS = {
    "Qwen/Qwen2.5-3B-Instruct": {
        "cache": "qwen25_3b_cache_audit_v1.json",
        "smoke": "qwen25_3b_load_smoke_v1.json",
    },
    "Qwen/Qwen2.5-7B-Instruct": {
        "cache": "qwen25_7b_cache_audit_v1.json",
        "smoke": "qwen25_7b_load_smoke_v1.json",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets" / "multiuav_plat"
    parser.add_argument(
        "--run-configs",
        type=Path,
        default=metadata / "accuracy_run_configs_v1.json",
    )
    parser.add_argument(
        "--model-id",
        required=True,
        choices=sorted(_ARTIFACTS),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=metadata / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=metadata / "accuracy_case_manifest_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=metadata / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument("--cache-audit", type=Path)
    parser.add_argument("--smoke-audit", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--checkpoint-zip", type=Path)
    parser.add_argument("--run-summary", type=Path)
    parser.add_argument("--compact-every-rows", type=int, default=250)
    parser.add_argument("--progress-every-rows", type=int, default=10)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    run_configs = _read_object(args.run_configs)
    config = load_bound_run_config(run_configs, args.model_id)
    dataset = _read_object(args.dataset)
    manifest = _read_object(args.manifest)
    protocol = _read_object(args.protocol)
    validate_bound_inputs(
        artifact=run_configs,
        config=config,
        manifest_path=args.manifest,
        protocol_path=args.protocol,
        manifest=manifest,
        protocol=protocol,
    )
    _validate_checkout(config.code_commit)
    cases = load_accuracy_evaluation_cases(dataset, manifest)
    if len(cases) != 1_420:
        raise ValueError("accuracy run requires exactly 1,420 approved cases")
    if args.progress_every_rows < 1:
        raise ValueError("progress-every-rows must be positive")

    registered = _ARTIFACTS[args.model_id]
    cache_audit_path = args.cache_audit or metadata / registered["cache"]
    smoke_audit_path = args.smoke_audit or metadata / registered["smoke"]
    cache_audit = _read_object(cache_audit_path)
    smoke_audit = _read_object(smoke_audit_path)
    _validate_runtime_audits(config, cache_audit, smoke_audit)
    cache_verification = verify_cached_snapshot(cache_audit)
    backend_config = _backend_config(config, smoke_audit)

    slug = config.model_id.rsplit("/", 1)[-1]
    result_root = ROOT / "outputs" / "multiuav" / "accuracy" / slug
    results_path = args.results or result_root / "results.jsonl"
    checkpoint_zip = args.checkpoint_zip or result_root / "checkpoint.zip"
    summary_path = args.run_summary or result_root / "run_summary.json"
    preflight = {
        "schema_version": 1,
        "status": (
            "preflight_passed_no_model_loaded"
            if args.preflight_only
            else "preflight_passed_model_run_pending"
        ),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "code_commit": config.code_commit,
        "config_hash": config.config_hash,
        "approved_cases": len(cases),
        "methods": list(config.methods),
        "expected_rows": len(cases) * len(config.methods),
        "cache_audit_sha256": sha256_file(cache_audit_path),
        "smoke_audit_sha256": sha256_file(smoke_audit_path),
        "cache_verification": cache_verification,
        "backend_config": backend_config.to_dict(),
        "runtime": _runtime_metadata(),
        "model_loaded": False,
        "study_inference_started": False,
    }
    if args.preflight_only:
        _write_json(summary_path, preflight)
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    backend = LocalQwenBackend.from_cached(backend_config)
    checkpoint = JsonlCheckpoint(results_path, config)

    def report_progress(progress: Mapping[str, Any]) -> None:
        completed = int(progress["completed_rows"])
        expected = int(progress["expected_rows"])
        if completed % args.progress_every_rows == 0 or completed == expected:
            print(
                json.dumps(
                    {
                        "status": "accuracy_matrix_progress",
                        **dict(progress),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    matrix = run_case_matrix(
        config=config,
        cases=cases,
        backend=backend,
        checkpoint=checkpoint,
        compact_zip_path=checkpoint_zip,
        compact_every_rows=args.compact_every_rows,
        progress_callback=report_progress,
    )
    summary = {
        **preflight,
        "status": "complete_accuracy_matrix_raw_results_unscored",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_loaded": True,
        "study_inference_started": True,
        "matrix": matrix,
        "results_sha256": sha256_file(results_path),
        "checkpoint_zip_sha256": sha256_file(checkpoint_zip),
        "scores_inspected": False,
    }
    _write_json(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


def load_bound_run_config(
    artifact: Mapping[str, Any],
    model_id: str,
) -> RunConfig:
    """Select and validate one model config from the final config artifact."""

    if artifact.get("status") != "final_accuracy_configs_bound_no_inference_started":
        raise ValueError("accuracy run configs are not final and inference-safe")
    records = artifact.get("configs")
    if not isinstance(records, list):
        raise ValueError("accuracy run config artifact requires config records")
    matches = [
        record
        for record in records
        if isinstance(record, Mapping)
        and isinstance(record.get("config"), Mapping)
        and record["config"].get("model_id") == model_id
    ]
    if len(matches) != 1:
        raise ValueError("accuracy run config must contain the model exactly once")
    record = matches[0]
    payload = dict(record["config"])
    payload["methods"] = tuple(payload["methods"])
    config = RunConfig(**payload)
    if config.to_dict() != dict(record):
        raise ValueError("stored run config hash or payload is invalid")
    if artifact.get("code_commit") != config.code_commit:
        raise ValueError("run config artifact and model config commits differ")
    return config


def validate_bound_inputs(
    *,
    artifact: Mapping[str, Any],
    config: RunConfig,
    manifest_path: Path,
    protocol_path: Path,
    manifest: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> None:
    """Reject any data, protocol, count, or decoding drift before model loading."""

    manifest_hash = sha256_file(manifest_path)
    protocol_hash = sha256_file(protocol_path)
    if artifact.get("accuracy_manifest_sha256") != manifest_hash:
        raise ValueError("run configs are not bound to the accuracy manifest")
    if artifact.get("protocol_freeze_sha256") != protocol_hash:
        raise ValueError("run configs are not bound to the protocol freeze")
    if config.dataset_sha256 != manifest_hash:
        raise ValueError("model config is not bound to the accuracy manifest")
    if manifest.get("case_count") != 1_420:
        raise ValueError("accuracy manifest case count differs from protocol")
    if protocol.get("expected_accuracy_rows") != 11_360:
        raise ValueError("accuracy protocol row count differs from registration")
    if artifact.get("expected_rows_per_model") != 5_680:
        raise ValueError("accuracy run config has the wrong per-model row count")
    if artifact.get("expected_rows_total") != 11_360:
        raise ValueError("accuracy run config has the wrong total row count")
    if dict(config.decoding) != dict(protocol.get("decoding", {})):
        raise ValueError("model decoding differs from the frozen protocol")


def _validate_runtime_audits(
    config: RunConfig,
    cache_audit: Mapping[str, Any],
    smoke_audit: Mapping[str, Any],
) -> None:
    if cache_audit.get("model_id") != config.model_id:
        raise ValueError("cache audit model id differs from run config")
    if cache_audit.get("revision") != config.model_revision:
        raise ValueError("cache audit revision differs from run config")
    backend = smoke_audit.get("backend_config")
    if not isinstance(backend, Mapping):
        raise ValueError("registered smoke backend config is absent")
    if backend.get("model_id") != config.model_id:
        raise ValueError("smoke audit model id differs from run config")
    if backend.get("revision") != config.model_revision:
        raise ValueError("smoke audit revision differs from run config")
    if smoke_audit.get("smoke_status") != "passed":
        raise ValueError("registered model load smoke did not pass")
    if smoke_audit.get("weights_loaded") is not True:
        raise ValueError("registered model smoke did not load weights")
    if smoke_audit.get("model_invoked") is not True:
        raise ValueError("registered model smoke did not invoke the model")
    if smoke_audit.get("study_cases_evaluated") is not False:
        raise ValueError("registered model smoke used study cases")
    if backend.get("do_sample") is not False or backend.get("num_beams") != 1:
        raise ValueError("registered smoke was not deterministic")


def _backend_config(
    config: RunConfig,
    smoke_audit: Mapping[str, Any],
) -> QwenBackendConfig:
    backend = smoke_audit["backend_config"]
    return QwenBackendConfig(
        model_id=config.model_id,
        revision=config.model_revision,
        max_new_tokens=int(config.decoding["max_new_tokens"]),
        dtype=str(backend["dtype"]),
        cache_dir=backend.get("cache_dir"),
        snapshot_dir=backend.get("snapshot_dir"),
        offload_folder=backend.get("offload_folder"),
        device_map=str(backend["device_map"]),
    )


def _runtime_metadata(torch_module: Any | None = None) -> dict[str, Any]:
    torch = torch_module or importlib.import_module("torch")
    cuda_available = bool(torch.cuda.is_available())
    gpus = []
    if cuda_available:
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            gpus.append(
                {
                    "index": index,
                    "name": properties.name,
                    "total_memory_bytes": properties.total_memory,
                }
            )
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu": platform.processor() or "not stated",
        "package_versions": {
            name: _package_version(name)
            for name in (
                "accelerate",
                "huggingface-hub",
                "safetensors",
                "torch",
                "transformers",
            )
        },
        "cuda_available": cuda_available,
        "cuda_runtime": torch.version.cuda,
        "gpus": gpus,
    }


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def _validate_checkout(code_commit: str) -> None:
    head = _git("rev-parse", "HEAD").strip().lower()
    if head != code_commit:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", code_commit, head],
            cwd=ROOT,
            check=False,
        )
        if ancestor.returncode != 0:
            raise ValueError("bound code commit is not an ancestor of HEAD")
        changed = _git("diff", "--name-only", code_commit, "--", "src", "scripts", "pyproject.toml")
        if changed.strip():
            raise ValueError("execution code differs from the bound commit")
    dirty = _git("status", "--porcelain", "--", "src", "scripts", "pyproject.toml")
    if dirty.strip():
        raise ValueError("execution source has uncommitted changes")


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


if __name__ == "__main__":
    main()
