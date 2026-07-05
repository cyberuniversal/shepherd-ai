import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_asr_intent_impact.py"


class AnalyzeAsrIntentImpactCliTests(unittest.TestCase):
    def test_cli_reports_transcript_change_with_constraint_impact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")
            manifest = audio_dir / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": "Send two drones west but keep them below fifty meters.",
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
                        "expected_transcript": "Send two drones west but keep them below fifty meters.",
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
            output = root / "impact.json"

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
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            impact = json.loads(output.read_text(encoding="utf-8"))

        summary = impact["summary"]["deterministic_v1"]
        self.assertIn('"intent_changed_records"', completed.stdout)
        self.assertEqual(summary["raw_transcript_changed_records"], 1)
        self.assertEqual(summary["normalized_word_changed_records"], 1)
        self.assertEqual(summary["intent_changed_records"], 1)
        self.assertEqual(summary["changed_field_counts"], {"constraints": 1})
        self.assertEqual(summary["semantic_intent_changed_records"], 0)
        self.assertEqual(summary["canonical_constraint_changed_records"], 0)
        self.assertEqual(summary["normalized_changed_field_counts"], {})
        self.assertEqual(summary["unchanged_intent_when_normalized_word_changed"], 0)
        self.assertEqual(summary["unchanged_semantic_intent_when_normalized_word_changed"], 1)
        self.assertEqual(summary["unchanged_canonical_constraint_when_normalized_word_changed"], 1)
        self.assertEqual(
            impact["records"][0]["human_canonical_constraints"][0]["value"],
            impact["records"][0]["asr_canonical_constraints"][0]["value"],
        )
        self.assertEqual(impact["records"][0]["split"], "test")


if __name__ == "__main__":
    unittest.main()
