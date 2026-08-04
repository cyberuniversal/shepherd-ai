import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_multiuav_execution_scope.py"


class AuditMultiUavExecutionScopeCliTests(unittest.TestCase):
    def test_audit_freezes_static_scope_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "scope.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["valid"])
        self.assertEqual(result["primary_scope"], "static_plan_fidelity")
        self.assertFalse(result["official_server_invoked_by_this_audit"])
        self.assertFalse(result["study_cases_evaluated"])


if __name__ == "__main__":
    unittest.main()
