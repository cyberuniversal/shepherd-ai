"""Evaluate the frozen Week 6 segmentation model on a disjoint Week 8 holdout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.segmentation import AgricultureVisionDataset, build_small_unet  # noqa: E402
from shepherd_ai.vision import (  # noqa: E402
    AGRICULTURE_VISION_2017_CLASSES,
    load_agriculture_vision_2017_target,
    load_vision_manifest,
    modified_multilabel_iou,
    require_cuda_device,
    sha256_file,
)
from shepherd_ai.week8_vision_evaluation import (  # noqa: E402
    MISSION_CLASS_NAMES,
    class_iou_summary,
    select_mission_records_lazily,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-manifest", required=True)
    parser.add_argument("--development-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--labels-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--mission-manifest-output", required=True)
    parser.add_argument("--raw-predictions-output", required=True)
    parser.add_argument(
        "--evaluation-output",
        default="outputs/evaluations/week8_mission_vision_evaluation.json",
    )
    parser.add_argument("--max-per-clause", type=int, default=32)
    parser.add_argument("--selection-seed", type=int, default=29)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--required-device-substring", default="T4")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import torch
    from torch.utils.data import DataLoader

    if args.device == "cuda":
        runtime = require_cuda_device(args.required_device_substring, torch)
        device = torch.device("cuda:0")
    else:
        runtime = {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device_names": [
                torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())
            ],
            "selected_device": "cpu",
        }
        device = torch.device("cpu")

    all_records = load_vision_manifest(args.full_manifest, dataset_root=args.dataset_root)
    development = load_vision_manifest(args.development_manifest, dataset_root=args.dataset_root)
    development_ids = {record.id for record in development}
    candidates = [
        {"id": record.id, "record": record, "split": record.split}
        for record in all_records
    ]

    def positive_classes_for(row: dict[str, Any]) -> list[str]:
        record = row["record"]
        target = load_agriculture_vision_2017_target(args.labels_dir, record.image_path.stem)
        return [
            class_name
            for index, class_name in enumerate(target.class_names[1:], start=1)
            if bool(target.targets[index].any())
        ]

    selected = select_mission_records_lazily(
        candidates,
        excluded_ids=development_ids,
        max_per_clause=args.max_per_clause,
        seed=args.selection_seed,
        positive_classes_for=positive_classes_for,
    )
    selected_rows = [
        (clause_id, row)
        for clause_id in ("clause_001", "clause_002")
        for row in selected[clause_id]
    ]
    selected_records = [row["record"] for _, row in selected_rows]
    _write_mission_manifest(args.mission_manifest_output, selected_rows, args.dataset_root)

    checkpoint_path = Path(args.checkpoint)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    config = dict(checkpoint.get("config", {}))
    model = build_small_unet(
        class_count=len(AGRICULTURE_VISION_2017_CLASSES),
        base_channels=int(config.get("base_channels", 16)),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    loader = DataLoader(
        AgricultureVisionDataset(selected_records, args.labels_dir),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=device.type == "cuda",
    )
    clause_by_id = {row["record"].id: clause_id for clause_id, row in selected_rows}
    confusions = {
        clause_id: np.zeros(
            (len(AGRICULTURE_VISION_2017_CLASSES), len(AGRICULTURE_VISION_2017_CLASSES)),
            dtype=np.int64,
        )
        for clause_id in MISSION_CLASS_NAMES
    }
    raw_rows: list[dict[str, Any]] = []
    started = perf_counter()
    with torch.no_grad():
        for batch in loader:
            logits = model(batch["image"].to(device, non_blocking=True))
            predictions = logits.argmax(dim=1).cpu().numpy()
            targets = batch["target"].numpy().astype(bool)
            valid_masks = batch["valid_mask"].numpy().astype(bool)
            for index, image_id in enumerate(batch["id"]):
                result = modified_multilabel_iou(
                    predictions[index], targets[index], valid_mask=valid_masks[index]
                )
                clause_id = clause_by_id[str(image_id)]
                confusions[clause_id] += result.confusion_matrix
                raw_rows.append(
                    {
                        "image_id": str(image_id),
                        "clause_id": clause_id,
                        "confusion_matrix": result.confusion_matrix.tolist(),
                        "per_class_iou": dict(zip(result_class_names(), result.per_class_iou)),
                        "valid_pixels": result.valid_pixels,
                    }
                )
    elapsed = perf_counter() - started
    _write_jsonl(args.raw_predictions_output, raw_rows)

    clause_metrics = {
        clause_id: class_iou_summary(
            confusion,
            class_names=AGRICULTURE_VISION_2017_CLASSES,
            selected_classes=MISSION_CLASS_NAMES[clause_id],
        )
        for clause_id, confusion in confusions.items()
    }
    evaluated_values = [
        value
        for metric in clause_metrics.values()
        for value in metric["per_class_iou"].values()
        if value is not None
    ]
    if not evaluated_values:
        raise RuntimeError("selected holdout produced no evaluable mission class IoUs")
    checkpoint_hash = sha256_file(checkpoint_path)
    manifest_hash = sha256_file(args.mission_manifest_output)
    raw_hash = sha256_file(args.raw_predictions_output)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_source": "roadmap_week8_fixed_scenario",
        "dataset": {
            "name": "Agriculture-Vision 2017 miniscale",
            "source_split": "official_validation_remainder",
            "development_ids_excluded": len(development_ids),
            "selection_seed": args.selection_seed,
            "selection_basis": "label_positive_then_seeded_hash",
            "license": "official terms accepted; pixels remain in private Google Drive",
        },
        "task_label_mapping": {
            "clause_001": {
                "mission_target": "crops",
                "classes": list(MISSION_CLASS_NAMES["clause_001"]),
            },
            "clause_002": {
                "mission_target": "irrigation",
                "classes": list(MISSION_CLASS_NAMES["clause_002"]),
            },
        },
        "manifest": {
            "path": str(Path(args.mission_manifest_output)).replace("\\", "/"),
            "sha256": manifest_hash,
            "records": len(selected_rows),
            "clause_ids": sorted(MISSION_CLASS_NAMES),
            "records_with_sha256": len(selected_rows),
            "records_with_labels": len(selected_rows),
        },
        "model": {
            "name": "small_unet_from_scratch",
            "source": "week6_frozen_bce_dice_development_checkpoint",
            "path": str(checkpoint_path).replace("\\", "/"),
            "sha256": checkpoint_hash,
            "training_config": config,
        },
        "inference": {
            "device": str(device),
            "runtime": runtime,
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "batch_size": args.batch_size,
            "elapsed_seconds": elapsed,
            "raw_predictions_path": str(Path(args.raw_predictions_output)).replace("\\", "/"),
            "raw_predictions_sha256": raw_hash,
        },
        "metrics": {
            "name": "mission_class_modified_mean_iou",
            "primary_value": float(np.mean(evaluated_values)),
            "denominator": len(evaluated_values),
            "image_denominator": len(selected_rows),
            "clause_metrics": clause_metrics,
        },
        "limitations": [
            "This is a disjoint internal validation remainder, not the official hidden test benchmark.",
            "Mission imagery is sampled from public agricultural data rather than captured by physical drones.",
            "The class mapping is a declared Week 8 protocol choice, not a claim from Agriculture-Vision.",
        ],
    }
    output = Path(args.evaluation_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(selected_rows), "metrics": payload["metrics"]}, indent=2))


def _write_mission_manifest(path: str | Path, rows: list[tuple[str, dict[str, Any]]], dataset_root: str | Path) -> None:
    root = Path(dataset_root).resolve()
    payloads = []
    for clause_id, row in rows:
        record = row["record"]
        payload = record.to_dict(root=root)
        payload.update(
            {
                "clause_id": clause_id,
                "mission_target": "crops" if clause_id == "clause_001" else "irrigation",
                "positive_classes": row["positive_classes"],
                "label_provenance": "official Agriculture-Vision 2017 masks",
                "sha256": record.sha256 or sha256_file(record.image_path),
            }
        )
        payloads.append(payload)
    _write_jsonl(path, payloads)


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def result_class_names() -> tuple[str, ...]:
    return AGRICULTURE_VISION_2017_CLASSES


if __name__ == "__main__":
    main()
