import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SCRIPT = ROOT / "scripts" / "train_intent_model.py"
EVAL_SCRIPT = ROOT / "scripts" / "evaluate_intent_model.py"
DATASET = ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl"


class EvaluateIntentModelCliTests(unittest.TestCase):
    def test_cli_evaluates_saved_model_on_selected_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "intent_nb_v1.json"
            metrics_path = root / "intent_eval.json"

            subprocess.run(
                [
                    sys.executable,
                    str(TRAIN_SCRIPT),
                    "--dataset",
                    str(DATASET),
                    "--model-output",
                    str(model_path),
                    "--metrics-output",
                    str(root / "train_metrics.json"),
                    "--comparison-output",
                    str(root / "comparison.json"),
                    "--seed",
                    "17",
                    "--model-name",
                    "trained_nb_v1",
                    "--model-version",
                    "0.2",
                    "--include-bigrams",
                    "--include-alias-features",
                    "--alias-feature-weight",
                    "3",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPT),
                    "--model",
                    str(model_path),
                    "--dataset",
                    str(DATASET),
                    "--split",
                    "validation",
                    "--output",
                    str(metrics_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(metrics["metadata"]["model_name"], "trained_nb_v1")
        self.assertEqual(metrics["metadata"]["split"], "validation")
        self.assertEqual(metrics["summary"]["records"], 4)
        self.assertEqual(metrics["summary"]["field_error_counts"], {})


if __name__ == "__main__":
    unittest.main()
