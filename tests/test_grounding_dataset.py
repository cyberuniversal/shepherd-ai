import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.grounding_dataset import (  # noqa: E402
    load_grounding_dataset,
    summarize_grounding_dataset,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class GroundingDatasetTests(unittest.TestCase):
    def test_load_grounding_dataset_validates_known_location_ids(self) -> None:
        locations = load_map_locations(MAP_PATH)

        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "grounding.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "grounding_001",
                        "text": "Inspect the greenhouse.",
                        "split": "synthetic_holdout",
                        "source": "unit_test",
                        "data_type": "synthetic_grounding_example",
                        "expected_grounding": {
                            "location": {"status": "not_provided", "location_id": None},
                            "target": {"status": "grounded", "location_id": "loc_greenhouse"},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = load_grounding_dataset(dataset, locations)
            summary = summarize_grounding_dataset(records)

        self.assertEqual(summary.records, 1)
        self.assertEqual(summary.expected_status_counts["grounded"], 1)
        self.assertEqual(summary.grounded_location_ids, ["loc_greenhouse"])

    def test_load_grounding_dataset_rejects_unknown_location_id(self) -> None:
        locations = load_map_locations(MAP_PATH)

        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "grounding.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "grounding_001",
                        "text": "Inspect the greenhouse.",
                        "split": "synthetic_holdout",
                        "source": "unit_test",
                        "data_type": "synthetic_grounding_example",
                        "expected_grounding": {
                            "target": {"status": "grounded", "location_id": "missing_location"},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown location_id"):
                load_grounding_dataset(dataset, locations)

    def test_load_grounding_dataset_rejects_ambiguous_without_candidates(self) -> None:
        locations = load_map_locations(MAP_PATH)

        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "grounding.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "grounding_001",
                        "text": "Scan the road.",
                        "split": "synthetic_holdout",
                        "source": "unit_test",
                        "data_type": "synthetic_grounding_example",
                        "expected_grounding": {
                            "location": {"status": "ambiguous", "location_id": None},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "requires at least two candidate_ids"):
                load_grounding_dataset(dataset, locations)


if __name__ == "__main__":
    unittest.main()
