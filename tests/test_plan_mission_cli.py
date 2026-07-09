import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_mission.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class PlanMissionCliTests(unittest.TestCase):
    def test_cli_writes_planned_mission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "plan.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--command",
                    "Scan the crops in the north field.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(completed.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "planned")
        self.assertTrue(summary["ready_for_scheduling"])
        self.assertTrue(summary["valid_plan"])
        self.assertEqual(payload["metadata"]["planner"], "deterministic_week4_v1")
        self.assertEqual(payload["mission_plan"]["primary_map_object"]["location_id"], "loc_north_field")
        self.assertEqual(payload["mission_plan"]["steps"][0]["action"], "validate_grounding")
        self.assertTrue(payload["mission_plan_validation"]["valid"])
        self.assertEqual(payload["mission_plan"]["task_graph"]["nodes"][0]["id"], "step_001")

    def test_cli_writes_blocked_plan_for_ambiguous_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "blocked.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--command",
                    "Check if there is any traffic on the road.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(completed.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "blocked")
        self.assertFalse(summary["ready_for_scheduling"])
        self.assertTrue(summary["valid_plan"])
        self.assertEqual(payload["mission_plan"]["steps"], [])
        self.assertTrue(payload["mission_plan_validation"]["valid"])
        self.assertIn("target_ambiguous", payload["mission_plan"]["issues"])


if __name__ == "__main__":
    unittest.main()
