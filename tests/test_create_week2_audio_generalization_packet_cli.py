import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_week2_audio_generalization_packet.py"


class CreateWeek2AudioGeneralizationPacketCliTests(unittest.TestCase):
    def test_cli_writes_blank_audio_slots_with_fixed_splits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = root / "commands.jsonl"
            spans = root / "spans.jsonl"
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")
            (audio_dir / "audio_002.wav").write_bytes(b"RIFF")
            manifest = audio_dir / "manifest.jsonl"
            second_manifest = audio_dir / "manifest_2.jsonl"
            text = "Send two drones north."
            second_text = "Return all drones to base."
            commands.write_text(
                json.dumps(
                    {
                        "id": "cmd_001",
                        "text": text,
                        "split": "train",
                        "source": "manual",
                        "data_type": "human_written_command",
                        "expected_intent": {
                            "action": "send",
                            "count": 2,
                            "location": "north",
                            "target": None,
                            "constraints": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            spans.write_text(
                json.dumps(
                    {
                        "id": "span_001",
                        "text": text,
                        "split": "train",
                        "source": "manual",
                        "data_type": "human_verified_span_command",
                        "spans": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": text,
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "train",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            second_manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_002",
                        "audio_path": "datasets/sample_audio/audio_002.wav",
                        "transcript": second_text,
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            jsonl_output = root / "packet.jsonl"
            markdown_output = root / "packet.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--commands",
                    str(commands),
                    "--spans",
                    str(spans),
                    "--existing-audio-manifest",
                    str(manifest),
                    "--existing-audio-manifest",
                    str(second_manifest),
                    "--dataset-root",
                    str(root),
                    "--jsonl-output",
                    str(jsonl_output),
                    "--markdown-output",
                    str(markdown_output),
                    "--validation-count",
                    "1",
                    "--test-count",
                    "2",
                    "--record-prefix",
                    "fresh_audio",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            rows = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn('"slots": 3', completed.stdout)
        self.assertEqual([row["split"] for row in rows], ["validation", "test", "test"])
        self.assertEqual(rows[0]["id"], "fresh_audio_001")
        self.assertEqual(rows[0]["transcript"], "")
        self.assertIn("Non-overlap required: true", markdown)
        self.assertIn("Existing normalized texts blocked for overlap: 2", markdown)


if __name__ == "__main__":
    unittest.main()
