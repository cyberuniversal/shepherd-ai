import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_week8_completion.py"


class AuditWeek8CompletionCliTests(unittest.TestCase):
    def test_cli_reports_completed_result_from_registered_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "audit.json"
            report = Path(temporary) / "audit.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--json-output",
                    str(output),
                    "--markdown-output",
                    str(report),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"completion_allowed": true', completed.stdout)
        self.assertTrue(payload["completion_allowed"])
        self.assertEqual(
            payload["decision"],
            "week8_complete_for_advancement_to_week9_paper_draft",
        )
        self.assertEqual(payload["blockers"], [])
        self.assertTrue(payload["gates_passed"])


if __name__ == "__main__":
    unittest.main()
