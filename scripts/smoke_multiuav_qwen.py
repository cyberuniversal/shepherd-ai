"""Load cached Qwen offline and preserve one synthetic generation smoke."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import socket
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import project_agent_visible_context  # noqa: E402
from shepherd_ai.multiuav_model_cache import (  # noqa: E402
    validate_external_cache_dir,
    verify_cached_snapshot,
)
from shepherd_ai.multiuav_offline_runtime import (  # noqa: E402
    NetworkIsolationError,
    offline_inference_guard,
)
from shepherd_ai.multiuav_prompts import build_first_call_request  # noqa: E402
from shepherd_ai.multiuav_qwen_backend import (  # noqa: E402
    LocalQwenBackend,
    QwenBackendConfig,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--offload-folder", type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    args = parser.parse_args()

    cache_audit = json.loads(args.cache_audit.read_text(encoding="utf-8"))
    cache_verification = verify_cached_snapshot(cache_audit)
    offload_folder = None
    if args.offload_folder is not None:
        offload_path = validate_external_cache_dir(args.offload_folder, ROOT)
        offload_path.mkdir(parents=True, exist_ok=True)
        offload_folder = str(offload_path)
    context = _synthetic_context()
    request = build_first_call_request("M1_monolithic", context)
    config = QwenBackendConfig(
        model_id=str(cache_audit["model_id"]),
        revision=str(cache_audit["revision"]),
        max_new_tokens=args.max_new_tokens,
        dtype=args.dtype,
        cache_dir=str(cache_audit["cache_dir"]),
        snapshot_dir=str(cache_audit["snapshot_dir"]),
        offload_folder=offload_folder,
        device_map=args.device_map,
    )
    network_probe = _network_block_probe()
    started = datetime.now(timezone.utc)
    output: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": started.isoformat(),
        "cache_audit_path": args.cache_audit.as_posix(),
        "cache_audit_sha256": sha256_file(args.cache_audit),
        "cache_verification": cache_verification,
        "backend_config": config.to_dict(),
        "synthetic_fixture": True,
        "study_case": False,
        "request": request.to_dict(),
        "network_block_probe": network_probe,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "weights_cached": True,
        "weights_loaded": False,
        "model_invoked": False,
        "study_cases_evaluated": False,
        "smoke_status": "running",
        "raw_output": None,
        "generation": None,
        "error": None,
        "claim_status": "synthetic_load_smoke_in_progress_not_study_evidence",
    }
    _write(args.output, output)
    try:
        backend = LocalQwenBackend.from_cached(config)
        output["weights_loaded"] = True
        generated = backend.generate(request)
        output["model_invoked"] = True
        output["raw_output"] = generated.raw_output
        output["generation"] = generated.to_dict()
        output["generation_reached_token_limit"] = (
            generated.output_tokens == args.max_new_tokens
        )
        output["output_interpreted_as_plan"] = False
        output["smoke_status"] = "passed"
        output["claim_status"] = (
            "pinned_qwen_loaded_and_invoked_on_synthetic_fixture_"
            "not_study_evidence"
        )
    except Exception as error:
        output["smoke_status"] = "failed"
        output["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
        output["claim_status"] = "synthetic_load_smoke_failed_not_study_evidence"
        raise
    finally:
        completed = datetime.now(timezone.utc)
        output["completed_at_utc"] = completed.isoformat()
        output["duration_seconds"] = (completed - started).total_seconds()
        output["hardware"] = _hardware_metadata()
        output["source_code_sha256"] = {
            "multiuav_model_cache.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_model_cache.py"
            ),
            "multiuav_offline_runtime.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_offline_runtime.py"
            ),
            "multiuav_qwen_backend.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_qwen_backend.py"
            ),
            "smoke_multiuav_qwen.py": sha256_file(
                ROOT / "scripts" / "smoke_multiuav_qwen.py"
            ),
        }
        _write(args.output, output)


def _synthetic_context() -> dict[str, Any]:
    return project_agent_visible_context(
        {
            "id": "synthetic-cache-smoke-session",
            "task_type": "return",
            "canvas_width": 100,
            "canvas_height": 100,
            "is_distance_3d": True,
            "status": "active",
            "drones": [
                {
                    "id": "synthetic-drone-1",
                    "name": "Drone 1",
                    "status": "idle",
                    "position": {"x": 0, "y": 0, "z": 0},
                    "home_position": {"x": 0, "y": 0, "z": 0},
                    "heading": 0,
                    "max_altitude": 50,
                }
            ],
            "environment": {
                "id": "synthetic-environment",
                "name": "Synthetic clear environment",
                "weather": "clear",
            },
        },
        task_id="synthetic-cache-smoke-task",
        instruction="Return Drone 1 to its visible home position.",
    )


def _network_block_probe() -> dict[str, Any]:
    with offline_inference_guard():
        try:
            socket.getaddrinfo("huggingface.co", 443)
        except NetworkIsolationError as error:
            return {
                "attempted_host": "huggingface.co",
                "expected": "blocked",
                "observed": "blocked",
                "error": str(error),
            }
    raise AssertionError("offline guard allowed a non-loopback DNS request")


def _hardware_metadata() -> dict[str, Any]:
    import torch

    cuda_available = torch.cuda.is_available()
    result: dict[str, Any] = {
        "cpu": platform.processor() or "not stated",
        "torch_version": str(torch.__version__),
        "cuda_available": cuda_available,
        "cuda_runtime": str(torch.version.cuda),
        "gpu_count": torch.cuda.device_count() if cuda_available else 0,
        "gpus": [],
    }
    if cuda_available:
        result["gpus"] = [
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "total_memory_bytes": torch.cuda.get_device_properties(
                    index
                ).total_memory,
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(index),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(index),
            }
            for index in range(torch.cuda.device_count())
        ]
    return result


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
