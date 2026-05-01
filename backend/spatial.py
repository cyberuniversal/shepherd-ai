import math
from typing import Mapping


METERS_PER_LAT_DEG = 111320.0
METERS_PER_LNG_DEG = 101100.0


RELATIVE_DIRECTION_OFFSETS = {
    "front": 0.0,
    "ahead": 0.0,
    "left": -90.0,
    "right": 90.0,
    "behind": 180.0,
}


DIRECTION_TERMS = {
    "front": ["front of me", "in front", "ahead", "forward", "قدامي", "امامي", "أمامي"],
    "left": ["left of me", "to my left", "left side", "يساري", "على اليسار"],
    "right": ["right of me", "to my right", "right side", "يميني", "على اليمين"],
    "behind": ["behind me", "behind", "back of me", "خلفي", "ورائي"],
}


def normalize_heading(heading_deg: float) -> float:
    return float(heading_deg) % 360.0


def detect_relative_direction(text: str | None) -> str | None:
    if not text:
        return None

    lower = str(text).lower()
    for direction, terms in DIRECTION_TERMS.items():
        if any(term in lower for term in terms):
            return direction
    return None


def bearing_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    y = math.sin(delta_lon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon)
    return normalize_heading(math.degrees(math.atan2(y, x)))


def angular_delta(a: float, b: float) -> float:
    return abs((normalize_heading(a) - normalize_heading(b) + 180.0) % 360.0 - 180.0)


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = (lat2 - lat1) * METERS_PER_LAT_DEG
    dlon = (lon2 - lon1) * METERS_PER_LNG_DEG
    return math.hypot(dlat, dlon)


def resolve_relative_target(
    user_pos: tuple[float, float],
    user_heading: float,
    targets_db: Mapping[str, tuple[float, float]],
    direction: str = "front",
    cone_deg: float = 45.0,
) -> dict | None:
    user_lat, user_lon = user_pos
    offset = RELATIVE_DIRECTION_OFFSETS.get(direction, 0.0)
    target_heading = normalize_heading(user_heading + offset)
    half_cone = max(1.0, cone_deg / 2.0)
    candidates = []

    for name, coords in targets_db.items():
        lat, lon = coords
        distance_m = distance_meters(user_lat, user_lon, lat, lon)
        if distance_m < 10.0:
            continue

        bearing_deg = bearing_between(user_lat, user_lon, lat, lon)
        delta_deg = angular_delta(bearing_deg, target_heading)
        if delta_deg <= half_cone:
            candidates.append(
                {
                    "name": name,
                    "lat": lat,
                    "lng": lon,
                    "bearing_deg": round(bearing_deg, 1),
                    "delta_deg": round(delta_deg, 1),
                    "distance_m": round(distance_m, 1),
                    "direction": direction,
                    "target_heading_deg": round(target_heading, 1),
                }
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item["distance_m"], item["delta_deg"]))
    return candidates[0]
