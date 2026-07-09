"""Render a Week 4 mission plan as a Mermaid flow diagram."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import mission_plan_mermaid, plan_grounded_mission  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "diagrams" / "week4_plan_north_field_flow.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", default="Scan the crops in the north field.")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    intent = parse_intent(args.command)
    grounded = ground_intent(intent, locations)
    plan = plan_grounded_mission(grounded)
    mermaid = mission_plan_mermaid(plan)
    payload = _markdown_payload(command=args.command, plan=plan.to_dict(), mermaid=mermaid)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": plan.status, "steps": len(plan.steps)}, indent=2))


def _markdown_payload(*, command: str, plan: dict[str, Any], mermaid: str) -> str:
    return (
        "# Week 4 Mission Flow Diagram\n\n"
        f"Command: `{command}`\n\n"
        "This diagram is a high-level mission-planning artifact. It is not scheduling, route feasibility, safety validation, or execution.\n\n"
        "```mermaid\n"
        f"{mermaid}"
        "```\n\n"
        "## Step Actions\n\n"
        + "\n".join(f"- `{step['step_id']}`: `{step['action']}`" for step in plan["steps"])
        + "\n"
    )


if __name__ == "__main__":
    main()
