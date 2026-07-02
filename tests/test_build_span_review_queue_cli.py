import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_span_review_queue.py"


class BuildSpanReviewQueueCliTests(unittest.TestCase):
    def test_writes_jsonl_and_summary(self) -> None:
        evaluation = {
            "metadata": {"model_name": "hf_token_classifier", "dataset": "test.jsonl"},
            "records": [
                {
                    "id": "cmd_1",
                    "split": "test",
                    "text": "Search the field for a truck.",
                    "tokens": ["Search", "the", "field", "for", "a", "truck", "."],
                    "offsets": [[0, 6], [7, 10], [11, 16], [17, 20], [21, 22], [23, 28], [28, 29]],
                    "expected_tags": ["B-action", "O", "B-location", "O", "O", "B-target", "O"],
                    "predicted_tags": ["B-action", "O", "B-target", "B-constraint", "I-constraint", "I-constraint", "O"],
                    "token_matches": [True, True, False, False, False, False, True],
                    "expected_entities": [["action", 0, 6], ["location", 11, 16], ["target", 23, 28]],
                    "predicted_entities": [["action", 0, 6], ["constraint", 17, 28], ["target", 11, 16]],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            evaluation_path = tmp_path / "evaluation.json"
            output_path = tmp_path / "review.jsonl"
            summary_path = tmp_path / "summary.json"
            evaluation_path.write_text(json.dumps(evaluation), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--evaluation",
                    str(evaluation_path),
                    "--output",
                    str(output_path),
                    "--summary-output",
                    str(summary_path),
                    "--focus-field",
                    "target",
                    "--focus-field",
                    "constraint",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn('"records_requiring_review": 1', completed.stdout)
            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(records[0]["id"], "cmd_1")
        self.assertEqual(records[0]["label_status"], "needs_human_review")
        self.assertEqual(summary["records_requiring_review"], 1)


if __name__ == "__main__":
    unittest.main()
