import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import (  # noqa: E402
    AudioManifestError,
    evaluate_transcripts,
    load_audio_manifest,
    word_error_details,
    word_error_rate,
)


class AudioManifestTests(unittest.TestCase):
    def test_loads_valid_audio_manifest_record(self) -> None:
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
                        "transcript": "Send two drones north and inspect the crops.",
                        "source": "self_recorded",
                        "data_type": "human_recorded_audio",
                        "split": "example",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = load_audio_manifest(manifest, dataset_root=root)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].id, "audio_001")
            self.assertEqual(records[0].audio_path, audio)
            self.assertEqual(records[0].transcript, "Send two drones north and inspect the crops.")
            self.assertEqual(records[0].split, "example")

    def test_rejects_manifest_record_outside_dataset_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "bad",
                        "audio_path": "../outside.wav",
                        "transcript": "Return all drones.",
                        "source": "test",
                        "data_type": "synthetic",
                        "split": "example",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(AudioManifestError):
                load_audio_manifest(manifest, dataset_root=root)

    def test_word_error_rate_counts_insertions_deletions_and_substitutions(self) -> None:
        self.assertAlmostEqual(word_error_rate("send two drones north", "send drones east now"), 0.75)
        self.assertEqual(word_error_rate("", ""), 0.0)
        self.assertEqual(word_error_rate("", "extra words"), 1.0)

    def test_word_error_details_reports_alignment_operations(self) -> None:
        details = word_error_details(
            "Send two drones west but keep them below fifty meters.",
            "Send two drones west, but keep them below 50 meters.",
        )

        self.assertAlmostEqual(details["word_error_rate"], 0.1)
        self.assertEqual(details["edit_distance"], 1)
        self.assertIn(
            {
                "operation": "substitute",
                "reference_index": 8,
                "hypothesis_index": 8,
                "reference": "fifty",
                "hypothesis": "50",
            },
            details["operations"],
        )

    def test_evaluate_transcripts_reports_per_record_and_summary(self) -> None:
        expected = {
            "audio_001": "Send two drones north.",
            "audio_002": "Return all drones.",
        }
        predicted = {
            "audio_001": "Send drones north.",
            "audio_002": "Return all drones.",
        }

        result = evaluate_transcripts(expected, predicted, model_name="cached-transcript")

        self.assertEqual(result["metadata"]["model_name"], "cached-transcript")
        self.assertEqual(result["summary"]["records"], 2)
        self.assertAlmostEqual(result["records"][0]["word_error_rate"], 0.25)
        self.assertAlmostEqual(result["summary"]["mean_word_error_rate"], 0.125)


if __name__ == "__main__":
    unittest.main()
