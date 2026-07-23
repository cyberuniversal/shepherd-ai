import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_evidence_aware_decisions.py"


class EvaluateEvidenceAwareDecisionsCliTests(unittest.TestCase):
    def test_cli_preserves_raw_cases_and_claim_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "evaluation.json"
            report = Path(temp_dir) / "report.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
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

        self.assertEqual(payload["summary"]["decision_cases"], 38)
        self.assertEqual(payload["summary"]["dialogue_cases"], 4)
        self.assertFalse(payload["claim_limits"]["monolithic_llm_baseline_evaluated"])
        self.assertFalse(payload["claim_limits"]["tacos_reimplementation_evaluated"])
        self.assertEqual(len(payload["decision_cases"]), 38)
        self.assertIn("not a fair substitute for a strong monolithic LLM baseline", report_text)


if __name__ == "__main__":
    unittest.main()
