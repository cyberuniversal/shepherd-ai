import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_span_intent_assembly.py"


class EvaluateSpanIntentAssemblyCliTests(unittest.TestCase):
    def test_cli_writes_span_to_intent_metrics(self) -> None:
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
            output = root / "assembled.json"

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

        self.assertIn('"exact_record_accuracy": 1.0', completed.stdout)
        self.assertEqual(result["summary"]["field_accuracy"], 1.0)
        self.assertEqual(result["records"][0]["predicted_intent"]["target"], "crops")
        self.assertEqual(result["metadata"]["source_model"], "unit_span_model")


if __name__ == "__main__":
    unittest.main()
