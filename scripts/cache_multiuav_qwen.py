"""Cache a pinned Qwen snapshot outside Git and store file checksums."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_model_cache import (  # noqa: E402
    cache_registered_snapshot,
)
from shepherd_ai.multiuav_model_revisions import (  # noqa: E402
    REGISTERED_MODEL_REVISIONS,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


DEFAULT_MODEL = REGISTERED_MODEL_REVISIONS[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=DEFAULT_MODEL.model_id)
    parser.add_argument("--revision", default=DEFAULT_MODEL.revision)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    cache_dir = args.cache_dir.expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    free_before = shutil.disk_usage(cache_dir).free
    started = datetime.now(timezone.utc)
    inventory = cache_registered_snapshot(
        model_id=args.model_id,
        revision=args.revision,
        cache_dir=cache_dir,
        repository_root=ROOT,
        snapshot_download=snapshot_download,
        max_workers=args.max_workers,
    )
    completed = datetime.now(timezone.utc)
    output = {
        "schema_version": 1,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": completed.isoformat(),
        "duration_seconds": (completed - started).total_seconds(),
        **inventory,
        "free_bytes_before": free_before,
        "free_bytes_after": shutil.disk_usage(cache_dir).free,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "package_versions": {
            name: _package_version(name)
            for name in ("huggingface-hub", "safetensors", "transformers", "torch")
        },
        "source_code_sha256": {
            "multiuav_model_cache.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_model_cache.py"
            ),
            "cache_multiuav_qwen.py": sha256_file(
                ROOT / "scripts" / "cache_multiuav_qwen.py"
            ),
        },
        "weights_cached": True,
        "weights_loaded": False,
        "model_invoked": False,
        "study_cases_evaluated": False,
        "claim_status": "pinned_qwen_cache_verified_no_model_inference",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: output[key]
                for key in (
                    "model_id",
                    "revision",
                    "file_count",
                    "weight_file_count",
                    "total_bytes",
                    "weight_bytes",
                    "duration_seconds",
                    "claim_status",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


if __name__ == "__main__":
    main()
