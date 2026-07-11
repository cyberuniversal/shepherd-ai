import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_audio_intent_review_packet.py"


class ValidateAudioIntentReviewPacketCliTests(unittest.TestCase):
    def test_cli_blocks_draft_packet_when_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            packet.write_text(json.dumps(_record(reviewed=False)) + "\n", encoding="utf-8")
            summary = root / "summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--summary-output",
                    str(summary),
                    "--require-reviewed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 1)
        self.assertFalse(payload["summary"]["ready_for_gold_evaluation"])
        self.assertEqual(payload["summary"]["draft_records"], 1)
        self.assertEqual(payload["summary"]["not_reviewed_records"], 1)

    def test_cli_accepts_human_reviewed_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            packet.write_text(json.dumps(_record(reviewed=True)) + "\n", encoding="utf-8")
            summary = root / "summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--summary-output",
                    str(summary),
                    "--require-reviewed",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertIn('"ready_for_gold_evaluation": true', completed.stdout)
        self.assertTrue(payload["summary"]["ready_for_gold_evaluation"])


def _record(*, reviewed: bool) -> dict:
    return {
        "id": "audio_001_intent",
        "audio_id": "audio_001",
        "text": "Send one drone to inspect the loading bay before noon.",
        "split": "validation",
        "source": "manual_review",
        "data_type": "human_verified_audio_intent_command" if reviewed else "human_recorded_audio_intent_draft",
        "label_source": "human_reviewed_v1" if reviewed else "deterministic_v1_draft",
        "review_status": "human_reviewed" if reviewed else "needs_human_review",
        "expected_intent": {
            "action": "inspect",
            "count": 1,
            "location": None,
            "target": "loading bay",
            "constraints": ["before noon"],
        },
    }


if __name__ == "__main__":
    unittest.main()
