"""Validation helpers for Week 3 grounding evaluation JSONL files."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from shepherd_ai.grounding import MapLocation


ALLOWED_EXPECTED_STATUSES = {"grounded", "ambiguous", "unresolved", "not_provided"}
REQUIRED_RECORD_FIELDS = {"id", "text", "split", "source", "data_type", "expected_grounding"}
REQUIRED_EXPECTED_FIELDS = {"status", "location_id"}


@dataclass(frozen=True)
class GroundingDatasetRecord:
    """One labeled command record for grounding evaluation."""

    id: str
    text: str
    split: str
    source: str
    data_type: str
    expected_grounding: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class GroundingDatasetSummary:
    """Summary of a validated grounding dataset."""

    records: int
    split_counts: dict[str, int]
    source_counts: dict[str, int]
    data_type_counts: dict[str, int]
    expected_field_counts: dict[str, int]
    expected_status_counts: dict[str, int]
    grounded_location_ids: list[str] = field(default_factory=list)
    ambiguous_reference_count: int = 0
    unresolved_reference_count: int = 0
    not_provided_reference_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "split_counts": self.split_counts,
            "source_counts": self.source_counts,
            "data_type_counts": self.data_type_counts,
            "expected_field_counts": self.expected_field_counts,
            "expected_status_counts": self.expected_status_counts,
            "grounded_location_ids": self.grounded_location_ids,
            "ambiguous_reference_count": self.ambiguous_reference_count,
            "unresolved_reference_count": self.unresolved_reference_count,
            "not_provided_reference_count": self.not_provided_reference_count,
            "warnings": self.warnings,
        }


def load_grounding_dataset(path: str | Path, locations: list[MapLocation]) -> list[GroundingDatasetRecord]:
    """Load and validate a grounding-evaluation JSONL dataset."""

    dataset_path = Path(path)
    records: list[GroundingDatasetRecord] = []
    seen_ids: set[str] = set()
    known_location_ids = {location.id for location in locations}

    for line_number, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, Mapping):
            raise ValueError(f"line {line_number}: record must be a JSON object")
        missing = REQUIRED_RECORD_FIELDS - set(raw)
        if missing:
            raise ValueError(f"line {line_number}: missing required fields: {', '.join(sorted(missing))}")

        record_id = _required_text(raw, "id", line_number=line_number)
        if record_id in seen_ids:
            raise ValueError(f"line {line_number}: duplicate record id: {record_id}")
        seen_ids.add(record_id)

        expected_grounding = _validate_expected_grounding(
            raw["expected_grounding"],
            known_location_ids=known_location_ids,
            line_number=line_number,
        )
        records.append(
            GroundingDatasetRecord(
                id=record_id,
                text=_required_text(raw, "text", line_number=line_number),
                split=_required_text(raw, "split", line_number=line_number),
                source=_required_text(raw, "source", line_number=line_number),
                data_type=_required_text(raw, "data_type", line_number=line_number),
                expected_grounding=expected_grounding,
            )
        )

    if not records:
        raise ValueError("grounding dataset is empty")
    return records


def summarize_grounding_dataset(records: list[GroundingDatasetRecord]) -> GroundingDatasetSummary:
    """Summarize a validated grounding dataset."""

    split_counts = Counter(record.split for record in records)
    source_counts = Counter(record.source for record in records)
    data_type_counts = Counter(record.data_type for record in records)
    expected_field_counts: Counter[str] = Counter()
    expected_status_counts: Counter[str] = Counter()
    grounded_location_ids: set[str] = set()

    for record in records:
        for field_name, expected in record.expected_grounding.items():
            expected_field_counts[field_name] += 1
            status = str(expected["status"])
            expected_status_counts[status] += 1
            if expected.get("location_id"):
                grounded_location_ids.add(str(expected["location_id"]))

    warnings = _summary_warnings(records, expected_status_counts)
    return GroundingDatasetSummary(
        records=len(records),
        split_counts=dict(sorted(split_counts.items())),
        source_counts=dict(sorted(source_counts.items())),
        data_type_counts=dict(sorted(data_type_counts.items())),
        expected_field_counts=dict(sorted(expected_field_counts.items())),
        expected_status_counts=dict(sorted(expected_status_counts.items())),
        grounded_location_ids=sorted(grounded_location_ids),
        ambiguous_reference_count=expected_status_counts["ambiguous"],
        unresolved_reference_count=expected_status_counts["unresolved"],
        not_provided_reference_count=expected_status_counts["not_provided"],
        warnings=warnings,
    )


def _validate_expected_grounding(
    payload: Any,
    *,
    known_location_ids: set[str],
    line_number: int,
) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping) or not payload:
        raise ValueError(f"line {line_number}: expected_grounding must be a non-empty object")

    expected_grounding: dict[str, dict[str, Any]] = {}
    for field_name, expected in payload.items():
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValueError(f"line {line_number}: expected grounding field name must be non-empty")
        if not isinstance(expected, Mapping):
            raise ValueError(f"line {line_number}: expected grounding for {field_name} must be an object")
        missing = REQUIRED_EXPECTED_FIELDS - set(expected)
        if missing:
            raise ValueError(
                f"line {line_number}: expected grounding for {field_name} is missing: {', '.join(sorted(missing))}"
            )

        status = str(expected["status"])
        if status not in ALLOWED_EXPECTED_STATUSES:
            raise ValueError(f"line {line_number}: unsupported status for {field_name}: {status}")
        location_id = expected.get("location_id")
        if status == "grounded":
            if not isinstance(location_id, str) or not location_id.strip():
                raise ValueError(f"line {line_number}: grounded {field_name} requires a location_id")
            if location_id not in known_location_ids:
                raise ValueError(f"line {line_number}: unknown location_id for {field_name}: {location_id}")
        elif location_id is not None:
            raise ValueError(f"line {line_number}: non-grounded {field_name} must use null location_id")

        candidate_ids = expected.get("candidate_ids", [])
        if candidate_ids is None:
            candidate_ids = []
        if not isinstance(candidate_ids, list):
            raise ValueError(f"line {line_number}: candidate_ids for {field_name} must be a list")
        for candidate_id in candidate_ids:
            if candidate_id not in known_location_ids:
                raise ValueError(f"line {line_number}: unknown candidate_id for {field_name}: {candidate_id}")
        if status == "ambiguous" and len(candidate_ids) < 2:
            raise ValueError(f"line {line_number}: ambiguous {field_name} requires at least two candidate_ids")

        expected_grounding[field_name] = {
            "status": status,
            "location_id": location_id,
            "candidate_ids": candidate_ids,
        }
    return expected_grounding


def _required_text(record: Mapping[str, Any], key: str, *, line_number: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {key} must be a non-empty string")
    return value


def _summary_warnings(
    records: list[GroundingDatasetRecord],
    expected_status_counts: Counter[str],
) -> list[str]:
    warnings: list[str] = []
    if len({record.split for record in records}) == 1:
        warnings.append("single_split_dataset")
    if expected_status_counts["ambiguous"] == 0:
        warnings.append("no_ambiguous_examples")
    if expected_status_counts["unresolved"] == 0:
        warnings.append("no_unresolved_examples")
    return warnings
