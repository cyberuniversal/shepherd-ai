import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_audio_intent_review_commands.py"


class ApplyAudioIntentReviewCommandsCliTests(unittest.TestCase):
    def test_cli_applies_reviewed_subset_and_reports_unreviewed_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            commands = root / "commands.jsonl"
            output = root / "reviewed.jsonl"
            summary = root / "summary.json"
            packet.write_text(
                json.dumps(_draft_record("audio_001_intent", "Inspect the loading bay.")) + "\n"
                + json.dumps(_draft_record("audio_002_intent", "Survey the west field.")) + "\n",
                encoding="utf-8",
            )
            commands.write_text(
                json.dumps(
                    {
                        "id": "audio_001_intent",
                        "action": "inspect",
                        "count": None,
                        "location": None,
                        "target": "loading bay",
                        "constraints": [],
                        "review_status": "human_reviewed",
                        "data_type": "human_verified_audio_intent_command",
                        "label_source": "human_reviewed_v1",
                        "review_notes": ["checked against transcript"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--commands-file",
                    str(commands),
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertIn('"applied_records": 1', completed.stdout)
        self.assertEqual(records[0]["review_status"], "human_reviewed")
        self.assertEqual(records[0]["data_type"], "human_verified_audio_intent_command")
        self.assertEqual(records[0]["expected_intent"]["target"], "loading bay")
        self.assertEqual(records[1]["review_status"], "needs_human_review")
        self.assertFalse(payload["summary"]["ready_for_gold_evaluation"])
        self.assertEqual(payload["summary"]["not_reviewed_records"], 1)

    def test_cli_require_reviewed_fails_for_exported_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            commands = root / "commands.jsonl"
            output = root / "reviewed.jsonl"
            summary = root / "summary.json"
            packet.write_text(json.dumps(_draft_record("audio_001_intent", "Inspect the loading bay.")) + "\n")
            command = {
                "id": "audio_001_intent",
                "action": "inspect",
                "count": None,
                "location": None,
                "target": "loading bay",
                "constraints": [],
                "review_status": "needs_human_review",
                "data_type": "human_recorded_audio_intent_draft",
                "label_source": "deterministic_v1_draft",
                "review_notes": [],
            }
            commands.write_text(json.dumps(command) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--commands-file",
                    str(commands),
                    "--output",
                    str(output),
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


def _draft_record(record_id: str, text: str) -> dict:
    return {
        "id": record_id,
        "audio_id": record_id.replace("_intent", ""),
        "text": text,
        "split": "validation",
        "source": "manual_week2_audio_generalization_v1",
        "data_type": "human_recorded_audio_intent_draft",
        "label_source": "deterministic_v1_draft",
        "review_status": "needs_human_review",
        "expected_intent": {
            "action": "inspect",
            "count": None,
            "location": None,
            "target": "loading bay",
            "constraints": [],
        },
    }


if __name__ == "__main__":
    unittest.main()
