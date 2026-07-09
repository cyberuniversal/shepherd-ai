import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_grounding_dataset.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class ValidateGroundingDatasetCliTests(unittest.TestCase):
    def test_cli_writes_grounding_dataset_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "grounding.jsonl"
            output = root / "summary.json"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "grounding_001",
                        "text": "Scan the road for blocked exits.",
                        "split": "synthetic_holdout",
                        "source": "unit_test",
                        "data_type": "synthetic_grounding_example",
                        "expected_grounding": {
                            "location": {
                                "status": "ambiguous",
                                "location_id": None,
                                "candidate_ids": ["loc_service_road", "loc_main_road"],
                            },
                            "target": {"status": "unresolved", "location_id": None},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--dataset",
                    str(dataset),
                    "--summary-output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["ambiguous_reference_count"], 1)
        self.assertEqual(summary["unresolved_reference_count"], 1)


if __name__ == "__main__":
    unittest.main()
