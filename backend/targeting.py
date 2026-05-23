from typing import Dict


TARGET_METADATA_SCHEMA = "target_metadata/1.0"
TARGET_OBJECT_SCHEMA = "shepherd_target/1.0"


def apply_target_metadata(intent: Dict) -> Dict:
    """Add nested target contract while preserving legacy target_zone fields."""
    updated = dict(intent)
    _merge_existing_target(updated)
    metadata = infer_target_metadata(updated)
    updated.setdefault("target_raw_text", metadata["target_raw_text"])
    updated.setdefault("target_type", metadata["target_type"])
    updated.setdefault("target_resolution_required", metadata["target_resolution_required"])
    updated["target_resolution_required"] = _coerce_bool(updated["target_resolution_required"])
    updated.setdefault("target_metadata_schema", TARGET_METADATA_SCHEMA)
    updated["target"] = build_target_object(updated)
    return updated


def build_target_object(intent: Dict) -> Dict:
    metadata = infer_target_metadata(intent)
    target_reference = _clean_text(intent.get("target_reference")) or None
    target_coords = intent.get("target_coords")
    coords = None
    if isinstance(target_coords, dict) and {"lat", "lng"}.issubset(target_coords):
        coords = {"lat": target_coords["lat"], "lng": target_coords["lng"]}
    return {
        "schema": TARGET_OBJECT_SCHEMA,
        "type": intent.get("target_type") or metadata["target_type"],
        "raw_text": intent.get("target_raw_text") or metadata["target_raw_text"],
        "legacy_zone": _clean_text(intent.get("target_zone")) or "unknown",
        "reference": target_reference,
        "resolution_required": _coerce_bool(intent.get("target_resolution_required", metadata["target_resolution_required"])),
        "coords": coords,
    }


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


def _merge_existing_target(intent: Dict) -> None:
    target = intent.get("target")
    if not isinstance(target, dict):
        return
    raw_text = target.get("raw_text") or target.get("label") or target.get("name")
    if raw_text and not intent.get("target_raw_text"):
        intent["target_raw_text"] = _clean_text(raw_text)
    target_type = target.get("type")
    if target_type and not intent.get("target_type"):
        intent["target_type"] = _clean_text(target_type)
    if "resolution_required" in target and "target_resolution_required" not in intent:
        intent["target_resolution_required"] = _coerce_bool(target.get("resolution_required"))
    reference = target.get("reference")
    if reference and not intent.get("target_reference"):
        intent["target_reference"] = _clean_text(reference)
    coords = target.get("coords")
    if isinstance(coords, dict) and {"lat", "lng"}.issubset(coords) and not intent.get("target_coords"):
        intent["target_coords"] = {"lat": coords["lat"], "lng": coords["lng"]}
    legacy_zone = target.get("legacy_zone")
    if legacy_zone and not intent.get("target_zone"):
        intent["target_zone"] = _clean_text(legacy_zone)
    elif raw_text and not intent.get("target_zone"):
        intent["target_zone"] = _clean_text(raw_text)


def _clean_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = _clean_text(value)
        if normalized in {"false", "0", "no", "none", "null"}:
            return False
        if normalized in {"true", "1", "yes"}:
            return True
    return bool(value)
