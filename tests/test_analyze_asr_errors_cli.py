import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_asr_errors.py"


class AnalyzeAsrErrorsCliTests(unittest.TestCase):
    def test_cli_writes_transcript_error_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation.json"
            output = root / "analysis.json"
            evaluation.write_text(
                json.dumps(
                    {
                        "metadata": {"model_name": "whisper", "model_version": "base"},
                        "summary": {"records": 1, "mean_word_error_rate": 0.1},
                        "records": [
                            {
                                "id": "audio_006",
                                "expected": "Send two drones west but keep them below fifty meters.",
                                "predicted": "Send two drones west, but keep them below 50 meters.",
                                "word_error_rate": 0.1,
                                "exact_match": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--evaluation",
                    str(evaluation),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            analysis = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"error_record_count"', completed.stdout)
        self.assertEqual(analysis["error_record_count"], 1)
        self.assertEqual(analysis["substitution_counts"], {"fifty -> 50": 1})


if __name__ == "__main__":
    unittest.main()
