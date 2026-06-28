import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "transcribe_audio_manifest.py"


class TranscriptionCliTests(unittest.TestCase):
    def test_cached_backend_writes_raw_transcription_output(self) -> None:
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
                        "source": "self_recorded",
                        "data_type": "human_recorded_audio",
                        "split": "example",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "outputs" / "transcripts.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--backend",
                    "cached",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(saved["metadata"]["model_name"], "cached-transcript")
        self.assertEqual(saved["records"][0]["predicted_transcript"], "Send two drones north.")
        self.assertEqual(saved["summary"]["mean_word_error_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
