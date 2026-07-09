import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_week2_to_week3_handoff.py"


class CreateWeek2ToWeek3HandoffCliTests(unittest.TestCase):
    def test_cli_creates_handoff_contract_from_evaluation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intent_accuracy = _write_json(
                root / "intent_accuracy.json",
                {
                    "summary": {
                        "deterministic_v3:human_transcript": {
                            "records": 30,
                            "exact_record_accuracy": 1.0,
                        },
                        "deterministic_v3:asr_transcript": {
                            "records": 30,
                            "exact_record_accuracy": 0.9,
                        },
                    }
                },
            )
            transformer_human = _write_json(
                root / "transformer_human.json",
                {
                    "summary": {
                        "deterministic_v3": {"records": 30, "exact_record_accuracy": 1.0},
                        "hybrid_span_parser": {"records": 30, "exact_record_accuracy": 0.2},
                        "span_intent_assembly": {"records": 30, "exact_record_accuracy": 0.1},
                    }
                },
            )
            transformer_asr = _write_json(
                root / "transformer_asr.json",
                {
                    "summary": {
                        "deterministic_v3": {"records": 30, "exact_record_accuracy": 0.9},
                        "hybrid_span_parser": {"records": 30, "exact_record_accuracy": 0.15},
                        "span_intent_assembly": {"records": 30, "exact_record_accuracy": 0.1},
                    }
                },
            )
            remediation = root / "remediation.jsonl"
            remediation.write_text(
                json.dumps(
                    {
                        "id": "audio_001_span_remediation",
                        "failed_intent_fields": ["location", "target"],
                        "label_status": "needs_human_span_review",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output_json = root / "handoff.json"
            output_md = root / "handoff.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--intent-accuracy",
                    str(intent_accuracy),
                    "--transformer-human-intent-accuracy",
                    str(transformer_human),
                    "--transformer-asr-intent-accuracy",
                    str(transformer_asr),
                    "--remediation-packet",
                    str(remediation),
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_md),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            handoff = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertIn("handoff_ready_for_week3_grounding", completed.stdout)
        self.assertTrue(handoff["summary"]["handoff_ready_for_week3_grounding"])
        self.assertEqual(handoff["summary"]["provisional_primary_intent_system"], "deterministic_v3")
        self.assertFalse(handoff["summary"]["transformer_span_path_primary"])
        self.assertEqual(handoff["evidence"]["span_remediation"]["failed_field_counts"], {"location": 1, "target": 1})
        self.assertIn("Do not silently invent coordinates", markdown)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
