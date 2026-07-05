import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_week2_audio_intent_review_packet.py"


class CreateWeek2AudioIntentReviewPacketCliTests(unittest.TestCase):
    def test_cli_writes_draft_review_packet_from_audio_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")
            manifest = audio_dir / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": "Send one drone to inspect the loading bay before noon.",
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "validation",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            jsonl_output = root / "intent_review.jsonl"
            markdown_output = root / "intent_review.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
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

            rows = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(rows[0]["id"], "audio_001_intent")
        self.assertEqual(rows[0]["audio_id"], "audio_001")
        self.assertEqual(rows[0]["review_status"], "needs_human_review")
        self.assertEqual(rows[0]["data_type"], "human_recorded_audio_intent_draft")
        self.assertEqual(rows[0]["expected_intent"]["action"], "inspect")
        self.assertEqual(rows[0]["parser"], "deterministic_v2")
        self.assertIn("constraint_review_needed", rows[0]["draft_review_flags"])
        self.assertIn("Do not use draft records", markdown)


if __name__ == "__main__":
    unittest.main()
