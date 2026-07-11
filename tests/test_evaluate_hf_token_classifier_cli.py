import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_hf_token_classifier.py"


class EvaluateHfTokenClassifierCliTests(unittest.TestCase):
    def test_help_runs_without_transformers_installed(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--model-dir", completed.stdout)
        self.assertIn("--evaluation-output", completed.stdout)
        self.assertIn("--error-analysis-output", completed.stdout)


if __name__ == "__main__":
    unittest.main()
