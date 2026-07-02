import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_span_record.py"


class CreateSpanRecordCliTests(unittest.TestCase):
    def test_cli_appends_span_record_with_computed_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "span_commands.jsonl"
            text = "Send the nearest drone to inspect the livestock pen without crossing the road."

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--id",
                    "span_cmd_001",
                    "--text",
                    text,
                    "--split",
                    "train",
                    "--source",
                    "manual_week2_span_annotation_v1",
                    "--data-type",
                    "human_verified_span_command",
                    "--action-span",
                    "inspect",
                    "--target-span",
                    "livestock pen",
                    "--constraint-span",
                    "without crossing the road",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            record = json.loads(output.read_text(encoding="utf-8").strip())

        self.assertIn("span_cmd_001", completed.stdout)
        self.assertEqual(record["spans"][0]["field"], "action")
        self.assertEqual(record["spans"][0]["text"], "inspect")
        self.assertEqual(record["spans"][1]["field"], "target")
        self.assertEqual(record["spans"][1]["text"], "livestock pen")
        self.assertEqual(record["spans"][2]["field"], "constraint")
        self.assertEqual(record["spans"][2]["text"], "without crossing the road")
        for span in record["spans"]:
            self.assertEqual(record["text"][span["start"] : span["end"]], span["text"])

    def test_cli_rejects_repeated_span_text_without_manual_disambiguation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "span_commands.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--id",
                    "span_cmd_001",
                    "--text",
                    "Scan the field and return to the field.",
                    "--split",
                    "train",
                    "--source",
                    "manual_week2_span_annotation_v1",
                    "--data-type",
                    "human_verified_span_command",
                    "--target-span",
                    "field",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("appears 2 times", completed.stderr)


if __name__ == "__main__":
    unittest.main()
