"""Import a packaged Hugging Face checkpoint zip into outputs/model_artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import zipfile


REQUIRED_MODEL_FILES = ("config.json",)
WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")
TOKENIZER_FILES = ("tokenizer.json", "vocab.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-zip", required=True, help="Packaged checkpoint zip downloaded from Colab.")
    parser.add_argument(
        "--output-dir",
        default="outputs/model_artifacts",
        help="Directory where the checkpoint folder should be installed.",
    )
    parser.add_argument(
        "--expected-name",
        default="hf_token_classifier_distilbert_colab_t4_expanded85",
        help="Expected top-level checkpoint folder name inside the zip.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing installed checkpoint folder.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = import_checkpoint(
            checkpoint_zip=Path(args.checkpoint_zip),
            output_dir=Path(args.output_dir),
            expected_name=args.expected_name,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


def import_checkpoint(
    *,
    checkpoint_zip: Path,
    output_dir: Path,
    expected_name: str,
    overwrite: bool = False,
) -> dict:
    """Validate and extract a packaged checkpoint zip."""

    checkpoint_zip = checkpoint_zip.resolve()
    output_dir = output_dir.resolve()
    if not checkpoint_zip.is_file():
        raise FileNotFoundError(f"checkpoint zip does not exist: {checkpoint_zip}")

    try:
        archive = zipfile.ZipFile(checkpoint_zip)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"checkpoint artifact is not a zip file: {checkpoint_zip}") from exc

    with archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        checkpoint_root = _find_checkpoint_root(names, expected_name=expected_name)
        _validate_archive_members(names, checkpoint_root)
        destination = output_dir / checkpoint_root
        if destination.exists():
            if not overwrite:
                raise FileExistsError(f"checkpoint already exists: {destination}")
            shutil.rmtree(destination)
        output_dir.mkdir(parents=True, exist_ok=True)
        _extract_checkpoint_members(archive, names, checkpoint_root, output_dir)

    installed_files = sorted(path for path in destination.rglob("*") if path.is_file())
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_zip": str(checkpoint_zip),
        "installed_dir": str(destination),
        "files": [
            {
                "path": path.relative_to(destination.parent).as_posix(),
                "size_bytes": path.stat().st_size,
            }
            for path in installed_files
        ],
        "note": "Imported generated checkpoint artifact. Do not commit model weights to git.",
    }
    (destination / "local_import_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest["files"].append(
        {
            "path": f"{destination.name}/local_import_manifest.json",
            "size_bytes": (destination / "local_import_manifest.json").stat().st_size,
        }
    )
    return manifest


def _find_checkpoint_root(names: list[str], *, expected_name: str) -> str:
    candidate_prefix = f"{expected_name}/"
    if any(name.startswith(candidate_prefix) for name in names):
        return expected_name
    roots = sorted({name.split("/", 1)[0] for name in names if "/" in name})
    valid_roots = [root for root in roots if _root_has_checkpoint_files(names, root)]
    if len(valid_roots) == 1:
        return valid_roots[0]
    raise ValueError(
        "could not find a single valid checkpoint folder in archive; "
        f"expected {expected_name!r}, valid roots: {valid_roots!r}"
    )


def _root_has_checkpoint_files(names: list[str], root: str) -> bool:
    root_files = {name.split("/", 1)[1] for name in names if name.startswith(f"{root}/") and "/" in name}
    return (
        all(file_name in root_files for file_name in REQUIRED_MODEL_FILES)
        and any(file_name in root_files for file_name in WEIGHT_FILES)
        and any(file_name in root_files for file_name in TOKENIZER_FILES)
    )


def _validate_archive_members(names: list[str], checkpoint_root: str) -> None:
    root_files = {name.split("/", 1)[1] for name in names if name.startswith(f"{checkpoint_root}/")}
    for file_name in REQUIRED_MODEL_FILES:
        if file_name not in root_files:
            raise FileNotFoundError(f"required checkpoint file is missing from zip: {checkpoint_root}/{file_name}")
    if not any(file_name in root_files for file_name in WEIGHT_FILES):
        raise FileNotFoundError(f"checkpoint zip has no supported weight file: one of {WEIGHT_FILES}")
    if not any(file_name in root_files for file_name in TOKENIZER_FILES):
        raise FileNotFoundError(f"checkpoint zip has no tokenizer file: one of {TOKENIZER_FILES}")


def _extract_checkpoint_members(
    archive: zipfile.ZipFile,
    names: list[str],
    checkpoint_root: str,
    output_dir: Path,
) -> None:
    root_prefix = f"{checkpoint_root}/"
    for name in names:
        if not name.startswith(root_prefix):
            continue
        target = (output_dir / name).resolve()
        if not _is_relative_to(target, output_dir):
            raise ValueError(f"unsafe archive path: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as source, target.open("wb") as sink:
            shutil.copyfileobj(source, sink)


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    main()
