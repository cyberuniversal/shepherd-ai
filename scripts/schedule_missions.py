"""Run Week 5 multi-drone scheduling simulations over Week 4 mission plans."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission, validate_mission_plan  # noqa: E402
from shepherd_ai.scheduling import (  # noqa: E402
    compare_scheduling_strategies,
    extract_tasks_from_plan_payloads,
    load_drones,
    render_allocation_html,
    render_assignment_csv,
    render_assignment_markdown,
    schedule_tasks,
)


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week5_schedule_comparison_v1.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "week5_schedule_comparison_v1.md"
DEFAULT_CSV = ROOT / "outputs" / "tables" / "week5_assignments_least_loaded.csv"
DEFAULT_HTML = ROOT / "outputs" / "visualizations" / "week5_drone_allocation_least_loaded.html"
DEFAULT_COMMANDS = (
    "Send two drones north and scan the crops.",
    "Inspect the greenhouse.",
    "Check the irrigation canal.",
    "Inspect the storage area.",
    "Check the water tank.",
)
DEFAULT_STRATEGIES = ("round_robin", "least_loaded", "nearest_available")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--plan-json", type=Path, action="append")
    parser.add_argument("--command", action="append")
    parser.add_argument("--strategy", action="append", default=None)
    parser.add_argument("--primary-strategy", default="least_loaded")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--assignment-csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--visualization-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    map_locations = {location.id: location for location in load_map_locations(args.map)}
    fleet_payload = _read_json(args.fleet)
    drones = load_drones(fleet_payload, map_locations)
    plan_payloads = _load_plan_payloads(args.plan_json, args.command, map_locations)
    tasks = extract_tasks_from_plan_payloads(plan_payloads)
    strategies = tuple(args.strategy or DEFAULT_STRATEGIES)
    comparison = compare_scheduling_strategies(tasks, drones, strategies=strategies)
    primary_result = schedule_tasks(tasks, drones, strategy=args.primary_strategy)

    output_payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(args.map),
            "fleet": str(args.fleet),
            "strategies": list(strategies),
            "primary_strategy": args.primary_strategy,
            "note": (
                "Week 5 scheduling simulation over custom map tasks. "
                "This is not route optimization, safety validation, execution, or physical-drone control."
            ),
        },
        "drones": [drone.to_dict() for drone in drones],
        "tasks": [task.to_dict() for task in tasks],
        "comparison": comparison,
        "primary_assignment": primary_result.to_dict(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(_comparison_markdown(output_payload, primary_result), encoding="utf-8")

    args.assignment_csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.assignment_csv_output.write_text(render_assignment_csv(primary_result), encoding="utf-8")

    args.visualization_output.parent.mkdir(parents=True, exist_ok=True)
    args.visualization_output.write_text(render_allocation_html(primary_result), encoding="utf-8")

    print(json.dumps(_summary(output_payload), indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    print(f"Wrote {args.assignment_csv_output}")
    print(f"Wrote {args.visualization_output}")


def _load_plan_payloads(
    plan_paths: list[Path] | None,
    commands: list[str] | None,
    map_locations: dict[str, Any],
) -> list[dict[str, Any]]:
    if plan_paths:
        return [_read_json(path) for path in plan_paths]
    plan_payloads: list[dict[str, Any]] = []
    for command in commands or list(DEFAULT_COMMANDS):
        intent = parse_intent(command)
        grounded = ground_intent(intent, map_locations.values())
        plan = plan_grounded_mission(grounded)
        validation = validate_mission_plan(plan)
        plan_payloads.append(
            {
                "command": command,
                "grounded_intent": grounded.to_dict(),
                "mission_plan": plan.to_dict(),
                "mission_plan_validation": validation.to_dict(),
            }
        )
    return plan_payloads


def _comparison_markdown(payload: dict[str, Any], primary_result: Any) -> str:
    lines = [
        "# Week 5 Scheduling Strategy Comparison",
        "",
        "This report compares deterministic scheduling baselines over simulated drones and Week 4 mission-plan tasks. It is not route optimization, safety validation, or mission execution.",
        "",
        "## Strategy Comparison",
        "",
        "| Strategy | Assigned | Unassigned | Drones Used | Makespan min | Travel m | Workload range min |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["comparison"]["comparison_table"]:
        lines.append(
            f"| {row['strategy']} | {row['assigned_tasks']} | {row['unassigned_tasks']} | "
            f"{row['drones_used']} | {row['makespan_min']} | {row['total_travel_distance_m']} | {row['workload_range_min']} |"
        )
    lines.extend(
        [
            "",
            f"- Best strategy by makespan: `{payload['comparison']['best_strategy_by_makespan']}`",
            "",
            "## Primary Assignment Table",
            "",
            render_assignment_markdown(primary_result),
        ]
    )
    return "\n".join(lines)


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    primary = payload["primary_assignment"]
    return {
        "tasks": len(payload["tasks"]),
        "drones": len(payload["drones"]),
        "strategies": len(payload["comparison"]["strategy_results"]),
        "primary_strategy": primary["strategy"],
        "assigned_tasks": primary["metrics"]["assigned_tasks"],
        "unassigned_tasks": primary["metrics"]["unassigned_tasks"],
        "drones_used": primary["metrics"]["drones_used"],
        "best_strategy_by_makespan": payload["comparison"]["best_strategy_by_makespan"],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
