import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPT = ROOT / "scripts" / "run_week7_workflow.py"
EVALUATE_SCRIPT = ROOT / "scripts" / "evaluate_week7_safety.py"
SUPERVISION_SCRIPT = ROOT / "scripts" / "evaluate_week7_supervision.py"
CLARIFICATION_SCRIPT = ROOT / "scripts" / "evaluate_week7_clarification.py"
ROUTE_SCRIPT = ROOT / "scripts" / "evaluate_week7_route_safety.py"
INTEGRATION_SCRIPT = ROOT / "scripts" / "evaluate_week7_integration.py"
SENSITIVITY_SCRIPT = ROOT / "scripts" / "evaluate_week7_policy_sensitivity.py"


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

    def test_supervision_evaluator_preserves_transition_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "supervision.json"
            report = Path(tmp) / "supervision.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SUPERVISION_SCRIPT),
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

        self.assertEqual(payload["summary"]["case_count"], 8)
        self.assertEqual(payload["summary"]["expected_final_status_matches"], 8)
        self.assertTrue(all(case["supervision_result"]["events"] for case in payload["cases"]))
        self.assertIn("Week 7 Mission Supervision Evaluation", report_text)

    def test_clarification_evaluator_preserves_dialogue_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "clarification.json"
            report = Path(tmp) / "clarification.md"
            subprocess.run(
                [
                    sys.executable,
                    str(CLARIFICATION_SCRIPT),
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

        self.assertEqual(payload["summary"]["case_count"], 4)
        self.assertEqual(payload["summary"]["expected_status_matches"], 4)
        self.assertTrue(all(case["dialogue_result"]["events"] for case in payload["cases"]))
        self.assertIn("Week 7 Clarification Dialogue Evaluation", report_text)

    def test_route_evaluator_covers_circle_and_polygon_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "route.json"
            report = Path(tmp) / "route.md"
            subprocess.run(
                [
                    sys.executable,
                    str(ROUTE_SCRIPT),
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

        self.assertEqual(payload["summary"]["case_count"], 3)
        self.assertEqual(payload["summary"]["expected_decision_matches"], 3)
        self.assertEqual(payload["metadata"]["safety_capabilities"], ["route_restricted_area_intersection"])
        self.assertIn("Week 7 Route Safety Evaluation", report_text)

    def test_integration_evaluator_covers_prior_module_interfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "integration.json"
            report = Path(tmp) / "integration.md"
            subprocess.run(
                [
                    sys.executable,
                    str(INTEGRATION_SCRIPT),
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

        self.assertEqual(payload["summary"]["case_count"], 3)
        self.assertEqual(payload["summary"]["expected_status_matches"], 3)
        self.assertIn("trained_intent_interface", payload["metadata"]["integrated_stages"])
        self.assertIn("vision_result_binding", payload["metadata"]["integrated_stages"])
        self.assertIn("Week 7 Prior-Module Integration Evaluation", report_text)

    def test_policy_sensitivity_evaluator_records_all_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "sensitivity.json"
            report = Path(tmp) / "sensitivity.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SENSITIVITY_SCRIPT),
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

        self.assertEqual(payload["summary"]["dimension_count"], 4)
        self.assertEqual(payload["summary"]["expected_sequence_matches"], 4)
        self.assertEqual(payload["summary"]["monotonicity_checks_passed"], 4)
        self.assertIn("Week 7 Policy Sensitivity Evaluation", report_text)


if __name__ == "__main__":
    unittest.main()
