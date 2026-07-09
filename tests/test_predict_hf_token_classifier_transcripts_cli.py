import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "predict_hf_token_classifier_transcripts.py"


class PredictHfTokenClassifierTranscriptsCliTests(unittest.TestCase):
    def test_help_runs_without_transformers_installed(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--input-jsonl", completed.stdout)
        self.assertIn("--transcript-field", completed.stdout)
        self.assertIn("--required-device-substring", completed.stdout)


if __name__ == "__main__":
    unittest.main()
