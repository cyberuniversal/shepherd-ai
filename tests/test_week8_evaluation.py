import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_evaluation import (  # noqa: E402
    evaluate_roadmap_intent_predictions,
)


class Week8EvaluationTests(unittest.TestCase):
    def test_roadmap_intent_evaluation_scores_exact_records_and_fields(self) -> None:
        predictions = {
            "metadata": {"runtime": {"torch_version": "test"}},
            "records": [
                {
                    "id": "week8_clause_001",
                    "transcript": "Send two drones north to inspect crops.",
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
                    "transcript": "Send one drone east to inspect irrigation.",
                    "hybrid_span_parser": {
                        "action": "send",
                        "count": 1,
                        "location": "east",
                        "target": "irrigation",
                        "constraints": [],
                    },
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "model.safetensors"
            checkpoint.write_bytes(b"frozen-test-checkpoint")

            result = evaluate_roadmap_intent_predictions(
                predictions,
                model_path=checkpoint,
            )

        self.assertEqual(result["scenario_source"], "roadmap_week8_fixed_scenario")
        self.assertEqual(result["model_role"], "frozen_trained_checkpoint")
        self.assertEqual(result["exact_match_accuracy"], 0.5)
        self.assertEqual(result["field_accuracy"], 0.9)
        self.assertEqual(result["records"][1]["field_matches"]["action"], False)
        self.assertEqual(result["records"][1]["gold_source"], "roadmap_specification")
        self.assertEqual(
            result["model"]["sha256"],
            hashlib.sha256(b"frozen-test-checkpoint").hexdigest(),
        )

    def test_roadmap_intent_evaluation_requires_both_fixed_clause_ids(self) -> None:
        predictions = {"records": [{"id": "week8_clause_001"}]}
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "model.safetensors"
            checkpoint.write_bytes(b"x")

            with self.assertRaisesRegex(ValueError, "missing fixed roadmap predictions"):
                evaluate_roadmap_intent_predictions(predictions, model_path=checkpoint)


if __name__ == "__main__":
    unittest.main()
