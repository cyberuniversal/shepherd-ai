import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_week3_human_grounding_packet.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class CreateWeek3HumanGroundingPacketCliTests(unittest.TestCase):
    def test_cli_writes_blank_jsonl_and_markdown_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jsonl_output = root / "packet.jsonl"
            markdown_output = root / "packet.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--jsonl-output",
                    str(jsonl_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(completed.stdout)
            records = [
                json.loads(line)
                for line in jsonl_output.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertEqual(summary["slots"], 22)
        self.assertEqual(len(records), 22)
        self.assertEqual(records[0]["label_status"], "needs_human_written_command")
        self.assertEqual(records[0]["text"], "")
        self.assertIn("not benchmark data", markdown)


if __name__ == "__main__":
    unittest.main()
