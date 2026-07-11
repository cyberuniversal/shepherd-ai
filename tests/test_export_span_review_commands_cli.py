import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_span_review_commands.py"


class ExportSpanReviewCommandsCliTests(unittest.TestCase):
    def test_exports_editable_commands_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            span_dataset = root / "span.jsonl"
            review_queue = root / "queue.jsonl"
            commands_output = root / "review_commands.txt"
            report_output = root / "review_report.md"
            span_dataset.write_text(
                json.dumps(
                    {
                        "id": "human_cmd_046",
                        "base_command_id": "human_cmd_046",
                        "text": "Search the open field for a missing vehicle.",
                        "split": "test",
                        "source": "manual_week2_span_annotation_v1",
                        "data_type": "human_verified_span_command",
                        "spans": [
                            {"field": "action", "start": 0, "end": 6, "text": "Search"},
                            {"field": "location", "start": 11, "end": 21, "text": "open field"},
                            {"field": "target", "start": 28, "end": 43, "text": "missing vehicle"},
                        ],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            review_queue.write_text(
                json.dumps(
                    {
                        "id": "human_cmd_046",
                        "text": "Search the open field for a missing vehicle.",
                        "review_fields": ["location", "target", "constraint"],
                        "focus_error_count": 6,
                        "token_error_count": 5,
                        "false_negative_entities": [
                            {"field": "target", "start": 28, "end": 43, "text": "missing vehicle"}
                        ],
                        "false_positive_entities": [
                            {"field": "constraint", "start": 22, "end": 25, "text": "for"}
                        ],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--span-dataset",
                    str(span_dataset),
                    "--review-queue",
                    str(review_queue),
                    "--commands-output",
                    str(commands_output),
                    "--report-output",
                    str(report_output),
                    "--source-command-dataset",
                    "datasets/commands/human_written_commands_curated_v1.jsonl",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            commands_text = commands_output.read_text(encoding="utf-8")
            report_text = report_output.read_text(encoding="utf-8")

        self.assertIn('"commands": 1', completed.stdout)
        self.assertIn("python scripts/create_span_record_from_command.py", commands_text)
        self.assertIn("--id human_cmd_046", commands_text)
        self.assertIn("--location-span 'open field'", commands_text)
        self.assertIn("--target-span 'missing vehicle'", commands_text)
        self.assertIn("model predictions are not gold labels", report_text)
        self.assertIn("human_cmd_046", report_text)


if __name__ == "__main__":
    unittest.main()
