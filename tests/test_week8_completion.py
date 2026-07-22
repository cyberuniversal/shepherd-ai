import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_completion import (  # noqa: E402
    ROADMAP_COMMAND,
    build_week8_completion_audit,
    render_week8_completion_markdown,
)


class Week8CompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulation = json.loads(
            (ROOT / "outputs/evaluations/week8_roadmap_scenario_simulation.json").read_text(
                encoding="utf-8"
            )
        )

    def test_current_evidence_blocks_completion_without_fabricating_inputs(self) -> None:
        audit = build_week8_completion_audit(
            simulation=self.simulation,
            asr_evidence=None,
            intent_evaluation=None,
            vision_evaluation=None,
            evaluation_summary=None,
            artifact_status={
                "raw_run": True,
                "telemetry": True,
                "animated_map": True,
            },
        )

        self.assertFalse(audit.completion_allowed)
        self.assertNotIn("software_simulation_completed", audit.blockers)
        self.assertIn("exact_scenario_asr_evidence", audit.blockers)
        self.assertIn("trained_two_clause_intent_evaluation", audit.blockers)
        self.assertIn("mission_assigned_vision_evaluation", audit.blockers)
        self.assertIn("all_roadmap_metrics_reported", audit.blockers)
        self.assertIn("raw_and_derived_artifacts_present", audit.blockers)

    def test_complete_synthetic_contract_fixture_passes_all_gates(self) -> None:
        asr = {
            "scenario_source": "roadmap_week8_fixed_scenario",
            "reference_transcript": ROADMAP_COMMAND,
            "predicted_transcript": ROADMAP_COMMAND,
            "audio": {
                "path": "private/week8.wav",
                "sha256": "a" * 64,
                "data_type": "human_recorded_audio",
            },
            "model": {"name": "whisper", "version": "base"},
        }
        intent = {
            "scenario_source": "roadmap_week8_fixed_scenario",
            "model_role": "frozen_trained_checkpoint",
            "exact_match_accuracy": 1.0,
            "records": [
                {"id": "clause_001", "gold_source": "roadmap_specification"},
                {"id": "clause_002", "gold_source": "roadmap_specification"},
            ],
        }
        vision = {
            "scenario_source": "roadmap_week8_fixed_scenario",
            "manifest": {
                "records": 2,
                "clause_ids": ["clause_001", "clause_002"],
                "records_with_sha256": 2,
                "records_with_labels": 2,
            },
            "model": {"sha256": "b" * 64},
            "metrics": {"primary_value": 0.5, "denominator": 2},
        }
        evaluation = {
            "metrics": {
                name: {"value": 1.0, "denominator": 1}
                for name in (
                    "intent_extraction_accuracy",
                    "grounding_accuracy",
                    "scheduling_quality",
                    "detection_performance",
                    "overall_execution_time",
                )
            },
            "physical_flight_claimed": False,
            "safety_guarantee_claimed": False,
            "novelty_claimed": False,
        }
        artifacts = {
            name: True
            for name in (
                "raw_run",
                "telemetry",
                "animated_map",
                "evaluation_summary",
                "mission_report",
                "demonstration_log",
                "demonstration_screenshot",
            )
        }

        audit = build_week8_completion_audit(
            simulation=self.simulation,
            asr_evidence=asr,
            intent_evaluation=intent,
            vision_evaluation=vision,
            evaluation_summary=evaluation,
            artifact_status=artifacts,
        )

        self.assertTrue(audit.completion_allowed)
        self.assertEqual(audit.blockers, ())

    def test_markdown_states_that_simulation_alone_is_insufficient(self) -> None:
        audit = build_week8_completion_audit(
            simulation=self.simulation,
            asr_evidence=None,
            intent_evaluation=None,
            vision_evaluation=None,
            evaluation_summary=None,
            artifact_status={},
        )

        markdown = render_week8_completion_markdown(audit)

        self.assertIn("movement simulation alone is insufficient", markdown)
        self.assertIn("Completion allowed: `false`", markdown)


if __name__ == "__main__":
    unittest.main()
