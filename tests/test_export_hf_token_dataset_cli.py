import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_hf_token_dataset.py"
DATASET = ROOT / "datasets" / "commands" / "human_verified_span_commands.jsonl"


class ExportHfTokenDatasetCliTests(unittest.TestCase):
    def test_cli_exports_split_jsonl_and_label_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "hf_token_dataset"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(DATASET),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            label_map = json.loads((output_dir / "label_map.json").read_text(encoding="utf-8"))
            train_record = json.loads((output_dir / "train.jsonl").read_text(encoding="utf-8").splitlines()[0])
            summary = json.loads((output_dir / "dataset_summary.json").read_text(encoding="utf-8"))

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(label_map["label2id"]["O"], 0)
        self.assertIn("B-target", label_map["label2id"])
        self.assertEqual(len(train_record["tokens"]), len(train_record["ner_tags"]))
        self.assertEqual(len(train_record["tokens"]), len(train_record["labels"]))
        self.assertEqual(summary["split_counts"], {"test": 10, "train": 30, "validation": 10})


if __name__ == "__main__":
    unittest.main()
