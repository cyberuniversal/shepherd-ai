import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_span_tagger_errors.py"


class AnalyzeSpanTaggerErrorsCliTests(unittest.TestCase):
    def test_cli_writes_error_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation.json"
            output = root / "analysis.json"
            evaluation.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "id": "span_cmd_001",
                                "text": "Inspect the greenhouse.",
                                "tokens": ["Inspect", "the", "greenhouse", "."],
                                "offsets": [[0, 7], [8, 11], [12, 22], [22, 23]],
                                "expected_tags": ["B-action", "O", "B-target", "O"],
                                "predicted_tags": ["B-action", "O", "O", "O"],
                                "expected_entities": [["action", 0, 7], ["target", 12, 22]],
                                "predicted_entities": [["action", 0, 7]],
                            }
                        ]
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

        self.assertIn('"worst_records"', completed.stdout)
        self.assertEqual(analysis["false_negative_entity_counts"], {"target": 1})


if __name__ == "__main__":
    unittest.main()
