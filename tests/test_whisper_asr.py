import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.audio_manifest import AudioManifestRecord
from shepherd_ai.whisper_asr import (
    build_whisper_prediction,
    load_whisper_predictions,
    prediction_transcript_map,
    require_device_substring,
    write_whisper_predictions,
)


class FakeCuda:
    def __init__(self, names):
        self._names = names

    def is_available(self):
        return bool(self._names)

    def device_count(self):
        return len(self._names)

    def get_device_name(self, index):
        return self._names[index]


class FakeTorch:
    def __init__(self, names):
        self.cuda = FakeCuda(names)


class WhisperAsrTests(unittest.TestCase):
    def test_prediction_rows_round_trip(self) -> None:
        record = AudioManifestRecord(
            id="audio_001",
            audio_path=Path("datasets/sample_audio/audio_001.wav"),
            transcript="Send two drones north.",
            source="test",
            data_type="human_recorded_audio",
            split="train",
        )
        prediction = build_whisper_prediction(
            record,
            predicted_transcript=" Send two drones north. ",
            model_name="whisper",
            model_version="base",
            parameters={"device": "cuda"},
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.jsonl"
            write_whisper_predictions(path, [prediction])
            loaded = load_whisper_predictions(path)

        self.assertEqual(loaded[0]["id"], "audio_001")
        self.assertEqual(loaded[0]["predicted_transcript"], "Send two drones north.")
        self.assertEqual(prediction_transcript_map(loaded), {"audio_001": "Send two drones north."})

    def test_require_device_substring_accepts_matching_cuda_device(self) -> None:
        metadata = require_device_substring("T4", torch_module=FakeTorch(["Tesla T4"]))

        self.assertEqual(metadata["cuda_device_names"], ["Tesla T4"])
        self.assertTrue(metadata["cuda_available"])

    def test_require_device_substring_rejects_missing_device(self) -> None:
        with self.assertRaises(RuntimeError):
            require_device_substring("T4", torch_module=FakeTorch(["CPU Only"]))


if __name__ == "__main__":
    unittest.main()
