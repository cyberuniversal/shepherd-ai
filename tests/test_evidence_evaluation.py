import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.evidence_evaluation import (  # noqa: E402
    score_clarification_recovery,
    score_decision_rows,
    workflow_status_to_decision,
)


class EvidenceEvaluationTests(unittest.TestCase):
    def test_maps_workflow_statuses_to_common_decisions(self) -> None:
        self.assertEqual(
            workflow_status_to_decision("ready_for_simulated_execution"),
            "proceed",
        )
        self.assertEqual(
            workflow_status_to_decision("clarification_required"),
            "clarify",
        )
        self.assertEqual(workflow_status_to_decision("safety_rejected"), "block")

    def test_rejects_unknown_workflow_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported workflow status"):
            workflow_status_to_decision("completed")

    def test_scores_false_refusals_and_silent_misexecutions(self) -> None:
        summary = score_decision_rows(
            [
                {"expected_decision": "proceed", "predicted_decision": "block"},
                {"expected_decision": "proceed", "predicted_decision": "proceed"},
                {"expected_decision": "clarify", "predicted_decision": "proceed"},
                {"expected_decision": "block", "predicted_decision": "block"},
            ]
        )

        self.assertEqual(summary["correct_decisions"], 2)
        self.assertEqual(summary["decision_accuracy"], 0.5)
        self.assertEqual(summary["false_refusal_rate"], 0.5)
        self.assertEqual(summary["silent_misexecution_rate"], 0.5)
        self.assertEqual(summary["clarification_recall"], 0.0)
        self.assertEqual(summary["block_recall"], 1.0)

    def test_uses_null_for_metrics_without_a_denominator(self) -> None:
        summary = score_decision_rows(
            [{"expected_decision": "proceed", "predicted_decision": "proceed"}]
        )

        self.assertIsNone(summary["silent_misexecution_rate"])
        self.assertIsNone(summary["clarification_recall"])
        self.assertIsNone(summary["block_recall"])

    def test_scores_only_attempted_clarification_recovery(self) -> None:
        summary = score_clarification_recovery(
            [
                {"recovery_attempted": True, "recovery_succeeded": True},
                {"recovery_attempted": True, "recovery_succeeded": False},
                {"recovery_attempted": False, "recovery_succeeded": False},
            ]
        )

        self.assertEqual(summary["recovery_attempts"], 2)
        self.assertEqual(summary["successful_recoveries"], 1)
        self.assertEqual(summary["clarification_recovery_rate"], 0.5)

    def test_can_score_invalid_model_output_as_an_error(self) -> None:
        summary = score_decision_rows(
            [
                {
                    "expected_decision": "proceed",
                    "predicted_decision": "invalid",
                }
            ],
            allow_invalid_prediction=True,
        )

        self.assertEqual(summary["decision_accuracy"], 0.0)
        self.assertEqual(summary["false_refusal_rate"], 1.0)
        self.assertEqual(summary["invalid_prediction_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
