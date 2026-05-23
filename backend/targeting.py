from typing import Dict


TARGET_METADATA_SCHEMA = "target_metadata/1.0"


def apply_target_metadata(intent: Dict) -> Dict:
    """Add backward-compatible target span metadata beside legacy target_zone."""
    updated = dict(intent)
    metadata = infer_target_metadata(updated)
    updated.setdefault("target_raw_text", metadata["target_raw_text"])
    updated.setdefault("target_type", metadata["target_type"])
    updated.setdefault("target_resolution_required", metadata["target_resolution_required"])
    updated.setdefault("target_metadata_schema", TARGET_METADATA_SCHEMA)
    return updated


def infer_target_metadata(intent: Dict) -> Dict:
    target_zone = _clean_text(intent.get("target_zone"))
    target_reference = _clean_text(intent.get("target_reference"))
    target_coords = intent.get("target_coords")

    if isinstance(target_coords, dict) and {"lat", "lng"}.issubset(target_coords):
        return _metadata(
            raw_text=f"{target_coords['lat']}, {target_coords['lng']}",
            target_type="coordinates",
            resolution_required=False,
        )

    if target_reference == "operator":
        return _metadata(
            raw_text=target_zone or "operator_current_position",
            target_type="operator_reference",
            resolution_required=True,
        )

    if target_reference == "operator_relative":
        return _metadata(
            raw_text=target_zone or "operator_relative",
            target_type="operator_relative",
            resolution_required=True,
        )

    if target_zone == "home":
        return _metadata(raw_text="home", target_type="home", resolution_required=False)

    if target_zone == "current_position":
        return _metadata(raw_text="current_position", target_type="current_position", resolution_required=False)

    if target_zone == "coordinates":
        return _metadata(raw_text="coordinates", target_type="coordinates", resolution_required=False)

    if target_zone == "multi_target":
        return _metadata(raw_text="multi_target", target_type="multi_target", resolution_required=True)

    if target_zone == "route_between_known_zones":
        return _metadata(raw_text="route_between_known_zones", target_type="route", resolution_required=True)

    if target_zone in {"", "unknown", "undefined", "none", "null"}:
        return _metadata(raw_text="unknown", target_type="unknown", resolution_required=True)

    return _metadata(raw_text=target_zone, target_type="place_name", resolution_required=True)


def _metadata(*, raw_text: str, target_type: str, resolution_required: bool) -> Dict:
    return {
        "target_raw_text": raw_text,
        "target_type": target_type,
        "target_resolution_required": bool(resolution_required),
    }


def _clean_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())
