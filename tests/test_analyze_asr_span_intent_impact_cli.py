import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_asr_span_intent_impact.py"


class AnalyzeAsrSpanIntentImpactCliTests(unittest.TestCase):
    def test_cli_reports_intent_changes_from_span_predictions_without_gold_asr_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            span_impact = root / "span_impact.json"
            span_impact.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "model_name": "span_nb_v1",
                            "model_version": "0.2",
                        },
                        "records": [
                            {
                                "id": "audio_001",
                                "split": "test",
                                "span_record_id": "span_001",
                                "human_transcript": "Send two drones north and inspect crops.",
                                "asr_transcript": "Send two drones north and inspect crops.",
                                "raw_transcript_changed": False,
                                "normalized_word_changed": False,
                                "semantic_span_prediction_changed": False,
                                "human_predicted_entities": [
                                    {"field": "action", "start": 0, "end": 4},
                                    {"field": "count", "start": 5, "end": 15},
                                    {"field": "location", "start": 16, "end": 21},
                                    {"field": "action", "start": 26, "end": 33},
                                    {"field": "target", "start": 34, "end": 39},
                                ],
                                "asr_predicted_entities": [
                                    {"field": "action", "start": 0, "end": 4},
                                    {"field": "count", "start": 5, "end": 15},
                                    {"field": "location", "start": 16, "end": 21},
                                    {"field": "action", "start": 26, "end": 33},
                                    {"field": "target", "start": 34, "end": 39},
                                ],
                            },
                            {
                                "id": "audio_002",
                                "split": "test",
                                "span_record_id": "span_002",
                                "human_transcript": "Keep one drone below fifty meters.",
                                "asr_transcript": "Keep one drone below 50 meters.",
                                "raw_transcript_changed": True,
                                "normalized_word_changed": True,
                                "semantic_span_prediction_changed": True,
                                "human_predicted_entities": [
                                    {"field": "count", "start": 5, "end": 14},
                                    {"field": "constraint", "start": 15, "end": 33},
                                ],
                                "asr_predicted_entities": [
                                    {"field": "count", "start": 5, "end": 14},
                                    {"field": "constraint", "start": 15, "end": 30},
                                ],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "span_intent_impact.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--span-impact",
                    str(span_impact),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("span_intent_assembly", completed.stdout)
        self.assertIn("not gold ASR intent accuracy", result["metadata"]["evaluation_note"])
        self.assertIn("hybrid_span_parser", result["summary"])
        self.assertEqual(result["summary"]["span_intent_assembly"]["records"], 2)
        self.assertEqual(result["summary"]["span_intent_assembly"]["intent_changed_records"], 1)
        self.assertEqual(result["summary"]["span_intent_assembly"]["field_change_counts"], {"constraints": 1})


if __name__ == "__main__":
    unittest.main()
