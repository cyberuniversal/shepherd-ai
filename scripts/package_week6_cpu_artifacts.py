"""Package non-image Week 6 CPU audit artifacts with checksums."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


ARTIFACT_PATHS = (
    "datasets/aerial_images/manifest.jsonl",
    "outputs/evaluations/week6_agriculture_vision_cache_provenance.json",
    "outputs/evaluations/week6_agriculture_vision_layout.json",
    "outputs/evaluations/week6_vision_manifest_summary.json",
    "outputs/evaluations/week6_agriculture_vision_label_audit.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-zip", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = package_artifacts(Path(args.repo_root), Path(args.output_zip))
    print(json.dumps(manifest, indent=2, sort_keys=True))


def package_artifacts(repo_root: Path, output_zip: Path) -> dict:
    repo_root = repo_root.resolve()
    output_zip = output_zip.resolve()
    files = [repo_root / relative for relative in ARTIFACT_PATHS]
    missing = [str(path.relative_to(repo_root)) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing Week 6 CPU artifacts: {', '.join(missing)}")

    records = [
        {
            "path": path.relative_to(repo_root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    ]
    manifest = {
        "artifact_type": "week6_cpu_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contains_licensed_pixels": False,
        "contains_model_weights": False,
        "files": records,
    }
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(repo_root).as_posix())
        archive.writestr("week6_cpu_artifact_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest["zip_size_bytes"] = output_zip.stat().st_size
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
