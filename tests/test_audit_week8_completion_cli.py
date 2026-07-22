import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_week8_completion.py"


class AuditWeek8CompletionCliTests(unittest.TestCase):
    def test_cli_preserves_current_incomplete_result(self) -> None:
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

        self.assertIn('"completion_allowed": false', completed.stdout)
        self.assertFalse(payload["completion_allowed"])
        self.assertIn("exact_scenario_asr_evidence", payload["blockers"])
        self.assertIn("mission_assigned_vision_evaluation", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
