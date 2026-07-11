import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_audio_intent_review_commands.py"


class ExportAudioIntentReviewCommandsCliTests(unittest.TestCase):
    def test_cli_exports_compact_editable_jsonl_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            commands = root / "commands.jsonl"
            report = root / "report.md"
            packet.write_text(json.dumps(_draft_record()) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--commands-output",
                    str(commands),
                    "--report-output",
                    str(report),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            command = json.loads(commands.read_text(encoding="utf-8"))
            report_text = report.read_text(encoding="utf-8")

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(command["id"], "audio_generalization_001_intent")
        self.assertEqual(command["action"], "inspect")
        self.assertEqual(command["review_status"], "needs_human_review")
        self.assertEqual(command["data_type"], "human_recorded_audio_intent_draft")
        self.assertIn("action_missing_or_unsupported", command["draft_review_flags"])
        self.assertIn("Week 2 Audio Intent Review Commands", report_text)
        self.assertIn("Draft flag counts", report_text)


def _draft_record() -> dict:
    return {
        "id": "audio_generalization_001_intent",
        "audio_id": "audio_generalization_001",
        "text": "Inspect the loading bay before noon.",
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
            "constraints": ["before noon"],
        },
        "draft_review_flags": ["action_missing_or_unsupported"],
    }


if __name__ == "__main__":
    unittest.main()
