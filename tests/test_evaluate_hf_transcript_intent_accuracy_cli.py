import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_hf_transcript_intent_accuracy.py"


class EvaluateHfTranscriptIntentAccuracyCliTests(unittest.TestCase):
    def test_cli_evaluates_prediction_intents_by_audio_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            predictions = root / "predictions.json"
            predictions.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "model_dir": "outputs/model_artifacts/test_model",
                            "transcript_field": "predicted_transcript",
                            "input_jsonl": "predictions.jsonl",
                        },
                        "summary": {},
                        "records": [
                            {
                                "id": "audio_001",
                                "split": "validation",
                                "transcript_field": "predicted_transcript",
                                "transcript": "Inspect crops before noon.",
                                "span_intent_assembly": {
                                    "action": "inspect",
                                    "count": None,
                                    "location": None,
                                    "target": "crops",
                                    "constraints": ["before noon"],
                                },
                                "hybrid_span_parser": {
                                    "action": "inspect",
                                    "count": None,
                                    "location": None,
                                    "target": "crops",
                                    "constraints": ["before noon"],
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gold = root / "gold.jsonl"
            gold.write_text(
                json.dumps(
                    {
                        "id": "audio_001_intent",
                        "audio_id": "audio_001",
                        "text": "Inspect crops before noon.",
                        "split": "validation",
                        "source": "unit_test",
                        "data_type": "human_verified_audio_intent_command",
                        "label_source": "human_reviewed_v1",
                        "review_status": "human_reviewed",
                        "expected_intent": {
                            "action": "inspect",
                            "count": None,
                            "location": None,
                            "target": "crops",
                            "constraints": ["before noon"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "evaluation.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--predictions",
                    str(predictions),
                    "--gold-commands",
                    str(gold),
                    "--output",
                    str(output),
                    "--include-deterministic",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("hybrid_span_parser", completed.stdout)
        self.assertEqual(result["summary"]["hybrid_span_parser"]["exact_record_accuracy"], 1.0)
        self.assertEqual(result["summary"]["span_intent_assembly"]["field_accuracy"], 1.0)
        self.assertIn("deterministic_v3", result["summary"])
        self.assertEqual(result["records"][0]["gold_record_id"], "audio_001_intent")
        self.assertEqual(result["metadata"]["unmatched_prediction_ids"], [])

    def test_cli_rejects_draft_gold_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            predictions = root / "predictions.json"
            predictions.write_text(
                json.dumps(
                    {
                        "metadata": {},
                        "records": [
                            {
                                "id": "audio_001",
                                "transcript": "Inspect crops.",
                                "span_intent_assembly": {},
                                "hybrid_span_parser": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gold = root / "gold.jsonl"
            gold.write_text(
                json.dumps(
                    {
                        "id": "audio_001_intent",
                        "audio_id": "audio_001",
                        "text": "Inspect crops.",
                        "data_type": "human_recorded_audio_intent_draft",
                        "label_source": "deterministic_v1_draft",
                        "review_status": "needs_human_review",
                        "expected_intent": {
                            "action": "inspect",
                            "count": None,
                            "location": None,
                            "target": "crops",
                            "constraints": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--predictions",
                    str(predictions),
                    "--gold-commands",
                    str(gold),
                    "--output",
                    str(root / "evaluation.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("draft labels cannot be used", completed.stderr)


if __name__ == "__main__":
    unittest.main()
