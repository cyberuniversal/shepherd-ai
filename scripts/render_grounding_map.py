"""Render Shepherd-AI map locations and optional grounding output as HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import GroundedIntent, GroundedReference, MapLocation, ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.map_visualization import render_map  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "maps" / "shepherd_test_map_v1.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--command", help="Typed command to parse, ground, and highlight.")
    source.add_argument("--grounded-json", type=Path, help="JSON output from scripts/ground_intent.py.")
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    grounded = _load_grounded_intent(args, locations)
    output = render_map(locations, args.output, grounded_intent=grounded)
    print(f"Wrote {output}")


def _load_grounded_intent(args: argparse.Namespace, locations: list[MapLocation]) -> GroundedIntent | None:
    if args.command:
        return ground_intent(parse_intent(args.command), locations)
    if args.grounded_json:
        payload = json.loads(args.grounded_json.read_text(encoding="utf-8"))
        grounded_payload = payload.get("grounded_intent", payload)
        return _grounded_intent_from_dict(grounded_payload)
    return None


def _grounded_intent_from_dict(payload: dict[str, Any]) -> GroundedIntent:
    references = []
    for reference in payload.get("references", []):
        location = _location_from_dict(reference.get("location"))
        candidates = tuple(
            _location_from_dict(candidate)
            for candidate in reference.get("candidates", [])
            if candidate is not None
        )
        references.append(
            GroundedReference(
                field=reference["field"],
                phrase=reference.get("phrase"),
                status=reference["status"],
                location=location,
                candidates=candidates,
                confidence=float(reference.get("confidence", 0.0)),
                note=reference.get("note"),
            )
        )
    return GroundedIntent(
        intent=dict(payload.get("intent", {})),
        references=tuple(references),
        ready_for_planning=bool(payload.get("ready_for_planning", False)),
        issues=tuple(payload.get("issues", [])),
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
