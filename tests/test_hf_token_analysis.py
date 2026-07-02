import unittest

from shepherd_ai.hf_token_analysis import evaluate_hf_token_predictions, summarize_hf_token_evaluation


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


if __name__ == "__main__":
    unittest.main()
