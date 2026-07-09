import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_intent import (
    assemble_hybrid_intent_from_entities,
    assemble_intent_from_entities,
    compare_intent_paths_from_span_evaluation,
    evaluate_span_intent_assembly,
    validate_assembled_intent,
)


class SpanIntentTests(unittest.TestCase):
    def test_assembles_normalized_intent_from_entities(self) -> None:
        text = "Have drone three photograph the cracked pavement near the gatehouse."
        intent = assemble_intent_from_entities(
            text,
            [
                ["count", 5, 16],
                ["action", 17, 27],
                ["target", 32, 48],
                ["location", 58, 67],
            ],
        )

        self.assertEqual(
            intent,
            {
                "action": "capture",
                "count": 1,
                "location": "gatehouse",
                "target": "cracked pavement",
                "constraints": [],
            },
        )

    def test_evaluates_predicted_entity_assembly_errors(self) -> None:
        evaluation = {
            "metadata": {"model_name": "hf_token_classifier", "dataset": "test.jsonl"},
            "records": [
                {
                    "id": "cmd_1",
                    "split": "test",
                    "text": "Inspect crops without crossing the road.",
                    "expected_entities": [["action", 0, 7], ["target", 8, 13], ["constraint", 14, 39]],
                    "predicted_entities": [["action", 0, 7], ["constraint", 8, 13], ["target", 14, 39]],
                }
            ],
        }

        result = evaluate_span_intent_assembly(evaluation)

        self.assertEqual(result["summary"]["records"], 1)
        self.assertEqual(result["summary"]["exact_record_accuracy"], 0.0)
        self.assertEqual(result["summary"]["field_error_counts"], {"constraints": 1, "target": 1})
        self.assertEqual(
            result["summary"]["predicted_validation_issue_counts"],
            {"suspicious_short_constraint": 1},
        )
        self.assertEqual(result["records"][0]["expected_intent"]["constraints"], ["without crossing the road"])
        self.assertEqual(result["records"][0]["predicted_intent"]["target"], "without crossing the road")

    def test_validates_missing_required_target_and_suspicious_constraint(self) -> None:
        validation = validate_assembled_intent(
            {
                "action": "inspect",
                "count": None,
                "location": None,
                "target": None,
                "constraints": ["of"],
            }
        )

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["issue_counts"], {"error": 1, "warning": 1})
        self.assertEqual(
            [issue["code"] for issue in validation["issues"]],
            ["missing_required_target", "suspicious_short_constraint"],
        )

    def test_compares_deterministic_and_span_assembled_paths(self) -> None:
        evaluation = {
            "metadata": {"model_name": "hf_token_classifier", "dataset": "test.jsonl"},
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

        comparison = compare_intent_paths_from_span_evaluation(evaluation)

        self.assertIn("deterministic_v3", comparison["summary"])
        self.assertIn("span_intent_assembly", comparison["summary"])
        self.assertIn("hybrid_span_parser", comparison["summary"])
        self.assertEqual(comparison["summary"]["span_intent_assembly"]["exact_record_accuracy"], 1.0)
        self.assertEqual(
            {row["system"] for row in comparison["records"]},
            {"deterministic_v3", "span_intent_assembly", "hybrid_span_parser"},
        )

    def test_hybrid_uses_parser_for_missing_action_and_filters_bad_constraint(self) -> None:
        text = "Inspect crops without crossing the road."
        intent = assemble_hybrid_intent_from_entities(
            text,
            [
                ["constraint", 8, 13],
                ["target", 14, 39],
            ],
        )

        self.assertEqual(intent["action"], "inspect")
        self.assertEqual(intent["constraints"], [])
        self.assertEqual(intent["target"], "without crossing the road")

    def test_hybrid_recovers_destination_from_battery_selection_constraint(self) -> None:
        text = "Send whichever drone has the most battery to the greenhouse."
        intent = assemble_hybrid_intent_from_entities(
            text,
            [
                ["action", 0, 4],
                ["count", 5, 20],
                ["constraint", 21, 59],
            ],
        )

        self.assertEqual(intent["action"], "send")
        self.assertEqual(intent["count"], 1)
        self.assertEqual(intent["location"], "greenhouse")
        self.assertIsNone(intent["target"])
        self.assertEqual(intent["constraints"], [])

    def test_hybrid_repairs_split_location_target_phrase(self) -> None:
        text = "Dispatch two drones to survey the parking lot for blocked exits."
        intent = assemble_hybrid_intent_from_entities(
            text,
            [
                ["action", 0, 8],
                ["action", 23, 29],
                ["count", 9, 19],
                ["location", 34, 41],
                ["target", 42, 45],
                ["target", 50, 63],
            ],
        )

        self.assertIsNone(intent["location"])
        self.assertEqual(intent["target"], "parking lot")

    def test_hybrid_recovers_equal_sections_constraint_from_secondary_target(self) -> None:
        text = "Send four drones to split the industrial zone into equal sections and report anything unusual."
        intent = assemble_hybrid_intent_from_entities(
            text,
            [
                ["action", 0, 4],
                ["action", 20, 25],
                ["count", 5, 16],
                ["target", 30, 45],
                ["target", 57, 65],
                ["target", 77, 93],
            ],
        )

        self.assertEqual(intent["target"], "industrial zone")
        self.assertEqual(intent["constraints"], ["into equal sections"])


if __name__ == "__main__":
    unittest.main()
