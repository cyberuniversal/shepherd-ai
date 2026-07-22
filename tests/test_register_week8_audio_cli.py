import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/register_week8_audio.py"


class RegisterWeek8AudioCliTests(unittest.TestCase):
    def test_cli_copies_pcm_wav_and_writes_fixed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            staged = root / "staged.wav"
            manifest = root / "manifest.jsonl"
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 160)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--wav",
                    str(source),
                    "--staged-wav",
                    str(staged),
                    "--manifest-output",
                    str(manifest),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            record = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(record["id"], "week8_exact_scenario_audio")
        self.assertEqual(record["data_type"], "human_recorded_audio")
        self.assertEqual(record["audio_metadata"]["sample_rate_hz"], 16000)


if __name__ == "__main__":
    unittest.main()
