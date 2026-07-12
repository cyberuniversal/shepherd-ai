"""Record an extracted Agriculture-Vision directory layout without copying data."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


LABEL_KEYWORDS = ("annotation", "bound", "ground_truth", "label", "mask")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True, help="Extracted dataset directory to inspect.")
    parser.add_argument("--output", required=True, help="JSON layout report path.")
    parser.add_argument("--sample-limit", type=int, default=80, help="Maximum relative file paths to record.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_limit < 0:
        raise SystemExit("--sample-limit must be non-negative")
    dataset_dir = Path(args.dataset_dir).resolve()
    if not dataset_dir.is_dir():
        raise SystemExit(f"dataset directory does not exist: {dataset_dir}")

    files = sorted(path for path in dataset_dir.rglob("*") if path.is_file())
    if not files:
        raise SystemExit(f"dataset directory contains no files: {dataset_dir}")
    directories = sorted(path for path in dataset_dir.rglob("*") if path.is_dir())
    relative_directories = [_relative(path, dataset_dir) for path in directories]
    label_like_directories = [
        path for path in relative_directories if any(keyword in path.lower() for keyword in LABEL_KEYWORDS)
    ]
    extension_counts = Counter(path.suffix.lower() or "<none>" for path in files)
    top_level_counts = Counter(_relative(path, dataset_dir).split("/", maxsplit=1)[0] for path in files)
    payload = {
        "summary": {
            "files": len(files),
            "directories": len(directories),
            "extension_counts": dict(sorted(extension_counts.items())),
            "top_level_file_counts": dict(sorted(top_level_counts.items())),
        },
        "top_level_entries": sorted(path.name for path in dataset_dir.iterdir()),
        "directories": relative_directories,
        "label_like_directories": label_like_directories,
        "sample_files": [_relative(path, dataset_dir) for path in files[: args.sample_limit]],
        "research_note": (
            "This report records relative paths and counts only. It does not validate label semantics, "
            "copy licensed imagery, or establish model performance."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


if __name__ == "__main__":
    main()
