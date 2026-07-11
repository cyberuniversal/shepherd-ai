"""Command grounding against explicit map records.

Grounding is intentionally deterministic at this stage. The literature review
warns against treating semantic grounding as solved, so this module accepts
normalized name or alias matches inside bounded intent fields and reports
unresolved or ambiguous phrases explicitly.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from shepherd_ai.intent import MissionIntent


REQUIRED_MAP_COLUMNS = {
    "id",
    "name",
    "category",
    "latitude",
    "longitude",
    "radius_m",
    "geometry_type",
    "map_role",
    "flyable",
    "requires_clearance",
    "aliases",
    "source",
    "split",
}

SUPPORTED_GEOMETRY_TYPES = {"circle", "polygon"}
CONSTRAINT_MAP_TRIGGERS = (
    "avoid",
    "without entering",
    "without crossing",
    "near",
    "above",
    "over",
    "return to",
    "back to",
)


@dataclass(frozen=True)
class MapLocation:
    """A named map location that can be grounded from language."""

    id: str
    name: str
    category: str
    latitude: float
    longitude: float
    radius_m: float
    geometry_type: str = "circle"
    map_role: str = "mission_area"
    flyable: bool = True
    requires_clearance: bool = False
    aliases: tuple[str, ...] = field(default_factory=tuple)
    source: str = ""
    split: str = ""
    boundary: tuple[tuple[float, float], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["aliases"] = list(self.aliases)
        payload["boundary"] = [
            {"latitude": latitude, "longitude": longitude}
            for latitude, longitude in self.boundary
        ]
        return payload


@dataclass(frozen=True)
class GroundedReference:
    """Grounding result for one intent field such as location or target."""

    field: str
    phrase: str | None
    status: str
    location: MapLocation | None = None
    candidates: tuple[MapLocation, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "phrase": self.phrase,
            "status": self.status,
            "location": self.location.to_dict() if self.location else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "confidence": self.confidence,
            "note": self.note,
        }


@dataclass(frozen=True)
class GroundedIntent:
    """Grounded intent output consumed by later planning milestones."""

    intent: dict[str, Any]
    references: tuple[GroundedReference, ...]
    ready_for_planning: bool
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "references": [reference.to_dict() for reference in self.references],
            "ready_for_planning": self.ready_for_planning,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class GroundedMapObject:
    """Planner-facing map object extracted from a grounded reference."""

    reference_field: str
    phrase: str | None
    location_id: str
    name: str
    category: str
    map_role: str
    geometry_type: str
    center: dict[str, float]
    radius_m: float
    flyable: bool
    requires_clearance: bool
    boundary: tuple[tuple[float, float], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["boundary"] = [
            {"latitude": latitude, "longitude": longitude}
            for latitude, longitude in self.boundary
        ]
        return payload


def load_map_locations(path: str | Path) -> list[MapLocation]:
    """Load and validate map locations from a CSV or GeoJSON file."""

    map_path = Path(path)
    suffix = map_path.suffix.lower()
    if suffix in {".geojson", ".json"}:
        return load_map_locations_geojson(map_path)
    return load_map_locations_csv(map_path)


def load_map_locations_csv(path: str | Path) -> list[MapLocation]:
    """Load and validate map locations from a CSV file."""

    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("map CSV must include a header row")
        missing = REQUIRED_MAP_COLUMNS - set(reader.fieldnames)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"map CSV is missing required columns: {missing_text}")

        locations: list[MapLocation] = []
        seen_ids: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            location = _location_from_row(row, line_number=line_number)
            if location.id in seen_ids:
                raise ValueError(f"duplicate map location id on line {line_number}: {location.id}")
            seen_ids.add(location.id)
            locations.append(location)

    if not locations:
        raise ValueError("map CSV must contain at least one location")
    return locations


def load_map_locations_geojson(path: str | Path) -> list[MapLocation]:
    """Load and validate map locations from a GeoJSON FeatureCollection.

    The current Week 3 model supports Point features with a `radius_m`
    property, representing circular regions. Polygon geometry is intentionally
    not implemented yet.
    """

    geojson_path = Path(path)
    payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError("map GeoJSON must be a FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("map GeoJSON must include a features list")

    locations: list[MapLocation] = []
    seen_ids: set[str] = set()
    for index, feature in enumerate(features, start=1):
        location = _location_from_geojson_feature(feature, feature_number=index)
        if location.id in seen_ids:
            raise ValueError(f"duplicate map location id in feature {index}: {location.id}")
        seen_ids.add(location.id)
        locations.append(location)

    if not locations:
        raise ValueError("map GeoJSON must contain at least one feature")
    return locations


def ground_phrase(
    phrase: str | None,
    locations: Iterable[MapLocation],
    *,
    field_name: str = "location",
) -> GroundedReference:
    """Ground one phrase by normalized name or alias match."""

    if phrase is None or not str(phrase).strip():
        return GroundedReference(
            field=field_name,
            phrase=None,
            status="not_provided",
            note="no phrase provided for this intent field",
        )

    normalized_phrase = normalize_grounding_phrase(str(phrase))
    matches = [
        location
        for location in locations
        if normalized_phrase in _location_terms(location)
    ]

    if len(matches) == 1:
        match = matches[0]
        confidence = 1.0 if normalized_phrase == normalize_grounding_phrase(match.name) else 0.9
        return GroundedReference(
            field=field_name,
            phrase=str(phrase),
            status="grounded",
            location=match,
            confidence=confidence,
        )
    if len(matches) > 1:
        return GroundedReference(
            field=field_name,
            phrase=str(phrase),
            status="ambiguous",
            candidates=tuple(matches),
            note="phrase matched multiple map records",
        )

    contained_matches = _locations_mentioned_in_phrase(normalized_phrase, locations)
    if len(contained_matches) == 1:
        return GroundedReference(
            field=field_name,
            phrase=str(phrase),
            status="grounded",
            location=contained_matches[0],
            confidence=0.75,
            note="map name or alias found inside a larger phrase",
        )
    if len(contained_matches) > 1:
        return GroundedReference(
            field=field_name,
            phrase=str(phrase),
            status="ambiguous",
            candidates=tuple(contained_matches),
            note="larger phrase matched multiple map records",
        )

    return GroundedReference(
        field=field_name,
        phrase=str(phrase),
        status="unresolved",
        note="phrase did not match any map name or alias",
    )


def ground_intent(intent: MissionIntent | Mapping[str, Any], locations: Iterable[MapLocation]) -> GroundedIntent:
    """Ground the location and target fields from a mission intent."""

    map_locations = list(locations)
    intent_dict = intent.to_dict() if isinstance(intent, MissionIntent) else dict(intent)
    references = (
        ground_phrase(intent_dict.get("location"), map_locations, field_name="location"),
        ground_phrase(intent_dict.get("target"), map_locations, field_name="target"),
        *_ground_constraint_references(intent_dict.get("constraints", []), map_locations),
    )
    issues = tuple(_issues_for_references(references))
    has_grounded_reference = any(reference.status == "grounded" for reference in references)
    has_ambiguity = any(reference.status == "ambiguous" for reference in references)
    issues = issues + tuple(_map_role_issues(references))
    ready_for_planning = has_grounded_reference and not has_ambiguity

    if not has_grounded_reference:
        issues = issues + ("no_grounded_map_reference",)

    return GroundedIntent(
        intent=intent_dict,
        references=references,
        ready_for_planning=ready_for_planning,
        issues=issues,
    )


def grounded_map_objects(grounded_intent: GroundedIntent) -> list[GroundedMapObject]:
    """Return grounded references as explicit map objects for later modules.

    This is a data-shaping step only. It does not plan routes, allocate drones,
    or approve safety constraints.
    """

    objects: list[GroundedMapObject] = []
    for reference in grounded_intent.references:
        if reference.status != "grounded" or reference.location is None:
            continue
        location = reference.location
        objects.append(
            GroundedMapObject(
                reference_field=reference.field,
                phrase=reference.phrase,
                location_id=location.id,
                name=location.name,
                category=location.category,
                map_role=location.map_role,
                geometry_type=location.geometry_type,
                center={"latitude": location.latitude, "longitude": location.longitude},
                radius_m=location.radius_m,
                boundary=location.boundary,
                flyable=location.flyable,
                requires_clearance=location.requires_clearance,
            )
        )
    return objects


def normalize_grounding_phrase(phrase: str) -> str:
    """Normalize a phrase for deterministic exact grounding."""

    normalized = phrase.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"^(?:the|a|an)\s+", "", normalized)
    return normalized


def _ground_constraint_references(
    constraints: Any,
    locations: Iterable[MapLocation],
) -> tuple[GroundedReference, ...]:
    if not isinstance(constraints, list):
        return ()

    references: list[GroundedReference] = []
    map_locations = list(locations)
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, str) or not constraint.strip():
            continue
        reference = _ground_constraint_phrase(
            constraint,
            map_locations,
            field_name=f"constraint[{index}]",
        )
        if reference is not None:
            references.append(reference)
    return tuple(references)


def _ground_constraint_phrase(
    phrase: str,
    locations: Iterable[MapLocation],
    *,
    field_name: str,
) -> GroundedReference | None:
    normalized_phrase = normalize_grounding_phrase(phrase)
    matches = _locations_mentioned_in_phrase(normalized_phrase, locations)

    if len(matches) == 1:
        return GroundedReference(
            field=field_name,
            phrase=phrase,
            status="grounded",
            location=matches[0],
            confidence=0.8,
            note="map reference found inside constraint phrase",
        )
    if len(matches) > 1:
        return GroundedReference(
            field=field_name,
            phrase=phrase,
            status="ambiguous",
            candidates=tuple(matches),
            note="constraint phrase matched multiple map records",
        )
    if _constraint_has_map_trigger(normalized_phrase):
        return GroundedReference(
            field=field_name,
            phrase=phrase,
            status="unresolved",
            note="constraint may reference a map location, but no map record matched",
        )
    return None


def _location_from_row(row: Mapping[str, str], *, line_number: int) -> MapLocation:
    location_id = _required_text(row, "id", line_number=line_number)
    name = _required_text(row, "name", line_number=line_number)
    category = _required_text(row, "category", line_number=line_number)
    latitude = _required_float(row, "latitude", line_number=line_number)
    longitude = _required_float(row, "longitude", line_number=line_number)
    radius_m = _required_float(row, "radius_m", line_number=line_number)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive on line {line_number}")
    geometry_type = _required_text(row, "geometry_type", line_number=line_number)
    if geometry_type not in SUPPORTED_GEOMETRY_TYPES:
        raise ValueError(f"unsupported geometry_type on line {line_number}: {geometry_type}")
    flyable = _required_bool(row, "flyable", line_number=line_number)
    requires_clearance = _required_bool(row, "requires_clearance", line_number=line_number)
    aliases = tuple(
        alias.strip()
        for alias in row.get("aliases", "").split("|")
        if alias.strip()
    )
    return MapLocation(
        id=location_id,
        name=name,
        category=category,
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        geometry_type=geometry_type,
        map_role=_required_text(row, "map_role", line_number=line_number),
        flyable=flyable,
        requires_clearance=requires_clearance,
        aliases=aliases,
        source=_required_text(row, "source", line_number=line_number),
        split=_required_text(row, "split", line_number=line_number),
    )


def _location_from_geojson_feature(feature: Mapping[str, Any], *, feature_number: int) -> MapLocation:
    if feature.get("type") != "Feature":
        raise ValueError(f"GeoJSON item {feature_number} must be a Feature")
    geometry = feature.get("geometry")
    if not isinstance(geometry, Mapping):
        raise ValueError(f"GeoJSON feature {feature_number} must include geometry")
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError(f"GeoJSON feature {feature_number} must include properties")

    row = {key: str(properties.get(key, "")) for key in REQUIRED_MAP_COLUMNS}
    aliases = properties.get("aliases", "")
    if isinstance(aliases, list):
        row["aliases"] = "|".join(str(alias) for alias in aliases)

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ValueError(f"GeoJSON feature {feature_number} must include [longitude, latitude]")
        row["longitude"] = str(coordinates[0])
        row["latitude"] = str(coordinates[1])
        row["geometry_type"] = row["geometry_type"] or "circle"
        return _location_from_row(row, line_number=feature_number)

    if geometry_type == "Polygon":
        boundary = _polygon_boundary(coordinates, feature_number=feature_number)
        center_latitude, center_longitude = _boundary_centroid(boundary)
        row["latitude"] = str(center_latitude)
        row["longitude"] = str(center_longitude)
        row["geometry_type"] = "polygon"
        if not row["radius_m"]:
            row["radius_m"] = str(_boundary_radius_m(center_latitude, center_longitude, boundary))
        location = _location_from_row(row, line_number=feature_number)
        return MapLocation(
            id=location.id,
            name=location.name,
            category=location.category,
            latitude=location.latitude,
            longitude=location.longitude,
            radius_m=location.radius_m,
            geometry_type=location.geometry_type,
            map_role=location.map_role,
            flyable=location.flyable,
            requires_clearance=location.requires_clearance,
            aliases=location.aliases,
            source=location.source,
            split=location.split,
            boundary=boundary,
        )

    raise ValueError(f"GeoJSON feature {feature_number} must use Point or Polygon geometry")


def _required_text(row: Mapping[str, str], key: str, *, line_number: int) -> str:
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"{key} is required on line {line_number}")
    return value


def _required_float(row: Mapping[str, str], key: str, *, line_number: int) -> float:
    value = _required_text(row, key, line_number=line_number)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be numeric on line {line_number}") from exc


def _required_bool(row: Mapping[str, str], key: str, *, line_number: int) -> bool:
    value = _required_text(row, key, line_number=line_number).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{key} must be true or false on line {line_number}")


def _location_terms(location: MapLocation) -> set[str]:
    return {
        normalize_grounding_phrase(term)
        for term in (location.name, *location.aliases)
        if term
    }


def _locations_mentioned_in_phrase(
    normalized_phrase: str,
    locations: Iterable[MapLocation],
) -> tuple[MapLocation, ...]:
    scored_matches: list[tuple[int, MapLocation]] = []
    for location in locations:
        matching_terms = [
            term
            for term in _location_terms(location)
            if _normalized_phrase_contains_term(normalized_phrase, term)
        ]
        if matching_terms:
            scored_matches.append((max(len(term.split()) for term in matching_terms), location))

    if not scored_matches:
        return ()

    longest_match = max(score for score, _ in scored_matches)
    return tuple(location for score, location in scored_matches if score == longest_match)


def _normalized_phrase_contains_term(normalized_phrase: str, normalized_term: str) -> bool:
    return re.search(rf"(?:^|\s){re.escape(normalized_term)}(?:\s|$)", normalized_phrase) is not None


def _constraint_has_map_trigger(normalized_phrase: str) -> bool:
    return any(
        _normalized_phrase_contains_term(normalized_phrase, trigger)
        for trigger in CONSTRAINT_MAP_TRIGGERS
    )


def _polygon_boundary(coordinates: Any, *, feature_number: int) -> tuple[tuple[float, float], ...]:
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError(f"GeoJSON polygon feature {feature_number} must include coordinate rings")
    exterior = coordinates[0]
    if not isinstance(exterior, list) or len(exterior) < 4:
        raise ValueError(f"GeoJSON polygon feature {feature_number} exterior ring must contain at least four points")

    boundary: list[tuple[float, float]] = []
    for point in exterior:
        if not isinstance(point, list) or len(point) < 2:
            raise ValueError(f"GeoJSON polygon feature {feature_number} must use [longitude, latitude] points")
        boundary.append((float(point[1]), float(point[0])))

    if boundary[0] == boundary[-1]:
        boundary = boundary[:-1]
    if len(boundary) < 3:
        raise ValueError(f"GeoJSON polygon feature {feature_number} exterior ring must define at least three vertices")
    return tuple(boundary)


def _boundary_centroid(boundary: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    return (
        sum(latitude for latitude, _ in boundary) / len(boundary),
        sum(longitude for _, longitude in boundary) / len(boundary),
    )


def _boundary_radius_m(
    center_latitude: float,
    center_longitude: float,
    boundary: tuple[tuple[float, float], ...],
) -> float:
    return max(
        _haversine_m(center_latitude, center_longitude, latitude, longitude)
        for latitude, longitude in boundary
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _issues_for_references(references: Iterable[GroundedReference]) -> list[str]:
    issues: list[str] = []
    for reference in references:
        if reference.status == "ambiguous":
            issues.append(f"{reference.field}_ambiguous")
        elif reference.status == "unresolved":
            issues.append(f"{reference.field}_unresolved")
    return issues


def _map_role_issues(references: Iterable[GroundedReference]) -> list[str]:
    issues: list[str] = []
    for reference in references:
        if reference.status != "grounded" or reference.location is None:
            continue
        if not reference.location.flyable:
            issues.append(f"{reference.field}_not_flyable")
        if reference.location.requires_clearance:
            issues.append(f"{reference.field}_requires_clearance")
    return issues
