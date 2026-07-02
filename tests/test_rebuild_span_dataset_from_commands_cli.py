import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rebuild_span_dataset_from_commands.py"


class RebuildSpanDatasetFromCommandsCliTests(unittest.TestCase):
    def test_cli_rebuilds_output_from_saved_create_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "commands.jsonl"
            output = root / "human_verified_span_commands.jsonl"
            summary = root / "summary.json"
            bio = root / "bio.jsonl"
            command_file = root / "span_label_commands.txt"
            source.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
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
                        ),
                        json.dumps(
                            {
                                "id": "human_cmd_013",
                                "text": "Inspect the greenhouse.",
                                "split": "validation",
                                "source": "manual_week2_collection_v1",
                                "data_type": "human_written_command_assistant_labeled",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            output.write_text("old data\n", encoding="utf-8")
            command_file.write_text(
                "\n".join(
                    [
                        "python -c \"from pathlib import Path; Path('datasets/commands/human_verified_span_commands.jsonl').unlink(missing_ok=True)\"",
                        f'python scripts/create_span_record_from_command.py --input "{source}" --id human_cmd_001 --output ignored.jsonl --count-span "two drones" --location-span "north" --action-span "inspect" --target-span "crops"',
                        f'python scripts/create_span_record_from_command.py --input "{source}" --id human_cmd_013 --output ignored.jsonl --action-span "Inspect" --target-span "greenhouse"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--commands-file",
                    str(command_file),
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                    "--bio-output",
                    str(bio),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            summary_payload = json.loads(summary.read_text(encoding="utf-8"))
            bio_records = [json.loads(line) for line in bio.read_text(encoding="utf-8").splitlines()]
            backups = list(root.glob("human_verified_span_commands.jsonl.bak-*"))

        self.assertIn('"records": 2', completed.stdout)
        self.assertEqual([record["id"] for record in records], ["human_cmd_001", "human_cmd_013"])
        self.assertEqual(summary_payload["records"], 2)
        self.assertEqual(len(bio_records), 2)
        self.assertEqual(len(backups), 1)

    def test_cli_rejects_non_span_label_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_file = root / "span_label_commands.txt"
            command_file.write_text("Remove-Item datasets/commands/human_verified_span_commands.jsonl\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--commands-file",
                    str(command_file),
                    "--output",
                    str(root / "out.jsonl"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported command", completed.stderr)


if __name__ == "__main__":
    unittest.main()
