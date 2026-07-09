import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_mission_planning.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class EvaluateMissionPlanningCliTests(unittest.TestCase):
    def test_cli_writes_planning_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "planning.jsonl"
            output = root / "planning_eval.json"
            dataset.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "plan_ok",
                                "text": "Scan the crops in the north field.",
                                "expected_grounding": {
                                    "target": {
                                        "status": "grounded",
                                        "location_id": "loc_north_field",
                                    }
                                },
                                "expected_plan": {
                                    "status": "planned",
                                    "required_actions": [
                                        "validate_grounding",
                                        "scan_area",
                                        "capture_images",
                                        "run_vision_model",
                                    ],
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "id": "plan_blocked",
                                "text": "Check if there is any traffic on the road.",
                                "expected_grounding": {
                                    "target": {
                                        "status": "ambiguous",
                                        "location_id": None,
                                        "candidate_ids": ["loc_service_road", "loc_main_road"],
                                    }
                                },
                                "expected_plan": {
                                    "status": "blocked",
                                    "required_issues": ["target_ambiguous"],
                                },
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--dataset",
                    str(dataset),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("Wrote", completed.stdout)
        self.assertEqual(payload["summary"]["records"], 2)
        self.assertEqual(payload["summary"]["planned_records"], 1)
        self.assertEqual(payload["summary"]["blocked_records"], 1)
        self.assertEqual(payload["summary"]["expected_status_accuracy"], 1.0)
        self.assertEqual(payload["summary"]["required_action_accuracy"], 1.0)
        self.assertEqual(payload["summary"]["required_issue_accuracy"], 1.0)
        self.assertEqual(payload["summary"]["valid_plan_contract_records"], 2)
        self.assertTrue(payload["records"][0]["valid_plan_contract"])
        self.assertTrue(payload["records"][0]["required_actions_present"])
        self.assertTrue(payload["records"][1]["required_issues_present"])
        self.assertEqual(payload["records"][0]["task_graph"]["nodes"][0]["id"], "step_001")


if __name__ == "__main__":
    unittest.main()
