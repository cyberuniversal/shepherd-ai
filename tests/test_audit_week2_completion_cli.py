import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week2_completion.py"


class AuditWeek2CompletionCliTests(unittest.TestCase):
    def test_cli_writes_blocking_audit_when_fresh_files_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            risk = root / "risk.json"
            handoff = root / "handoff.json"
            criteria = root / "criteria.json"
            output_json = root / "audit.json"
            output_md = root / "audit.md"

            status.write_text(json.dumps(_status()), encoding="utf-8")
            risk.write_text(json.dumps(_risk()), encoding="utf-8")
            handoff.write_text(json.dumps(_handoff()), encoding="utf-8")
            criteria.write_text(json.dumps(_criteria()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--status-summary",
                    str(status),
                    "--performance-risk-audit",
                    str(risk),
                    "--handoff",
                    str(handoff),
                    "--fresh-manifest-audit",
                    str(root / "missing_manifest_audit.json"),
                    "--fresh-intent-review-summary",
                    str(root / "missing_review_summary.json"),
                    "--fresh-asr-evaluation",
                    str(root / "missing_asr.json"),
                    "--fresh-intent-evaluation",
                    str(root / "missing_intent.json"),
                    "--acceptance-criteria",
                    str(criteria),
                    "--json-output",
                    str(output_json),
                    "--markdown-output",
                    str(output_md),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            audit = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertIn("advancement_allowed", completed.stdout)
        self.assertFalse(audit["advancement_allowed"])
        self.assertIn("fresh_asr_evaluation_recorded", audit["blockers"])
        self.assertIn("Week 2 Completion Gate Audit", markdown)


def _status() -> dict:
    return {
        "headline": {
            "audio_records": 10,
            "asr_exact_match_accuracy": 0.9,
            "asr_mean_word_error_rate": 0.01,
            "colab_t4_distilbert_test_entity_f1": 0.78,
            "trained_human_intent_exact_accuracy": 1.0,
        }
    }


def _risk() -> dict:
    return {"summary": {"risk_factor_count": 4, "command_records": 50, "span_records": 85}}


def _handoff() -> dict:
    return {
        "metadata": {"note": "development handoff"},
        "handoff_contract": {
            "intent_schema": {
                "action": "string",
                "count": "int",
                "location": "string",
                "target": "string",
                "constraints": "list",
            },
            "not_yet_handoff_primary": {"transformer_span_paths": ["span_intent_assembly"]},
        },
        "week2_carry_forward_debt": [
            "Validate deterministic_v3 on a fresh non-overlapping audio/text packet before treating it as generalized."
        ],
    }


def _criteria() -> dict:
    return {
        "scope": "week2_clean_post_development_completion_gate_v1",
        "not_final_end_to_end_benchmark": True,
        "thresholds": {
            "fresh_audio_records_min": 30,
            "fresh_manifest_overlap_records_max": 0,
            "fresh_manifest_duplicate_transcripts_max": 0,
            "fresh_intent_review_ready_required": True,
            "fresh_asr_records_min": 30,
            "fresh_intent_eval_records_min": 30,
            "fresh_intent_systems_min": 3,
        },
    }


if __name__ == "__main__":
    unittest.main()
