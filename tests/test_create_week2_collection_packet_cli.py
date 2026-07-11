import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_week2_collection_packet.py"


class CreateWeek2CollectionPacketCliTests(unittest.TestCase):
    def test_writes_blank_packet_files(self) -> None:
        plan = {
            "field_priorities": [
                {
                    "field": "target",
                    "heuristic_requested_new_records": 2,
                    "collection_guidance": ["Collect target boundary cases."],
                },
                {
                    "field": "constraint",
                    "heuristic_requested_new_records": 1,
                    "collection_guidance": ["Collect explicit restrictions."],
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_path = tmp_path / "plan.json"
            jsonl_output = tmp_path / "packet.jsonl"
            markdown_output = tmp_path / "packet.md"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--plan",
                    str(plan_path),
                    "--jsonl-output",
                    str(jsonl_output),
                    "--markdown-output",
                    str(markdown_output),
                    "--record-prefix",
                    "slot",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            rows = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn('"slots": 3', completed.stdout)
        self.assertEqual(rows[0]["slot_id"], "slot_001")
        self.assertEqual(rows[0]["text"], "")
        self.assertEqual(rows[0]["spans"], [])
        self.assertIn("Total blank slots: 3", markdown)


if __name__ == "__main__":
    unittest.main()
