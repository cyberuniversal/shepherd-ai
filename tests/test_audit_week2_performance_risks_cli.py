import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent_training import load_labeled_commands, save_intent_model, train_intent_model  # noqa: E402
from shepherd_ai.span_annotations import build_spans_from_phrases  # noqa: E402

SCRIPT = ROOT / "scripts" / "audit_week2_performance_risks.py"


class AuditWeek2PerformanceRisksCliTests(unittest.TestCase):
    def test_cli_reports_overlap_and_hybrid_model_risks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "Send two drones west but keep them below fifty meters."
            commands = root / "commands.jsonl"
            commands.write_text(
                json.dumps(
                    {
                        "id": "cmd_001",
                        "text": text,
                        "split": "train",
                        "source": "manual",
                        "data_type": "human_written_command_assistant_labeled",
                        "label_source": "assistant_curated_v1_from_user_text",
                        "expected_intent": {
                            "action": "send",
                            "count": 2,
                            "location": "west",
                            "target": None,
                            "constraints": ["keep them below fifty meters"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            spans = root / "spans.jsonl"
            spans.write_text(
                json.dumps(
                    {
                        "id": "span_001",
                        "text": text,
                        "split": "train",
                        "source": "manual_week2_span_annotation_v2",
                        "data_type": "human_verified_span_command",
                        "spans": build_spans_from_phrases(
                            text,
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
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_001.wav").write_bytes(b"RIFF")
            manifest = audio_dir / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "audio_001",
                        "audio_path": "datasets/sample_audio/audio_001.wav",
                        "transcript": text,
                        "source": "manual",
                        "data_type": "human_recorded_audio",
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            status = root / "status.json"
            status.write_text(
                json.dumps({"headline": {"audio_records": 1}}),
                encoding="utf-8",
            )
            model_path = root / "intent_model.json"
            save_intent_model(
                train_intent_model(
                    load_labeled_commands(commands),
                    model_name="test_hybrid",
                    use_rule_overrides=True,
                ),
                model_path,
            )
            output_json = root / "audit.json"
            output_markdown = root / "audit.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--commands",
                    str(commands),
                    "--spans",
                    str(spans),
                    "--audio-manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--status-summary",
                    str(status),
                    "--intent-model",
                    str(model_path),
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

            audit = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_markdown.read_text(encoding="utf-8")

        risk_ids = {risk["id"] for risk in audit["risk_factors"]}
        self.assertIn('"risk_factor_count"', completed.stdout)
        self.assertIn("audio_text_overlap", risk_ids)
        self.assertIn("audio_span_overlap", risk_ids)
        self.assertIn("assistant_curated_intent_labels", risk_ids)
        self.assertIn("hybrid_intent_model", risk_ids)
        self.assertIn("Week 2 Performance Risk Audit", markdown)


if __name__ == "__main__":
    unittest.main()
