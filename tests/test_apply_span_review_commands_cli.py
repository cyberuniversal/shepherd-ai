import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_span_review_commands.py"


class ApplySpanReviewCommandsCliTests(unittest.TestCase):
    def test_applies_review_subset_without_dropping_unreviewed_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_commands = root / "commands.jsonl"
            base_dataset = root / "base_spans.jsonl"
            output = root / "merged_spans.jsonl"
            summary = root / "summary.json"
            bio = root / "bio.jsonl"
            command_file = root / "review_commands.txt"
            source_commands.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "cmd_1",
                                "text": "Inspect the greenhouse.",
                                "split": "train",
                                "source": "manual_week2_collection_v1",
                                "data_type": "human_written_command",
                            },
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "id": "cmd_2",
                                "text": "Return to base.",
                                "split": "test",
                                "source": "manual_week2_collection_v1",
                                "data_type": "human_written_command",
                            },
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            base_dataset.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "cmd_1",
                                "base_command_id": "cmd_1",
                                "text": "Inspect the greenhouse.",
                                "split": "train",
                                "source": "manual_week2_span_annotation_v1",
                                "data_type": "human_verified_span_command",
                                "spans": [
                                    {"field": "action", "start": 0, "end": 7, "text": "Inspect"},
                                    {"field": "target", "start": 12, "end": 22, "text": "greenhouse"},
                                ],
                            },
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "id": "cmd_2",
                                "base_command_id": "cmd_2",
                                "text": "Return to base.",
                                "split": "test",
                                "source": "manual_week2_span_annotation_v1",
                                "data_type": "human_verified_span_command",
                                "spans": [
                                    {"field": "action", "start": 0, "end": 6, "text": "Return"},
                                    {"field": "location", "start": 10, "end": 14, "text": "base"},
                                ],
                            },
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            command_file.write_text(
                f'python scripts/create_span_record_from_command.py --input "{source_commands}" --id cmd_1 --output ignored.jsonl --action-span Inspect\n',
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--base-dataset",
                    str(base_dataset),
                    "--commands-file",
                    str(command_file),
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                    "--bio-output",
                    str(bio),
                    "--no-backup",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            summary_payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertIn('"reviewed_records": 1', completed.stdout)
        self.assertEqual([record["id"] for record in records], ["cmd_1", "cmd_2"])
        self.assertEqual([(span["field"], span["text"]) for span in records[0]["spans"]], [("action", "Inspect")])
        self.assertEqual([(span["field"], span["text"]) for span in records[1]["spans"]], [("action", "Return"), ("location", "base")])
        self.assertEqual(summary_payload["records"], 2)

    def test_rejects_review_command_for_unknown_base_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_commands = root / "commands.jsonl"
            base_dataset = root / "base_spans.jsonl"
            command_file = root / "review_commands.txt"
            source_commands.write_text(
                json.dumps(
                    {
                        "id": "cmd_missing",
                        "text": "Inspect the greenhouse.",
                        "split": "train",
                        "source": "manual_week2_collection_v1",
                        "data_type": "human_written_command",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            base_dataset.write_text(
                json.dumps(
                    {
                        "id": "cmd_1",
                        "text": "Return to base.",
                        "split": "test",
                        "source": "manual_week2_span_annotation_v1",
                        "data_type": "human_verified_span_command",
                        "spans": [{"field": "action", "start": 0, "end": 6, "text": "Return"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            command_file.write_text(
                f'python scripts/create_span_record_from_command.py --input "{source_commands}" --id cmd_missing --output ignored.jsonl --action-span Inspect\n',
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--base-dataset",
                    str(base_dataset),
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
        self.assertIn("not present in base dataset", completed.stderr)


if __name__ == "__main__":
    unittest.main()
