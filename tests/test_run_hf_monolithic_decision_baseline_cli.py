from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_hf_monolithic_decision_baseline.py"


class RunHfMonolithicDecisionBaselineCliTests(unittest.TestCase):
    def test_help_does_not_require_heavy_dependencies(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--required-device-substring", completed.stdout)
        self.assertIn("--revision", completed.stdout)
        self.assertIn("--resume", completed.stdout)


if __name__ == "__main__":
    unittest.main()
