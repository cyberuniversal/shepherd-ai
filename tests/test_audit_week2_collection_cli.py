import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week2_collection.py"


class AuditWeek2CollectionCliTests(unittest.TestCase):
    def test_cli_reports_duplicates_draft_labels_and_audio_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = root / "commands.jsonl"
            manifest = root / "manifest.jsonl"
            audio = root / "audio_001.wav"
            audio.write_bytes(b"RIFF")
            command_payloads = [
                {
                    "id": "human_cmd_001",
                    "text": "Inspect the greenhouse.",
                    "split": "train",
                    "source": "manual",
                    "data_type": "human_written_command_draft_labeled",
                    "label_source": "deterministic_v0_draft",
                    "expected_intent": {
                        "action": "inspect",
                        "count": None,
                        "location": None,
                        "target": "greenhouse",
                        "constraints": [],
                    },
                },
                {
                    "id": "human_cmd_002",
                    "text": "Inspect the greenhouse.",
                    "split": "train",
                    "source": "manual",
                    "data_type": "human_written_command_draft_labeled",
                    "label_source": "deterministic_v0_draft",
                    "expected_intent": {
                        "action": "inspect",
                        "count": None,
                        "location": None,
                        "target": "greenhouse",
                        "constraints": [],
                    },
                },
            ]
            commands.write_text(
                "\n".join(json.dumps(payload) for payload in command_payloads) + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "audio_001.wav",
                        "transcript": "Inspect the greenhouse.",
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "train",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "audit.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--commands",
                    str(commands),
                    "--audio-manifest",
                    str(manifest),
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

        self.assertIn('"warnings"', completed.stdout)
        self.assertEqual(audit["commands"]["records"], 2)
        self.assertEqual(audit["audio"]["records"], 1)
        self.assertEqual(audit["warnings"]["duplicate_command_texts"][0]["count"], 2)
        self.assertEqual(audit["warnings"]["draft_labeled_records"], 2)
        self.assertIn("validation", audit["warnings"]["missing_command_splits"])
        self.assertIn("test", audit["warnings"]["missing_command_splits"])


if __name__ == "__main__":
    unittest.main()
