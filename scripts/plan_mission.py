"""Plan a grounded Shepherd-AI mission from a typed command or intent JSON."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, grounded_map_objects, load_map_locations  # noqa: E402
from shepherd_ai.grounding_clarification import build_clarification_report  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission, validate_mission_plan  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--command", help="Typed mission command to parse, ground, and plan.")
    source.add_argument("--intent-json", type=Path, help="Path to a JSON file containing an intent record.")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    intent = _load_intent(args)
    locations = load_map_locations(args.map)
    grounded = ground_intent(intent, locations)
    plan = plan_grounded_mission(grounded)
    validation = validate_mission_plan(plan)
    clarification = build_clarification_report(grounded)
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(args.map),
            "parser": intent.get("parser") if isinstance(intent, dict) else DETERMINISTIC_PARSER_NAME,
            "planner": "deterministic_week4_v1",
            "note": "Week 4 deterministic planning output; not scheduling, execution, or safety validation.",
        },
        "grounded_intent": grounded.to_dict(),
        "map_objects": [map_object.to_dict() for map_object in grounded_map_objects(grounded)],
        "clarification_report": clarification.to_dict(),
        "mission_plan": plan.to_dict(),
        "mission_plan_validation": validation.to_dict(),
    }

    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": plan.status,
                    "ready_for_scheduling": plan.ready_for_scheduling,
                    "valid_plan": validation.valid,
                    "steps": len(plan.steps),
                    "issues": list(plan.issues),
                    "output": str(args.output),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(text)


def _load_intent(args: argparse.Namespace) -> dict[str, Any]:
    if args.command:
        return parse_intent(args.command).to_dict()
    raw = json.loads(args.intent_json.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("--intent-json must contain a JSON object")
    if "intent" in raw and isinstance(raw["intent"], dict):
        return dict(raw["intent"])
    return raw


if __name__ == "__main__":
    main()
