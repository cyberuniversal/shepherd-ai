import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week2_audio_generalization_manifest.py"


class AuditWeek2AudioGeneralizationManifestCliTests(unittest.TestCase):
    def test_cli_reports_existing_text_overlap_and_candidate_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = root / "commands.jsonl"
            spans = root / "spans.jsonl"
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            for name in ("audio_001.wav", "candidate_001.wav", "candidate_002.wav", "candidate_003.wav"):
                (audio_dir / name).write_bytes(b"RIFF")

            existing_text = "Send two drones north."
            new_text = "Inspect the loading dock after sunrise."
            commands.write_text(_command_line("cmd_001", existing_text), encoding="utf-8")
            spans.write_text(_span_line("span_001", existing_text), encoding="utf-8")
            existing_manifest = audio_dir / "manifest.jsonl"
            existing_manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": existing_text,
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "train",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            candidate_manifest = audio_dir / "candidate_manifest.jsonl"
            candidate_manifest.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "candidate_001",
                                "audio_path": "datasets/sample_audio/candidate_001.wav",
                                "transcript": existing_text,
                                "source": "manual_week2_audio_generalization_v1",
                                "data_type": "human_recorded_audio",
                                "split": "validation",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "candidate_002",
                                "audio_path": "datasets/sample_audio/candidate_002.wav",
                                "transcript": new_text,
                                "source": "manual_week2_audio_generalization_v1",
                                "data_type": "human_recorded_audio",
                                "split": "test",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "candidate_003",
                                "audio_path": "datasets/sample_audio/candidate_003.wav",
                                "transcript": new_text,
                                "source": "manual_week2_audio_generalization_v1",
                                "data_type": "human_recorded_audio",
                                "split": "test",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "audit.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--candidate-manifest",
                    str(candidate_manifest),
                    "--commands",
                    str(commands),
                    "--spans",
                    str(spans),
                    "--existing-audio-manifest",
                    str(existing_manifest),
                    "--dataset-root",
                    str(root),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            audit = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"passes_non_overlap_policy": false', completed.stdout)
        self.assertEqual(audit["summary"]["records"], 3)
        self.assertEqual(audit["summary"]["overlap_records"], 1)
        self.assertEqual(audit["summary"]["duplicate_transcripts_within_candidate"], 1)
        self.assertFalse(audit["summary"]["passes_non_overlap_policy"])


def _command_line(record_id: str, text: str) -> str:
    return (
        json.dumps(
            {
                "id": record_id,
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
        + "\n"
    )


def _span_line(record_id: str, text: str) -> str:
    return (
        json.dumps(
            {
                "id": record_id,
                "text": text,
                "split": "train",
                "source": "manual",
                "data_type": "human_verified_span_command",
                "spans": [],
            }
        )
        + "\n"
    )


if __name__ == "__main__":
    unittest.main()
