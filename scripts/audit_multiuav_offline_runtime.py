"""Freeze the local Qwen backend and offline-runtime contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_model_revisions import (  # noqa: E402
    REGISTERED_MODEL_REVISIONS,
)
from shepherd_ai.multiuav_offline_runtime import (  # noqa: E402
    OFFLINE_ENVIRONMENT,
)
from shepherd_ai.multiuav_qwen_backend import (  # noqa: E402
    QwenBackendConfig,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    backend_configs = [
        QwenBackendConfig(
            model_id=item.model_id,
            revision=item.revision,
            max_new_tokens=1024,
            dtype="float16",
        ).to_dict()
        for item in REGISTERED_MODEL_REVISIONS
    ]
    source_names = (
        "multiuav_offline_runtime.py",
        "multiuav_qwen_backend.py",
    )
    result = {
        "schema_version": 1,
        "valid": True,
        "backend_contracts": backend_configs,
        "offline_contract": {
            "local_files_only_required": True,
            "trust_remote_code": False,
            "safetensors_required": True,
            "offline_environment": dict(OFFLINE_ENVIRONMENT),
            "blocked_python_socket_operations": [
                "socket.socket.connect",
                "socket.socket.connect_ex",
                "socket.create_connection",
                "socket.getaddrinfo",
            ],
            "loopback_allowed": True,
            "non_loopback_blocked": True,
            "guard_applies_during_model_loading": True,
            "guard_applies_during_generation": True,
            "isolation_scope": "python_process",
        },
        "decoding_contract": {
            "do_sample": False,
            "num_beams": 1,
            "chat_template_add_generation_prompt": True,
            "raw_generated_text_retained_by_runner": True,
        },
        "generation_metadata_contract": [
            "model_id",
            "model_revision",
            "dtype",
            "device",
            "device_map",
            "cache_dir",
            "snapshot_dir",
            "offload_folder",
            "input_tokens",
            "output_tokens",
            "latency_ms",
            "transformers_version",
            "torch_version",
            "non_loopback_sockets_blocked",
            "offline_environment",
        ],
        "source_code_sha256": {
            **{
                name: sha256_file(ROOT / "src" / "shepherd_ai" / name)
                for name in source_names
            },
            "audit_multiuav_offline_runtime.py": sha256_file(
                ROOT / "scripts" / "audit_multiuav_offline_runtime.py"
            ),
        },
        "weights_cached": False,
        "weights_loaded": False,
        "model_invoked": False,
        "study_cases_evaluated": False,
        "claim_status": (
            "local_qwen_backend_and_process_socket_isolation_implemented_"
            "synthetic_tests_only"
        ),
        "limitations": [
            (
                "No Qwen weights were cached, loaded, or invoked while creating "
                "this contract artifact."
            ),
            (
                "Python socket patching is process-level isolation, not an "
                "operating-system firewall, container boundary, or proof that "
                "native extensions cannot perform network I/O."
            ),
            (
                "Deterministic greedy decoding does not establish model "
                "correctness or bitwise equality across hardware and package stacks."
            ),
            (
                "The unreviewed intervention pilot remains blocked from every "
                "model backend."
            ),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
