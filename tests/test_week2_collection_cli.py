import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CREATE_COMMAND_SCRIPT = ROOT / "scripts" / "create_command_record.py"
VALIDATE_COMMAND_SCRIPT = ROOT / "scripts" / "validate_command_dataset.py"
VALIDATE_AUDIO_SCRIPT = ROOT / "scripts" / "validate_audio_manifest.py"
COLLECT_SAMPLE_SCRIPT = ROOT / "scripts" / "collect_week2_sample.py"
SYNTHETIC_DATASET = ROOT / "datasets" / "commands" / "intent_labeled_synthetic.jsonl"


class Week2CollectionCliTests(unittest.TestCase):
    def test_create_command_record_appends_valid_labeled_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "human_commands.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_COMMAND_SCRIPT),
                    "--output",
                    str(output),
                    "--id",
                    "human_cmd_001",
                    "--text",
                    "Send two drones north and inspect the crops.",
                    "--split",
                    "train",
                    "--source",
                    "human_written_collection_v1",
                    "--data-type",
                    "human_written_command",
                    "--action",
                    "inspect",
                    "--count",
                    "2",
                    "--location",
                    "north",
                    "--target",
                    "crops",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            record = json.loads(output.read_text(encoding="utf-8").strip())

        self.assertIn("human_cmd_001", completed.stdout)
        self.assertEqual(record["expected_intent"]["count"], 2)
        self.assertEqual(record["expected_intent"]["constraints"], [])

    def test_validate_command_dataset_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_COMMAND_SCRIPT),
                    "--dataset",
                    str(SYNTHETIC_DATASET),
                    "--summary-output",
                    str(summary_path),
                    "--require-splits",
                    "train,validation,test",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertIn('"records"', completed.stdout)
        self.assertEqual(summary["records"], 26)
        self.assertEqual(summary["split_counts"], {"test": 4, "train": 18, "validation": 4})

    def test_validate_audio_manifest_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "datasets" / "sample_audio" / "audio_001.wav"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"RIFF")
            manifest = root / "datasets" / "sample_audio" / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": "Send two drones north.",
                        "source": "self_recorded_collection_v1",
                        "data_type": "human_recorded_audio",
                        "split": "validation",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            summary_path = root / "audio_summary.json"

            subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_AUDIO_SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--summary-output",
                    str(summary_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["split_counts"], {"validation": 1})
        self.assertEqual(summary["data_type_counts"], {"human_recorded_audio": 1})

    def test_collect_week2_sample_copies_wav_and_writes_draft_command_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_audio = root / "input.wav"
            source_audio.write_bytes(b"RIFF")
            command_output = root / "datasets" / "commands" / "human_written_commands_draft.jsonl"
            audio_manifest = root / "datasets" / "sample_audio" / "manifest.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(COLLECT_SAMPLE_SCRIPT),
                    "--text",
                    "Send two drones north and inspect the crops.",
                    "--wav",
                    str(source_audio),
                    "--split",
                    "train",
                    "--dataset-root",
                    str(root),
                    "--command-output",
                    str(command_output),
                    "--audio-dir",
                    str(root / "datasets" / "sample_audio"),
                    "--audio-manifest",
                    str(audio_manifest),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            command_record = json.loads(command_output.read_text(encoding="utf-8").strip())
            audio_record = json.loads(audio_manifest.read_text(encoding="utf-8").strip())
            copied_audio_exists = (root / audio_record["audio_path"]).exists()

        self.assertIn("human_cmd_001", completed.stdout)
        self.assertEqual(command_record["data_type"], "human_written_command_draft_labeled")
        self.assertEqual(command_record["label_source"], "deterministic_v2_draft")
        self.assertEqual(command_record["expected_intent"]["action"], "inspect")
        self.assertEqual(command_record["expected_intent"]["count"], 2)
        self.assertEqual(audio_record["id"], "audio_001")
        self.assertEqual(audio_record["audio_path"], "datasets/sample_audio/audio_001.wav")
        self.assertTrue(copied_audio_exists)


if __name__ == "__main__":
    unittest.main()
