import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_week2_status.py"


class SummarizeWeek2StatusCliTests(unittest.TestCase):
    def test_cli_builds_json_and_markdown_status_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = _write_json(
                root / "audio.json",
                {
                    "metadata": {
                        "model_name": "whisper",
                        "model_version": "base",
                        "parameters": {"device_metadata": {"cuda_device_names": ["Test GPU"]}},
                    },
                    "summary": {
                        "records": 2,
                        "exact_match_accuracy": 0.5,
                        "mean_word_error_rate": 0.25,
                    },
                },
            )
            intent_accuracy = _write_json(
                root / "intent_accuracy.json",
                {
                    "summary": {
                        "deterministic_v1:human_transcript": {"exact_record_accuracy": 1.0},
                        "deterministic_v1:asr_transcript": {"exact_record_accuracy": 0.5},
                        "trained_nb_human_curated_v2:human_transcript": {"exact_record_accuracy": 1.0},
                        "trained_nb_human_curated_v2:asr_transcript": {"exact_record_accuracy": 0.5},
                    }
                },
            )
            intent_impact = _write_json(
                root / "intent_impact.json",
                {
                    "summary": {
                        "deterministic_v1": {"canonical_constraint_changed_records": 0},
                        "trained_nb_human_curated_v2": {"canonical_constraint_changed_records": 0},
                    }
                },
            )
            span_impact = _write_json(
                root / "span_impact.json",
                {
                    "summary": {
                        "human_transcript_span_accuracy": {"entity_f1": 0.75},
                        "span_prediction_changed_records": 1,
                        "semantic_span_prediction_changed_records": 0,
                    }
                },
            )
            hf_metrics = _write_json(
                root / "hf_metrics.json",
                {
                    "metadata": {"runtime": {"cuda_device_names": ["Tesla T4"]}},
                    "metrics": {
                        "eval_entity_f1": 0.8,
                        "eval_entity_precision": 0.7,
                        "eval_entity_recall": 0.9,
                    },
                },
            )
            hf_errors = _write_json(
                root / "hf_errors.json",
                {
                    "false_positive_entity_counts": {"target": 1},
                    "false_negative_entity_counts": {"constraint": 1},
                    "worst_records": [{"id": "cmd_001"}],
                },
            )
            output_json = root / "summary.json"
            output_markdown = root / "summary.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--audio-evaluation",
                    str(audio),
                    "--intent-accuracy",
                    str(intent_accuracy),
                    "--intent-impact",
                    str(intent_impact),
                    "--span-impact",
                    str(span_impact),
                    "--hf-token-metrics",
                    str(hf_metrics),
                    "--hf-token-error-analysis",
                    str(hf_errors),
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_markdown),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_markdown.read_text(encoding="utf-8")

        self.assertIn('"asr_exact_match_accuracy"', completed.stdout)
        self.assertEqual(summary["headline"]["audio_records"], 2)
        self.assertEqual(summary["headline"]["colab_t4_distilbert_error_records"], 1)
        self.assertIn("Week 2 Status Summary", markdown)
        self.assertIn("not a final benchmark", summary["metadata"]["status_note"])


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
