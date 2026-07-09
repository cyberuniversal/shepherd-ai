import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GROUND_SCRIPT = ROOT / "scripts" / "ground_intent.py"
EVALUATE_SCRIPT = ROOT / "scripts" / "evaluate_grounding.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
EXAMPLES_PATH = ROOT / "datasets" / "maps" / "grounding_examples_v1.jsonl"


class GroundIntentCliTests(unittest.TestCase):
    def test_ground_intent_cli_writes_grounded_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "grounded.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(GROUND_SCRIPT),
                    "--command",
                    "Send two drones north and inspect the crops.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("Wrote", completed.stdout)
        self.assertTrue(payload["grounded_intent"]["ready_for_planning"])
        refs = {
            reference["field"]: reference
            for reference in payload["grounded_intent"]["references"]
        }
        self.assertEqual(refs["location"]["location"]["id"], "loc_north_field")
        self.assertEqual(payload["map_objects"][0]["location_id"], "loc_north_field")
        self.assertEqual(payload["map_objects"][0]["geometry_type"], "circle")
        self.assertEqual(payload["map_objects"][0]["map_role"], "mission_area")
        self.assertFalse(payload["clarification_report"]["blocks_planning"])
        self.assertEqual(payload["clarification_report"]["requests"], [])

    def test_ground_intent_cli_includes_clarification_for_ambiguous_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "grounded.json"

            subprocess.run(
                [
                    sys.executable,
                    str(GROUND_SCRIPT),
                    "--command",
                    "Monitor the road until the ambulance arrives.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(payload["clarification_report"]["blocks_planning"])
        self.assertEqual(len(payload["clarification_report"]["requests"]), 2)

    def test_evaluate_grounding_cli_writes_development_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "grounding_eval.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE_SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--dataset",
                    str(EXAMPLES_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(payload["summary"]["records"], 6)
        self.assertEqual(
            payload["metadata"]["parameters"]["matching"],
            "normalized_name_or_alias_exact_or_embedded_longest_match",
        )

    def test_evaluate_grounding_cli_scores_constraint_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "constraint_eval.jsonl"
            output = root / "grounding_eval.json"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "constraint_eval_001",
                        "text": "Inspect the greenhouse and avoid the power lines.",
                        "split": "unit_test",
                        "source": "unit_test",
                        "data_type": "synthetic_grounding_example",
                        "expected_grounding": {
                            "location": {"status": "not_provided", "location_id": None},
                            "target": {"status": "grounded", "location_id": "loc_greenhouse"},
                            "constraint[0]": {"status": "grounded", "location_id": "obs_power_lines"},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE_SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--dataset",
                    str(dataset),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["records"], 1)
        self.assertEqual(payload["summary"]["total_references"], 3)
        self.assertEqual(payload["summary"]["reference_matches"], 3)
        self.assertEqual(
            payload["records"][0]["actual_grounding"]["constraint[0]"]["location_id"],
            "obs_power_lines",
        )


if __name__ == "__main__":
    unittest.main()
