import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "finalize_week3_human_grounding_packet.py"


class FinalizeWeek3HumanGroundingPacketCliTests(unittest.TestCase):
    def test_cli_fails_when_packet_contains_blank_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            output = root / "benchmark.jsonl"
            packet.write_text(
                json.dumps(
                    {
                        "id": "human_ground_001",
                        "text": "",
                        "expected_grounding": {
                            "target": {"status": "grounded", "location_id": "loc_north_field"}
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--packet", str(packet), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("text must be a non-empty string", completed.stderr)

    def test_cli_writes_finalized_human_benchmark_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            output = root / "benchmark.jsonl"
            packet.write_text(
                json.dumps(
                    {
                        "id": "human_ground_001",
                        "label_status": "needs_human_written_command",
                        "text": "Inspect the north field.",
                        "expected_grounding": {
                            "target": {"status": "grounded", "location_id": "loc_north_field"}
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--packet", str(packet), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(completed.stdout)
            records = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(summary["records"], 1)
        self.assertEqual(records[0]["data_type"], "human_written_grounding_benchmark")
        self.assertEqual(records[0]["split"], "human_holdout")
        self.assertNotIn("label_status", records[0])


if __name__ == "__main__":
    unittest.main()
