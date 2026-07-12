"""Week 6 aerial-image manifest and detection output helpers.

The roadmap calls for YOLO-based aerial-image inference, but the repository
does not yet specify a public dataset, license, labels, or split. This module
therefore enforces explicit image provenance before inference artifacts can be
treated as research data.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
ALLOWED_SPLITS = {"train", "validation", "test", "demo"}
AGRICULTURE_VISION_2017_CLASSES = (
    "background",
    "double_plant",
    "drydown",
    "endrow",
    "nutrient_deficiency",
    "planter_skip",
    "storm_damage",
    "water",
    "waterway",
    "weed_cluster",
)
REQUIRED_MANIFEST_FIELDS = (
    "id",
    "image_path",
    "split",
    "source",
    "data_type",
    "license",
    "provenance_url",
)


class VisionManifestError(ValueError):
    """Raised when an aerial-image manifest is malformed."""


@dataclass(frozen=True)
class VisionManifestRecord:
    """One aerial image with explicit provenance."""

    id: str
    image_path: Path
    split: str
    source: str
    data_type: str
    license: str
    provenance_url: str
    labels_path: Path | None = None
    notes: str | None = None
    sha256: str | None = None
    terms_url: str | None = None

    def to_dict(self, *, root: Path | None = None) -> dict[str, Any]:
        payload = asdict(self)
        payload["image_path"] = _display_path(self.image_path, root=root)
        if self.labels_path is not None:
            payload["labels_path"] = _display_path(self.labels_path, root=root)
        return payload


@dataclass(frozen=True)
class DetectionRecord:
    """One model detection for one image."""

    image_id: str
    image_path: str
    model_name: str
    model_version: str
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bbox_xyxy"] = list(self.bbox_xyxy)
        return payload


@dataclass(frozen=True)
class SegmentationMetricResult:
    """Overlap-aware semantic-segmentation evaluation output."""

    confusion_matrix: np.ndarray
    per_class_iou: tuple[float | None, ...]
    mean_iou: float
    valid_pixels: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "confusion_matrix": self.confusion_matrix.tolist(),
            "per_class_iou": list(self.per_class_iou),
            "mean_iou": self.mean_iou,
            "valid_pixels": self.valid_pixels,
        }


@dataclass(frozen=True)
class AgricultureVisionTarget:
    """One aligned Agriculture-Vision 2017 multilabel target stack."""

    image_id: str
    class_names: tuple[str, ...]
    targets: np.ndarray
    valid_mask: np.ndarray


def load_agriculture_vision_2017_target(
    dataset_dir: str | Path,
    image_id: str,
) -> AgricultureVisionTarget:
    """Load the observed 2017 binary masks for one aligned 512x512 tile."""

    root = Path(dataset_dir)
    boundary = _load_binary_mask(root / "field_bounds" / f"{image_id}.png")
    field_mask = _load_binary_mask(root / "field_masks" / f"{image_id}.png", shape=boundary.shape)
    anomaly_masks = np.stack(
        [
            _load_binary_mask(
                root / "field_labels" / class_name / f"{image_id}.png",
                shape=boundary.shape,
            )
            for class_name in AGRICULTURE_VISION_2017_CLASSES[1:]
        ]
    )
    valid_mask = boundary & field_mask
    background = ~anomaly_masks.any(axis=0)
    targets = np.concatenate((background[np.newaxis, ...], anomaly_masks), axis=0)
    targets[:, ~valid_mask] = False
    return AgricultureVisionTarget(
        image_id=image_id,
        class_names=AGRICULTURE_VISION_2017_CLASSES,
        targets=targets,
        valid_mask=valid_mask,
    )


def modified_multilabel_iou(
    predictions: np.ndarray,
    targets: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
) -> SegmentationMetricResult:
    """Compute Agriculture-Vision's overlap-aware modified mean IoU.

    ``predictions`` is a two-dimensional integer class map. ``targets`` is a
    boolean ``(classes, height, width)`` stack because Agriculture-Vision
    anomalies may overlap. Pixels excluded by ``valid_mask`` do not contribute.
    Classes with no prediction or target union are reported as ``None`` and are
    excluded from the mean.
    """

    predicted = np.asarray(predictions)
    target_stack = np.asarray(targets, dtype=bool)
    if predicted.ndim != 2:
        raise ValueError("predictions must have shape (height, width)")
    if target_stack.ndim != 3 or target_stack.shape[1:] != predicted.shape:
        raise ValueError("targets must have shape (classes, height, width)")
    if target_stack.shape[0] < 1:
        raise ValueError("targets must contain at least one class")
    if not np.issubdtype(predicted.dtype, np.integer):
        raise ValueError("predictions must contain integer class IDs")

    class_count = target_stack.shape[0]
    if np.any(predicted < 0) or np.any(predicted >= class_count):
        raise ValueError(f"predictions must contain class IDs in the range 0..{class_count - 1}")

    included = np.ones(predicted.shape, dtype=bool)
    if valid_mask is not None:
        included = np.asarray(valid_mask, dtype=bool)
        if included.shape != predicted.shape:
            raise ValueError("valid_mask must match the prediction shape")
    if np.any(included & ~target_stack.any(axis=0)):
        raise ValueError("every valid pixel must have at least one target class")

    confusion = np.zeros((class_count, class_count), dtype=np.int64)
    for row, column in np.argwhere(included):
        predicted_class = int(predicted[row, column])
        target_classes = np.flatnonzero(target_stack[:, row, column])
        if target_stack[predicted_class, row, column]:
            confusion[target_classes, target_classes] += 1
        else:
            confusion[predicted_class, target_classes] += 1

    true_positive = np.diag(confusion)
    prediction_count = confusion.sum(axis=1)
    target_count = confusion.sum(axis=0)
    union = prediction_count + target_count - true_positive
    per_class = tuple(
        None if class_union == 0 else float(true_positive[index] / class_union)
        for index, class_union in enumerate(union)
    )
    evaluated = [score for score in per_class if score is not None]
    mean_iou = float(np.mean(evaluated)) if evaluated else 0.0
    return SegmentationMetricResult(
        confusion_matrix=confusion,
        per_class_iou=per_class,
        mean_iou=mean_iou,
        valid_pixels=int(included.sum()),
    )


def load_vision_manifest(path: str | Path, *, dataset_root: str | Path) -> list[VisionManifestRecord]:
    """Load and validate a JSONL aerial-image manifest."""

    manifest = Path(path)
    root = Path(dataset_root).resolve()
    records: list[VisionManifestRecord] = []
    ids: set[str] = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in raw]
        if missing:
            raise VisionManifestError(f"line {line_number}: missing required fields: {', '.join(missing)}")
        record_id = _required_text(raw["id"], "id", line_number)
        if record_id in ids:
            raise VisionManifestError(f"line {line_number}: duplicate id: {record_id}")
        ids.add(record_id)
        split = _required_text(raw["split"], "split", line_number)
        if split not in ALLOWED_SPLITS:
            raise VisionManifestError(
                f"line {line_number}: split must be one of {sorted(ALLOWED_SPLITS)}"
            )
        image_path = _resolve_path(root, raw["image_path"], "image_path", line_number)
        if image_path.suffix.lower() not in IMAGE_SUFFIXES:
            raise VisionManifestError(
                f"line {line_number}: image_path must end with one of {sorted(IMAGE_SUFFIXES)}"
            )
        if not image_path.exists():
            raise VisionManifestError(f"line {line_number}: image file does not exist: {image_path}")
        declared_sha256 = _optional_sha256(raw.get("sha256"), line_number)
        if declared_sha256 is not None:
            actual_sha256 = sha256_file(image_path)
            if actual_sha256 != declared_sha256:
                raise VisionManifestError(
                    f"line {line_number}: sha256 mismatch for {image_path}: "
                    f"expected {declared_sha256}, got {actual_sha256}"
                )
        labels_path = None
        if raw.get("labels_path") not in (None, ""):
            labels_path = _resolve_path(root, raw["labels_path"], "labels_path", line_number)
            if not labels_path.exists():
                raise VisionManifestError(f"line {line_number}: labels file does not exist: {labels_path}")

        records.append(
            VisionManifestRecord(
                id=record_id,
                image_path=image_path,
                split=split,
                source=_required_text(raw["source"], "source", line_number),
                data_type=_required_text(raw["data_type"], "data_type", line_number),
                license=_required_text(raw["license"], "license", line_number),
                provenance_url=_required_text(raw["provenance_url"], "provenance_url", line_number),
                labels_path=labels_path,
                notes=str(raw["notes"]) if raw.get("notes") is not None else None,
                sha256=declared_sha256,
                terms_url=str(raw["terms_url"]).strip() if raw.get("terms_url") else None,
            )
        )
    return records


def summarize_vision_manifest(records: list[VisionManifestRecord]) -> dict[str, Any]:
    """Summarize provenance and split metadata for aerial-image records."""

    return {
        "records": len(records),
        "split_counts": _count(record.split for record in records),
        "source_counts": _count(record.source for record in records),
        "data_type_counts": _count(record.data_type for record in records),
        "license_counts": _count(record.license for record in records),
        "records_with_labels": sum(1 for record in records if record.labels_path is not None),
        "records_with_sha256": sum(1 for record in records if record.sha256 is not None),
    }


def summarize_detections(records: list[DetectionRecord], *, image_count: int) -> dict[str, Any]:
    """Summarize model detections without claiming benchmark performance."""

    class_counts: Counter[str] = Counter(record.class_name for record in records)
    return {
        "images": image_count,
        "detections": len(records),
        "class_counts": dict(sorted(class_counts.items())),
        "evaluation_note": (
            "Detection count summary only. This is not mAP, recall, mission success, "
            "or safety evidence unless labeled data and an evaluation protocol are added."
        ),
    }


def _count(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _resolve_path(root: Path, raw_path: Any, field_name: str, line_number: int) -> Path:
    value = _required_text(raw_path, field_name, line_number)
    candidate = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise VisionManifestError(f"line {line_number}: {field_name} must stay within dataset_root") from exc
    return candidate


def _required_text(value: Any, field_name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisionManifestError(f"line {line_number}: {field_name} must be a non-empty string")
    return value.strip()


def _optional_sha256(value: Any, line_number: int) -> str | None:
    if value in (None, ""):
        return None
    valid = (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )
    if not valid:
        raise VisionManifestError(f"line {line_number}: sha256 must be 64 hexadecimal characters")
    return value.lower()


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return a streaming SHA-256 digest for a research input file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_cuda_device(required_substring: str, torch_module: Any) -> dict[str, Any]:
    """Return CUDA metadata and fail unless the requested device is present."""

    cuda_available = bool(torch_module.cuda.is_available())
    device_names = (
        [str(torch_module.cuda.get_device_name(index)) for index in range(torch_module.cuda.device_count())]
        if cuda_available
        else []
    )
    metadata = {
        "cuda_available": cuda_available,
        "cuda_device_count": len(device_names),
        "cuda_device_names": device_names,
        "required_device_substring": required_substring,
    }
    if not cuda_available or not any(required_substring in name for name in device_names):
        raise RuntimeError(
            f"required CUDA device containing {required_substring!r} is unavailable: {device_names}"
        )
    return metadata


def _display_path(path: Path, *, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_binary_mask(path: Path, *, shape: tuple[int, ...] | None = None) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to load Agriculture-Vision masks") from exc
    if not path.is_file():
        raise FileNotFoundError(f"required Agriculture-Vision mask does not exist: {path}")
    with Image.open(path) as image:
        values = np.asarray(image)
    if values.ndim != 2:
        raise ValueError(f"Agriculture-Vision mask must be single-channel: {path}")
    if shape is not None and values.shape != shape:
        raise ValueError(f"Agriculture-Vision mask shape mismatch: {path}: {values.shape} != {shape}")
    unique_values = set(int(value) for value in np.unique(values))
    if not unique_values.issubset({0, 255}):
        raise ValueError(f"Agriculture-Vision mask must use binary 0/255 values: {path}: {sorted(unique_values)}")
    return values == 255
