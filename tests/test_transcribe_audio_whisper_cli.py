import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "transcribe_audio_whisper.py"


class TranscribeAudioWhisperCliTests(unittest.TestCase):
    def test_help_documents_required_outputs_and_device_guard(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--predictions-output", completed.stdout)
        self.assertIn("--evaluation-output", completed.stdout)
        self.assertIn("--required-device-substring", completed.stdout)


if __name__ == "__main__":
    unittest.main()
