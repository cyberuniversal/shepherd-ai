"""Apply explicit operator clarification choices to a grounded artifact."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import (  # noqa: E402
    GroundedIntent,
    GroundedReference,
    MapLocation,
    grounded_map_objects,
    load_map_locations,
)
from shepherd_ai.grounding_clarification import (  # noqa: E402
    apply_clarification_choices,
    build_clarification_report,
)


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grounded-json", type=Path, required=True)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument(
        "--choice",
        action="append",
        default=[],
        help="Operator choice in field=location_id form. May be repeated.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    grounded = _grounded_intent_from_payload(
        json.loads(args.grounded_json.read_text(encoding="utf-8"))
    )
    choices = _parse_choices(args.choice)
    resolved = apply_clarification_choices(grounded, choices, locations=locations)
    clarification = build_clarification_report(resolved)

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(args.map),
            "source_grounded_json": str(args.grounded_json),
            "note": "Week 3 operator-applied grounding clarification; original command text is preserved.",
        },
        "operator_choices": choices,
        "resolved_grounded_intent": resolved.to_dict(),
        "map_objects": [map_object.to_dict() for map_object in grounded_map_objects(resolved)],
        "clarification_report": clarification.to_dict(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "choices": len(choices),
                "remaining_requests": len(clarification.requests),
                "blocks_planning": clarification.blocks_planning,
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"Wrote {args.output}")


def _parse_choices(raw_choices: list[str]) -> dict[str, str]:
    choices: dict[str, str] = {}
    for raw_choice in raw_choices:
        if "=" not in raw_choice:
            raise ValueError("--choice must use field=location_id form")
        field, location_id = raw_choice.split("=", 1)
        field = field.strip()
        location_id = location_id.strip()
        if not field or not location_id:
            raise ValueError("--choice must include both field and location_id")
        choices[field] = location_id
    if not choices:
        raise ValueError("at least one --choice is required")
    return choices


def _grounded_intent_from_payload(payload: dict[str, Any]) -> GroundedIntent:
    grounded_payload = payload.get("grounded_intent", payload)
    references = tuple(
        _reference_from_dict(reference)
        for reference in grounded_payload.get("references", [])
    )
    return GroundedIntent(
        intent=dict(grounded_payload.get("intent", {})),
        references=references,
        ready_for_planning=bool(grounded_payload.get("ready_for_planning", False)),
        issues=tuple(grounded_payload.get("issues", [])),
    )


def _reference_from_dict(payload: dict[str, Any]) -> GroundedReference:
    return GroundedReference(
        field=payload["field"],
        phrase=payload.get("phrase"),
        status=payload["status"],
        location=_location_from_dict(payload.get("location")),
        candidates=tuple(
            location
            for location in (_location_from_dict(candidate) for candidate in payload.get("candidates", []))
            if location is not None
        ),
        confidence=float(payload.get("confidence", 0.0)),
        note=payload.get("note"),
    )


def _location_from_dict(payload: dict[str, Any] | None) -> MapLocation | None:
    if payload is None:
        return None
    return MapLocation(
        id=payload["id"],
        name=payload["name"],
        category=payload["category"],
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        radius_m=float(payload["radius_m"]),
        geometry_type=payload.get("geometry_type", "circle"),
        map_role=payload.get("map_role", "mission_area"),
        flyable=bool(payload.get("flyable", True)),
        requires_clearance=bool(payload.get("requires_clearance", False)),
        aliases=tuple(payload.get("aliases", [])),
        source=payload.get("source", ""),
        split=payload.get("split", ""),
    )


if __name__ == "__main__":
    main()
