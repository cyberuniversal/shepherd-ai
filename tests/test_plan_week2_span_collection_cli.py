import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_week2_span_collection.py"


class PlanWeek2SpanCollectionCliTests(unittest.TestCase):
    def test_writes_json_and_markdown_plan(self) -> None:
        span_record = {
            "id": "cmd_1",
            "text": "Search the field for a truck.",
            "split": "train",
            "source": "human_written_collection_v1",
            "data_type": "human_verified_span_command",
            "spans": [
                {"field": "action", "start": 0, "end": 6, "text": "Search"},
                {"field": "location", "start": 11, "end": 16, "text": "field"},
                {"field": "target", "start": 23, "end": 28, "text": "truck"},
            ],
        }
        evaluation = {
            "summary": {
                "records": 1,
                "entity_f1": 0.4,
                "entity_precision": 0.5,
                "entity_recall": 0.3333333333,
                "token_accuracy": 0.7,
            }
        }
        error_analysis = {
            "false_negative_entity_counts": {"target": 2},
            "false_positive_entity_counts": {"constraint": 3},
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            span_path = tmp_path / "spans.jsonl"
            eval_path = tmp_path / "eval.json"
            error_path = tmp_path / "errors.json"
            json_output = tmp_path / "plan.json"
            markdown_output = tmp_path / "plan.md"
            span_path.write_text(json.dumps(span_record) + "\n", encoding="utf-8")
            eval_path.write_text(json.dumps(evaluation), encoding="utf-8")
            error_path.write_text(json.dumps(error_analysis), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--span-dataset",
                    str(span_path),
                    "--evaluation",
                    str(eval_path),
                    "--error-analysis",
                    str(error_path),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            plan = json.loads(json_output.read_text(encoding="utf-8"))
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn("minimum_human_written_span_records", completed.stdout)
        self.assertEqual(plan["roadmap_anchor"]["week"], "Week 2")
        self.assertIn("targeted follow-up records", markdown)


if __name__ == "__main__":
    unittest.main()
