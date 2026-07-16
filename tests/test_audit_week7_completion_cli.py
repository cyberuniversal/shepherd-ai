import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week7_completion.py"


class AuditWeek7CompletionCliTests(unittest.TestCase):
    def test_cli_writes_completion_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audit.json"
            report = Path(tmp) / "audit.md"
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
            report_text = report.read_text(encoding="utf-8")

        self.assertIn("advancement_allowed", completed.stdout)
        self.assertTrue(payload["advancement_allowed"])
        self.assertEqual(payload["blockers"], [])
        self.assertIn("Research Gates", report_text)


if __name__ == "__main__":
    unittest.main()
