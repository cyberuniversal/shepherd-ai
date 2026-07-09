"""Week 6 aerial-image manifest and detection output helpers.

The roadmap calls for YOLO-based aerial-image inference, but the repository
does not yet specify a public dataset, license, labels, or split. This module
therefore enforces explicit image provenance before inference artifacts can be
treated as research data.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
ALLOWED_SPLITS = {"train", "validation", "test", "demo"}
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


def _display_path(path: Path, *, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)
