"""Build a checked, split-preserving Agriculture-Vision RGB manifest.

This script does not download the dataset or accept its terms for the user.
Run it only after downloading from the official source and reviewing the terms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import AGRICULTURE_VISION_2017_CLASSES, sha256_file  # noqa: E402


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
    parser.add_argument(
        "--split-json",
        help="Official Agriculture-Vision JSON mapping train/val/test to farmland IDs.",
    )
    parser.add_argument("--max-per-split", type=int, default=10, help="Deterministic RGB-image limit per split.")
    parser.add_argument(
        "--selection-strategy",
        choices=("sorted-prefix", "seeded-hash", "train-label-stratified"),
        default="sorted-prefix",
        help="Select the sorted prefix or a deterministic hash-ranked sample.",
    )
    parser.add_argument(
        "--labels-dir",
        help="Agriculture-Vision label root required by train-label-stratified selection.",
    )
    parser.add_argument(
        "--min-positive-records-per-class",
        type=int,
        default=4,
        help="Training-record reservation target per anomaly class for stratified selection.",
    )
    parser.add_argument(
        "--selection-seed",
        type=int,
        default=17,
        help="Seed included in hash ranking when --selection-strategy=seeded-hash.",
    )
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
    if args.min_positive_records_per_class < 1:
        raise SystemExit("--min-positive-records-per-class must be at least 1")
    if args.selection_strategy == "train-label-stratified" and not args.labels_dir:
        raise SystemExit("train-label-stratified selection requires --labels-dir")

    dataset_dir = Path(args.dataset_dir).resolve()
    dataset_root = Path(args.dataset_root).resolve()
    try:
        dataset_dir.relative_to(dataset_root)
    except ValueError as exc:
        raise SystemExit("--dataset-dir must stay within --dataset-root") from exc

    field_splits = _load_field_splits(Path(args.split_json)) if args.split_json else {}
    grouped: dict[str, list[Path]] = {"train": [], "validation": [], "test": []}
    for image in sorted(path for path in dataset_dir.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES):
        if "rgb" not in {part.lower() for part in image.parts}:
            continue
        split = field_splits.get(_field_id(image)) if field_splits else _infer_split(image, dataset_dir)
        if split is not None:
            grouped[split].append(image)

    labels_dir = Path(args.labels_dir).resolve() if args.labels_dir else None
    if labels_dir is not None:
        try:
            labels_dir.relative_to(dataset_root)
        except ValueError as exc:
            raise SystemExit("--labels-dir must stay within --dataset-root") from exc

    rows = []
    available_train_positive_records = None
    selected_train_positive_records = None
    for split in sorted(grouped):
        if split == "train" and args.selection_strategy == "train-label-stratified":
            selected, available_train_positive_records, selected_train_positive_records = (
                _select_label_stratified_train_images(
                    grouped[split],
                    limit=args.max_per_split,
                    seed=args.selection_seed,
                    dataset_dir=dataset_dir,
                    labels_dir=labels_dir,
                    minimum_per_class=args.min_positive_records_per_class,
                )
            )
        else:
            strategy = (
                "seeded-hash"
                if args.selection_strategy == "train-label-stratified"
                else args.selection_strategy
            )
            selected = _select_images(
                grouped[split],
                limit=args.max_per_split,
                strategy=strategy,
                seed=args.selection_seed,
                dataset_dir=dataset_dir,
            )
        for image in selected:
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
    print(
        json.dumps(
            {
                "records": len(rows),
                "selection_strategy": args.selection_strategy,
                "selection_seed": args.selection_seed,
                "min_positive_records_per_class": (
                    args.min_positive_records_per_class
                    if args.selection_strategy == "train-label-stratified"
                    else None
                ),
                "available_train_positive_records": available_train_positive_records,
                "selected_train_positive_records": selected_train_positive_records,
                "split_counts": {
                    key: min(len(value), args.max_per_split) for key, value in grouped.items()
                },
            },
            indent=2,
        )
    )


def _select_images(
    images: list[Path],
    *,
    limit: int,
    strategy: str,
    seed: int,
    dataset_dir: Path,
) -> list[Path]:
    if strategy == "sorted-prefix":
        return images[:limit]
    if strategy == "seeded-hash":
        ranked = sorted(
            images,
            key=lambda image: hashlib.sha256(
                f"{seed}:{image.relative_to(dataset_dir).as_posix()}".encode("utf-8")
            ).digest(),
        )
        return ranked[:limit]
    raise ValueError(f"unsupported selection strategy: {strategy}")


def _select_label_stratified_train_images(
    images: list[Path],
    *,
    limit: int,
    seed: int,
    dataset_dir: Path,
    labels_dir: Path,
    minimum_per_class: int,
) -> tuple[list[Path], dict[str, int], dict[str, int]]:
    anomaly_classes = AGRICULTURE_VISION_2017_CLASSES[1:]
    ranked = _select_images(
        images,
        limit=len(images),
        strategy="seeded-hash",
        seed=seed,
        dataset_dir=dataset_dir,
    )
    positives = {
        image: {
            class_name
            for class_name in anomaly_classes
            if _mask_has_positive_pixel(labels_dir / "field_labels" / class_name / f"{image.stem}.png")
        }
        for image in ranked
    }
    available = {
        class_name: sum(class_name in image_classes for image_classes in positives.values())
        for class_name in anomaly_classes
    }
    selected: list[Path] = []
    selected_set: set[Path] = set()
    selected_counts = {class_name: 0 for class_name in anomaly_classes}
    for class_name in sorted(anomaly_classes, key=lambda name: (available[name], name)):
        target = min(minimum_per_class, available[class_name])
        for image in ranked:
            if selected_counts[class_name] >= target or len(selected) >= limit:
                break
            if image in selected_set or class_name not in positives[image]:
                continue
            selected.append(image)
            selected_set.add(image)
            for present_class in positives[image]:
                selected_counts[present_class] += 1
    for image in ranked:
        if len(selected) >= limit:
            break
        if image in selected_set:
            continue
        selected.append(image)
        selected_set.add(image)
        for present_class in positives[image]:
            selected_counts[present_class] += 1
    return selected, available, selected_counts


def _mask_has_positive_pixel(path: Path) -> bool:
    if not path.is_file():
        return False
    from PIL import Image

    with Image.open(path) as image:
        return image.getbbox() is not None


def _infer_split(image: Path, dataset_dir: Path) -> str | None:
    for part in image.relative_to(dataset_dir).parts:
        split = SPLIT_ALIASES.get(part.lower())
        if split is not None:
            return split
    return None


def _load_field_splits(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    field_splits: dict[str, str] = {}
    for raw_split, field_ids in payload.items():
        split = SPLIT_ALIASES.get(str(raw_split).lower())
        if split is None:
            continue
        if not isinstance(field_ids, list):
            raise SystemExit(f"split {raw_split!r} must contain a list of farmland IDs")
        for field_id in field_ids:
            normalized_id = str(field_id).strip()
            if normalized_id in field_splits:
                raise SystemExit(f"farmland ID appears in multiple splits: {normalized_id}")
            field_splits[normalized_id] = split
    if not field_splits:
        raise SystemExit("split JSON did not contain train/val/test farmland IDs")
    return field_splits


def _field_id(image: Path) -> str:
    return image.stem.split("_", maxsplit=1)[0]


if __name__ == "__main__":
    main()
