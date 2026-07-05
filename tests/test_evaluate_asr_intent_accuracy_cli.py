import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_asr_intent_accuracy.py"


class EvaluateAsrIntentAccuracyCliTests(unittest.TestCase):
    def test_cli_evaluates_audio_transcripts_against_matched_gold_commands(self) -> None:
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
                        "transcript": "Send two drones north and inspect the crops.",
                        "source": "test",
                        "data_type": "human_recorded_audio",
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            predictions = root / "predictions.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "expected_transcript": "Send two drones north and inspect the crops.",
                        "predicted_transcript": "Send two drones north and inspect the crops.",
                        "model_name": "whisper",
                        "model_version": "base",
                        "parameters": {},
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            gold = root / "gold.jsonl"
            gold.write_text(
                json.dumps(
                    {
                        "id": "gold_001",
                        "text": "Send two drones north and inspect the crops.",
                        "split": "test",
                        "source": "test",
                        "data_type": "human_written_command_assistant_labeled",
                        "label_source": "unit_test",
                        "expected_intent": {
                            "action": "inspect",
                            "count": 2,
                            "location": "north",
                            "target": "crops",
                            "constraints": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "accuracy.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--predictions",
                    str(predictions),
                    "--gold-commands",
                    str(gold),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("deterministic_v1:human_transcript", completed.stdout)
        summary = result["summary"]["deterministic_v1:asr_transcript"]
        self.assertEqual(summary["exact_record_accuracy"], 1.0)
        self.assertEqual(result["records"][0]["gold_label_sources"], ["unit_test"])

    def test_cli_rejects_draft_review_packet_as_gold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")
            manifest = audio_dir / "manifest.jsonl"
            transcript = "Send one drone to inspect the loading bay before noon."
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": transcript,
                        "source": "test",
                        "data_type": "human_recorded_audio",
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            predictions = root / "predictions.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "expected_transcript": transcript,
                        "predicted_transcript": transcript,
                        "model_name": "whisper",
                        "model_version": "base",
                        "parameters": {},
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            draft_gold = root / "draft_gold.jsonl"
            draft_gold.write_text(
                json.dumps(
                    {
                        "id": "audio_001_intent",
                        "text": transcript,
                        "split": "test",
                        "source": "test",
                        "data_type": "human_recorded_audio_intent_draft",
                        "label_source": "deterministic_v1_draft",
                        "review_status": "needs_human_review",
                        "expected_intent": {
                            "action": "inspect",
                            "count": 1,
                            "location": None,
                            "target": "loading bay",
                            "constraints": ["before noon"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--predictions",
                    str(predictions),
                    "--gold-commands",
                    str(draft_gold),
                    "--output",
                    str(root / "accuracy.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("draft labels cannot be used", completed.stderr)


if __name__ == "__main__":
    unittest.main()
