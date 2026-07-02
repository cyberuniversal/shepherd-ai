import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_span_tagger.py"
DATASET = ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl"


class TrainSpanTaggerCliTests(unittest.TestCase):
    def test_cli_writes_model_validation_and_test_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "outputs" / "model_artifacts" / "span_nb_v0.json"
            metrics_path = root / "outputs" / "evaluations" / "span_nb_v0_metrics.json"
            validation_path = root / "outputs" / "evaluations" / "span_nb_v0_validation_metrics.json"

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
                    "--validation-output",
                    str(validation_path),
                    "--seed",
                    "17",
                    "--model-name",
                    "span_nb_v0",
                    "--model-version",
                    "0.1",
                    "--use-transitions",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            model = json.loads(model_path.read_text(encoding="utf-8"))
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            validation = json.loads(validation_path.read_text(encoding="utf-8"))

        self.assertIn('"test_records"', completed.stdout)
        self.assertEqual(model["model_name"], "span_nb_v0")
        self.assertEqual(model["parameters"]["use_transitions"], True)
        self.assertIn("<START>", model["transition_counts"])
        self.assertEqual(model["training_metadata"]["random_seed"], 17)
        self.assertEqual(model["training_metadata"]["split_counts"], {"test": 10, "train": 30, "validation": 10})
        self.assertEqual(metrics["metadata"]["split"], "test")
        self.assertIn("entity_f1", metrics["summary"])
        self.assertEqual(validation["metadata"]["split"], "validation")


if __name__ == "__main__":
    unittest.main()
