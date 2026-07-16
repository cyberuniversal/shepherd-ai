import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_week8_simulation.py"


class RunWeek8SimulationCliTests(unittest.TestCase):
    def test_writes_resolved_simulation_telemetry_and_map(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.json"
            telemetry = Path(temp_dir) / "telemetry.jsonl"
            map_output = Path(temp_dir) / "simulation.html"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--telemetry-output",
                    str(telemetry),
                    "--map-output",
                    str(map_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            telemetry_rows = telemetry.read_text(encoding="utf-8").splitlines()
            html = map_output.read_text(encoding="utf-8")

        self.assertIn('"status": "completed"', completed.stdout)
        self.assertEqual(payload["simulation"]["status"], "completed")
        self.assertEqual(payload["metadata"]["destination_resolution"], {"clause_002": "loc_east_field"})
        self.assertEqual(len(telemetry_rows), payload["simulation"]["telemetry_records"])
        self.assertIn("timeDimension", html)


if __name__ == "__main__":
    unittest.main()
