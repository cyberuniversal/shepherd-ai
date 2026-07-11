"""Package a saved Hugging Face checkpoint directory into a zip archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile


REQUIRED_MODEL_FILES = ("config.json",)
WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")
TOKENIZER_FILES = ("tokenizer.json", "vocab.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, help="Saved Hugging Face checkpoint directory.")
    parser.add_argument("--output-zip", required=True, help="Zip file to create.")
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Optional additional file to include, preserving its relative path from the current directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = package_checkpoint(
        model_dir=Path(args.model_dir),
        output_zip=Path(args.output_zip),
        include_paths=[Path(path) for path in args.include],
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


def package_checkpoint(
    *,
    model_dir: Path,
    output_zip: Path,
    include_paths: list[Path] | None = None,
) -> dict:
    """Write a checkpoint zip and return a provenance manifest."""

    model_dir = model_dir.resolve()
    output_zip = output_zip.resolve()
    include_paths = include_paths or []
    _validate_checkpoint(model_dir)

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    model_files = sorted(path for path in model_dir.rglob("*") if path.is_file())
    included_files = [_resolve_existing_file(path) for path in include_paths]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir_name": model_dir.name,
        "model_dir": str(model_dir),
        "output_zip": str(output_zip),
        "model_files": [_file_record(path, model_dir.parent) for path in model_files],
        "included_files": [_file_record(path, Path.cwd()) for path in included_files],
    }

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in model_files:
            archive.write(path, path.relative_to(model_dir.parent).as_posix())
        for path in included_files:
            archive.write(path, path.relative_to(Path.cwd()).as_posix())
        archive.writestr(f"{model_dir.name}/checkpoint_manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    manifest["zip_size_bytes"] = output_zip.stat().st_size
    return manifest


def _validate_checkpoint(model_dir: Path) -> None:
    if not model_dir.is_dir():
        raise FileNotFoundError(f"model directory does not exist: {model_dir}")
    for file_name in REQUIRED_MODEL_FILES:
        if not (model_dir / file_name).is_file():
            raise FileNotFoundError(f"required checkpoint file is missing: {model_dir / file_name}")
    if not any((model_dir / file_name).is_file() for file_name in WEIGHT_FILES):
        raise FileNotFoundError(f"checkpoint has no supported weight file: one of {WEIGHT_FILES}")
    if not any((model_dir / file_name).is_file() for file_name in TOKENIZER_FILES):
        raise FileNotFoundError(f"checkpoint has no tokenizer file: one of {TOKENIZER_FILES}")


def _resolve_existing_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"included file does not exist: {path}")
    return resolved


def _file_record(path: Path, base_dir: Path) -> dict:
    return {
        "path": path.relative_to(base_dir.resolve()).as_posix(),
        "size_bytes": path.stat().st_size,
    }


if __name__ == "__main__":
    main()
