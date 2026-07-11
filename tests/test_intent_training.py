import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import (  # noqa: E402
    analyze_intent_errors,
    evaluate_intent_model,
    compare_with_deterministic_baseline,
    load_intent_model,
    load_labeled_commands,
    save_intent_model,
    summarize_labeled_commands,
    train_intent_model,
    validate_split_integrity,
)


class IntentTrainingTests(unittest.TestCase):
    def test_load_labeled_commands_requires_split_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "commands.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "cmd_001",
                        "text": "Inspect the north field.",
                        "split": "train",
                        "source": "synthetic_literature_guided",
                        "data_type": "synthetic_command",
                        "expected_intent": {
                            "action": "inspect",
                            "count": None,
                            "location": "north",
                            "target": "field",
                            "constraints": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = load_labeled_commands(path)

        self.assertEqual(records[0].id, "cmd_001")
        self.assertEqual(records[0].split, "train")
        self.assertEqual(records[0].source, "synthetic_literature_guided")
        self.assertEqual(records[0].expected_intent["target"], "field")

    def test_train_model_predicts_action_location_and_target_from_text(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        train_records = [record for record in records if record.split == "train"]
        test_record = next(record for record in records if record.id == "synthetic_test_001")

        model = train_intent_model(train_records)
        predicted = model.predict("Please survey the north field with two drones.").to_dict()

        self.assertEqual(test_record.expected_intent["action"], "inspect")
        self.assertEqual(predicted["action"], "inspect")
        self.assertEqual(predicted["count"], 2)
        self.assertEqual(predicted["location"], "north")
        self.assertEqual(predicted["target"], "field")
        self.assertEqual(predicted["parser"], "trained_nb_v0")

    def test_evaluate_intent_model_reports_held_out_metrics(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        train_records = [record for record in records if record.split == "train"]
        test_records = [record for record in records if record.split == "test"]

        model = train_intent_model(train_records)
        result = evaluate_intent_model(model, test_records, dataset_name="intent_labeled_synthetic")

        self.assertEqual(result["metadata"]["model_name"], "trained_nb_v0")
        self.assertEqual(result["metadata"]["dataset"], "intent_labeled_synthetic")
        self.assertEqual(result["summary"]["records"], len(test_records))
        self.assertGreaterEqual(result["summary"]["field_accuracy"], 0.75)
        self.assertIn("synthetic_test_001", {row["id"] for row in result["records"]})
        self.assertIn("field_error_counts", result["summary"])
        self.assertEqual(result["summary"]["field_error_counts"]["location"], 3)

    def test_summarize_labeled_commands_reports_split_and_label_counts(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")

        summary = summarize_labeled_commands(records)

        self.assertEqual(summary["records"], 26)
        self.assertEqual(summary["split_counts"], {"test": 4, "train": 18, "validation": 4})
        self.assertEqual(summary["data_type_counts"], {"synthetic_command": 26})
        self.assertGreaterEqual(summary["label_counts"]["location"]["north"], 4)

    def test_error_analysis_lists_failed_fields_and_records(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        train_records = [record for record in records if record.split == "train"]
        test_records = [record for record in records if record.split == "test"]
        model = train_intent_model(train_records)
        result = evaluate_intent_model(model, test_records, dataset_name="intent_labeled_synthetic")

        analysis = analyze_intent_errors(result)

        self.assertEqual(analysis["field_error_counts"], {"location": 3})
        self.assertEqual(
            [error["id"] for error in analysis["errors_by_field"]["location"]],
            ["synthetic_test_002", "synthetic_test_003", "synthetic_test_004"],
        )

    def test_train_model_with_schema_alias_features_improves_location_predictions(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        train_records = [record for record in records if record.split == "train"]
        test_records = [record for record in records if record.split == "test"]

        model = train_intent_model(
            train_records,
            model_name="trained_nb_v1",
            model_version="0.2",
            include_bigrams=True,
            include_alias_features=True,
        )
        result = evaluate_intent_model(model, test_records, dataset_name="intent_labeled_synthetic")

        self.assertEqual(model.model_name, "trained_nb_v1")
        self.assertEqual(model.parameters["feature_config"]["include_bigrams"], True)
        self.assertEqual(model.parameters["feature_config"]["include_alias_features"], True)
        self.assertEqual(result["summary"]["field_error_counts"].get("location", 0), 0)
        self.assertEqual(result["summary"]["exact_record_accuracy"], 1.0)

    def test_train_model_with_rule_overrides_handles_unseen_curated_targets(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "human_written_commands_curated_v1.jsonl")
        train_records = [record for record in records if record.split == "train"]
        target_record = next(record for record in records if record.id == "human_cmd_050")

        model = train_intent_model(
            train_records,
            model_name="trained_nb_human_curated_v2",
            model_version="0.2",
            include_bigrams=True,
            include_alias_features=True,
            use_rule_overrides=True,
        )
        predicted = model.predict(target_record.text).to_dict()

        self.assertEqual(predicted["action"], "inspect")
        self.assertEqual(predicted["count"], 1)
        self.assertIsNone(predicted["location"])
        self.assertEqual(predicted["target"], "water tank")
        self.assertEqual(predicted["constraints"], ["highest battery"])

    def test_rule_overrides_do_not_hallucinate_location_when_rule_location_is_absent(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "human_written_commands_curated_v1.jsonl")
        train_records = [record for record in records if record.split == "train"]
        target_record = next(record for record in records if record.id == "human_cmd_030")

        model = train_intent_model(
            train_records,
            model_name="trained_nb_human_curated_v2",
            model_version="0.2",
            include_bigrams=True,
            include_alias_features=True,
            use_rule_overrides=True,
        )
        predicted = model.predict(target_record.text).to_dict()

        self.assertEqual(predicted["target"], "greenhouse")
        self.assertIsNone(predicted["location"])

    def test_validate_split_integrity_rejects_duplicate_text_across_splits(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        duplicate = records[0]
        contaminated = records + [
            type(duplicate)(
                id="duplicate_test",
                text=duplicate.text,
                split="test",
                source=duplicate.source,
                data_type=duplicate.data_type,
                expected_intent=duplicate.expected_intent,
            )
        ]

        with self.assertRaises(ValueError):
            validate_split_integrity(contaminated)

    def test_compare_with_deterministic_baseline_reports_both_systems(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        model = train_intent_model([record for record in records if record.split == "train"])
        test_records = [record for record in records if record.split == "test"]

        comparison = compare_with_deterministic_baseline(
            model,
            test_records,
            dataset_name="intent_labeled_synthetic",
        )

        self.assertEqual(set(comparison["systems"]), {"deterministic_v3", "trained_nb_v0"})
        self.assertEqual(comparison["metadata"]["dataset"], "intent_labeled_synthetic")
        self.assertEqual(comparison["systems"]["trained_nb_v0"]["summary"]["records"], len(test_records))

    def test_model_round_trips_through_json(self) -> None:
        records = load_labeled_commands(ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl")
        model = train_intent_model(
            [record for record in records if record.split == "train"],
            model_name="trained_nb_v1",
            model_version="0.2",
            include_bigrams=True,
            include_alias_features=True,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intent_model.json"
            save_intent_model(model, path)
            loaded = load_intent_model(path)

        self.assertEqual(
            loaded.predict("Return all drones.").to_dict()["action"],
            model.predict("Return all drones.").to_dict()["action"],
        )


if __name__ == "__main__":
    unittest.main()
