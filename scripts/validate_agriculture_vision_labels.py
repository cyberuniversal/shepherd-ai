"""Audit Agriculture-Vision train/validation masks without inspecting test labels."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import (  # noqa: E402
    AGRICULTURE_VISION_2017_CLASSES,
    load_agriculture_vision_2017_target,
    load_vision_manifest,
)


ALLOWED_AUDIT_SPLITS = {"train", "validation"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--labels-dir", required=True)
    parser.add_argument("--split", action="append", dest="splits")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_splits = set(args.splits or sorted(ALLOWED_AUDIT_SPLITS))
    unsupported = selected_splits - ALLOWED_AUDIT_SPLITS
    if unsupported:
        raise SystemExit(f"label audit is limited to train/validation; rejected: {sorted(unsupported)}")

    records = load_vision_manifest(args.manifest, dataset_root=args.dataset_root)
    selected = [record for record in records if record.split in selected_splits]
    if not selected:
        raise SystemExit(f"manifest contains no records for splits: {sorted(selected_splits)}")

    positive_pixels = Counter({class_name: 0 for class_name in AGRICULTURE_VISION_2017_CLASSES})
    split_counts = Counter()
    valid_pixels = 0
    overlap_pixels = 0
    for record in selected:
        target = load_agriculture_vision_2017_target(args.labels_dir, record.image_path.stem)
        split_counts[record.split] += 1
        valid_pixels += int(target.valid_mask.sum())
        for index, class_name in enumerate(target.class_names):
            positive_pixels[class_name] += int(target.targets[index].sum())
        overlap_pixels += int((target.targets[1:].sum(axis=0) > 1).sum())

    all_splits = {record.split for record in records}
    payload = {
        "records": len(selected),
        "selected_splits": sorted(selected_splits),
        "excluded_splits": sorted(all_splits - selected_splits),
        "split_counts": dict(sorted(split_counts.items())),
        "valid_pixels": valid_pixels,
        "positive_pixels": dict(positive_pixels),
        "positive_pixel_fraction": {
            class_name: (count / valid_pixels if valid_pixels else 0.0)
            for class_name, count in positive_pixels.items()
        },
        "overlap_pixels": overlap_pixels,
        "overlap_pixel_fraction": overlap_pixels / valid_pixels if valid_pixels else 0.0,
        "research_note": (
            "Structural and prevalence audit only. Test labels are excluded. "
            "These counts are not model-performance results."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
