import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_span_dataset.py"


class ValidateSpanDatasetCliTests(unittest.TestCase):
    def test_cli_writes_summary_and_bio_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "span_commands.jsonl"
            text = "Capture images of the red pickup truck."
            start = text.index("red pickup truck")
            dataset.write_text(
                json.dumps(
                    {
                        "id": "span_cmd_001",
                        "text": text,
                        "split": "train",
                        "source": "manual_week2_span_annotation_v1",
                        "data_type": "human_verified_span_command",
                        "spans": [
                            {
                                "field": "target",
                                "start": start,
                                "end": start + len("red pickup truck"),
                                "text": "red pickup truck",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            summary_output = root / "summary.json"
            bio_output = root / "bio.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(dataset),
                    "--summary-output",
                    str(summary_output),
                    "--bio-output",
                    str(bio_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(summary_output.read_text(encoding="utf-8"))
            bio_record = json.loads(bio_output.read_text(encoding="utf-8").strip())

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(summary["span_field_counts"], {"target": 1})
        self.assertEqual(bio_record["id"], "span_cmd_001")
        self.assertIn("B-target", bio_record["tags"])
        self.assertEqual(len(bio_record["tokens"]), len(bio_record["tags"]))


if __name__ == "__main__":
    unittest.main()
