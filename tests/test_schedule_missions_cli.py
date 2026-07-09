import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "schedule_missions.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"


class ScheduleMissionsCliTests(unittest.TestCase):
    def test_cli_writes_comparison_table_and_visualization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "schedule.json"
            markdown = root / "schedule.md"
            csv_output = root / "assignments.csv"
            html_output = root / "allocation.html"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--fleet",
                    str(FLEET_PATH),
                    "--command",
                    "Send two drones north and scan the crops.",
                    "--command",
                    "Inspect the greenhouse.",
                    "--command",
                    "Check the irrigation canal.",
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--assignment-csv-output",
                    str(csv_output),
                    "--visualization-output",
                    str(html_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            markdown_exists = markdown.exists()
            csv_exists = csv_output.exists()
            html_exists = html_output.exists()

        self.assertIn("Wrote", completed.stdout)
        self.assertEqual(len(payload["drones"]), 3)
        self.assertEqual(payload["primary_assignment"]["metrics"]["unassigned_tasks"], 0)
        self.assertEqual(payload["primary_assignment"]["metrics"]["drones_used"], 3)
        self.assertTrue(markdown_exists)
        self.assertTrue(csv_exists)
        self.assertTrue(html_exists)


if __name__ == "__main__":
    unittest.main()
