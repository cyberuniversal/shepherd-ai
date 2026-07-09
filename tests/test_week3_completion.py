import unittest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week3_completion import (  # noqa: E402
    build_week3_completion_audit,
    render_week3_completion_markdown,
)

ACCEPTANCE_CRITERIA = {
    "scope": "synthetic_week3_completion_gate_v1",
    "not_real_world_benchmark": True,
    "thresholds": {
        "synthetic_exact_record_accuracy_min": 1.0,
        "synthetic_reference_accuracy_min": 1.0,
        "dataset_validation_records_min": 1,
        "main_map_coverage_fraction_min": 1.0,
        "coverage_warnings_max": 0,
        "ambiguous_reference_count_min": 1,
        "unresolved_reference_count_min": 1,
        "restricted_records_min": 1,
        "obstacle_records_min": 1,
        "polygon_records_min": 1,
    },
}
RESEARCH_DEFERRALS = {
    "scope": "week3_research_deferrals_v1",
    "deferrals": {
        "real_map_or_public_benchmark_provenance_exists": {
            "status": "deferred_for_week3",
            "reason": "custom simulation map is sufficient for the synthetic Week 3 gate",
        }
    },
}


class Week3CompletionTests(unittest.TestCase):
    def test_completion_audit_blocks_advancement_when_research_gates_are_missing(self) -> None:
        audit = build_week3_completion_audit(
            map_validation={
                "records": 20,
                "restricted_records": [{"id": "zone"}],
                "obstacle_records": [{"id": "obs"}],
            },
            region_map_validation={"geometry_counts": {"polygon": 2}},
            grounding_evaluations=[
                {
                    "summary": {
                        "records": 2,
                        "exact_record_matches": 2,
                        "exact_record_accuracy": 1.0,
                        "reference_matches": 4,
                        "total_references": 4,
                        "reference_accuracy": 1.0,
                    }
                }
            ],
            grounding_dataset_validations=[
                {
                    "records": 2,
                    "ambiguous_reference_count": 1,
                    "unresolved_reference_count": 1,
                    "data_type_counts": {"synthetic_grounding_example": 2},
                }
            ],
            coverage_report={
                "map_records": 2,
                "covered_location_ids": ["a", "b"],
                "warnings": [],
            },
            week3_status={
                "readiness": {
                    "development_handoff_ready": True,
                    "reason": "synthetic_grounding_slice_has_validation_evaluation_clarification_and_resolution_artifacts",
                }
            },
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
        )
        payload = audit.to_dict()

        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertFalse(payload["research_gates_passed"])
        self.assertFalse(payload["advancement_allowed"])
        self.assertIn("human_collected_grounding_benchmark_exists", payload["blockers"])
        self.assertNotIn("formal_acceptance_threshold_defined", payload["blockers"])
        self.assertNotIn("real_map_or_public_benchmark_provenance_exists", payload["blockers"])

    def test_completion_markdown_lists_decision_and_blockers(self) -> None:
        audit = build_week3_completion_audit(
            map_validation={"records": 0, "restricted_records": [], "obstacle_records": []},
            region_map_validation={"geometry_counts": {}},
            grounding_evaluations=[],
            grounding_dataset_validations=[],
            coverage_report={"map_records": 0, "covered_location_ids": [], "warnings": []},
            week3_status={"readiness": {"development_handoff_ready": False}},
        )

        markdown = render_week3_completion_markdown(audit)

        self.assertIn("Week 3 Completion Gate Audit", markdown)
        self.assertIn("Advancement allowed", markdown)
        self.assertIn("human_collected_grounding_benchmark_exists", markdown)

    def test_completion_audit_accepts_filled_human_grounding_benchmark_evidence(self) -> None:
        audit = build_week3_completion_audit(
            map_validation={
                "records": 20,
                "restricted_records": [{"id": "zone"}],
                "obstacle_records": [{"id": "obs"}],
            },
            region_map_validation={"geometry_counts": {"polygon": 2}},
            grounding_evaluations=[
                {
                    "summary": {
                        "records": 2,
                        "exact_record_matches": 2,
                        "exact_record_accuracy": 1.0,
                        "reference_matches": 4,
                        "total_references": 4,
                        "reference_accuracy": 1.0,
                    }
                }
            ],
            grounding_dataset_validations=[
                {
                    "records": 2,
                    "ambiguous_reference_count": 1,
                    "unresolved_reference_count": 1,
                    "data_type_counts": {"synthetic_grounding_example": 2},
                }
            ],
            coverage_report={
                "map_records": 2,
                "covered_location_ids": ["a", "b"],
                "warnings": [],
            },
            week3_status={
                "readiness": {
                    "development_handoff_ready": True,
                    "reason": "synthetic_grounding_slice_has_validation_evaluation_clarification_and_resolution_artifacts",
                }
            },
            acceptance_criteria=ACCEPTANCE_CRITERIA,
            research_deferrals=RESEARCH_DEFERRALS,
            human_grounding_dataset_validation={
                "records": 22,
                "data_type_counts": {"human_written_grounding_benchmark": 22},
            },
            human_grounding_evaluation={
                "summary": {
                    "records": 22,
                    "exact_record_matches": 22,
                    "reference_matches": 44,
                    "total_references": 44,
                }
            },
        )
        payload = audit.to_dict()

        self.assertTrue(payload["research_gates_passed"])
        self.assertTrue(payload["advancement_allowed"])
        self.assertNotIn("human_collected_grounding_benchmark_exists", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
