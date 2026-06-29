import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_intent_model.py"
DATASET = ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl"


class TrainIntentModelCliTests(unittest.TestCase):
    def test_cli_writes_model_metrics_and_comparison_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "outputs" / "models" / "intent_nb_v0.json"
            metrics_path = root / "outputs" / "evaluations" / "intent_nb_v0_metrics.json"
            comparison_path = root / "outputs" / "evaluations" / "intent_nb_v0_vs_deterministic.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(DATASET),
                    "--model-output",
                    str(model_path),
                    "--metrics-output",
                    str(metrics_path),
                    "--comparison-output",
                    str(comparison_path),
                    "--seed",
                    "17",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            model = json.loads(model_path.read_text(encoding="utf-8"))
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))

        self.assertIn('"test_records"', completed.stdout)
        self.assertEqual(model["model_name"], "trained_nb_v0")
        self.assertEqual(model["training_metadata"]["dataset"], str(DATASET))
        self.assertEqual(model["training_metadata"]["random_seed"], 17)
        self.assertEqual(model["training_metadata"]["split_counts"], {"test": 4, "train": 18, "validation": 4})
        self.assertEqual(
            model["training_metadata"]["evaluation_artifacts"],
            {
                "comparison": str(comparison_path),
                "metrics": str(metrics_path),
            },
        )
        self.assertEqual(metrics["metadata"]["split"], "test")
        self.assertEqual(metrics["metadata"]["random_seed"], 17)
        self.assertIn("deterministic_v0", comparison["systems"])
        self.assertIn("trained_nb_v0", comparison["systems"])


if __name__ == "__main__":
    unittest.main()
