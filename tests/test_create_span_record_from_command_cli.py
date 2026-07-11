import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_span_record_from_command.py"


class CreateSpanRecordFromCommandCliTests(unittest.TestCase):
    def test_cli_labels_existing_command_by_id_without_retyping_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "commands.jsonl"
            output_path = root / "span_commands.jsonl"
            command = {
                "id": "human_cmd_001",
                "text": "Send two drones north and inspect the crops.",
                "split": "train",
                "source": "manual_week2_collection_v1",
                "data_type": "human_written_command_assistant_labeled",
                "expected_intent": {
                    "action": "inspect",
                    "count": 2,
                    "location": "north",
                    "target": "crops",
                    "constraints": [],
                },
            }
            input_path.write_text(json.dumps(command) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(input_path),
                    "--id",
                    "human_cmd_001",
                    "--output",
                    str(output_path),
                    "--count-span",
                    "two drones",
                    "--location-span",
                    "north",
                    "--action-span",
                    "inspect",
                    "--target-span",
                    "crops",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            record = json.loads(output_path.read_text(encoding="utf-8").strip())

        self.assertIn("human_cmd_001", completed.stdout)
        self.assertEqual(record["id"], "human_cmd_001")
        self.assertEqual(record["base_command_id"], "human_cmd_001")
        self.assertEqual(record["text"], command["text"])
        self.assertEqual(record["split"], "train")
        self.assertEqual(record["expected_intent"], command["expected_intent"])
        self.assertEqual(
            [(span["field"], span["text"]) for span in record["spans"]],
            [("count", "two drones"), ("location", "north"), ("action", "inspect"), ("target", "crops")],
        )

    def test_cli_allows_span_id_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "commands.jsonl"
            output_path = root / "span_commands.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "id": "human_cmd_013",
                        "text": "Inspect the greenhouse.",
                        "split": "train",
                        "source": "manual_week2_collection_v1",
                        "data_type": "human_written_command_assistant_labeled",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(input_path),
                    "--id",
                    "human_cmd_013",
                    "--span-id",
                    "span_cmd_013",
                    "--output",
                    str(output_path),
                    "--action-span",
                    "Inspect",
                    "--target-span",
                    "greenhouse",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            record = json.loads(output_path.read_text(encoding="utf-8").strip())

        self.assertEqual(record["id"], "span_cmd_013")
        self.assertEqual(record["base_command_id"], "human_cmd_013")


if __name__ == "__main__":
    unittest.main()
