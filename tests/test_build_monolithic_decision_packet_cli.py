import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_monolithic_decision_packet.py"


class BuildMonolithicDecisionPacketCliTests(unittest.TestCase):
    def test_builds_label_separated_hashed_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            inputs = temp / "inputs.jsonl"
            gold = temp / "gold.jsonl"
            manifest = temp / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inputs-output",
                    str(inputs),
                    "--gold-output",
                    str(gold),
                    "--manifest-output",
                    str(manifest),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            input_rows = [
                json.loads(line) for line in inputs.read_text(encoding="utf-8").splitlines()
            ]
            gold_rows = [
                json.loads(line) for line in gold.read_text(encoding="utf-8").splitlines()
            ]
            metadata = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(len(input_rows), 38)
        self.assertEqual(len(gold_rows), 38)
        self.assertEqual(metadata["case_count"], 38)
        self.assertFalse(metadata["inputs"]["contains_gold_labels"])
        self.assertFalse(metadata["gold"]["loaded_by_model_runner"])
        self.assertNotIn("expected_decision", input_rows[0])
        self.assertIn("expected_decision", gold_rows[0])
        self.assertEqual(len(input_rows[0]["prompt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
