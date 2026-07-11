"""Build a checked, split-preserving Agriculture-Vision RGB manifest.

This script does not download the dataset or accept its terms for the user.
Run it only after downloading from the official source and reviewing the terms.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import sha256_file  # noqa: E402


SOURCE = "Agriculture-Vision CVPR 2020 dataset"
PROVENANCE_URL = "https://registry.opendata.aws/intelinair_agriculture_vision/"
TERMS_URL = (
    "https://intelinair-data-releases.s3.amazonaws.com/agriculture-vision/"
    "cvpr_paper_2020/Agriculture-Vision%20Dataset%20Terms%20of%20Use.pdf"
)
LICENSE = "IntelinAir limited non-commercial research license; redistribution prohibited"
SPLIT_ALIASES = {"train": "train", "training": "train", "val": "validation", "validation": "validation", "test": "test"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True, help="Extracted Agriculture-Vision directory.")
    parser.add_argument("--dataset-root", required=True, help="Root used for manifest-relative paths.")
    parser.add_argument("--output", required=True, help="Manifest JSONL output path.")
    parser.add_argument("--max-per-split", type=int, default=10, help="Deterministic RGB-image limit per split.")
    parser.add_argument(
        "--accept-terms",
        action="store_true",
        help="Confirm that you reviewed and accept the official Agriculture-Vision terms.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.accept_terms:
        raise SystemExit(f"Review {TERMS_URL} and rerun with --accept-terms only if you agree.")
    if args.max_per_split < 1:
        raise SystemExit("--max-per-split must be at least 1")

    dataset_dir = Path(args.dataset_dir).resolve()
    dataset_root = Path(args.dataset_root).resolve()
    try:
        dataset_dir.relative_to(dataset_root)
    except ValueError as exc:
        raise SystemExit("--dataset-dir must stay within --dataset-root") from exc

    grouped: dict[str, list[Path]] = {"train": [], "validation": [], "test": []}
    for image in sorted(path for path in dataset_dir.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES):
        if "rgb" not in {part.lower() for part in image.parts}:
            continue
        split = _infer_split(image, dataset_dir)
        if split is not None:
            grouped[split].append(image)

    rows = []
    for split in sorted(grouped):
        for image in grouped[split][: args.max_per_split]:
            relative = image.relative_to(dataset_root).as_posix()
            rows.append(
                {
                    "id": f"agriculture_vision_{split}_{image.stem}",
                    "image_path": relative,
                    "split": split,
                    "source": SOURCE,
                    "data_type": "public_human_annotated_aerial_imagery",
                    "license": LICENSE,
                    "provenance_url": PROVENANCE_URL,
                    "terms_url": TERMS_URL,
                    "sha256": sha256_file(image),
                    "notes": (
                        "RGB input only. Agriculture-Vision ground truth is overlapping semantic-segmentation "
                        "masks; generic YOLO detections are not Agriculture-Vision benchmark predictions."
                    ),
                }
            )

    if not rows:
        raise SystemExit(
            "No RGB images were found under train/val/test directories. "
            "Check the extracted Agriculture-Vision layout."
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"records": len(rows), "split_counts": {key: len(value[: args.max_per_split]) for key, value in grouped.items()}}, indent=2))


def _infer_split(image: Path, dataset_dir: Path) -> str | None:
    for part in image.relative_to(dataset_dir).parts:
        split = SPLIT_ALIASES.get(part.lower())
        if split is not None:
            return split
    return None


if __name__ == "__main__":
    main()
