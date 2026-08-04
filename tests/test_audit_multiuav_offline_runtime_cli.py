import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_multiuav_offline_runtime.py"


class AuditMultiUavOfflineRuntimeCliTests(unittest.TestCase):
    def test_audit_records_contract_without_claiming_model_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "audit.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["valid"])
        self.assertEqual(len(result["backend_contracts"]), 2)
        self.assertTrue(
            all(
                item["local_files_only"]
                and item["revision"] != "main"
                and not item["trust_remote_code"]
                for item in result["backend_contracts"]
            )
        )
        self.assertTrue(result["offline_contract"]["non_loopback_blocked"])
        self.assertEqual(
            result["offline_contract"]["isolation_scope"],
            "python_process",
        )
        self.assertFalse(result["weights_cached"])
        self.assertFalse(result["weights_loaded"])
        self.assertFalse(result["model_invoked"])
        self.assertFalse(result["study_cases_evaluated"])


if __name__ == "__main__":
    unittest.main()
