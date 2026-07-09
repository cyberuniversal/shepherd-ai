import unittest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week4_completion import (  # noqa: E402
    build_week4_completion_audit,
    render_week4_completion_markdown,
)

FLOW_DIAGRAM = """# Week 4 Mission Flow Diagram

```mermaid
flowchart TD
    step_001["step_001: takeoff"]
    step_002["step_002: fly_to"]
    step_003["step_003: capture_images"]
    step_004["step_004: run_vision_model"]
```
"""

ACCEPTANCE_CRITERIA = {
    "scope": "synthetic_week4_completion_gate_v1",
    "not_execution_benchmark": True,
    "thresholds": {
        "records_min": 1,
        "expected_status_accuracy_min": 1.0,
        "required_action_accuracy_min": 1.0,
        "required_issue_accuracy_min": 1.0,
        "valid_plan_contract_fraction_min": 1.0,
    },
}
RESEARCH_DEFERRALS = {
    "scope": "week4_research_deferrals_v1",
    "deferrals": {
        "scheduling_deferred_for_week4": {"status": "deferred_for_week4", "reason": "week 5"},
        "route_optimization_deferred_for_week4": {"status": "deferred_for_week4", "reason": "later"},
        "safety_validation_deferred_for_week4": {"status": "deferred_for_week4", "reason": "later"},
        "simulation_execution_deferred_for_week4": {"status": "deferred_for_week4", "reason": "later"},
    },
}


def _evaluation_payload(dataset: str = "datasets/maps/human_grounding_benchmark_v1.jsonl") -> dict:
    return {
        "metadata": {
            "dataset": dataset,
            "dataset_note": "not scheduling, execution, route feasibility, or safety validation",
        },
        "summary": {
            "records": 2,
            "expected_status_accuracy": 1.0,
            "required_action_accuracy": 1.0,
            "required_issue_accuracy": 1.0,
            "planned_records": 1,
            "blocked_records": 1,
            "ready_for_scheduling_records": 1,
            "valid_plan_contract_records": 2,
        },
        "records": [
            {
                "actual_plan_status": "planned",
                "ready_for_scheduling": True,
                "step_count": 9,
                "required_actions": ["review_constraints", "capture_images", "run_vision_model"],
                "required_actions_present": True,
                "step_actions": [
                    "validate_grounding",
                    "review_constraints",
                    "takeoff",
                    "fly_to",
                    "scan_area",
                    "capture_images",
                    "run_vision_model",
                    "save_observation_results",
                    "return_to_launch_area",
                ],
                "issues": ["constraint[0]_not_flyable", "constraint[0]_requires_clearance"],
                "task_graph": {
                    "nodes": [{"id": f"step_{index:03d}"} for index in range(1, 10)],
                    "edges": [
                        {"from": f"step_{index:03d}", "to": f"step_{index + 1:03d}"}
                        for index in range(1, 9)
                    ],
                },
            },
            {
                "actual_plan_status": "blocked",
                "ready_for_scheduling": False,
                "step_count": 0,
                "required_actions": [],
                "required_actions_present": True,
                "step_actions": [],
                "issues": ["target_ambiguous", "grounding_not_ready_for_planning"],
                "task_graph": {"nodes": [], "edges": []},
            },
        ],
    }


class Week4CompletionTests(unittest.TestCase):
    def test_completion_audit_allows_advancement_when_planning_gates_pass(self) -> None:
        audit = build_week4_completion_audit(
            human_benchmark_planning=_evaluation_payload(),
            focused_planning_cases=_evaluation_payload("datasets/maps/week4_planning_cases_v1.jsonl"),
            flow_diagram_markdown=FLOW_DIAGRAM,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertTrue(payload["research_gates_passed"])
        self.assertTrue(payload["advancement_allowed"])
        self.assertEqual([], payload["blockers"])

    def test_completion_audit_blocks_when_deferrals_are_missing(self) -> None:
        audit = build_week4_completion_audit(
            human_benchmark_planning=_evaluation_payload(),
            focused_planning_cases=_evaluation_payload("datasets/maps/week4_planning_cases_v1.jsonl"),
            flow_diagram_markdown=FLOW_DIAGRAM,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=None,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertFalse(payload["research_gates_passed"])
        self.assertFalse(payload["advancement_allowed"])
        self.assertIn("scheduling_deferred_for_week4", payload["blockers"])

    def test_completion_audit_blocks_when_task_graph_contract_is_broken(self) -> None:
        focused = _evaluation_payload("datasets/maps/week4_planning_cases_v1.jsonl")
        focused["records"][0]["task_graph"]["edges"] = []
        audit = build_week4_completion_audit(
            human_benchmark_planning=_evaluation_payload(),
            focused_planning_cases=focused,
            flow_diagram_markdown=FLOW_DIAGRAM,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertFalse(payload["roadmap_gates_passed"])
        self.assertIn("task_graph_contract_present", payload["blockers"])

    def test_completion_markdown_lists_decision_and_scope(self) -> None:
        audit = build_week4_completion_audit(
            human_benchmark_planning=_evaluation_payload(),
            focused_planning_cases=_evaluation_payload("datasets/maps/week4_planning_cases_v1.jsonl"),
            flow_diagram_markdown=FLOW_DIAGRAM,
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )

        markdown = render_week4_completion_markdown(audit)

        self.assertIn("Week 4 Completion Gate Audit", markdown)
        self.assertIn("Advancement allowed", markdown)
        self.assertIn("not a scheduling", markdown)

    def test_completion_audit_blocks_without_flow_diagram(self) -> None:
        audit = build_week4_completion_audit(
            human_benchmark_planning=_evaluation_payload(),
            focused_planning_cases=_evaluation_payload("datasets/maps/week4_planning_cases_v1.jsonl"),
            flow_diagram_markdown="",
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertFalse(payload["roadmap_gates_passed"])
        self.assertIn("mission_flow_diagram_present", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
