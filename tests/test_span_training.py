import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_training import (  # noqa: E402
    analyze_span_tagger_errors,
    evaluate_span_tagger,
    load_span_tagger,
    records_from_span_commands,
    save_span_tagger,
    summarize_span_tag_records,
    train_span_tagger,
)


class SpanTrainingTests(unittest.TestCase):
    def test_records_from_span_commands_converts_to_bio_records(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")

        first = records[0]
        self.assertEqual(first.id, "human_cmd_001")
        self.assertEqual(first.split, "train")
        self.assertEqual(first.tokens[1:3], ["two", "drones"])
        self.assertEqual(first.tags[1:3], ["B-count", "I-count"])

    def test_summarize_span_tag_records_reports_splits_and_tags(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")

        summary = summarize_span_tag_records(records)

        self.assertEqual(summary["records"], 50)
        self.assertEqual(summary["split_counts"], {"test": 10, "train": 30, "validation": 10})
        self.assertEqual(summary["tag_counts"]["B-action"], 50)

    def test_train_span_tagger_predicts_bio_tags(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")
        train_records = [record for record in records if record.split == "train"]

        model = train_span_tagger(train_records, model_name="span_nb_v0", model_version="0.1")
        prediction = model.predict(["Inspect", "the", "greenhouse", "."])

        self.assertEqual(len(prediction), 4)
        self.assertIn("B-action", set(prediction))

    def test_train_span_tagger_can_use_transition_decoding(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")
        train_records = [record for record in records if record.split == "train"]

        model = train_span_tagger(
            train_records,
            model_name="span_nb_v1",
            model_version="0.2",
            use_transitions=True,
        )
        prediction = model.predict(["Search", "the", "open", "field", "for", "a", "missing", "vehicle", "."])

        self.assertEqual(model.parameters["use_transitions"], True)
        self.assertIn("<START>", model.transition_counts)
        self.assertEqual(len(prediction), 9)

    def test_evaluate_span_tagger_reports_token_and_entity_metrics(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")
        train_records = [record for record in records if record.split == "train"]
        validation_records = [record for record in records if record.split == "validation"]
        model = train_span_tagger(train_records, model_name="span_nb_v0", model_version="0.1")

        result = evaluate_span_tagger(model, validation_records, dataset_name="human_verified_span_commands")

        self.assertEqual(result["metadata"]["model_name"], "span_nb_v0")
        self.assertEqual(result["summary"]["records"], len(validation_records))
        self.assertIn("token_accuracy", result["summary"])
        self.assertIn("entity_f1", result["summary"])
        self.assertEqual(len(result["records"]), len(validation_records))

    def test_analyze_span_tagger_errors_groups_confusions_and_entity_errors(self) -> None:
        evaluation = {
            "records": [
                {
                    "id": "span_cmd_001",
                    "text": "Inspect the greenhouse.",
                    "tokens": ["Inspect", "the", "greenhouse", "."],
                    "offsets": [[0, 7], [8, 11], [12, 22], [22, 23]],
                    "expected_tags": ["B-action", "O", "B-target", "O"],
                    "predicted_tags": ["B-action", "O", "O", "O"],
                    "expected_entities": [["action", 0, 7], ["target", 12, 22]],
                    "predicted_entities": [["action", 0, 7]],
                },
                {
                    "id": "span_cmd_002",
                    "text": "Scan the car.",
                    "tokens": ["Scan", "the", "car", "."],
                    "offsets": [[0, 4], [5, 8], [9, 12], [12, 13]],
                    "expected_tags": ["B-action", "O", "B-target", "O"],
                    "predicted_tags": ["B-action", "O", "B-location", "O"],
                    "expected_entities": [["action", 0, 4], ["target", 9, 12]],
                    "predicted_entities": [["action", 0, 4], ["location", 9, 12]],
                },
            ]
        }

        analysis = analyze_span_tagger_errors(evaluation)

        self.assertEqual(analysis["token_confusion"]["B-target"]["O"], 1)
        self.assertEqual(analysis["token_confusion"]["B-target"]["B-location"], 1)
        self.assertEqual(analysis["false_negative_entity_counts"]["target"], 2)
        self.assertEqual(analysis["false_positive_entity_counts"]["location"], 1)
        self.assertEqual(analysis["worst_records"][0]["id"], "span_cmd_001")

    def test_span_tagger_round_trips_through_json(self) -> None:
        records = records_from_span_commands(ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl")
        train_records = [record for record in records if record.split == "train"]
        model = train_span_tagger(train_records, model_name="span_nb_v0", model_version="0.1")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "span_model.json"
            save_span_tagger(model, path)
            loaded = load_span_tagger(path)

        tokens = ["Scan", "the", "car", "."]
        self.assertEqual(loaded.predict(tokens), model.predict(tokens))


if __name__ == "__main__":
    unittest.main()
