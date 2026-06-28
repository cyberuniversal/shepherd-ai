import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import AudioManifestRecord  # noqa: E402
from shepherd_ai.transcription import (  # noqa: E402
    CachedTranscriptTranscriber,
    TranscriptionResult,
    WhisperTranscriber,
    transcribe_records,
    write_transcription_output,
)


class FakeTranscriber:
    model_name = "fake-speech-model"
    model_version = "test"
    parameters = {"temperature": 0}

    def __init__(self) -> None:
        self.paths: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        self.paths.append(audio_path)
        return f"predicted transcript for {audio_path.stem}"


class FakeWhisperModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def transcribe(self, audio_path: str, **options: str) -> dict[str, str]:
        self.calls.append((audio_path, options))
        return {"text": "  Send two drones north.  "}


class FakeWhisperModule:
    __version__ = "2026.06.test"

    def __init__(self) -> None:
        self.loaded_model_name: str | None = None
        self.model = FakeWhisperModel()

    def load_model(self, model_name: str) -> FakeWhisperModel:
        self.loaded_model_name = model_name
        return self.model


class TranscriptionWorkflowTests(unittest.TestCase):
    def test_transcribe_records_calls_transcriber_for_each_audio_file(self) -> None:
        records = [
            AudioManifestRecord(
                id="audio_001",
                audio_path=Path("audio_001.wav"),
                transcript="Send two drones north.",
                source="test",
                data_type="human_recorded_audio",
                split="example",
            ),
            AudioManifestRecord(
                id="audio_002",
                audio_path=Path("audio_002.wav"),
                transcript="Return all drones.",
                source="test",
                data_type="human_recorded_audio",
                split="example",
            ),
        ]
        transcriber = FakeTranscriber()

        output = transcribe_records(records, transcriber)

        self.assertEqual(transcriber.paths, [Path("audio_001.wav"), Path("audio_002.wav")])
        self.assertEqual(output["metadata"]["model_name"], "fake-speech-model")
        self.assertEqual(output["metadata"]["model_version"], "test")
        self.assertEqual(output["metadata"]["parameters"], {"temperature": 0})
        self.assertEqual(output["summary"]["records"], 2)
        self.assertEqual(output["records"][0]["id"], "audio_001")
        self.assertEqual(output["records"][0]["predicted_transcript"], "predicted transcript for audio_001")
        self.assertEqual(output["records"][0]["expected_transcript"], "Send two drones north.")

    def test_cached_transcript_transcriber_uses_manifest_transcripts_without_model_inference(self) -> None:
        records = [
            AudioManifestRecord(
                id="audio_001",
                audio_path=Path("audio_001.wav"),
                transcript="Scan the western field.",
                source="test",
                data_type="cached_transcript",
                split="example",
            )
        ]

        output = transcribe_records(records, CachedTranscriptTranscriber.from_records(records))

        self.assertEqual(output["metadata"]["model_name"], "cached-transcript")
        self.assertEqual(output["records"][0]["predicted_transcript"], "Scan the western field.")
        self.assertEqual(output["records"][0]["word_error_rate"], 0.0)
        self.assertTrue(output["records"][0]["exact_match"])

    def test_write_transcription_output_persists_raw_json(self) -> None:
        result = TranscriptionResult(
            id="audio_001",
            audio_path=Path("audio_001.wav"),
            expected_transcript="Return all drones.",
            predicted_transcript="Return all drones.",
            word_error_rate=0.0,
            exact_match=True,
        )
        payload = {
            "metadata": {"model_name": "cached-transcript"},
            "summary": {"records": 1},
            "records": [result.to_dict()],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "nested" / "transcripts.json"
            write_transcription_output(payload, output_path)

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["records"][0]["id"], "audio_001")
        self.assertEqual(saved["records"][0]["audio_path"], "audio_001.wav")

    def test_whisper_transcriber_uses_injected_module_without_downloading_weights(self) -> None:
        fake_module = FakeWhisperModule()
        transcriber = WhisperTranscriber(
            model_name="tiny",
            language="en",
            whisper_module=fake_module,
        )

        transcript = transcriber.transcribe(Path("audio_001.wav"))

        self.assertEqual(fake_module.loaded_model_name, "tiny")
        self.assertEqual(fake_module.model.calls, [("audio_001.wav", {"language": "en"})])
        self.assertEqual(transcript, "Send two drones north.")
        self.assertEqual(transcriber.model_name, "whisper-tiny")
        self.assertEqual(transcriber.model_version, "2026.06.test")
        self.assertEqual(transcriber.parameters, {"model_size": "tiny", "language": "en"})


if __name__ == "__main__":
    unittest.main()
