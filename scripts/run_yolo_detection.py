"""Run Ultralytics YOLO on a validated Week 6 aerial-image manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import (  # noqa: E402
    DetectionRecord,
    load_vision_manifest,
    require_cuda_device,
    summarize_detections,
    summarize_vision_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Aerial-image manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root all manifest paths must stay within.")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics YOLO model name or local weights path.")
    parser.add_argument("--confidence", type=float, default=0.25, help="YOLO confidence threshold.")
    parser.add_argument("--device", help="Optional Ultralytics device string, for example '0' or 'cpu'.")
    parser.add_argument(
        "--required-device-substring",
        help="Require an available CUDA device name containing this text, for example T4.",
    )
    parser.add_argument("--limit", type=int, help="Optional maximum number of manifest records to process.")
    parser.add_argument("--predictions-output", required=True, help="Detection JSONL output path.")
    parser.add_argument("--summary-output", required=True, help="Detection summary JSON output path.")
    parser.add_argument("--annotated-dir", help="Optional directory for annotated images.")
    args = parser.parse_args()

    records = load_vision_manifest(args.manifest, dataset_root=args.dataset_root)
    if args.limit is not None:
        records = records[: args.limit]
    yolo_cls = _load_yolo()
    import torch

    device_metadata = (
        require_cuda_device(args.required_device_substring, torch)
        if args.required_device_substring
        else {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cuda_device_names": [
                str(torch.cuda.get_device_name(index)) for index in range(torch.cuda.device_count())
            ]
            if torch.cuda.is_available()
            else [],
            "required_device_substring": None,
        }
    )
    model = yolo_cls(args.model)

    detections: list[DetectionRecord] = []
    annotated_dir = Path(args.annotated_dir) if args.annotated_dir else None
    if annotated_dir is not None:
        annotated_dir.mkdir(parents=True, exist_ok=True)

    for record in records:
        result_items = model.predict(
            source=str(record.image_path),
            conf=args.confidence,
            device=args.device,
            verbose=False,
        )
        for result in result_items:
            detections.extend(_detections_from_result(record.id, str(record.image_path), args.model, result))
            if annotated_dir is not None:
                result.save(filename=str(annotated_dir / f"{record.id}_yolo.jpg"))

    predictions_output = Path(args.predictions_output)
    predictions_output.parent.mkdir(parents=True, exist_ok=True)
    predictions_output.write_text(
        "".join(json.dumps(record.to_dict(), sort_keys=True) + "\n" for record in detections),
        encoding="utf-8",
    )

    summary = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "manifest": str(Path(args.manifest)),
            "model": args.model,
            "parameters": {
                "confidence": args.confidence,
                "device": args.device or "ultralytics_default",
                "device_metadata": device_metadata,
                "limit": args.limit,
            },
            "manifest_summary": summarize_vision_manifest(records),
            "research_note": (
                "YOLO detections are perception outputs only. Do not report detection performance "
                "without labels, dataset provenance, split definitions, and an evaluation protocol."
            ),
        },
        "summary": summarize_detections(detections, image_count=len(records)),
    }
    summary_output = Path(args.summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["summary"], indent=2, sort_keys=True))


def _load_yolo() -> Any:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Ultralytics is not installed. Install the vision extra first, for example: "
            "python -m pip install -e .[vision]"
        ) from exc
    return YOLO


def _detections_from_result(
    image_id: str,
    image_path: str,
    model_name: str,
    result: Any,
) -> list[DetectionRecord]:
    names = getattr(result, "names", {}) or {}
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    xyxy = boxes.xyxy.cpu().tolist()
    confidences = boxes.conf.cpu().tolist()
    class_ids = [int(value) for value in boxes.cls.cpu().tolist()]
    return [
        DetectionRecord(
            image_id=image_id,
            image_path=image_path,
            model_name=model_name,
            model_version="ultralytics_runtime",
            class_id=class_id,
            class_name=str(names.get(class_id, class_id)),
            confidence=float(confidence),
            bbox_xyxy=tuple(float(value) for value in bbox),
        )
        for bbox, confidence, class_id in zip(xyxy, confidences, class_ids)
    ]


if __name__ == "__main__":
    main()
