import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week5_completion.py"


class AuditWeek5CompletionCliTests(unittest.TestCase):
    def test_cli_writes_completion_gate_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schedule = root / "schedule.json"
            csv_path = root / "assignments.csv"
            html_path = root / "allocation.html"
            notebook = root / "Notebook5_Scheduler.ipynb"
            criteria = root / "criteria.json"
            deferrals = root / "deferrals.json"
            output_json = root / "completion.json"
            output_markdown = root / "completion.md"

            schedule.write_text(json.dumps(_schedule_payload()), encoding="utf-8")
            csv_path.write_text(_assignment_csv(), encoding="utf-8")
            html_path.write_text(
                "<h1>Week 5 Drone Allocation</h1><table><tr><td><div class='track'><div class='bar'>scan</div></div></td></tr></table>",
                encoding="utf-8",
            )
            notebook.write_text(
                "schedule_missions.py audit_week5_completion.py week5_schedule_comparison_v1.json",
                encoding="utf-8",
            )
            criteria.write_text(json.dumps(_criteria()), encoding="utf-8")
            deferrals.write_text(json.dumps(_deferrals()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--schedule-comparison",
                    str(schedule),
                    "--assignment-csv",
                    str(csv_path),
                    "--allocation-visualization",
                    str(html_path),
                    "--scheduler-notebook",
                    str(notebook),
                    "--acceptance-criteria",
                    str(criteria),
                    "--research-deferrals",
                    str(deferrals),
                    "--json-output",
                    str(output_json),
                    "--markdown-output",
                    str(output_markdown),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            audit = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_markdown.read_text(encoding="utf-8")

        self.assertIn("advancement_allowed", completed.stdout)
        self.assertTrue(audit["advancement_allowed"])
        self.assertEqual("week5_complete_for_advancement_to_week6_vision", audit["decision"])
        self.assertIn("Research Gates", markdown)


def _schedule_payload() -> dict:
    assignments = [
        _assignment("mission_001_drone_01", "drone_bravo"),
        _assignment("mission_001_drone_02", "drone_charlie"),
        _assignment("mission_002", "drone_alpha"),
    ]
    metrics = {
        "total_tasks": 3,
        "assigned_tasks": 3,
        "unassigned_tasks": 0,
        "drones_used": 3,
        "makespan_min": 10.0,
        "total_travel_distance_m": 300.0,
        "workload_range_min": 1.0,
    }
    rows = [
        {
            "strategy": strategy,
            "assigned_tasks": 3,
            "unassigned_tasks": 0,
            "drones_used": 3,
            "makespan_min": 10.0,
            "total_travel_distance_m": 300.0,
            "workload_range_min": 1.0,
        }
        for strategy in ("round_robin", "least_loaded", "nearest_available")
    ]
    return {
        "metadata": {
            "note": "This is not route optimization, safety validation, execution, or physical-drone control."
        },
        "drones": [
            {"drone_id": "drone_alpha", "status": "idle"},
            {"drone_id": "drone_bravo", "status": "idle"},
            {"drone_id": "drone_charlie", "status": "idle"},
        ],
        "tasks": [
            {"task_id": "mission_001_drone_01", "source_plan_id": "mission_001", "required_drone_index": 1},
            {"task_id": "mission_001_drone_02", "source_plan_id": "mission_001", "required_drone_index": 2},
            {"task_id": "mission_002", "source_plan_id": "mission_002", "required_drone_index": 1},
        ],
        "comparison": {
            "best_strategy_by_makespan": "least_loaded",
            "comparison_table": rows,
            "strategy_results": [{"strategy": row["strategy"], "metrics": metrics} for row in rows],
            "notes": [
                "Classical deterministic baselines only; no LLM assignment is used.",
                "Metrics are synthetic scheduling proxies over the custom map, not physical flight performance.",
            ],
        },
        "primary_assignment": {"strategy": "least_loaded", "assignments": assignments, "metrics": metrics},
    }


def _assignment(task_id: str, drone_id: str) -> dict:
    return {
        "task_id": task_id,
        "drone_id": drone_id,
        "strategy": "least_loaded",
        "start_min": 0.0,
        "end_min": 10.0,
        "duration_min": 10.0,
        "travel_distance_m": 100.0,
        "target_location_id": "loc_north_field",
        "target_name": "North Field",
        "action": "scan",
    }


def _assignment_csv() -> str:
    return (
        "task_id,drone_id,strategy,start_min,end_min,duration_min,travel_distance_m,target_location_id,target_name,action\n"
        "mission_001_drone_01,drone_bravo,least_loaded,0,10,10,100,loc_north_field,North Field,scan\n"
        "mission_001_drone_02,drone_charlie,least_loaded,0,10,10,100,loc_north_field,North Field,scan\n"
        "mission_002,drone_alpha,least_loaded,0,10,10,100,loc_north_field,North Field,scan\n"
    )


def _criteria() -> dict:
    return {
        "scope": "synthetic_week5_scheduling_gate_v1",
        "not_execution_benchmark": True,
        "thresholds": {
            "simulated_drones_required": 3,
            "strategies_min": 3,
            "unassigned_tasks_max": 0,
            "drones_used_min": 3,
            "assignment_table_required": True,
            "allocation_visualization_required": True,
        },
    }


def _deferrals() -> dict:
    return {
        "scope": "week5_research_deferrals_v1",
        "deferrals": {
            "task_allocation_review_conflict_caveat": {
                "status": "recorded_caveat",
                "reason": "paper #12 caveat",
            },
            "route_optimization_deferred_for_week5": {"status": "deferred_for_week5", "reason": "later"},
            "safety_validation_deferred_for_week5": {"status": "deferred_for_week5", "reason": "Week 7"},
            "execution_deferred_for_week5": {"status": "deferred_for_week5", "reason": "later"},
            "optimality_not_claimed": {"status": "recorded_caveat", "reason": "simple baselines only"},
        },
    }


if __name__ == "__main__":
    unittest.main()
