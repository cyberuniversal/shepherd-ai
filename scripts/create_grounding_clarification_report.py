"""Create an operator-facing clarification report for a grounded command."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.grounding_clarification import build_clarification_report  # noqa: E402
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "grounding_clarification_ambiguous_road.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--command", help="Typed mission command to parse, ground, and inspect.")
    source.add_argument("--intent-json", type=Path, help="Path to a JSON file containing an intent record.")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    intent = _load_intent(args)
    locations = load_map_locations(args.map)
    grounded = ground_intent(intent, locations)
    report = build_clarification_report(grounded)

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(args.map),
            "parser": intent.get("parser") if isinstance(intent, dict) else DETERMINISTIC_PARSER_NAME,
            "note": "Week 3 grounding clarification report; not a planner or safety validator.",
        },
        "grounded_intent": grounded.to_dict(),
        "clarification_report": report.to_dict(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"requests": len(report.requests), "blocks_planning": report.blocks_planning}, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


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
