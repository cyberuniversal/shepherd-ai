import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPT = ROOT / "scripts" / "run_week7_workflow.py"
EVALUATE_SCRIPT = ROOT / "scripts" / "evaluate_week7_safety.py"


class Week7CliTests(unittest.TestCase):
    def test_run_workflow_writes_complete_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "workflow.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUN_SCRIPT),
                    "--command",
                    "Inspect the greenhouse.",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["workflow_result"]["status"], "ready_for_simulated_execution")
        self.assertEqual(payload["workflow_result"]["safety_report"]["summary"]["passed_checks"], 4)

    def test_evaluator_writes_raw_cases_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "evaluation.json"
            report = Path(tmp) / "evaluation.md"
            subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE_SCRIPT),
                    "--output",
                    str(output),
                    "--report-output",
                    str(report),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            report_text = report.read_text(encoding="utf-8")

        self.assertEqual(payload["summary"]["case_count"], 12)
        self.assertEqual(payload["summary"]["expected_status_matches"], 12)
        self.assertEqual(len(payload["cases"]), 12)
        self.assertIn("Week 7 Safety Development Evaluation", report_text)


if __name__ == "__main__":
    unittest.main()
