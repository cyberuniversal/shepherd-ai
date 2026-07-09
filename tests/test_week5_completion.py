from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week5_completion import (  # noqa: E402
    build_week5_completion_audit,
    render_week5_completion_markdown,
)


ASSIGNMENT_CSV = """task_id,drone_id,strategy,start_min,end_min,duration_min,travel_distance_m,target_location_id,target_name,action
mission_001_drone_01,drone_bravo,least_loaded,0.0,10.0,10.0,100.0,loc_north_field,North Field,scan
mission_001_drone_02,drone_charlie,least_loaded,0.0,10.1,10.1,105.0,loc_north_field,North Field,scan
mission_002,drone_alpha,least_loaded,0.0,8.0,8.0,80.0,loc_greenhouse,Greenhouse,inspect
"""

HTML = """<!doctype html><html><body><h1>Week 5 Drone Allocation</h1><table><tr><td><div class='track'><div class='bar'>scan</div></div></td></tr></table></body></html>"""
NOTEBOOK = """{"cells":[{"source":["!python scripts/schedule_missions.py\\n","!python scripts/audit_week5_completion.py\\n","week5_schedule_comparison_v1.json\\n"]}]}"""

ACCEPTANCE_CRITERIA = {
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
RESEARCH_DEFERRALS = {
    "scope": "week5_research_deferrals_v1",
    "deferrals": {
        "task_allocation_review_conflict_caveat": {
            "status": "recorded_caveat",
            "reason": "paper #12 narrative and extracted tables conflict on which algorithm is best",
        },
        "route_optimization_deferred_for_week5": {"status": "deferred_for_week5", "reason": "later milestone"},
        "safety_validation_deferred_for_week5": {"status": "deferred_for_week5", "reason": "Week 7"},
        "execution_deferred_for_week5": {"status": "deferred_for_week5", "reason": "Week 8 integration"},
        "optimality_not_claimed": {"status": "recorded_caveat", "reason": "simple baselines only"},
    },
}


def _schedule_payload() -> dict:
    assignments = [
        {
            "task_id": "mission_001_drone_01",
            "drone_id": "drone_bravo",
            "strategy": "least_loaded",
            "start_min": 0.0,
            "end_min": 10.0,
            "duration_min": 10.0,
            "travel_distance_m": 100.0,
            "target_location_id": "loc_north_field",
            "target_name": "North Field",
            "action": "scan",
        },
        {
            "task_id": "mission_001_drone_02",
            "drone_id": "drone_charlie",
            "strategy": "least_loaded",
            "start_min": 0.0,
            "end_min": 10.1,
            "duration_min": 10.1,
            "travel_distance_m": 105.0,
            "target_location_id": "loc_north_field",
            "target_name": "North Field",
            "action": "scan",
        },
        {
            "task_id": "mission_002",
            "drone_id": "drone_alpha",
            "strategy": "least_loaded",
            "start_min": 0.0,
            "end_min": 8.0,
            "duration_min": 8.0,
            "travel_distance_m": 80.0,
            "target_location_id": "loc_greenhouse",
            "target_name": "Greenhouse",
            "action": "inspect",
        },
    ]
    metrics = {
        "total_tasks": 3,
        "assigned_tasks": 3,
        "unassigned_tasks": 0,
        "drones_used": 3,
        "makespan_min": 10.1,
        "total_travel_distance_m": 285.0,
        "workload_range_min": 2.1,
    }
    rows = [
        {
            "strategy": strategy,
            "assigned_tasks": 3,
            "unassigned_tasks": 0,
            "drones_used": 3,
            "makespan_min": 10.1,
            "total_travel_distance_m": 285.0,
            "workload_range_min": 2.1,
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
        "primary_assignment": {
            "strategy": "least_loaded",
            "assignments": assignments,
            "metrics": metrics,
            "unassigned_tasks": [],
        },
    }


class Week5CompletionTests(unittest.TestCase):
    def test_completion_audit_allows_advancement_when_scheduling_gates_pass(self) -> None:
        audit = build_week5_completion_audit(
            schedule_comparison=_schedule_payload(),
            assignment_csv_text=ASSIGNMENT_CSV,
            allocation_visualization_html=HTML,
            scheduler_notebook_text=NOTEBOOK,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertTrue(payload["research_gates_passed"])
        self.assertTrue(payload["advancement_allowed"])
        self.assertEqual([], payload["blockers"])

    def test_completion_audit_blocks_when_notebook_is_placeholder(self) -> None:
        audit = build_week5_completion_audit(
            schedule_comparison=_schedule_payload(),
            assignment_csv_text=ASSIGNMENT_CSV,
            allocation_visualization_html=HTML,
            scheduler_notebook_text="print('placeholder')",
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertFalse(payload["roadmap_gates_passed"])
        self.assertIn("scheduler_notebook_workflow_present", payload["blockers"])

    def test_completion_audit_blocks_when_research_deferrals_are_missing(self) -> None:
        audit = build_week5_completion_audit(
            schedule_comparison=_schedule_payload(),
            assignment_csv_text=ASSIGNMENT_CSV,
            allocation_visualization_html=HTML,
            scheduler_notebook_text=NOTEBOOK,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=None,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertFalse(payload["research_gates_passed"])
        self.assertIn("task_allocation_caveat_preserved", payload["blockers"])

    def test_completion_markdown_lists_decision_and_scope(self) -> None:
        audit = build_week5_completion_audit(
            schedule_comparison=_schedule_payload(),
            assignment_csv_text=ASSIGNMENT_CSV,
            allocation_visualization_html=HTML,
            scheduler_notebook_text=NOTEBOOK,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )

        markdown = render_week5_completion_markdown(audit)

        self.assertIn("Week 5 Completion Gate Audit", markdown)
        self.assertIn("Advancement allowed", markdown)
        self.assertIn("not route optimization", markdown)


if __name__ == "__main__":
    unittest.main()
