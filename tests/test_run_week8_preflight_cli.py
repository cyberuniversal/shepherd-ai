import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_week8_preflight.py"


class RunWeek8PreflightCliTests(unittest.TestCase):
    def test_default_roadmap_scenario_stores_blocked_negative_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "preflight.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"status": "clarification_required"', completed.stdout)
        self.assertEqual(payload["metadata"]["input_mode"], "typed_development")
        self.assertEqual(payload["pipeline_result"]["blocking_clauses"], ["clause_002"])
        self.assertEqual(payload["pipeline_result"]["schedule"], None)


if __name__ == "__main__":
    unittest.main()
