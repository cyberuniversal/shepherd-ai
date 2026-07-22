import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_asr import build_week8_asr_evidence  # noqa: E402
from shepherd_ai.week8_completion import ROADMAP_COMMAND  # noqa: E402


class Week8AsrTests(unittest.TestCase):
    def test_builds_hashed_exact_scenario_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "week8.wav"
            with wave.open(str(wav), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 160)
            result = build_week8_asr_evidence(
                {
                    "id": "week8_exact_scenario_audio",
                    "audio_path": str(wav),
                    "transcript": ROADMAP_COMMAND,
                    "data_type": "human_recorded_audio",
                    "source": "unit_test",
                    "split": "scenario_evaluation",
                },
                {
                    "id": "week8_exact_scenario_audio",
                    "predicted_transcript": ROADMAP_COMMAND,
                    "model_name": "whisper",
                    "model_version": "base",
                    "parameters": {"record_inference_elapsed_seconds": 1.5},
                },
                {
                    "id": "week8_exact_scenario_audio",
                    "word_error_rate": 0.0,
                    "exact_match": True,
                },
            )

            self.assertEqual(result["audio"]["sha256"], hashlib.sha256(wav.read_bytes()).hexdigest())
        self.assertEqual(result["inference_elapsed_seconds"], 1.5)

    def test_rejects_non_human_audio(self) -> None:
        with self.assertRaisesRegex(ValueError, "human_recorded_audio"):
            build_week8_asr_evidence(
                {
                    "id": "week8_exact_scenario_audio",
                    "transcript": ROADMAP_COMMAND,
                    "data_type": "synthetic_audio",
                },
                {},
                {},
            )


if __name__ == "__main__":
    unittest.main()
