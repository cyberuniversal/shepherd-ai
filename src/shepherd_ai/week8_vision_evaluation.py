"""Leakage-aware Agriculture-Vision selection for the Week 8 mission."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

import numpy as np


MISSION_CLASS_NAMES: dict[str, tuple[str, ...]] = {
    "clause_001": (
        "double_plant",
        "drydown",
        "endrow",
        "nutrient_deficiency",
        "planter_skip",
        "storm_damage",
        "weed_cluster",
    ),
    "clause_002": ("water", "waterway"),
}


def select_mission_records(
    records: Iterable[Mapping[str, Any]],
    *,
    excluded_ids: set[str],
    max_per_clause: int,
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    """Select disjoint labeled validation records for both mission clauses."""

    if max_per_clause < 1:
        raise ValueError("max_per_clause must be positive")
    candidates = [
        dict(record)
        for record in records
        if record.get("split") == "validation" and str(record.get("id")) not in excluded_ids
    ]
    candidates.sort(key=lambda row: _rank(seed, str(row.get("id"))))
    selected: dict[str, list[dict[str, Any]]] = {"clause_001": [], "clause_002": []}
    used: set[str] = set()
    # Irrigation is selected first because water/waterway positives are rarer.
    for clause_id in ("clause_002", "clause_001"):
        relevant = set(MISSION_CLASS_NAMES[clause_id])
        for record in candidates:
            record_id = str(record.get("id"))
            positive = {str(value) for value in record.get("positive_classes", [])}
            if record_id in used or not positive.intersection(relevant):
                continue
            selected[clause_id].append(record)
            used.add(record_id)
            if len(selected[clause_id]) == max_per_clause:
                break
        if not selected[clause_id]:
            raise ValueError(f"no positive held-out validation records for {clause_id}")
    return selected


def class_iou_summary(
    confusion_matrix: np.ndarray,
    *,
    class_names: tuple[str, ...],
    selected_classes: Iterable[str],
) -> dict[str, Any]:
    """Calculate IoU only for the mission-declared semantic classes."""

    confusion = np.asarray(confusion_matrix, dtype=np.int64)
    if confusion.shape != (len(class_names), len(class_names)):
        raise ValueError("confusion matrix shape does not match class names")
    diagonal = np.diag(confusion)
    union = confusion.sum(axis=1) + confusion.sum(axis=0) - diagonal
    values: dict[str, float | None] = {}
    for class_name in selected_classes:
        if class_name not in class_names:
            raise ValueError(f"unknown class name: {class_name}")
        index = class_names.index(class_name)
        values[class_name] = (
            None if union[index] == 0 else float(diagonal[index] / union[index])
        )
    evaluated = [value for value in values.values() if value is not None]
    return {
        "per_class_iou": values,
        "mean_iou": float(np.mean(evaluated)) if evaluated else None,
        "evaluated_class_count": len(evaluated),
    }


def _rank(seed: int, record_id: str) -> str:
    return hashlib.sha256(f"{seed}:{record_id}".encode("utf-8")).hexdigest()
