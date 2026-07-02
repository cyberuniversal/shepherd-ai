import unittest

from shepherd_ai.hf_token_analysis import (
    build_span_review_queue,
    evaluate_hf_token_predictions,
    summarize_hf_token_evaluation,
)


class HfTokenAnalysisTests(unittest.TestCase):
    def test_evaluates_entity_and_token_errors(self) -> None:
        records = [
            {
                "id": "cmd_1",
                "split": "test",
                "text": "Inspect north field.",
                "tokens": ["Inspect", "north", "field", "."],
                "offsets": [[0, 7], [8, 13], [14, 19], [19, 20]],
                "labels": ["B-action", "B-target", "I-target", "O"],
                "data_type": "human_verified_span_command",
            }
        ]

        evaluation = evaluate_hf_token_predictions(
            records,
            {"cmd_1": ["B-action", "B-location", "I-location", "O"]},
            dataset_name="test.jsonl",
            model_name="hf_token_classifier",
        )

        self.assertEqual(evaluation["summary"]["records"], 1)
        self.assertEqual(evaluation["summary"]["token_accuracy"], 0.5)
        self.assertEqual(evaluation["summary"]["entity_f1"], 0.5)
        self.assertEqual(evaluation["records"][0]["expected_entities"], [["action", 0, 7], ["target", 8, 19]])
        self.assertEqual(evaluation["records"][0]["predicted_entities"], [["action", 0, 7], ["location", 8, 19]])

    def test_summary_counts_false_negative_fields(self) -> None:
        records = [
            {
                "id": "cmd_1",
                "split": "test",
                "text": "Inspect crops.",
                "tokens": ["Inspect", "crops", "."],
                "offsets": [[0, 7], [8, 13], [13, 14]],
                "labels": ["B-action", "B-target", "O"],
                "data_type": "human_verified_span_command",
            }
        ]

        evaluation = evaluate_hf_token_predictions(
            records,
            {"cmd_1": ["B-action", "O", "O"]},
            dataset_name="test.jsonl",
            model_name="hf_token_classifier",
        )

        summary = summarize_hf_token_evaluation(evaluation)
        self.assertEqual(summary["records_with_errors"], 1)
        self.assertEqual(summary["false_negative_entity_counts"], {"target": 1})

    def test_builds_focus_prioritized_human_review_queue(self) -> None:
        evaluation = {
            "metadata": {"model_name": "hf_token_classifier", "dataset": "test.jsonl"},
            "records": [
                {
                    "id": "cmd_clean",
                    "split": "test",
                    "text": "Inspect crops.",
                    "tokens": ["Inspect", "crops", "."],
                    "offsets": [[0, 7], [8, 13], [13, 14]],
                    "expected_tags": ["B-action", "B-target", "O"],
                    "predicted_tags": ["B-action", "B-target", "O"],
                    "token_matches": [True, True, True],
                    "expected_entities": [["action", 0, 7], ["target", 8, 13]],
                    "predicted_entities": [["action", 0, 7], ["target", 8, 13]],
                },
                {
                    "id": "cmd_constraint_confusion",
                    "split": "test",
                    "text": "Inspect crops without crossing the road.",
                    "tokens": ["Inspect", "crops", "without", "crossing", "the", "road", "."],
                    "offsets": [[0, 7], [8, 13], [14, 21], [22, 30], [31, 34], [35, 39], [39, 40]],
                    "expected_tags": [
                        "B-action",
                        "B-target",
                        "B-constraint",
                        "I-constraint",
                        "I-constraint",
                        "I-constraint",
                        "O",
                    ],
                    "predicted_tags": ["B-action", "B-constraint", "B-target", "I-target", "I-target", "I-target", "O"],
                    "token_matches": [True, False, False, False, False, False, True],
                    "expected_entities": [["action", 0, 7], ["constraint", 14, 39], ["target", 8, 13]],
                    "predicted_entities": [["action", 0, 7], ["constraint", 8, 13], ["target", 14, 39]],
                },
                {
                    "id": "cmd_action_error",
                    "split": "test",
                    "text": "Return to base.",
                    "tokens": ["Return", "to", "base", "."],
                    "offsets": [[0, 6], [7, 9], [10, 14], [14, 15]],
                    "expected_tags": ["B-action", "O", "B-location", "O"],
                    "predicted_tags": ["O", "O", "B-location", "O"],
                    "token_matches": [False, True, True, True],
                    "expected_entities": [["action", 0, 6], ["location", 10, 14]],
                    "predicted_entities": [["location", 10, 14]],
                },
            ],
        }

        queue = build_span_review_queue(evaluation, focus_fields=("target", "constraint"))

        self.assertEqual(queue["summary"]["records_requiring_review"], 2)
        self.assertEqual(queue["records"][0]["id"], "cmd_constraint_confusion")
        self.assertEqual(queue["records"][0]["focus_error_count"], 4)
        self.assertIn("target", queue["records"][0]["review_fields"])
        self.assertIn("constraint", queue["records"][0]["review_fields"])
        self.assertEqual(queue["records"][0]["label_status"], "needs_human_review")
        self.assertEqual(queue["records"][0]["prediction_status"], "model_generated_not_gold")
        self.assertEqual(queue["records"][1]["id"], "cmd_action_error")


if __name__ == "__main__":
    unittest.main()
