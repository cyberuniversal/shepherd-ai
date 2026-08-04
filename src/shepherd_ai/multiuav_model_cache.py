"""Immutable local-cache acquisition and checksum verification for Qwen."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS


_REGISTERED_REVISIONS = {
    item.model_id: item.revision for item in REGISTERED_MODEL_REVISIONS
}
_PROHIBITED_WEIGHT_SUFFIXES = frozenset({".bin", ".pt", ".pth"})


def cache_registered_snapshot(
    *,
    model_id: str,
    revision: str,
    cache_dir: Path,
    repository_root: Path,
    snapshot_download: Callable[..., str],
    max_workers: int = 4,
) -> dict[str, Any]:
    """Download one pinned snapshot, then return its complete file inventory."""

    _validate_registered_revision(model_id, revision)
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    cache_root = validate_external_cache_dir(cache_dir, repository_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = Path(
        snapshot_download(
            repo_id=model_id,
            revision=revision,
            cache_dir=str(cache_root),
            local_files_only=False,
            max_workers=max_workers,
        )
    )
    return inventory_registered_snapshot(
        model_id=model_id,
        revision=revision,
        cache_dir=cache_root,
        snapshot_dir=snapshot_path,
    )


def inventory_registered_snapshot(
    *,
    model_id: str,
    revision: str,
    cache_dir: Path,
    snapshot_dir: Path,
) -> dict[str, Any]:
    """Hash every file required by a locally cached immutable snapshot."""

    _validate_registered_revision(model_id, revision)
    cache_root = cache_dir.resolve()
    snapshot = snapshot_dir.resolve()
    if not snapshot.is_dir():
        raise FileNotFoundError(f"cached snapshot directory not found: {snapshot}")
    if not snapshot.is_relative_to(cache_root):
        raise ValueError("snapshot directory must stay within cache_dir")
    if snapshot.name != revision:
        raise ValueError("cached snapshot directory does not match pinned revision")

    records: list[dict[str, Any]] = []
    prohibited_weights: list[str] = []
    for path in sorted(snapshot_dir.rglob("*")):
        if not path.is_file():
            continue
        resolved_file = path.resolve()
        if not resolved_file.is_relative_to(cache_root):
            raise ValueError(f"cached file resolves outside cache_dir: {path}")
        relative = path.relative_to(snapshot_dir).as_posix()
        suffix = path.suffix.lower()
        if suffix in _PROHIBITED_WEIGHT_SUFFIXES:
            prohibited_weights.append(relative)
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "is_safetensors_weight": suffix == ".safetensors",
            }
        )
    if not records:
        raise ValueError("cached snapshot contains no files")
    if prohibited_weights:
        raise ValueError(
            "cached snapshot contains prohibited weight formats: "
            + ", ".join(prohibited_weights)
        )
    weight_records = [row for row in records if row["is_safetensors_weight"]]
    if not weight_records:
        raise ValueError("cached snapshot contains no safetensors weights")
    paths = {row["path"] for row in records}
    if "config.json" not in paths:
        raise ValueError("cached snapshot is missing config.json")
    if not ({"tokenizer.json", "tokenizer.model"} & paths):
        raise ValueError("cached snapshot is missing tokenizer data")

    return {
        "model_id": model_id,
        "revision": revision,
        "cache_dir": str(cache_root),
        "snapshot_dir": str(snapshot),
        "file_count": len(records),
        "weight_file_count": len(weight_records),
        "total_bytes": sum(row["bytes"] for row in records),
        "weight_bytes": sum(row["bytes"] for row in weight_records),
        "all_weights_safetensors": True,
        "files": records,
    }


def verify_cached_snapshot(audit: dict[str, Any]) -> dict[str, Any]:
    """Re-hash a stored cache inventory before loading any model weights."""

    inventory = inventory_registered_snapshot(
        model_id=str(audit["model_id"]),
        revision=str(audit["revision"]),
        cache_dir=Path(str(audit["cache_dir"])),
        snapshot_dir=Path(str(audit["snapshot_dir"])),
    )
    expected = {
        str(row["path"]): (int(row["bytes"]), str(row["sha256"]))
        for row in audit["files"]
    }
    observed = {
        str(row["path"]): (int(row["bytes"]), str(row["sha256"]))
        for row in inventory["files"]
    }
    if observed != expected:
        raise ValueError("cached snapshot differs from recorded file inventory")
    return {
        "valid": True,
        "file_count": inventory["file_count"],
        "weight_file_count": inventory["weight_file_count"],
        "total_bytes": inventory["total_bytes"],
        "weight_bytes": inventory["weight_bytes"],
    }


def validate_external_cache_dir(cache_dir: Path, repository_root: Path) -> Path:
    """Keep downloaded model files outside the Git repository."""

    cache_root = cache_dir.expanduser().resolve()
    repository = repository_root.resolve()
    if cache_root == repository or cache_root.is_relative_to(repository):
        raise ValueError("model cache must stay outside the repository")
    return cache_root


def _validate_registered_revision(model_id: str, revision: str) -> None:
    if _REGISTERED_REVISIONS.get(model_id) != revision:
        raise ValueError("model id/revision is absent from the frozen registry")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
