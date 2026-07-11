"""Coverage reporting for Week 3 grounding datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from shepherd_ai.grounding import MapLocation
from shepherd_ai.grounding_dataset import GroundingDatasetRecord


@dataclass(frozen=True)
class GroundingCoverageReport:
    """How much of a map is exercised by grounding evaluation datasets."""

    map_records: int
    dataset_records: int
    reference_count: int
    grounded_location_ids: list[str]
    candidate_location_ids: list[str]
    covered_location_ids: list[str]
    untested_location_ids: list[str]
    untested_by_role: dict[str, list[str]]
    status_counts: dict[str, int]
    field_counts: dict[str, int]
    role_coverage: dict[str, dict[str, Any]]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_records": self.map_records,
            "dataset_records": self.dataset_records,
            "reference_count": self.reference_count,
            "grounded_location_ids": self.grounded_location_ids,
            "candidate_location_ids": self.candidate_location_ids,
            "covered_location_ids": self.covered_location_ids,
            "untested_location_ids": self.untested_location_ids,
            "untested_by_role": self.untested_by_role,
            "status_counts": self.status_counts,
            "field_counts": self.field_counts,
            "role_coverage": self.role_coverage,
            "warnings": self.warnings,
        }


def build_grounding_coverage_report(
    locations: list[MapLocation],
    datasets: list[list[GroundingDatasetRecord]],
) -> GroundingCoverageReport:
    """Build coverage report from validated grounding datasets."""

    records = [record for dataset in datasets for record in dataset]
    location_by_id = {location.id: location for location in locations}
    grounded_location_ids: set[str] = set()
    candidate_location_ids: set[str] = set()
    status_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()

    for record in records:
        for field_name, expected in record.expected_grounding.items():
            field_counts[field_name] += 1
            status = str(expected["status"])
            status_counts[status] += 1
            if expected.get("location_id"):
                grounded_location_ids.add(str(expected["location_id"]))
            candidate_location_ids.update(str(candidate_id) for candidate_id in expected.get("candidate_ids", []))

    covered_location_ids = grounded_location_ids | candidate_location_ids
    map_location_ids = set(location_by_id)
    untested_location_ids = sorted(map_location_ids - covered_location_ids)
    role_coverage = _role_coverage(locations, covered_location_ids)
    untested_by_role = _untested_by_role(locations, untested_location_ids)
    warnings = _warnings(
        locations=locations,
        records=records,
        untested_location_ids=untested_location_ids,
        status_counts=status_counts,
        role_coverage=role_coverage,
    )

    return GroundingCoverageReport(
        map_records=len(locations),
        dataset_records=len(records),
        reference_count=sum(status_counts.values()),
        grounded_location_ids=sorted(grounded_location_ids),
        candidate_location_ids=sorted(candidate_location_ids),
        covered_location_ids=sorted(covered_location_ids),
        untested_location_ids=untested_location_ids,
        untested_by_role=untested_by_role,
        status_counts=dict(sorted(status_counts.items())),
        field_counts=dict(sorted(field_counts.items())),
        role_coverage=role_coverage,
        warnings=warnings,
    )


def render_grounding_coverage_markdown(report: GroundingCoverageReport, *, map_path: str) -> str:
    """Render a Markdown report for map coverage by grounding datasets."""

    payload = report.to_dict()
    lines = [
        "# Week 3 Grounding Coverage Report",
        "",
        f"Map: `{map_path}`",
        "",
        "This report audits synthetic grounding dataset coverage. It is not real-world grounding accuracy and not a planning or safety result.",
        "",
        "## Summary",
        "",
        f"- Map records: {payload['map_records']}",
        f"- Dataset records: {payload['dataset_records']}",
        f"- Expected references: {payload['reference_count']}",
        f"- Covered map records: {len(payload['covered_location_ids'])}",
        f"- Untested map records: {len(payload['untested_location_ids'])}",
        "",
        "## Status Counts",
        "",
        *_format_counts(payload["status_counts"]),
        "",
        "## Field Counts",
        "",
        *_format_counts(payload["field_counts"]),
        "",
        "## Role Coverage",
        "",
    ]
    for role, coverage in payload["role_coverage"].items():
        lines.append(
            f"- `{role}`: {coverage['covered']} / {coverage['total']} covered; "
            f"untested {coverage['untested_location_ids']}"
        )

    lines.extend(["", "## Untested Location IDs", ""])
    if payload["untested_location_ids"]:
        lines.extend(f"- `{location_id}`" for location_id in payload["untested_location_ids"])
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if payload["warnings"]:
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _role_coverage(
    locations: list[MapLocation],
    covered_location_ids: set[str],
) -> dict[str, dict[str, Any]]:
    locations_by_role: dict[str, list[MapLocation]] = defaultdict(list)
    for location in locations:
        locations_by_role[location.map_role].append(location)

    coverage: dict[str, dict[str, Any]] = {}
    for role, role_locations in sorted(locations_by_role.items()):
        role_ids = {location.id for location in role_locations}
        covered = sorted(role_ids & covered_location_ids)
        untested = sorted(role_ids - covered_location_ids)
        coverage[role] = {
            "total": len(role_ids),
            "covered": len(covered),
            "covered_location_ids": covered,
            "untested_location_ids": untested,
        }
    return coverage


def _untested_by_role(
    locations: list[MapLocation],
    untested_location_ids: list[str],
) -> dict[str, list[str]]:
    location_by_id = {location.id: location for location in locations}
    by_role: dict[str, list[str]] = defaultdict(list)
    for location_id in untested_location_ids:
        by_role[location_by_id[location_id].map_role].append(location_id)
    return {role: ids for role, ids in sorted(by_role.items())}


def _warnings(
    *,
    locations: list[MapLocation],
    records: list[GroundingDatasetRecord],
    untested_location_ids: list[str],
    status_counts: Counter[str],
    role_coverage: dict[str, dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if not records:
        warnings.append("no_dataset_records")
    if untested_location_ids:
        warnings.append("map_records_without_grounding_coverage")
    if status_counts["ambiguous"] == 0:
        warnings.append("no_ambiguous_grounding_coverage")
    if status_counts["unresolved"] == 0:
        warnings.append("no_unresolved_grounding_coverage")
    for role, coverage in role_coverage.items():
        if coverage["covered"] == 0:
            warnings.append(f"role_without_grounding_coverage:{role}")
    if any(location.map_role == "obstacle" for location in locations) and role_coverage.get("obstacle", {}).get("covered", 0) == 0:
        warnings.append("obstacle_records_without_grounding_coverage")
    if any(location.map_role == "restricted_area" for location in locations) and role_coverage.get("restricted_area", {}).get("covered", 0) == 0:
        warnings.append("restricted_records_without_grounding_coverage")
    return warnings


def _format_counts(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in counts.items()]
