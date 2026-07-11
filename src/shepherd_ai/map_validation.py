"""Validation and audit reporting for Shepherd-AI map datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from shepherd_ai.grounding import MapLocation, normalize_grounding_phrase


@dataclass(frozen=True)
class MapValidationReport:
    """Structured audit report for one map dataset."""

    records: int
    category_counts: dict[str, int]
    role_counts: dict[str, int]
    geometry_counts: dict[str, int]
    split_counts: dict[str, int]
    flyable_counts: dict[str, int]
    clearance_counts: dict[str, int]
    ambiguous_terms: list[dict[str, Any]] = field(default_factory=list)
    restricted_records: list[dict[str, Any]] = field(default_factory=list)
    obstacle_records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "category_counts": self.category_counts,
            "role_counts": self.role_counts,
            "geometry_counts": self.geometry_counts,
            "split_counts": self.split_counts,
            "flyable_counts": self.flyable_counts,
            "clearance_counts": self.clearance_counts,
            "ambiguous_terms": self.ambiguous_terms,
            "restricted_records": self.restricted_records,
            "obstacle_records": self.obstacle_records,
            "warnings": self.warnings,
        }


def validate_map_locations(locations: Iterable[MapLocation]) -> MapValidationReport:
    """Summarize map structure and known grounding hazards."""

    map_locations = list(locations)
    category_counts = Counter(location.category for location in map_locations)
    role_counts = Counter(location.map_role for location in map_locations)
    geometry_counts = Counter(location.geometry_type for location in map_locations)
    split_counts = Counter(location.split for location in map_locations)
    flyable_counts = Counter(str(location.flyable).lower() for location in map_locations)
    clearance_counts = Counter(str(location.requires_clearance).lower() for location in map_locations)

    ambiguous_terms = _ambiguous_terms(map_locations)
    restricted_records = [
        _location_summary(location)
        for location in map_locations
        if location.map_role == "restricted_area" or location.category == "restricted_area"
    ]
    obstacle_records = [
        _location_summary(location)
        for location in map_locations
        if location.map_role == "obstacle" or location.category == "obstacle"
    ]
    warnings = _warnings(map_locations, ambiguous_terms)

    return MapValidationReport(
        records=len(map_locations),
        category_counts=dict(sorted(category_counts.items())),
        role_counts=dict(sorted(role_counts.items())),
        geometry_counts=dict(sorted(geometry_counts.items())),
        split_counts=dict(sorted(split_counts.items())),
        flyable_counts=dict(sorted(flyable_counts.items())),
        clearance_counts=dict(sorted(clearance_counts.items())),
        ambiguous_terms=ambiguous_terms,
        restricted_records=restricted_records,
        obstacle_records=obstacle_records,
        warnings=warnings,
    )


def render_map_validation_markdown(report: MapValidationReport, *, map_path: str) -> str:
    """Render a concise Markdown version of a map validation report."""

    lines = [
        "# Week 3 Map Validation Report",
        "",
        f"Map: `{map_path}`",
        "",
        "This report audits the explicit map dataset used for deterministic grounding. It is not a safety certificate and does not validate route feasibility.",
        "",
        "## Summary",
        "",
        f"- Records: {report.records}",
        f"- Ambiguous grounding terms: {len(report.ambiguous_terms)}",
        f"- Restricted records: {len(report.restricted_records)}",
        f"- Obstacle records: {len(report.obstacle_records)}",
        f"- Warnings: {len(report.warnings)}",
        "",
        "## Counts",
        "",
        _format_counts("Categories", report.category_counts),
        "",
        _format_counts("Map roles", report.role_counts),
        "",
        _format_counts("Geometry types", report.geometry_counts),
        "",
        _format_counts("Flyable", report.flyable_counts),
        "",
        _format_counts("Requires clearance", report.clearance_counts),
        "",
        "## Ambiguous Terms",
        "",
    ]
    if report.ambiguous_terms:
        lines.extend(
            f"- `{term['term']}` -> {', '.join(term['location_ids'])}"
            for term in report.ambiguous_terms
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Restricted Records", ""])
    if report.restricted_records:
        lines.extend(_format_location_lines(report.restricted_records))
    else:
        lines.append("- None")

    lines.extend(["", "## Obstacle Records", ""])
    if report.obstacle_records:
        lines.extend(_format_location_lines(report.obstacle_records))
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _ambiguous_terms(locations: list[MapLocation]) -> list[dict[str, Any]]:
    term_locations: dict[str, list[MapLocation]] = defaultdict(list)
    for location in locations:
        terms = {normalize_grounding_phrase(location.name)}
        terms.update(normalize_grounding_phrase(alias) for alias in location.aliases)
        for term in terms:
            if term:
                term_locations[term].append(location)

    ambiguous = []
    for term, matches in sorted(term_locations.items()):
        if len(matches) <= 1:
            continue
        ambiguous.append(
            {
                "term": term,
                "location_ids": [location.id for location in matches],
                "names": [location.name for location in matches],
                "categories": [location.category for location in matches],
                "map_roles": [location.map_role for location in matches],
            }
        )
    return ambiguous


def _location_summary(location: MapLocation) -> dict[str, Any]:
    return {
        "id": location.id,
        "name": location.name,
        "category": location.category,
        "map_role": location.map_role,
        "flyable": location.flyable,
        "requires_clearance": location.requires_clearance,
    }


def _warnings(locations: list[MapLocation], ambiguous_terms: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if ambiguous_terms:
        warnings.append("ambiguous_terms_require_clarification_before_planning")
    if not any(location.map_role == "base" for location in locations):
        warnings.append("no_base_location_defined")
    for location in locations:
        if not location.flyable and not location.requires_clearance:
            warnings.append(f"{location.id}_not_flyable_without_clearance_flag")
        if location.map_role in {"restricted_area", "obstacle"} and location.flyable:
            warnings.append(f"{location.id}_hazard_role_marked_flyable")
        if location.requires_clearance and location.flyable:
            warnings.append(f"{location.id}_requires_clearance_but_marked_flyable")
    return warnings


def _format_counts(title: str, counts: dict[str, int]) -> str:
    if not counts:
        return f"### {title}\n\n- None"
    lines = [f"### {title}", ""]
    lines.extend(f"- `{key}`: {value}" for key, value in counts.items())
    return "\n".join(lines)


def _format_location_lines(records: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"- `{record['id']}` ({record['name']}): role `{record['map_role']}`, "
            f"flyable `{str(record['flyable']).lower()}`, "
            f"requires_clearance `{str(record['requires_clearance']).lower()}`"
        )
        for record in records
    ]
