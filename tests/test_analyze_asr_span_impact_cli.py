import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import build_spans_from_phrases  # noqa: E402
from shepherd_ai.span_training import records_from_span_commands, save_span_tagger, train_span_tagger  # noqa: E402

SCRIPT = ROOT / "scripts" / "analyze_asr_span_impact.py"


class AnalyzeAsrSpanImpactCliTests(unittest.TestCase):
    def test_cli_reports_asr_span_prediction_impact_without_claiming_asr_gold_accuracy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")

            transcript = "Send two drones west but keep them below fifty meters."
            manifest = audio_dir / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": transcript,
                        "source": "test",
                        "data_type": "human_recorded_audio",
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            predictions = root / "predictions.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "expected_transcript": transcript,
                        "predicted_transcript": "Send two drones west, but keep them below 50 meters.",
                        "model_name": "whisper",
                        "model_version": "base",
                        "parameters": {},
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            span_dataset = root / "span_commands.jsonl"
            span_dataset.write_text(
                json.dumps(
                    {
                        "id": "span_001",
                        "text": transcript,
                        "split": "test",
                        "source": "test",
                        "data_type": "human_verified_span_command",
                        "spans": build_spans_from_phrases(
                            transcript,
                            [
                                ("action", "Send"),
                                ("count", "two drones"),
                                ("location", "west"),
                                ("constraint", "keep them below fifty meters"),
                            ],
                        ),
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            model_path = root / "span_model.json"
            save_span_tagger(
                train_span_tagger(records_from_span_commands(span_dataset), model_name="test_span_nb"),
                model_path,
            )
            output = root / "span_impact.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--predictions",
                    str(predictions),
                    "--span-dataset",
                    str(span_dataset),
                    "--model",
                    str(model_path),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"matched_audio_records"', completed.stdout)
        self.assertEqual(result["summary"]["matched_audio_records"], 1)
        self.assertEqual(result["summary"]["unmatched_audio_ids"], [])
        self.assertEqual(result["records"][0]["split"], "test")
        self.assertEqual(result["records"][0]["normalized_word_changed"], True)
        self.assertIn("not ASR span accuracy", result["metadata"]["evaluation_note"])
        self.assertIn("human_transcript_span_accuracy", result["summary"])


if __name__ == "__main__":
    unittest.main()
