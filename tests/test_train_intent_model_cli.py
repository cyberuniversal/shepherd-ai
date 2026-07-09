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
            model_path = root / "outputs" / "models" / "intent_nb_v1.json"
            metrics_path = root / "outputs" / "evaluations" / "intent_nb_v1_metrics.json"
            comparison_path = root / "outputs" / "evaluations" / "intent_nb_v1_vs_deterministic.json"
            validation_path = root / "outputs" / "evaluations" / "intent_nb_v1_validation_metrics.json"

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
                    "--validation-output",
                    str(validation_path),
                    "--seed",
                    "17",
                    "--model-name",
                    "trained_nb_v1",
                    "--model-version",
                    "0.2",
                    "--include-bigrams",
                    "--include-alias-features",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            model = json.loads(model_path.read_text(encoding="utf-8"))
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
            validation = json.loads(validation_path.read_text(encoding="utf-8"))

        self.assertIn('"test_records"', completed.stdout)
        self.assertIn('"validation_records"', completed.stdout)
        self.assertEqual(model["model_name"], "trained_nb_v1")
        self.assertEqual(model["model_version"], "0.2")
        self.assertEqual(model["parameters"]["feature_config"]["include_bigrams"], True)
        self.assertEqual(model["parameters"]["feature_config"]["include_alias_features"], True)
        self.assertEqual(model["training_metadata"]["dataset"], str(DATASET))
        self.assertEqual(model["training_metadata"]["random_seed"], 17)
        self.assertEqual(model["training_metadata"]["split_counts"], {"test": 4, "train": 18, "validation": 4})
        self.assertEqual(model["training_metadata"]["dataset_summary"]["records"], 26)
        self.assertEqual(
            model["training_metadata"]["evaluation_artifacts"],
            {
                "comparison": str(comparison_path),
                "metrics": str(metrics_path),
                "validation": str(validation_path),
            },
        )
        self.assertEqual(metrics["metadata"]["split"], "test")
        self.assertEqual(metrics["metadata"]["random_seed"], 17)
        self.assertEqual(metrics["summary"]["field_error_counts"], {})
        self.assertEqual(validation["metadata"]["split"], "validation")
        self.assertEqual(validation["summary"]["records"], 4)
        self.assertIn("deterministic_v3", comparison["systems"])
        self.assertIn("trained_nb_v1", comparison["systems"])


if __name__ == "__main__":
    unittest.main()
