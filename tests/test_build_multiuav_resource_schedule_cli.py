import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BuildResourceScheduleCliTests(unittest.TestCase):
    def test_writes_candidate_manifest_without_running_models(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "resource_subset.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_multiuav_resource_schedule.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(artifact["summary"]["source_tasks"], 30)
            self.assertEqual(artifact["summary"]["strata"], 15)
            self.assertEqual(artifact["summary"]["conditions"], 24)
            self.assertEqual(artifact["summary"]["planned_method_case_rows"], 3600)
            self.assertFalse(artifact["model_invocation"]["performed"])
            self.assertEqual(
                artifact["claim_status"],
                "candidate_source_subset_and_condition_order_only",
            )


if __name__ == "__main__":
    unittest.main()
