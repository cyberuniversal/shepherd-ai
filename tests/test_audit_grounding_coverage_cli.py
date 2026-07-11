import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_grounding_coverage.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
EXAMPLES_PATH = ROOT / "datasets" / "maps" / "grounding_examples_v1.jsonl"
DIAGNOSTICS_PATH = ROOT / "datasets" / "maps" / "grounding_diagnostics_v1.jsonl"


class AuditGroundingCoverageCliTests(unittest.TestCase):
    def test_cli_writes_json_and_markdown_coverage_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_output = root / "coverage.json"
            markdown_output = root / "coverage.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--dataset",
                    str(EXAMPLES_PATH),
                    "--dataset",
                    str(DIAGNOSTICS_PATH),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(json_output.read_text(encoding="utf-8"))
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn('"covered_location_ids"', completed.stdout)
        self.assertEqual(payload["map_records"], 20)
        self.assertIn("loc_north_field", payload["covered_location_ids"])
        self.assertIn("Untested Location IDs", markdown)


if __name__ == "__main__":
    unittest.main()
