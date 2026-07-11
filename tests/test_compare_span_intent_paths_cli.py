import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_span_intent_paths.py"


class CompareSpanIntentPathsCliTests(unittest.TestCase):
    def test_cli_writes_comparison_for_two_intent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "span_eval.json"
            evaluation.write_text(
                json.dumps(
                    {
                        "metadata": {"model_name": "unit_span_model", "dataset": "test.jsonl"},
                        "records": [
                            {
                                "id": "cmd_1",
                                "split": "test",
                                "text": "Inspect crops.",
                                "expected_entities": [["action", 0, 7], ["target", 8, 13]],
                                "predicted_entities": [["action", 0, 7], ["target", 8, 13]],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "comparison.json"

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

            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"span_intent_assembly"', completed.stdout)
        self.assertIn("deterministic_v3", result["summary"])
        self.assertIn("hybrid_span_parser", result["summary"])
        self.assertIn("span_intent_assembly", result["summary"])
        self.assertEqual(len(result["records"]), 3)


if __name__ == "__main__":
    unittest.main()
