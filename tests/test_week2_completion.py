from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week2_completion import (  # noqa: E402
    build_week2_completion_audit,
    render_week2_completion_markdown,
)


CRITERIA = {
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


class Week2CompletionTests(unittest.TestCase):
    def test_audit_blocks_without_fresh_benchmark(self) -> None:
        audit = build_week2_completion_audit(
            status_summary=_status(),
            performance_risk_audit=_risk(),
            handoff=_handoff(),
            fresh_manifest_audit=None,
            fresh_intent_review_summary=None,
            fresh_asr_evaluation=None,
            fresh_intent_evaluation=None,
            acceptance_criteria=CRITERIA,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertFalse(payload["research_gates_passed"])
        self.assertFalse(payload["advancement_allowed"])
        self.assertIn("fresh_post_development_manifest_non_overlapping", payload["blockers"])
        self.assertIn("fresh_asr_evaluation_recorded", payload["blockers"])

    def test_audit_allows_when_clean_fresh_benchmark_exists(self) -> None:
        audit = build_week2_completion_audit(
            status_summary=_status(),
            performance_risk_audit=_risk(),
            handoff=_handoff(),
            fresh_manifest_audit=_fresh_manifest(),
            fresh_intent_review_summary=_fresh_review(),
            fresh_asr_evaluation=_fresh_asr(),
            fresh_intent_evaluation=_fresh_intent_eval(),
            acceptance_criteria=CRITERIA,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertTrue(payload["research_gates_passed"])
        self.assertTrue(payload["advancement_allowed"])
        self.assertEqual([], payload["blockers"])

    def test_markdown_reports_blockers(self) -> None:
        audit = build_week2_completion_audit(
            status_summary=_status(),
            performance_risk_audit=_risk(),
            handoff=_handoff(),
            fresh_manifest_audit=None,
            fresh_intent_review_summary=None,
            fresh_asr_evaluation=None,
            fresh_intent_evaluation=None,
            acceptance_criteria=CRITERIA,
        )

        markdown = render_week2_completion_markdown(audit)

        self.assertIn("Week 2 Completion Gate Audit", markdown)
        self.assertIn("fresh_asr_evaluation_recorded", markdown)
        self.assertIn("Advancement allowed", markdown)


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
        "metadata": {"note": "Week 2 NLP handoff contract. This is a development handoff."},
        "handoff_contract": {
            "intent_schema": {
                "action": "string",
                "count": "integer",
                "location": "string",
                "target": "string",
                "constraints": "list",
            },
            "not_yet_handoff_primary": {
                "transformer_span_paths": ["span_intent_assembly", "hybrid_span_parser"]
            },
        },
        "week2_carry_forward_debt": [
            "Validate deterministic_v3 on a fresh non-overlapping audio/text packet before treating it as generalized."
        ],
    }


def _fresh_manifest() -> dict:
    return {
        "summary": {
            "records": 30,
            "overlap_records": 0,
            "duplicate_transcripts_within_candidate": 0,
            "passes_non_overlap_policy": True,
        }
    }


def _fresh_review() -> dict:
    return {
        "summary": {
            "records": 30,
            "ready_for_gold_evaluation": True,
            "draft_records": 0,
            "not_reviewed_records": 0,
        }
    }


def _fresh_asr() -> dict:
    return {"summary": {"records": 30, "exact_match_accuracy": 0.7, "mean_word_error_rate": 0.05}}


def _fresh_intent_eval() -> dict:
    return {"summary": {"records": 30}, "systems": ["deterministic_v3", "trained_nb", "hybrid_span_parser"]}


if __name__ == "__main__":
    unittest.main()
