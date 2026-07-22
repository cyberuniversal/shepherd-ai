import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_evaluation import (  # noqa: E402
    build_week8_end_to_end_evaluation,
    render_week8_demonstration_log,
    render_week8_mission_report,
)


class Week8EndToEndEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulation = {
            "preparation": {
                "preparation_elapsed_seconds": 0.1,
                "clause_results": [
                    {
                        "clause_id": "clause_001",
                        "effective_grounded_intent": {
                            "references": [
                                {"status": "grounded", "location": {"id": "loc_north_field"}}
                            ]
                        },
                    },
                    {
                        "clause_id": "clause_002",
                        "effective_grounded_intent": {
                            "references": [
                                {"status": "grounded", "location": {"id": "loc_east_field"}}
                            ]
                        },
                    },
                ],
                "schedule": {
                    "assignments": [{}, {}, {}],
                    "metrics": {"assigned_tasks": 3, "total_tasks": 3},
                },
                "safety_report": {"status": "approved"},
            },
            "simulation": {
                "status": "completed",
                "wall_clock_seconds": 0.2,
                "telemetry_records": 43,
                "events": [{"time_min": 0, "event": "phase_changed", "phase": "outbound"}],
            },
        }
        self.asr = {
            "inference_elapsed_seconds": 1.0,
            "metrics": {"word_error_rate": 0.0, "exact_match": True},
        }
        self.intent = {
            "exact_match_accuracy": 0.5,
            "exact_match_denominator": 2,
            "model": {"inference_elapsed_seconds": 0.3},
        }
        self.vision = {
            "metrics": {
                "name": "mission_class_modified_mean_iou",
                "primary_value": 0.25,
                "denominator": 4,
                "image_denominator": 8,
            },
            "inference": {"elapsed_seconds": 2.0},
        }

    def test_builds_all_five_metrics_without_inventing_thresholds(self) -> None:
        result = build_week8_end_to_end_evaluation(
            simulation=self.simulation,
            asr_evidence=self.asr,
            intent_evaluation=self.intent,
            vision_evaluation=self.vision,
        )

        self.assertEqual(len(result["metrics"]), 5)
        self.assertEqual(result["metrics"]["intent_extraction_accuracy"]["value"], 0.5)
        self.assertEqual(result["metrics"]["grounding_accuracy"]["value"], 1.0)
        self.assertEqual(result["metrics"]["scheduling_quality"]["value"], 1.0)
        self.assertAlmostEqual(result["metrics"]["overall_execution_time"]["value"], 3.6)
        self.assertFalse(result["physical_flight_claimed"])

    def test_rejects_missing_stage_timing(self) -> None:
        self.asr["inference_elapsed_seconds"] = None
        with self.assertRaisesRegex(ValueError, "ASR inference time"):
            build_week8_end_to_end_evaluation(
                simulation=self.simulation,
                asr_evidence=self.asr,
                intent_evaluation=self.intent,
                vision_evaluation=self.vision,
            )

    def test_report_and_log_are_traceable_summaries(self) -> None:
        result = build_week8_end_to_end_evaluation(
            simulation=self.simulation,
            asr_evidence=self.asr,
            intent_evaluation=self.intent,
            vision_evaluation=self.vision,
        )
        self.assertIn("intent_extraction_accuracy", render_week8_mission_report(result))
        self.assertIn("phase=outbound", render_week8_demonstration_log(self.simulation, result))


if __name__ == "__main__":
    unittest.main()
