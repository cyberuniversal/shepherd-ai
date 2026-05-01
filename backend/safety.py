from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


try:
    from shapely.geometry import LineString, Polygon
except Exception:
    LineString = None
    Polygon = None


MAX_ALTITUDE_M = 120.0
MIN_ALTITUDE_M = 1.0
RIYADH_LAT_RANGE = (24.3, 25.1)
RIYADH_LNG_RANGE = (46.3, 47.05)
METERS_PER_LAT_DEG = 111320.0
METERS_PER_LNG_DEG = 101100.0


@dataclass(frozen=True)
class ForbiddenZone:
    zone_id: str
    coordinates: List[Tuple[float, float]]
    zone_type: str = "no_fly_zone"


def _box_around(lat: float, lng: float, half_size_m: float) -> List[Tuple[float, float]]:
    dlat = half_size_m / METERS_PER_LAT_DEG
    dlng = half_size_m / METERS_PER_LNG_DEG
    return [
        (lat - dlat, lng - dlng),
        (lat - dlat, lng + dlng),
        (lat + dlat, lng + dlng),
        (lat + dlat, lng - dlng),
    ]


DEFAULT_FORBIDDEN_ZONES = [
    ForbiddenZone(
        "ministry_of_defense_cordon",
        _box_around(24.6644, 46.7126, 140.0),
        "restricted_cordon",
    ),
    ForbiddenZone(
        "embassy_quarter_cordon",
        _box_around(24.6810, 46.6238, 160.0),
        "restricted_cordon",
    ),
]


def _orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> int:
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else 2


def _on_segment(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
    return (
        min(a[0], c[0]) <= b[0] <= max(a[0], c[0])
        and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])
    )


def _segments_intersect(p1, q1, p2, q2) -> bool:
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, q1):
        return True
    if o2 == 0 and _on_segment(p1, q2, q1):
        return True
    if o3 == 0 and _on_segment(p2, p1, q2):
        return True
    if o4 == 0 and _on_segment(p2, q1, q2):
        return True
    return False


def _point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    x = point[1]
    y = point[0]
    inside = False
    j = len(polygon) - 1
    for i, vertex in enumerate(polygon):
        xi = vertex[1]
        yi = vertex[0]
        xj = polygon[j][1]
        yj = polygon[j][0]
        intersects = ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def _line_intersects_polygon_fallback(start, end, polygon) -> bool:
    if _point_in_polygon(start, polygon) or _point_in_polygon(end, polygon):
        return True

    closed = polygon + [polygon[0]]
    for index in range(len(closed) - 1):
        if _segments_intersect(start, end, closed[index], closed[index + 1]):
            return True
    return False


def _line_intersects_polygon(start, end, polygon) -> bool:
    if LineString and Polygon:
        line = LineString([(start[1], start[0]), (end[1], end[0])])
        shape = Polygon([(lng, lat) for lat, lng in polygon])
        return line.intersects(shape)
    return _line_intersects_polygon_fallback(start, end, polygon)


def _coordinate_in_riyadh_bounds(lat: float, lng: float) -> bool:
    return RIYADH_LAT_RANGE[0] <= lat <= RIYADH_LAT_RANGE[1] and RIYADH_LNG_RANGE[0] <= lng <= RIYADH_LNG_RANGE[1]


def validate_route_leg(
    drone_id: str,
    start: Tuple[float, float],
    end: Tuple[float, float],
    altitude_m: float,
    forbidden_zones: Optional[Iterable[ForbiddenZone]] = None,
) -> Dict:
    issues = []
    zones = list(forbidden_zones or DEFAULT_FORBIDDEN_ZONES)

    if not _coordinate_in_riyadh_bounds(end[0], end[1]):
        issues.append(f"{drone_id}: target coordinate outside Riyadh operating bounds")
    if altitude_m < MIN_ALTITUDE_M or altitude_m > MAX_ALTITUDE_M:
        issues.append(f"{drone_id}: altitude {altitude_m:.1f}m outside {MIN_ALTITUDE_M:.0f}-{MAX_ALTITUDE_M:.0f}m envelope")

    for zone in zones:
        if _line_intersects_polygon(start, end, zone.coordinates):
            issues.append(f"{drone_id}: route intersects {zone.zone_type} {zone.zone_id}")

    return {
        "passed": len(issues) == 0,
        "safe": len(issues) == 0,
        "issues": issues,
        "engine": "shapely" if LineString and Polygon else "fallback_geometry",
        "checks": [
            "coordinate bounds",
            "altitude envelope",
            "forbidden polygon intersection",
        ],
    }


def validate_mission_program(program: Dict, current_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict:
    issues = []
    checked_legs = 0
    current_positions = current_positions or {}

    for drone_program in program.get("drone_programs", []):
        drone_id = drone_program.get("drone_id", "unknown")
        current_pos = current_positions.get(drone_id)
        for step in drone_program.get("steps", []):
            op = step.get("op")
            if op == "TAKEOFF":
                altitude_m = float(step.get("altitude_m", 10.0))
                if altitude_m < MIN_ALTITUDE_M or altitude_m > MAX_ALTITUDE_M:
                    issues.append(f"{drone_id}: takeoff altitude {altitude_m:.1f}m outside safety envelope")
            elif op == "GOTO":
                end = (float(step["lat"]), float(step["lng"]))
                altitude_m = float(step.get("altitude_m", 10.0))
                if current_pos:
                    leg_result = validate_route_leg(drone_id, current_pos, end, altitude_m)
                    issues.extend(leg_result["issues"])
                    checked_legs += 1
                else:
                    if not _coordinate_in_riyadh_bounds(end[0], end[1]):
                        issues.append(f"{drone_id}: target coordinate outside Riyadh operating bounds")
                    if altitude_m < MIN_ALTITUDE_M or altitude_m > MAX_ALTITUDE_M:
                        issues.append(f"{drone_id}: altitude {altitude_m:.1f}m outside safety envelope")
                current_pos = end

    return {
        "passed": len(issues) == 0,
        "safe": len(issues) == 0,
        "issues": issues,
        "checked_legs": checked_legs,
        "engine": "shapely" if LineString and Polygon else "fallback_geometry",
        "checks": [
            "SHEPHERD-IR step scan",
            "takeoff altitude envelope",
            "GOTO coordinate bounds",
            "forbidden polygon route intersection",
        ],
    }
