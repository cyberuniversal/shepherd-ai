import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/evaluate_week8_intent.py"


class EvaluateWeek8IntentCliTests(unittest.TestCase):
    def test_cli_writes_fixed_scenario_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            predictions = root / "predictions.json"
            predictions.write_text(
                json.dumps(
                    {
                        "metadata": {},
                        "records": [
                            {
                                "id": "week8_clause_001",
                                "hybrid_span_parser": {
                                    "action": "inspect",
                                    "count": 2,
                                    "location": "north",
                                    "target": "crops",
                                    "constraints": [],
                                },
                            },
                            {
                                "id": "week8_clause_002",
                                "hybrid_span_parser": {
                                    "action": "inspect",
                                    "count": 1,
                                    "location": "east",
                                    "target": "irrigation",
                                    "constraints": [],
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            checkpoint = root / "model.safetensors"
            checkpoint.write_bytes(b"checkpoint")
            output = root / "evaluation.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--predictions",
                    str(predictions),
                    "--model-path",
                    str(checkpoint),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"exact_match_accuracy": 1.0', completed.stdout)
        self.assertEqual(result["exact_match_denominator"], 2)


if __name__ == "__main__":
    unittest.main()
