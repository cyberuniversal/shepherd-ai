"""Evaluate deterministic Week 4 planning over labeled grounding commands."""

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
from shepherd_ai.intent import DETERMINISTIC_PARSER_NAME, parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission, validate_mission_plan  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_DATASET = ROOT / "datasets" / "maps" / "human_grounding_benchmark_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week4_planning_human_grounding_benchmark_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = evaluate(args.map, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


def evaluate(map_path: Path, dataset_path: Path) -> dict[str, Any]:
    locations = load_map_locations(map_path)
    rows: list[dict[str, Any]] = []
    for record in _load_jsonl(dataset_path):
        intent = parse_intent(record["text"])
        grounded = ground_intent(intent, locations)
        plan = plan_grounded_mission(grounded)
        validation = validate_mission_plan(plan)
        expected_status = _expected_plan_status(record)
        expected_plan = record.get("expected_plan", {})
        required_actions = _expected_list(expected_plan, "required_actions")
        required_issues = _expected_list(expected_plan, "required_issues")
        step_actions = [step.action for step in plan.steps]
        plan_issues = list(plan.issues)
        rows.append(
            {
                "id": record["id"],
                "text": record["text"],
                "expected_plan_status": expected_status,
                "actual_plan_status": plan.status,
                "status_matches_expected": expected_status == plan.status,
                "required_actions": required_actions,
                "required_actions_present": all(action in step_actions for action in required_actions),
                "required_issues": required_issues,
                "required_issues_present": all(issue in plan_issues for issue in required_issues),
                "ready_for_scheduling": plan.ready_for_scheduling,
                "valid_plan_contract": validation.valid,
                "step_count": len(plan.steps),
                "step_actions": step_actions,
                "task_graph": plan.to_dict()["task_graph"],
                "primary_location_id": (
                    plan.primary_map_object.get("location_id")
                    if isinstance(plan.primary_map_object, dict)
                    else None
                ),
                "issues": plan_issues,
                "validation_issues": list(validation.issues),
                "validation_warnings": list(validation.warnings),
            }
        )

    expected_matches = sum(1 for row in rows if row["status_matches_expected"])
    action_matches = sum(1 for row in rows if row["required_actions_present"])
    issue_matches = sum(1 for row in rows if row["required_issues_present"])
    planned_rows = [row for row in rows if row["actual_plan_status"] == "planned"]
    blocked_rows = [row for row in rows if row["actual_plan_status"] == "blocked"]
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(map_path),
            "dataset": str(dataset_path),
            "parser": DETERMINISTIC_PARSER_NAME,
            "planner": "deterministic_week4_v1",
            "dataset_note": (
                "Week 4 planning evaluation over existing grounding labels. "
                "This is not scheduling, execution, route feasibility, or safety validation."
            ),
        },
        "summary": {
            "records": len(rows),
            "expected_status_matches": expected_matches,
            "expected_status_accuracy": expected_matches / len(rows) if rows else 0.0,
            "required_action_matches": action_matches,
            "required_action_accuracy": action_matches / len(rows) if rows else 0.0,
            "required_issue_matches": issue_matches,
            "required_issue_accuracy": issue_matches / len(rows) if rows else 0.0,
            "planned_records": len(planned_rows),
            "blocked_records": len(blocked_rows),
            "ready_for_scheduling_records": sum(1 for row in rows if row["ready_for_scheduling"]),
            "valid_plan_contract_records": sum(1 for row in rows if row["valid_plan_contract"]),
        },
        "records": rows,
    }


def _expected_plan_status(record: dict[str, Any]) -> str:
    expected_plan = record.get("expected_plan")
    if isinstance(expected_plan, dict) and isinstance(expected_plan.get("status"), str):
        return str(expected_plan["status"])
    expected = record.get("expected_grounding", {})
    statuses = [
        str(reference.get("status"))
        for reference in expected.values()
        if isinstance(reference, dict)
    ]
    if "ambiguous" in statuses:
        return "blocked"
    if statuses and all(status in {"unresolved", "not_provided"} for status in statuses):
        return "blocked"
    return "planned"


def _expected_list(payload: Any, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"line {line_number}: record must be a JSON object")
        if "id" not in record or "text" not in record or "expected_grounding" not in record:
            raise ValueError(f"line {line_number}: missing id, text, or expected_grounding")
        records.append(record)
    if not records:
        raise ValueError("planning evaluation dataset is empty")
    return records


if __name__ == "__main__":
    main()
