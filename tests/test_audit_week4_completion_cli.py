import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week4_completion.py"


class AuditWeek4CompletionCliTests(unittest.TestCase):
    def test_cli_writes_completion_gate_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            human_eval = root / "human.json"
            focused_eval = root / "focused.json"
            criteria = root / "criteria.json"
            deferrals = root / "deferrals.json"
            flow_diagram = root / "flow.md"
            output_json = root / "completion.json"
            output_markdown = root / "completion.md"

            payload = _evaluation_payload()
            human_eval.write_text(json.dumps(payload), encoding="utf-8")
            focused_payload = _evaluation_payload(dataset="datasets/maps/week4_planning_cases_v1.jsonl")
            focused_eval.write_text(json.dumps(focused_payload), encoding="utf-8")
            criteria.write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )
            deferrals.write_text(
                json.dumps(
                    {
                        "scope": "week4_research_deferrals_v1",
                        "deferrals": {
                            "scheduling_deferred_for_week4": {
                                "status": "deferred_for_week4",
                                "reason": "week 5",
                            },
                            "route_optimization_deferred_for_week4": {
                                "status": "deferred_for_week4",
                                "reason": "later",
                            },
                            "safety_validation_deferred_for_week4": {
                                "status": "deferred_for_week4",
                                "reason": "later",
                            },
                            "simulation_execution_deferred_for_week4": {
                                "status": "deferred_for_week4",
                                "reason": "later",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            flow_diagram.write_text(
                "# Flow\n\n```mermaid\nflowchart TD\n    a[\"capture_images\"] --> b[\"run_vision_model\"]\n```\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--human-planning-evaluation",
                    str(human_eval),
                    "--focused-planning-evaluation",
                    str(focused_eval),
                    "--acceptance-criteria",
                    str(criteria),
                    "--research-deferrals",
                    str(deferrals),
                    "--flow-diagram",
                    str(flow_diagram),
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
        self.assertEqual("week4_complete_for_advancement_to_week5_scheduling", audit["decision"])
        self.assertIn("Research Gates", markdown)


def _evaluation_payload(*, dataset: str = "datasets/maps/human_grounding_benchmark_v1.jsonl") -> dict:
    return {
        "metadata": {"dataset": dataset},
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
                "issues": ["primary_map_object_requires_clearance"],
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
                "issues": ["grounding_not_ready_for_planning"],
                "task_graph": {"nodes": [], "edges": []},
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
